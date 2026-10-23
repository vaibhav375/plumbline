"""Supabase REST (PostgREST) access, always as the caller: the anon key plus the user's own JWT,
so row-level security decides what this process can read. The service key is never loaded here."""

import hashlib
import json

import httpx

from plumbline.config import Settings
from plumbline.models import ApprovedWording, Fact, OrgContext, Rule, Term


def client_for(s: Settings, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=f"{s.supabase_url.rstrip('/')}/rest/v1",
        headers={"apikey": s.supabase_anon_key, "Authorization": f"Bearer {token}"},
        timeout=10,
    )


def fetch_profile(s: Settings, token: str, user_id: str) -> dict | None:
    with client_for(s, token) as c:
        r = c.get("/profiles", params={"user_id": f"eq.{user_id}", "select": "org_id,role"})
        r.raise_for_status()
        rows = r.json()
    return rows[0] if rows else None


def load_org_context(s: Settings, token: str, org_id: str) -> OrgContext:
    """The caller's rulebook. RLS scopes every read to their org (and hides confidential facts
    from roles that may not see them)."""
    with client_for(s, token) as c:

        def get(table: str, **params) -> list[dict]:
            r = c.get(f"/{table}", params={"select": "*", **params})
            r.raise_for_status()
            return r.json()

        rules = [Rule.model_validate(r) for r in get("rules", active="is.true", order="id")]
        facts = [Fact.model_validate(f) for f in get("facts", order="id")]
        wordings = [ApprovedWording.model_validate(w) for w in get("approved_wordings", order="id")]
        terms = [Term.model_validate(t) for t in get("terms", order="id")]
    # The version changes whenever any rule changes, so cached reports can't outlive their rulebook.
    digest = hashlib.sha256(
        json.dumps([r.model_dump() for r in rules], sort_keys=True).encode()
    ).hexdigest()
    return OrgContext(
        org_id=org_id,
        rulebook_version=f"rb-{digest[:10]}",
        rules=rules,
        facts=facts,
        wordings=wordings,
        terms=terms,
    )


def load_confidential_facts(s: Settings, org_id: str) -> list[Fact]:
    """One org's confidential and embargoed facts, through the narrow checker role (migration
    0006). They are only ever matched in code; they never reach a client or a model."""
    if not s.checker_database_url:
        return []
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(s.checker_database_url, connect_timeout=5, row_factory=dict_row) as conn:
        rows = conn.execute("select * from public.confidential_facts(%s)", (org_id,)).fetchall()
    return [Fact.model_validate(r) for r in rows]


class ReportCache:
    """run_check's cache backed by check_runs, read as the caller (RLS decides what they may reuse).
    Writes happen in save_check, which stores the key with the run."""

    def __init__(self, s: Settings, token: str):
        self.s, self.token, self.key, self._hit = s, token, None, None

    def __contains__(self, key: str) -> bool:
        with client_for(self.s, self.token) as c:
            r = c.get(
                "/check_runs",
                params={
                    "cache_key": f"eq.{key}",
                    "select": "report_json",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            r.raise_for_status()
            rows = r.json()
        self._hit = json.dumps(rows[0]["report_json"]) if rows else None
        return self._hit is not None

    def __getitem__(self, key: str) -> str:
        return self._hit

    def __setitem__(self, key: str, value: str) -> None:
        self.key = key


def get_content(s: Settings, token: str, content_id: str) -> dict | None:
    with client_for(s, token) as c:
        r = c.get(
            "/contents",
            params={"id": f"eq.{content_id}", "select": "id,org_id,title,channel,region"},
        )
        if r.status_code == 400:  # not a UUID
            return None
        r.raise_for_status()
        rows = r.json()
    return rows[0] if rows else None


def latest_version(s: Settings, token: str, content_id: str) -> dict | None:
    with client_for(s, token) as c:
        r = c.get(
            "/versions",
            params={
                "content_id": f"eq.{content_id}",
                "select": "id,n,text,doc_json,intent_json",
                "order": "n.desc",
                "limit": "1",
            },
        )
        r.raise_for_status()
        rows = r.json()
    return rows[0] if rows else None


def save_check(
    s: Settings,
    token: str,
    *,
    user_id: str,
    org_id: str,
    content_id: str | None,
    title: str,
    channel: str,
    region: str,
    origin: str,
    doc: dict,
    intent: dict,
    private: bool,
    status: str,
    report: dict,
    rulebook_version: str,
    cache_key: str | None,
    egress: list[dict],
) -> tuple[str, str, list[str]]:
    """Persist a check as the caller: content (if new), version, check run, findings, egress events.
    Returns (content_id, version_id, finding record ids in report order: findings, then needs_human)."""

    def post(c: httpx.Client, table: str, rows, one: bool = True):
        r = c.post(f"/{table}", json=rows, headers={"Prefer": "return=representation"})
        r.raise_for_status()
        return r.json()[0] if one else r.json()

    with client_for(s, token) as c:
        if content_id is None:
            content_id = post(
                c,
                "contents",
                {
                    "org_id": org_id,
                    "title": title[:120],
                    "channel": channel,
                    "region": region,
                    "origin": origin,
                    "created_by": user_id,
                },
            )["id"]
        latest = c.get(
            "/versions",
            params={
                "content_id": f"eq.{content_id}",
                "select": "n",
                "order": "n.desc",
                "limit": "1",
            },
        ).json()
        n = (latest[0]["n"] + 1) if latest else 1
        version = post(
            c,
            "versions",
            {
                "org_id": org_id,
                "content_id": content_id,
                "n": n,
                "text": doc["text"],
                "doc_json": doc,
                "intent_json": intent,
                "private": private,
                "status": status,
                "created_by": user_id,
            },
        )
        run_id = report["run_id"]
        post(
            c,
            "check_runs",
            {
                "id": run_id,
                "org_id": org_id,
                "version_id": version["id"],
                "report_json": report,
                "rulebook_version": rulebook_version,
                "models_used": report["models_used"],
                "ms_code": report["ms_code"],
                "ms_total": report["ms_total"],
                "cache_key": cache_key,
            },
        )
        rows = [
            {
                "org_id": org_id,
                "run_id": run_id,
                "rule_id": f["rule_id"],
                "fact_id": f["fact_id"],
                "category": f["category"],
                "severity": f["severity"],
                "advisory": f["advisory"],
                "quote": f["quote"],
                "span_start": (f["span"] or {}).get("start"),
                "span_end": (f["span"] or {}).get("end"),
                "payload_json": f | {"group": group},
            }
            for group in ("findings", "needs_human")
            for f in report[group]
        ]
        record_ids = [r["id"] for r in post(c, "findings", rows, one=False)] if rows else []
        if egress:
            post(
                c,
                "egress_events",
                [
                    {
                        "org_id": org_id,
                        "run_id": run_id,
                        "provider": e["provider"],
                        "model": e["model"],
                        "purpose": e["task"],
                        "chars_sent": e["chars_sent"],
                        "status": e["status"],
                        "ms": e["ms"],
                        "at": e["at"],
                    }
                    for e in egress
                ],
                one=False,
            )
    return content_id, version["id"], record_ids


def load_version(s: Settings, token: str, version_id: str) -> dict | None:
    """A version the caller can see, with its document, intent and latest report."""
    from plumbline.models import Document

    with client_for(s, token) as c:
        r = c.get(
            "/versions",
            params={"id": f"eq.{version_id}", "select": "id,content_id,text,doc_json,intent_json"},
        )
        if r.status_code == 400:
            return None
        r.raise_for_status()
        rows = r.json()
        if not rows:
            return None
        runs = c.get(
            "/check_runs",
            params={
                "version_id": f"eq.{version_id}",
                "select": "report_json",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        runs.raise_for_status()
    v = rows[0]
    doc = (
        Document.model_validate(v["doc_json"])
        if v.get("doc_json")
        else Document(format="text", text=v["text"], blocks=[], images=[])
    )
    report = runs.json()[0]["report_json"] if runs.json() else None
    return {
        "id": v["id"],
        "content_id": v["content_id"],
        "doc": doc,
        "intent": v.get("intent_json") or {},
        "report": report,
    }


def get_finding(s: Settings, token: str, record_id: str) -> dict | None:
    with client_for(s, token) as c:
        r = c.get("/findings", params={"id": f"eq.{record_id}", "select": "id,org_id,severity"})
        if r.status_code == 400:
            return None
        r.raise_for_status()
        rows = r.json()
    return rows[0] if rows else None


def insert_decision(
    s: Settings,
    token: str,
    *,
    org_id: str,
    user_id: str,
    finding_id: str,
    action: str,
    reason: str | None = None,
    edited_text: str | None = None,
) -> None:
    """One decision as the caller; the audit trigger chains it into the org's log."""
    with client_for(s, token) as c:
        r = c.post(
            "/decisions",
            json={
                "org_id": org_id,
                "finding_id": finding_id,
                "actor": user_id,
                "action": action,
                "reason": reason,
                "edited_text": edited_text,
            },
        )
        r.raise_for_status()


def record_decisions(
    s: Settings,
    token: str,
    *,
    org_id: str,
    user_id: str,
    accepted: list[str],
    edits: dict[str, str],
) -> None:
    rows = [
        {"org_id": org_id, "finding_id": rid, "actor": user_id, "action": "accept"}
        for rid in accepted
    ]
    rows += [
        {
            "org_id": org_id,
            "finding_id": rid,
            "actor": user_id,
            "action": "edit",
            "edited_text": text,
        }
        for rid, text in edits.items()
    ]
    if rows:
        with client_for(s, token) as c:
            c.post("/decisions", json=rows).raise_for_status()
