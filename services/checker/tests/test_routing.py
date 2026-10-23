from plumbline.models import Finding
from plumbline.routing import can_approve, can_decide, required_stages


def f(
    fid,
    category="tone",
    severity="minor",
    advisory=True,
    rule_id="TN-01",
    fact_id=None,
    claim_status=None,
):
    return Finding(
        id=fid,
        category=category,
        severity=severity,
        advisory=advisory,
        rule_id=rule_id,
        fact_id=fact_id,
        quote="q",
        span=None,
        image_id=None,
        explanation="e",
        basis_excerpt="b",
        method="code",
        claim_status=claim_status,
    )


CLAIM = f("c", "claim", "blocking", False, "CL-01", "FACT-014", "contradicted")
SECRET = f("s", "confidential", "blocking", False, None, "FACT-031", "restricted")
A11Y = f("a", "accessibility", "blocking", False, "A11Y-CONTRAST")
TONE = f("t")


def test_first_stage_always():
    assert required_stages([TONE], set()) == ["first"]
    assert required_stages([], set()) == ["first"]


def test_claim_requires_compliance():
    assert required_stages([CLAIM, TONE], set()) == ["first", "compliance"]
    assert required_stages([SECRET], set()) == ["first", "compliance"]


def test_overruled_blocking_requires_second():
    assert required_stages([CLAIM], {"c"}) == ["first", "compliance", "second"]


def test_overruled_accessibility_requires_accessibility_stage():
    assert required_stages([A11Y], {"a"}) == ["first", "accessibility", "second"]
    assert required_stages([A11Y], set()) == ["first"]


def test_who_may_decide_what():
    assert can_decide("compliance", CLAIM) and not can_decide("reviewer", CLAIM)
    assert can_decide("compliance", SECRET) and not can_decide("brand_owner", SECRET)
    assert can_decide("brand_owner", A11Y) and not can_decide(
        "reviewer", A11Y
    )  # small team: brand owner holds it
    assert (
        can_decide("reviewer", TONE)
        and not can_decide("creator", TONE)
        and not can_decide("external_creator", TONE)
    )


def test_who_may_approve_which_stage():
    assert can_approve("reviewer", "first") and can_approve("brand_owner", "first")
    assert can_approve("compliance", "compliance") and not can_approve("reviewer", "compliance")
    assert can_approve("brand_owner", "accessibility") and not can_approve(
        "reviewer", "accessibility"
    )
    assert not can_approve("creator", "first") and not can_approve("auditor", "first")
