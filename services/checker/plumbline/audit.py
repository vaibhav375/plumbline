"""Audit chain verification and export. Rows come from `audit_events` read with `payload::text`,
so each payload is the exact text the database hashed (see migrations/0003_audit.sql)."""

import csv
import hashlib
import io
from datetime import UTC, datetime

from plumbline.review import ACTION_WORDS

GENESIS = "0" * 64
COLUMNS = ["at", "actor", "kind", "entity", "entity_id", "prev_hash", "hash", "payload"]


def audit_ts(at: str) -> str:
    """The trigger's `audit_ts`: UTC, microseconds, a trailing Z."""
    return datetime.fromisoformat(at).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def event_hash(prev_hash: str, payload: str, at: str) -> str:
    return hashlib.sha256((prev_hash + payload + audit_ts(at)).encode()).hexdigest()


def verify_chain(rows: list[dict]) -> dict:
    """Rows in id order. `broken_at` is the 1-based position of the first event whose link or hash
    doesn't hold: an edited event fails its own hash, a removed one breaks the next link."""
    prev = GENESIS
    for i, r in enumerate(rows, 1):
        if r["prev_hash"] != prev or event_hash(prev, r["payload"], r["at"]) != r["hash"]:
            return {"valid": False, "length": len(rows), "broken_at": i}
        prev = r["hash"]
    return {"valid": True, "length": len(rows), "broken_at": None}


def to_csv(rows: list[dict]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(COLUMNS)
    w.writerows([r.get(c) or "" for c in COLUMNS] for r in rows)
    return out.getvalue()


def describe(kind: str, p: dict) -> str:
    """One plain line per event for the audit page."""
    if kind == "decisions.insert":
        return f"{ACTION_WORDS.get(p.get('action'), p.get('action'))} a finding"
    if kind == "approvals.insert":
        verb = "approved" if p.get("outcome") == "approve" else "requested changes at"
        return f"{verb} the {p.get('stage')} stage"
    if kind == "versions.update":
        frm, to = (str(p.get(k, "")).replace("_", " ") for k in ("from_status", "status"))
        return f"moved a version from {frm} to {to}"
    if kind == "rule_changes.insert":
        return {
            "graduate": f"Plumbline made {p.get('rule_id')} blocking: {p.get('why')}",
            "demote": f"Plumbline made {p.get('rule_id')} advisory again: {p.get('why')}",
            "undo": f"undid the automatic graduation of {p.get('rule_id')}",
            "unpin": f"let Plumbline decide again about {p.get('rule_id')}",
            "clarify": f"accepted a clearer wording for {p.get('rule_id')}",
            "revert": f"restored the earlier wording of {p.get('rule_id')}",
        }.get(p.get("kind"), "changed a rule")
    if kind == "versions.insert":
        return f"saved version {p.get('n')}" + (" (private)" if p.get("private") else "")
    return kind
