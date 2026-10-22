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
