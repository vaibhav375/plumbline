"""Seed the Aurelle demo org. Idempotent: rows are keyed on stable IDs, and a re-run reports
0 inserted. Local only: needs DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and
DEMO_USER_PASSWORD (all from secrets.env via `make seed`)."""

import csv
import json
import os
import secrets
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SEED = Path(__file__).resolve().parents[3] / "supabase" / "seed" / "aurelle"
NS = uuid.uuid5(uuid.NAMESPACE_URL, "plumbline:aurelle")
ORG_ID = uuid.uuid5(NS, "org")
RULEBOOK_VERSION = "v1.3"


def sid(*parts) -> uuid.UUID:
    return uuid.uuid5(NS, ":".join(map(str, parts)))


def read_csv(name):
    with (SEED / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_json(name):
    return json.loads((SEED / name).read_text(encoding="utf-8"))


def split(v):
    return [x for x in v.split("|") if x] if v else []


def blank(v):
    return v if v != "" else None


def upsert(conn, table, key, rows):
    """Insert or update; returns (inserted, updated, unchanged). Unchanged rows aren't touched."""
    if not rows:
        return 0, 0, 0
    cols = list(rows[0])
    rest = [c for c in cols if c not in key]
    q = sql.SQL(
        "insert into {t} ({cols}) values ({vals}) on conflict ({key}) do update set {sets}"
        " where ({cur}) is distinct from ({new}) returning (xmax = 0)"
    ).format(
        t=sql.Identifier(table),
        cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
        vals=sql.SQL(", ").join(sql.Placeholder(c) for c in cols),
        key=sql.SQL(", ").join(map(sql.Identifier, key)),
        sets=sql.SQL(", ").join(
            sql.SQL("{c} = excluded.{c}").format(c=sql.Identifier(c)) for c in rest
        ),
        cur=sql.SQL(", ").join(
            sql.SQL("{t}.{c}").format(t=sql.Identifier(table), c=sql.Identifier(c)) for c in rest
        ),
        new=sql.SQL(", ").join(sql.SQL("excluded.{c}").format(c=sql.Identifier(c)) for c in rest),
    )
    inserted = updated = 0
    with conn.cursor() as cur:
        cur.executemany(q, rows, returning=True)
        while True:
            for (was_insert,) in cur.fetchall():
                inserted += was_insert
                updated += not was_insert
            if not cur.nextset():
                break
    return inserted, updated, len(rows) - inserted - updated


class Auth:
    """Supabase Auth admin API (service-role key). Creates users once; never resets passwords."""

    def __init__(self, url, key):
        self.http = httpx.Client(
            base_url=f"{url}/auth/v1/admin",
            timeout=20,
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        users = (
            self.http.get("/users", params={"per_page": 1000}).raise_for_status().json()["users"]
        )
        self.ids = {u["email"]: uuid.UUID(u["id"]) for u in users}
        self.created = 0

    def ensure(self, email, password, display_name):
        if email not in self.ids:
            r = self.http.post(
                "/users",
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"display_name": display_name},
                },
            )
            r.raise_for_status()
            self.ids[email] = uuid.UUID(r.json()["id"])
            self.created += 1
        return self.ids[email]


def rule_rows(rules):
    return [
        {
            "org_id": ORG_ID,
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "cls": r["cls"],
            "check_type": r["check_type"],
            "params": Jsonb(json.loads(r["params"] or "{}")),
            "severity": r["severity"],
            "tier": r["tier"],
            "maturity": r["maturity"],
            "examples_good": split(r["examples_good"]),
            "examples_bad": split(r["examples_bad"]),
            "source_ref": r["source_ref"],
            "owner_function": r["owner_function"],
        }
        for r in rules
    ]


def fact_rows():
    return [
        {
            "org_id": ORG_ID,
            "id": f["id"],
            "statement": f["statement"],
            "value": float(f["value"]) if f["value"] else None,
            "unit": blank(f["unit"]),
            "product": blank(f["product"]),
            "market": f["market"],
            "population": blank(f["population"]),
            "duration": blank(f["duration"]),
            "owner": f["owner"],
            "valid_from": f["valid_from"],
            "valid_until": blank(f["valid_until"]),
            "confidentiality": f["confidentiality"],
            "embargo_until": blank(f["embargo_until"]),
            "verified": f["verified"] == "true",
            "aliases": split(f["aliases"]),
        }
        for f in read_csv("facts.csv")
    ]


def history_rows(history, rules, author_ids, reviewer_for):
    """Expand history.json into one submitted post per decision, so every quote is in its text."""
    out = {k: [] for k in ("contents", "versions", "check_runs", "findings", "decisions")}
    authors = history["authors"]
    start = datetime.combine(date.fromisoformat(history["start_date"]), datetime.min.time(), UTC)
    n = 0
    for rule_id, spec in history["rules"].items():
        rule = rules[rule_id]
        actions = (
            ["uphold"] * spec["upheld"]
            + ["overrule"] * spec["overruled"]
            + ["dismiss"] * spec["dismissed"]
        )
        for i, action in enumerate(actions):
            author = authors[n % len(authors)]
            at = start + timedelta(hours=7 * n)
            cid, vid, rid, fid, did = (
                sid("hist", rule_id, i, k) for k in ("c", "v", "r", "f", "d")
            )
            start_ix = spec["sample"].index(spec["quote"])
            out["contents"].append(
                {
                    "id": cid,
                    "org_id": ORG_ID,
                    "title": f"[synthetic] {rule_id} sample {i + 1}",
                    "channel": "instagram",
                    "region": "IN",
                    "origin": author["origin"],
                    "created_by": author_ids[author["key"]],
                    "created_at": at,
                }
            )
            out["versions"].append(
                {
                    "id": vid,
                    "org_id": ORG_ID,
                    "content_id": cid,
                    "n": 1,
                    "text": spec["sample"],
                    "private": False,
                    "status": "approved",
                    "created_by": author_ids[author["key"]],
                    "created_at": at,
                }
            )
            out["check_runs"].append(
                {
                    "id": rid,
                    "org_id": ORG_ID,
                    "version_id": vid,
                    "report_json": Jsonb({"synthetic": True}),
                    "rulebook_version": RULEBOOK_VERSION,
                    "created_at": at,
                }
            )
            out["findings"].append(
                {
                    "id": fid,
                    "org_id": ORG_ID,
                    "run_id": rid,
                    "rule_id": rule_id,
                    "category": rule["category"],
                    "severity": rule["severity"],
                    "advisory": not (rule["tier"] == "mandatory" or rule["maturity"] == "blocking"),
                    "quote": spec["quote"],
                    "span_start": start_ix,
                    "span_end": start_ix + len(spec["quote"]),
                    "payload_json": Jsonb({"synthetic": True}),
                }
            )
            out["decisions"].append(
                {
                    "id": did,
                    "org_id": ORG_ID,
                    "finding_id": fid,
                    "actor": reviewer_for[rule["owner_function"]],
                    "action": action,
                    "reason": "synthetic",
                    "at": at + timedelta(hours=2),
                }
            )
            n += 1
    return out


def main() -> int:
    env = os.environ
    missing = [
        k
        for k in ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "DEMO_USER_PASSWORD")
        if not env.get(k)
    ]
    if missing:
        print("missing env:", ", ".join(missing), file=sys.stderr)
        return 1

    auth = Auth(env["SUPABASE_URL"].rstrip("/"), env["SUPABASE_SERVICE_ROLE_KEY"])
    users = read_json("users.json")
    history = read_json("history.json")
    ids = {
        u["key"]: auth.ensure(u["email"], env["DEMO_USER_PASSWORD"], u["display_name"])
        for u in users
    }
    for a in history["authors"]:  # never sign in; random password, discarded
        ids[a["key"]] = auth.ensure(
            f"{a['key']}@synthetic.example", secrets.token_urlsafe(24), a["name"]
        )

    rules_csv = read_csv("rules.csv")
    rules = {r["id"]: r for r in rules_csv}
    reviewer_for = {
        "brand": ids["reviewer"],
        "compliance": ids["compliance"],
        "accessibility": ids["brand_owner"],
    }
    hist = history_rows(history, rules, ids, reviewer_for)

    profiles = [
        {
            "user_id": ids[u["key"]],
            "org_id": ORG_ID,
            "display_name": u["display_name"],
            "role": u["role"],
        }
        for u in users
    ]
    profiles += [
        {"user_id": ids[a["key"]], "org_id": ORG_ID, "display_name": a["name"], "role": "creator"}
        for a in history["authors"]
    ]

    steps = [
        ("organizations", ["id"], [{"id": ORG_ID, "name": "Aurelle Skin (fictional demo)"}]),
        ("profiles", ["user_id"], profiles),
        ("rules", ["org_id", "id"], rule_rows(rules_csv)),
        ("facts", ["org_id", "id"], fact_rows()),
        (
            "approved_wordings",
            ["org_id", "id"],
            [
                {
                    "org_id": ORG_ID,
                    "id": w["id"],
                    "fact_id": w["fact_id"],
                    "market": w["market"],
                    "channel": w["channel"],
                    "text": w["text"],
                    "disclaimer": blank(w["disclaimer"]),
                }
                for w in read_csv("wordings.csv")
            ],
        ),
        (
            "terms",
            ["org_id", "id"],
            [
                {
                    "org_id": ORG_ID,
                    "id": t["id"],
                    "preferred": t["preferred"],
                    "variants": split(t["variants"]),
                }
                for t in read_csv("terms.csv")
            ],
        ),
        *(
            (t, ["id"], hist[t])
            for t in ("contents", "versions", "check_runs", "findings", "decisions")
        ),
    ]
    with psycopg.connect(env["DATABASE_URL"]) as conn:
        print(f"{'auth users':18} created {auth.created:4}  existing {len(ids) - auth.created:4}")
        for table, key, rows in steps:
            ins, upd, same = upsert(conn, table, key, rows)
            print(f"{table:18} inserted {ins:4}  updated {upd:4}  unchanged {same:4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
