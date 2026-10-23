"""Review state from saved rows: which stages are needed, approved and pending; the queue's risk
order; and a version's timeline. Pure functions over what the database returned."""

from plumbline.models import CheckReport
from plumbline.routing import required_stages

REVIEWER_ACTIONS = {"uphold", "overrule"}


def latest_decisions(decisions: list[dict]) -> dict[str, dict]:
    """The latest decision per finding record id."""
    out: dict[str, dict] = {}
    for d in sorted(decisions, key=lambda d: d["at"]):
        out[d["finding_id"]] = d
    return out


def stage_state(report: CheckReport, decisions: list[dict], approvals: list[dict]) -> dict:
    latest = latest_decisions(decisions)
    overruled = {
        f.id
        for f in report.findings
        if latest.get(f.record_id or "", {}).get("action") == "overrule"
    }
    required = required_stages(report.findings, overruled)
    last_by_stage: dict[str, dict] = {}
    for a in sorted(approvals, key=lambda a: a["at"]):
        last_by_stage[a["stage"]] = a
    approved = [s for s in required if last_by_stage.get(s, {}).get("outcome") == "approve"]
    undecided = [
        f
        for f in report.findings
        if f.severity == "blocking"
        and latest.get(f.record_id or "", {}).get("action") not in REVIEWER_ACTIONS
    ]
    return {
        "required": required,
        "approved": approved,
        "pending": [s for s in required if s not in approved],
        "undecided_blocking": [f.record_id for f in undecided],
        "overruled": sorted(overruled),
    }


def queue_row(
    version: dict,
    content: dict,
    report: CheckReport,
    decisions: list[dict],
    approvals: list[dict],
    names: dict[str, str],
) -> dict:
    state = stage_state(report, decisions, approvals)
    return {
        "version_id": version["id"],
        "content_id": version["content_id"],
        "n": version["n"],
        "title": content.get("title"),
        "channel": content.get("channel"),
        "origin": content.get("origin"),
        "status": version["status"],
        "submitted_at": version["created_at"],
        "author": names.get(version["created_by"], "Someone"),
        "blocking": sum(f.severity == "blocking" for f in report.findings),
        "claims": sum(f.category in ("claim", "confidential") for f in report.findings),
        "required": state["required"],
        "approved": state["approved"],
        "pending": state["pending"],
    }


def risk_order(rows: list[dict]) -> list[dict]:
    """Most blocking first, then most claims, then oldest."""
    return sorted(rows, key=lambda r: (-r["blocking"], -r["claims"], r["submitted_at"]))


ACTION_WORDS = {
    "escalate": "asked a reviewer about",
    "uphold": "upheld",
    "overrule": "overruled",
    "accept": "accepted the fix for",
    "edit": "edited",
    "dismiss": "dismissed",
}


def timeline(
    version: dict,
    report: CheckReport,
    decisions: list[dict],
    approvals: list[dict],
    names: dict[str, str],
) -> list[dict]:
    by_record = {f.record_id: f for f in report.findings + report.needs_human if f.record_id}
    events = [
        {
            "at": version["created_at"],
            "who": names.get(version["created_by"], "Someone"),
            "what": "submitted for review"
            if version["status"] != "precheck"
            else "checked privately",
        }
    ]
    for d in decisions:
        f = by_record.get(d["finding_id"])
        label = (f.rule_id or f.fact_id) if f else "a finding"
        events.append(
            {
                "at": d["at"],
                "who": names.get(d["actor"], "Someone"),
                "what": f"{ACTION_WORDS.get(d['action'], d['action'])} {label}",
                "reason": d.get("reason"),
            }
        )
    for a in approvals:
        verb = "approved" if a["outcome"] == "approve" else "requested changes at"
        events.append(
            {
                "at": a["at"],
                "who": names.get(a["actor"], "Someone"),
                "what": f"{verb} the {a['stage']} stage",
                "reason": a.get("reason"),
            }
        )
    return sorted(events, key=lambda e: e["at"])
