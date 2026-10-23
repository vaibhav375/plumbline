"""Supabase REST (PostgREST) access, always as the caller: the anon key plus the user's own JWT,
so row-level security decides what this process can read. The service key is never loaded here."""

import hashlib
import json
from datetime import UTC, datetime

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
                "select": "id,report_json",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        runs.raise_for_status()
        saved = []
        if runs.json():
            # The stored report predates its finding rows, so their record ids are re-attached here.
            f = c.get(
                "/findings",
                params={"run_id": f"eq.{runs.json()[0]['id']}", "select": "id,payload_json"},
            )
            f.raise_for_status()
            saved = f.json()
    v = rows[0]
    doc = (
        Document.model_validate(v["doc_json"])
        if v.get("doc_json")
        else Document(format="text", text=v["text"], blocks=[], images=[])
    )
    report = runs.json()[0]["report_json"] if runs.json() else None
    if report:
        ids = {
            (r["payload_json"].get("group"), r["payload_json"].get("id")): r["id"] for r in saved
        }
        for group in ("findings", "needs_human"):
            report[group] = [f | {"record_id": ids.get((group, f["id"]))} for f in report[group]]
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


REVIEW_STATUSES = "(submitted,in_review,changes_requested,approved)"


def _get(c: httpx.Client, table: str, **params) -> list[dict]:
    r = c.get(f"/{table}", params=params)
    r.raise_for_status()
    return r.json()


def _reports_with_ids(c: httpx.Client, version_ids: list[str]) -> dict[str, dict]:
    """Latest report per version, with finding record ids re-attached from the saved rows."""
    if not version_ids:
        return {}
    runs = _get(
        c,
        "check_runs",
        version_id=f"in.({','.join(version_ids)})",
        select="id,version_id,report_json,created_at",
        order="created_at.desc",
    )
    latest: dict[str, dict] = {}
    for r in runs:
        latest.setdefault(r["version_id"], r)
    # Seeded history runs hold {"synthetic": true}, not a report; nothing in them is reviewable.
    latest = {v: r for v, r in latest.items() if "findings" in (r["report_json"] or {})}
    if not latest:
        return {}
    rows = _get(
        c,
        "findings",
        run_id=f"in.({','.join(r['id'] for r in latest.values())})",
        select="id,run_id,payload_json",
    )
    ids = {
        (r["run_id"], r["payload_json"].get("group"), r["payload_json"].get("id")): r["id"]
        for r in rows
    }
    out = {}
    for vid, run in latest.items():
        report = run["report_json"]
        for group in ("findings", "needs_human"):
            report[group] = [
                f | {"record_id": ids.get((run["id"], group, f["id"]))} for f in report[group]
            ]
        out[vid] = report
    return out


def _names(c: httpx.Client) -> dict[str, str]:
    return {
        p["user_id"]: p["display_name"] for p in _get(c, "profiles", select="user_id,display_name")
    }


def upsert_rules(s: Settings, token: str, rows: list[dict]) -> None:
    """Insert or update by (org, id) as the caller; RLS limits this to rule owners. Importing a
    rule again reactivates it."""
    now = datetime.now(UTC).isoformat()
    with client_for(s, token) as c:
        c.post(
            "/rules",
            params={"on_conflict": "org_id,id"},
            json=[r | {"active": True, "updated_at": now} for r in rows],
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        ).raise_for_status()


def list_facts(s: Settings, token: str) -> tuple[list[dict], list[dict]]:
    with client_for(s, token) as c:
        return (
            _get(c, "facts", select="*", order="id"),
            _get(c, "approved_wordings", select="*", order="id"),
        )


AUDIT_PAGE = 1000  # Supabase's default max rows per request


def audit_events(s: Settings, token: str) -> tuple[list[dict], dict[str, str]]:
    """The caller's org chain in id order (RLS scopes it), with `payload` as the exact hashed text."""
    rows: list[dict] = []
    with client_for(s, token) as c:
        while True:
            page = _get(
                c,
                "audit_events",
                select="id,actor,kind,entity,entity_id,payload::text,prev_hash,hash,at",
                order="id.asc",
                limit=str(AUDIT_PAGE),
                offset=str(len(rows)),
            )
            rows += page
            if len(page) < AUDIT_PAGE:
                return rows, _names(c)


def review_queue(s: Settings, token: str) -> dict:
    """Submitted versions the caller can see (pre-checks are private, so RLS never returns them)."""
    with client_for(s, token) as c:
        versions = _get(
            c,
            "versions",
            status=f"in.{REVIEW_STATUSES}",
            private="is.false",
            select="id,content_id,n,status,created_by,created_at",
            order="created_at.desc",
            limit="50",
        )
        # Only each content's newest submitted version is in the queue.
        newest: dict[str, dict] = {}
        for v in versions:
            newest.setdefault(v["content_id"], v)
        versions = list(newest.values())
        vids = [v["id"] for v in versions]
        contents = (
            {
                c_["id"]: c_
                for c_ in _get(
                    c,
                    "contents",
                    id=f"in.({','.join(v['content_id'] for v in versions)})",
                    select="id,title,channel,origin",
                )
            }
            if versions
            else {}
        )
        reports = _reports_with_ids(c, vids)
        record_ids = [
            f["record_id"] for r in reports.values() for f in r["findings"] if f.get("record_id")
        ]
        decisions = (
            _get(
                c,
                "decisions",
                finding_id=f"in.({','.join(record_ids)})",
                select="finding_id,actor,action,reason,at",
            )
            if record_ids
            else []
        )
        approvals = (
            _get(
                c,
                "approvals",
                version_id=f"in.({','.join(vids)})",
                select="version_id,actor,stage,outcome,reason,at",
            )
            if vids
            else []
        )
        names = _names(c)
    return {
        "versions": versions,
        "contents": contents,
        "reports": reports,
        "decisions": decisions,
        "approvals": approvals,
        "names": names,
    }


def load_review(s: Settings, token: str, version_id: str) -> dict | None:
    with client_for(s, token) as c:
        r = c.get(
            "/versions",
            params={
                "id": f"eq.{version_id}",
                "private": "is.false",
                "select": "id,content_id,n,text,status,created_by,created_at",
            },
        )
        if r.status_code == 400:
            return None
        r.raise_for_status()
        if not r.json():
            return None
        version = r.json()[0]
        content = _get(
            c, "contents", id=f"eq.{version['content_id']}", select="id,title,channel,origin"
        )[0]
        report = _reports_with_ids(c, [version_id]).get(version_id)
        record_ids = [
            f["record_id"]
            for f in (report or {}).get("findings", []) + (report or {}).get("needs_human", [])
            if f.get("record_id")
        ]
        decisions = (
            _get(
                c,
                "decisions",
                finding_id=f"in.({','.join(record_ids)})",
                select="finding_id,actor,action,reason,at",
            )
            if record_ids
            else []
        )
        approvals = _get(
            c, "approvals", version_id=f"eq.{version_id}", select="actor,stage,outcome,reason,at"
        )
        comments = _get(
            c,
            "comments",
            version_id=f"eq.{version_id}",
            select="author,body,created_at",
            order="created_at.asc",
        )
        names = _names(c)
    return {
        "version": version,
        "content": content,
        "report": report,
        "decisions": decisions,
        "approvals": approvals,
        "comments": comments,
        "names": names,
    }


class SecondApproverError(Exception):
    pass


def add_approval(
    s: Settings,
    token: str,
    *,
    org_id: str,
    user_id: str,
    version_id: str,
    stage: str,
    outcome: str,
    reason: str | None,
) -> None:
    with client_for(s, token) as c:
        r = c.post(
            "/approvals",
            json={
                "org_id": org_id,
                "version_id": version_id,
                "actor": user_id,
                "stage": stage,
                "outcome": outcome,
                "reason": reason,
            },
        )
        if r.status_code >= 400 and "different person" in r.text:
            raise SecondApproverError()  # the database's separation-of-duties trigger (0003)
        r.raise_for_status()


def set_status(s: Settings, token: str, version_id: str, status: str) -> None:
    with client_for(s, token) as c:
        c.patch(
            "/versions", params={"id": f"eq.{version_id}"}, json={"status": status}
        ).raise_for_status()


def add_comment(
    s: Settings, token: str, *, org_id: str, user_id: str, version_id: str, body: str
) -> None:
    with client_for(s, token) as c:
        c.post(
            "/comments",
            json={"org_id": org_id, "version_id": version_id, "author": user_id, "body": body},
        ).raise_for_status()


def escalations(s: Settings, token: str, record_ids: list[str]) -> list[dict]:
    """The writer's "ask a reviewer" decisions on these findings."""
    if not record_ids:
        return []
    with client_for(s, token) as c:
        return _get(
            c,
            "decisions",
            finding_id=f"in.({','.join(record_ids)})",
            action="eq.escalate",
            select="finding_id,reason",
        )
