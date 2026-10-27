"""Round 3, improvement 2: link codes, per-brand chat context and the publish gate.

Every database call here goes through the narrow `plumbline_checker` role and the security-definer
functions of migration 0013, so this process never gains table access or a service key. Codes and
keys are stored as hashes; the plain value is shown once.
"""

import hashlib
import json
import secrets
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import tuple_row

from plumbline.config import Settings
from plumbline.models import ApprovedWording, Fact, OrgContext, Rule, Term
from plumbline.review import latest_decisions

# No 0/O/1/I/L: a code is read aloud or retyped from a screen.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_MINUTES = 15
KEY_PREFIX = "plk_"


class NotEnabled(Exception):
    """CHECKER_DATABASE_URL isn't set, so the connect features are off."""


def new_code() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def normalise_code(text: str) -> str:
    """What people type: any case, with or without the dash or spaces."""
    raw = "".join(ch for ch in text.upper() if ch.isalnum())
    return f"{raw[:4]}-{raw[4:]}" if len(raw) == 8 else ""


def new_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(24)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def _conn(s: Settings) -> Iterator[psycopg.Connection]:
    if not s.checker_database_url:
        raise NotEnabled
    with psycopg.connect(s.checker_database_url, connect_timeout=5, row_factory=tuple_row) as c:
        yield c


def _one(s: Settings, sql: str, *args):
    with _conn(s) as c:
        row = c.execute(sql, args).fetchone()
    return row[0] if row else None


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


# ---- linking ----------------------------------------------------------------------------------


def make_code(s: Settings, org_id: str, user_id: str) -> tuple[str, str]:
    """A fresh one-time code for this org: (code, expires_at as ISO text)."""
    code = new_code()
    expires = _one(
        s,
        "select public.agent_make_code(%s, %s, %s, %s)",
        org_id,
        user_id,
        digest(code),
        CODE_MINUTES,
    )
    return code, expires.isoformat()


def redeem_code(s: Settings, code: str, address: str) -> dict | None:
    norm = normalise_code(code)
    if not norm:
        return None
    return _json(_one(s, "select public.agent_redeem_code(%s, %s)", digest(norm), address))


def link_for(s: Settings, address: str) -> dict | None:
    return _json(_one(s, "select public.agent_link_for(%s)", address))


def unlink(s: Settings, address: str, org_id: str | None = None) -> int:
    return _one(s, "select public.agent_unlink(%s, %s)", address, org_id)


def links_list(s: Settings, org_id: str) -> list[dict]:
    return _json(_one(s, "select public.agent_links_list(%s)", org_id))


def open_codes(s: Settings, org_id: str) -> int:
    return _one(s, "select public.agent_codes_open(%s)", org_id)


def org_context(s: Settings, org_id: str) -> OrgContext:
    """What an agency writer of this org would see: the rulebook without confidential facts."""
    raw = _json(_one(s, "select public.agent_org_context(%s)", org_id))
    rules = [Rule.model_validate(r) for r in raw["rules"]]
    digest_ = hashlib.sha256(
        json.dumps([r.model_dump() for r in rules], sort_keys=True).encode()
    ).hexdigest()
    return OrgContext(
        org_id=org_id,
        rulebook_version=f"rb-{digest_[:10]}",
        rules=rules,
        facts=[Fact.model_validate(f) for f in raw["facts"]],
        wordings=[ApprovedWording.model_validate(w) for w in raw["wordings"]],
        terms=[Term.model_validate(t) for t in raw["terms"]],
    )


# ---- the publish gate -------------------------------------------------------------------------


def key_create(s: Settings, org_id: str, user_id: str, label: str) -> tuple[str, str]:
    key = new_key()
    kid = _one(
        s, "select public.gate_key_create(%s, %s, %s, %s)", org_id, user_id, digest(key), label
    )
    return str(kid), key


def key_org(s: Settings, key: str) -> str | None:
    org = _one(s, "select public.gate_key_org(%s)", digest(key))
    return str(org) if org else None


def keys_list(s: Settings, org_id: str) -> list[dict]:
    return _json(_one(s, "select public.gate_keys_list(%s)", org_id))


def key_revoke(s: Settings, org_id: str, key_id: str) -> int:
    return _one(s, "select public.gate_key_revoke(%s, %s)", org_id, key_id)


def latest_version(s: Settings, org_id: str, content_id: str) -> str | None:
    v = _one(s, "select public.gate_latest_version(%s, %s)", org_id, content_id)
    return str(v) if v else None


def snapshot(s: Settings, org_id: str, version_id: str) -> dict | None:
    return _json(_one(s, "select public.gate_snapshot(%s, %s)", org_id, version_id))


def log_call(s: Settings, org_id: str, version_id: str | None, decision: str, reasons: list[str]):
    _one(s, "select public.gate_log(%s, %s, %s, %s)", org_id, version_id, decision, reasons)


def calls_recent(s: Settings, org_id: str, limit: int = 20) -> list[dict]:
    return _json(_one(s, "select public.gate_calls_recent(%s, %s)", org_id, limit))


def text_hash(text: str) -> str:
    """What a tool sends as text_sha256: SHA-256 of the UTF-8 text, surrounding whitespace trimmed."""
    return hashlib.sha256(text.strip().encode()).hexdigest()


def decide(snap: dict, text_sha256: str | None = None) -> tuple[str, list[str]]:
    """The gate's answer: "go" only for an approved version with no open blocking finding and, when the
    tool says what text it will publish, exactly the approved text. Pure, so it is tested without a
    database. A blocking finding stays open unless a reviewer overruled it ("upheld" doesn't clear it)."""
    reasons: list[str] = []
    version, report = snap["version"], snap.get("report")
    if version["status"] not in ("approved", "published"):
        reasons.append(f"Not approved yet (status: {version['status'].replace('_', ' ')}).")
    if not report or "findings" not in report:
        reasons.append("No completed check is on file for this version.")
    else:
        ids = {
            (f["payload"].get("group"), f["payload"].get("id")): f["id"] for f in snap["findings"]
        }
        latest = latest_decisions(snap["decisions"])
        open_ = [
            f
            for f in report["findings"]
            if f["severity"] == "blocking"
            and not f["advisory"]
            and latest.get(ids.get(("findings", f["id"])), {}).get("action") != "overrule"
        ]
        if open_:
            names = ", ".join(
                dict.fromkeys(f.get("rule_id") or f.get("fact_id") or "?" for f in open_)
            )
            n = len(open_)
            reasons.append(
                f"{n} blocking {'finding is' if n == 1 else 'findings are'} open: {names}."
            )
    if text_sha256 and text_sha256.strip().lower() != text_hash(version["text"]):
        reasons.append("The text differs from the approved version.")
    return ("not_yet" if reasons else "go"), reasons
