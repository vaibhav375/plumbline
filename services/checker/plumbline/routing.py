"""Risk routing and permissions for review (§4.5).

Stages: "first" always; "compliance" for any claim or confidential finding; "accessibility" when an
accessibility finding was overruled; "second" when any blocking finding was overruled. The second
approval must come from a different person than the first: the database enforces that.
"""

from typing import Literal

from plumbline.models import Finding

Stage = Literal["first", "compliance", "accessibility", "second"]
STAGES: list[Stage] = ["first", "compliance", "accessibility", "second"]
REVIEWERS = {"reviewer", "compliance", "brand_owner", "accessibility"}
APPROVERS: dict[str, set[str]] = {
    "first": {"reviewer", "compliance", "brand_owner"},
    "compliance": {"compliance"},
    "accessibility": {"accessibility", "brand_owner"},  # small teams: the brand owner holds it
    "second": {"reviewer", "compliance", "brand_owner"},
}


def required_stages(findings: list[Finding], overruled: set[str]) -> list[Stage]:
    """`overruled`: ids of findings a reviewer overruled."""
    needed = {"first"}
    if any(f.category in ("claim", "confidential") for f in findings):
        needed.add("compliance")
    if any(f.category == "accessibility" and f.id in overruled for f in findings):
        needed.add("accessibility")
    if any(f.severity == "blocking" and f.id in overruled for f in findings):
        needed.add("second")
    return [s for s in STAGES if s in needed]


def can_decide(role: str, f: Finding) -> bool:
    """Uphold or overrule a finding (§4.5: blocking claims and confidential findings are Compliance's;
    accessibility findings belong to the named accessibility approver)."""
    if f.category in ("claim", "confidential") and f.severity == "blocking":
        return role == "compliance"
    if f.category == "accessibility":
        return role in ("accessibility", "brand_owner")
    return role in ("reviewer", "compliance", "brand_owner")


def can_approve(role: str, stage: str) -> bool:
    return role in APPROVERS.get(stage, set())
