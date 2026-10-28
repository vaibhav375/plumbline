import json
from datetime import date

import pytest

from plumbline.claims import check_claims, detect_claims, match_fact, verify_claim
from plumbline.llm import FakeLLM, LLMUnavailable
from plumbline.models import Document

TODAY = date(2026, 10, 23)
WORKED = (
    "Meet the NEW Aurelle Vitamin-C serum!!! 100% natural, eco-friendly and clinically proven to fade "
    "dark spots by 60% in just 2 weeks. Dermatologist recommended. Launching with our Mumbai flagship on "
    "15 Nov. Click here to shop!"
)
EXTRACTED = json.dumps(
    {
        "claims": [
            {"text": "100% natural, eco-friendly", "kind": "environmental"},
            {
                "text": "clinically proven to fade dark spots by 60% in just 2 weeks",
                "kind": "efficacy",
            },
            {"text": "Dermatologist recommended", "kind": "endorsement"},
        ]
    }
)


def doc(text: str) -> Document:
    return Document(format="text", text=text, blocks=[], images=[])


def run(aurelle, text=WORKED, llm=None, today=TODAY):
    llm = llm or FakeLLM({("extract", "dark spots"): EXTRACTED})
    findings, claims = check_claims(
        doc(text), aurelle, llm, market="IN", channel="instagram", today=today, allow={"Aurelle"}
    )
    return findings, claims, llm


def by_quote(findings, fragment):
    return next(f for f in findings if fragment in f.quote)


def test_detect_claims_by_code(aurelle):
    claims = detect_claims(doc(WORKED))
    kinds = {c.kind for c in claims}
    assert {"environmental", "efficacy", "endorsement"} <= kinds
    numeric = next(c for c in claims if "60%" in c.text)
    assert (60.0, "%") in numeric.numbers and (2.0, "weeks") in numeric.numbers


def test_60_percent_2_weeks_contradicted(aurelle):
    findings, _, _ = run(aurelle)
    f = by_quote(findings, "60%")
    assert f.fact_id == "FACT-014" and f.claim_status == "contradicted"
    assert "32%" in f.explanation and "8 weeks" in f.explanation
    assert f.fix.kind == "approved_wording" and f.fix.ref_id == "AW-014b"
    assert f.fix.note and "In-house study, 48 participants, 2026." in f.fix.note  # DL-02
    assert f.severity == "blocking" and not f.advisory


def test_eco_friendly_regulated(aurelle):
    findings, _, _ = run(aurelle)
    f = by_quote(findings, "eco-friendly")
    assert f.rule_id == "CL-03" and f.fix.kind == "approved_wording" and f.fix.ref_id == "AW-009a"


def test_dermatologist_unsupported_no_fix(aurelle):
    findings, _, _ = run(aurelle)
    f = by_quote(findings, "Dermatologist recommended")
    assert f.rule_id == "CL-05" and f.claim_status == "unsupported" and f.severity == "blocking"
    assert (
        f.fix.kind == "none" and f.fix.note == "No approved wording exists, so no fix is offered."
    )


def test_embargoed_sentence_is_a_restricted_finding(aurelle):
    findings, _, _ = run(aurelle)
    f = by_quote(findings, "Mumbai flagship")
    assert (
        f.fact_id == "FACT-031" and f.category == "confidential" and f.claim_status == "restricted"
    )
    assert f.severity == "blocking" and f.fix.kind == "remove" and f.method == "code"


def test_confidential_fact_never_sent_to_llm(aurelle):
    _, _, llm = run(aurelle)
    assert llm.calls, "extraction should have been called"
    assert not any("Mumbai" in user or "15 Nov" in user for _, user in llm.calls)


def test_pii_redacted_before_extraction(aurelle):
    llm = FakeLLM({("extract", "dark spots"): EXTRACTED})
    run(aurelle, WORKED + " Loved by Priya Sharma, call 98765 43210.", llm)
    assert not any("Priya" in user or "98765" in user for _, user in llm.calls)


def test_expired_fact_outdated(aurelle):
    fact = next(f for f in aurelle.facts if f.id == "FACT-014").model_copy(
        update={"valid_until": date(2026, 1, 1)}
    )
    claim = next(
        c for c in detect_claims(doc("Reduces dark spots by 32% in 8 weeks.")) if c.numbers
    )
    f = verify_claim(claim, fact, 0.95, TODAY, FakeLLM({}), 0.72, aurelle, "IN", "instagram")
    assert f.claim_status == "outdated" and "2026-01-01" in f.explanation


def test_unverified_fact_needs_human(aurelle):
    fact = next(f for f in aurelle.facts if f.id == "FACT-034")  # preliminary study, verified=false
    assert not fact.verified
    claim = next(c for c in detect_claims(doc("21% fewer breakouts in 6 weeks.")) if c.numbers)
    f = verify_claim(claim, fact, 0.95, TODAY, FakeLLM({}), 0.72, aurelle, "IN", "instagram")
    assert f.claim_status == "needs_human" and f.advisory


def test_low_match_score_needs_human_never_a_guess(aurelle):
    fact = next(f for f in aurelle.facts if f.id == "FACT-014")
    claim = detect_claims(doc("Clinically proven results."))[0]
    f = verify_claim(claim, fact, 0.40, TODAY, FakeLLM({}), 0.72, aurelle, "IN", "instagram")
    assert f.claim_status == "needs_human"


def test_consistent_numbers_supported(aurelle):
    findings, claims, _ = run(
        aurelle,
        "Up to 72 hours of hydration* in a light gel.\n*Instrumental study, 30 participants, 2025.",
        FakeLLM({}),
    )
    assert not [f for f in findings if f.claim_status in ("contradicted", "unsupported")]
    assert any(f.claim_status == "supported" and f.fact_id == "FACT-010" for f in findings)


def test_non_numeric_claim_uses_ai_entailment(aurelle):
    llm = FakeLLM(
        {
            ("support", "fragrance-free"): json.dumps(
                {"verdict": "supported", "reason": "Fact says so."}
            )
        }
    )
    findings, _, _ = run(aurelle, "The serum is fragrance-free and gentle.", llm)
    f = next(f for f in findings if f.fact_id == "FACT-004")
    assert f.claim_status == "supported" and f.method == "ai+code"


def test_ai_down_still_checks_claims_by_code(aurelle):
    """Review Focus 1: with extraction unavailable, regex-detected claims are still verified."""
    llm = FakeLLM(
        {("extract", "dark spots"): LLMUnavailable("groq rate-limited, gemini timed out")}
    )
    findings, _, _ = run(aurelle, llm=llm)
    statuses = {f.claim_status for f in findings}
    assert {"contradicted", "unsupported", "restricted"} <= statuses


def test_extracted_quote_not_in_text_is_ignored(aurelle):
    bogus = json.dumps({"claims": [{"text": "cures acne overnight", "kind": "efficacy"}]})
    findings, claims, _ = run(aurelle, llm=FakeLLM({("extract", "dark spots"): bogus}))
    assert not any("cures acne" in c.text for c in claims)


@pytest.mark.parametrize(
    "text,expected_fact",
    [
        ("clinically proven to fade dark spots by 60% in just 2 weeks", "FACT-014"),
        ("100% natural, eco-friendly", "FACT-009"),
        ("up to 72 hours of hydration", "FACT-010"),
    ],
)
def test_match_fact(aurelle, text, expected_fact):
    claim = detect_claims(doc(text))[0]
    fact, score = match_fact(claim, aurelle.facts, "IN")
    assert fact is not None and fact.id == expected_fact and score >= 0.72


def test_dermatologist_matches_nothing(aurelle):
    claim = detect_claims(doc("Dermatologist recommended."))[0]
    fact, score = match_fact(claim, aurelle.facts, "IN")
    assert fact is None or score < 0.72


def test_product_names_are_not_claims(aurelle):
    """Live run: "Brightening" in the product's own name was read as an efficacy claim."""
    names = {t.preferred for t in aurelle.terms}
    text = "Meet the new Aurelle Vitamin C Brightening Serum. Shop the Vitamin C Brightening Serum."
    assert detect_claims(doc(text), ignore=names) == []


def test_footnotes_are_evidence_not_claims(aurelle):
    text = "No white cast on Indian skin tones*.\n*In-use test, 60 participants, 2026."
    assert [c.text for c in detect_claims(doc(text))] == ["No white cast on Indian skin tones"]


def test_approved_wording_choice_does_not_depend_on_row_order(aurelle):
    """Task 14 live run: the DB returned AW-014a first and it was offered instead of AW-014b."""
    reordered = aurelle.model_copy(
        update={"wordings": sorted(aurelle.wordings, key=lambda w: w.id)}
    )
    for ctx in (aurelle, reordered):
        findings, _, _ = run(ctx)
        assert by_quote(findings, "60%").fix.ref_id == "AW-014b"


def test_a_rulebook_with_its_own_claim_rule_ids_works(aurelle):
    # Found by loading a second brand: claims used to cite CL-01, CL-03, CL-04 and CL-05 by name.
    renamed = {"CL-01": "FN-C1", "CL-03": "FN-C3", "CL-04": "FN-C4", "CL-05": "FN-C5"}
    # A brand whose claim rules all have their own ids: Aurelle's other claim rules (CL-02, CL-07) would
    # sort first, so they are left out.
    rules = [
        r.model_copy(update={"id": renamed.get(r.id, r.id)})
        for r in aurelle.rules
        if r.category != "claim" or r.id in renamed
    ]
    ctx = aurelle.model_copy(update={"rules": rules})
    findings, _, _ = run(ctx)
    claim_findings = [f for f in findings if f.category == "claim"]
    assert claim_findings and all(f.rule_id.startswith("FN-C") for f in claim_findings)
    assert not any(f.rule_id in renamed for f in claim_findings)


def test_a_rulebook_with_no_claim_rule_says_so(aurelle):
    ctx = aurelle.model_copy(update={"rules": [r for r in aurelle.rules if r.category != "claim"]})
    with pytest.raises(ValueError, match="category 'claim'"):
        run(ctx)


def test_a_ranking_claim_cites_the_ranking_rule_in_another_brands_rulebook(aurelle):
    from plumbline.claims import Claim, rule_for
    from plumbline.models import Span

    rules = [
        r.model_copy(update={"id": i, "title": t})
        for r, (i, t) in zip(  # noqa: B905
            [r for r in aurelle.rules if r.category == "claim"][:3],
            [
                ("FN-C1", "Financial claims need a matching fact"),
                ("FN-C2", "Regulator endorsement claims need evidence"),
                ("FN-C3", "Rankings and superlatives need a source"),
            ],
        )
    ]
    ctx = aurelle.model_copy(update={"rules": rules})

    def mk(kind):
        return Claim(text="x", span=Span(start=0, end=1), kind=kind, numbers=[])

    assert rule_for(mk("superlative"), ctx).id == "FN-C3"
    assert rule_for(mk("endorsement"), ctx).id == "FN-C2"
    assert rule_for(mk("timing"), ctx).id == "FN-C1"
