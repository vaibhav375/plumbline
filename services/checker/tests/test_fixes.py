import json
from datetime import date

import pytest

from plumbline.claims import check_claims
from plumbline.fixes import Intent, apply_fixes, check_intent, propose_rewrite, suggested_version
from plumbline.llm import FakeLLM
from plumbline.models import Document, Finding, Fix, Span
from plumbline.rules.engine import run_rules

TODAY = date(2026, 10, 23)
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
CTA_REWRITE = json.dumps({"sentence": "Shop the Vitamin C Brightening Serum."})


def doc(text: str) -> Document:
    return Document(format="text", text=text, blocks=[], images=[])


def finding(fid, start, end, text, fix=None, category="style", rule_id="X", claim_status=None):
    return Finding(
        id=fid,
        category=category,
        severity="minor",
        advisory=True,
        rule_id=rule_id,
        fact_id=None,
        quote=text[start:end],
        span=Span(start=start, end=end),
        image_id=None,
        explanation="x",
        basis_excerpt="b",
        method="code",
        fix=fix,
        claim_status=claim_status,
    )


def worked(aurelle, samples, llm):
    d = doc(samples["worked-example"]["text"])
    code = run_rules(d, aurelle.rules, aurelle.terms)
    claims_found, claims = check_claims(
        d, aurelle, llm, "IN", "instagram", TODAY, allow={"Aurelle"}
    )
    return d, code + claims_found, claims


def test_suggested_version_matches_spec(aurelle, samples):
    llm = FakeLLM({("extract", "dark spots"): EXTRACTED, ("rewrite", "Click here"): CTA_REWRITE})
    d, findings, claims = worked(aurelle, samples, llm)
    intent = Intent(key_phrases=["dark spots"], cta="Shop", channel="instagram")
    text, result = suggested_version(
        d, findings, intent, llm, aurelle.rules, aurelle.terms, claims=claims
    )
    low = text.lower()
    assert "shown to visibly reduce dark spots by 32% in 8 weeks.*" in low
    assert "made with 94% naturally derived ingredients" in low
    assert "!!!" not in text and "Mumbai" not in text and "Dermatologist" not in text
    assert "*In-house study, 48 participants, 2026." in text  # DL-02 footnote
    assert "Vitamin C Brightening Serum" in text and "NEW" not in text
    assert result.model_dump() == dict.fromkeys(result.model_dump(), True), result
    assert result.passed


def test_suggested_version_adds_no_new_findings(aurelle, samples):
    llm = FakeLLM({("extract", "dark spots"): EXTRACTED, ("rewrite", "Click here"): CTA_REWRITE})
    d, findings, claims = worked(aurelle, samples, llm)
    text, _ = suggested_version(
        d,
        findings,
        Intent(cta="Shop", channel="instagram"),
        llm,
        aurelle.rules,
        aurelle.terms,
        claims=claims,
    )
    before = {(f.rule_id, f.quote.lower()) for f in run_rules(d, aurelle.rules, aurelle.terms)}
    after = {
        (f.rule_id, f.quote.lower()) for f in run_rules(doc(text), aurelle.rules, aurelle.terms)
    }
    assert after - before == set(), after - before


def test_claim_fix_never_generated(aurelle, samples):
    llm = FakeLLM({("extract", "dark spots"): EXTRACTED, ("rewrite", "Click here"): CTA_REWRITE})
    d, findings, claims = worked(aurelle, samples, llm)
    suggested_version(
        d,
        findings,
        Intent(cta="Shop", channel="instagram"),
        llm,
        aurelle.rules,
        aurelle.terms,
        claims=claims,
    )
    rewrites = [user for task, user in llm.calls if task == "rewrite"]
    assert rewrites and all(
        "dark spots" not in u and "natural" not in u and "Dermatologist" not in u for u in rewrites
    )
    claim = finding("c", 0, 5, "Cures acne fast.", category="claim", claim_status="unsupported")
    assert propose_rewrite("Cures acne fast.", claim, llm) is None


def test_rewrite_that_drops_cta_rejected(aurelle):
    text = "Click here to shop!"
    d = doc(text)
    findings = run_rules(d, aurelle.rules, aurelle.terms)
    llm = FakeLLM({("rewrite", "Click here"): json.dumps({"sentence": "Our serum is lovely."})})
    out, result = suggested_version(
        d, findings, Intent(cta="shop", channel="instagram"), llm, aurelle.rules, aurelle.terms
    )
    assert "shop" in out.lower()  # the rewrite was discarded, so the CTA stays
    assert result.cta_kept


def test_rewrite_that_invents_a_number_is_rejected(aurelle):
    claim_free = finding("f", 0, 19, "Click here to shop!", rule_id="CTA-02")
    llm = FakeLLM(
        {("rewrite", "Click"): json.dumps({"sentence": "Shop now: loved by 10,000 customers."})}
    )
    assert propose_rewrite("Click here to shop!", claim_free, llm) is None


def test_apply_right_to_left_offsets():
    text = "aaa BBB ccc DDD eee"
    fs = [
        finding("1", 4, 7, text, Fix(kind="replace_term", text="bb-longer")),
        finding("2", 12, 15, text, Fix(kind="replace_term", text="d")),
        finding("3", 0, 4, text, Fix(kind="remove")),
    ]
    assert apply_fixes(text, fs, {"1", "2", "3"}) == "bb-longer ccc d eee"
    assert apply_fixes(text, fs, {"2"}) == "aaa BBB ccc d eee"


def test_overlapping_fixes_first_wins_and_text_is_never_garbled():
    text = "Click here to shop now"
    fs = [
        finding("wide", 0, 18, text, Fix(kind="replace_term", text="Shop the serum")),
        finding("inner", 6, 10, text, Fix(kind="replace_term", text="THERE")),
    ]
    assert apply_fixes(text, fs, {"wide", "inner"}) == "Shop the serum now"


@pytest.mark.parametrize(
    "after,broken",
    [
        ("Meet the serum.", "cta_kept"),
        ("Shop the serum for your skin.", "pinned_phrases_kept"),
        ("Shop the serum. " + "x" * 2300, "channel_limits_ok"),
    ],
)
def test_intent_checks_fail_for_the_right_reason(after, broken):
    before = "Shop the serum for dark spots."
    result = check_intent(
        before, after, Intent(key_phrases=["dark spots"], cta="Shop", channel="instagram"), [], []
    )
    assert getattr(result, broken) is False and not result.passed


def test_silently_dropped_claim_is_caught(aurelle):
    before = "Our gel gives up to 72 hours of hydration. Shop now."
    d = doc(before)
    _, claims = check_claims(d, aurelle, FakeLLM({}), "IN", "instagram", TODAY, allow=set())
    result = check_intent(before, "Shop now.", Intent(cta="Shop"), [], claims)
    assert result.no_claim_dropped is False


def test_edits_outside_flagged_sentences_are_caught():
    before = "Meet the serum. Click here to shop!"
    f = finding("cta", 16, 26, before, rule_id="CTA-02")
    result = check_intent(
        before, "Meet our lovely serum. Shop the serum.", Intent(cta="Shop"), [f], []
    )
    assert result.edits_in_flagged_sentences is False


def test_added_footnotes_are_not_counted_as_edits():
    before = "Made with 100% natural goodness. Shop now."
    f = finding(
        "c",
        0,
        31,
        before,
        category="claim",
        claim_status="contradicted",
        fix=Fix(kind="approved_wording", text="made with 94% naturally derived ingredients"),
    )
    after = "Made with 94% naturally derived ingredients. Shop now.\nCalculated per ISO 16128."
    with_notes = check_intent(
        before, after, Intent(cta="Shop"), [f], [], ["Calculated per ISO 16128."]
    )
    assert with_notes.edits_in_flagged_sentences
    assert not check_intent(
        before,
        after + "\nA brand new sentence.",
        Intent(cta="Shop"),
        [f],
        [],
        ["Calculated per ISO 16128."],
    ).edits_in_flagged_sentences


def _suggest(aurelle, text, findings=None, rewrite=None, intent=None):
    d = doc(text)
    findings = findings if findings is not None else run_rules(d, aurelle.rules, aurelle.terms)
    llm = FakeLLM({("rewrite", k): json.dumps({"sentence": v}) for k, v in (rewrite or {}).items()})
    return suggested_version(
        d, findings, intent or Intent(), llm, aurelle.rules, aurelle.terms, claims=[]
    )


def claim_f(text, fragment, status="unsupported"):
    start = text.index(fragment)
    return finding(
        f"c{start}",
        start,
        start + len(fragment),
        text,
        category="claim",
        claim_status=status,
        rule_id="CL-01",
    )


def test_removing_a_claim_never_leaves_a_fragment(aurelle):
    text = "Ceramide Barrier Cream is the treatment for eczema and dry, itchy skin. Find out more."
    out, _ = _suggest(aurelle, text, [claim_f(text, "treatment for eczema and dry, itchy skin")])
    assert out == "Find out more."
    text = "Get fairer, brighter skin this festive season with Aurelle Kumkumadi Glow Oil. Buy it."
    out, _ = _suggest(
        aurelle, text, [claim_f(text, "Get fairer, brighter skin this festive season")]
    )
    assert out == "Buy it."


def test_dangling_conjunction_is_tidied(aurelle):
    text = "It smells like nothing and my skin looks so fresh. Obsessed."
    out, _ = _suggest(aurelle, text, [claim_f(text, "my skin looks so fresh")])
    assert out == "It smells like nothing. Obsessed."


def test_sentence_with_only_kept_claims_is_untouched(aurelle):
    text = "No white cast on Indian skin tones*. Shop now!\n*In-use test, 60 participants, 2026."
    out, _ = _suggest(
        aurelle, text, [claim_f(text, "No white cast on Indian skin tones", "supported")]
    )
    assert out == text


def test_paragraph_breaks_and_footnotes_keep_their_lines(aurelle):
    text = "Subject: Your glow, sorted\n\nShop the Vitamin C Brightening Serum.\n*In-house study, 48 participants, 2026."
    out, result = _suggest(aurelle, text)
    assert out == text and result.edits_in_flagged_sentences


def test_rewrite_is_told_which_product_this_post_is_about(aurelle):
    text = "Ceramide Barrier Cream for dry skin. Find out more: click here."
    llm_text = "Find out more about the Ceramide Barrier Cream."
    d = doc(text)
    llm = FakeLLM({("rewrite", "click here"): json.dumps({"sentence": llm_text})})
    suggested_version(
        d,
        run_rules(d, aurelle.rules, aurelle.terms),
        Intent(),
        llm,
        aurelle.rules,
        aurelle.terms,
        claims=[],
    )
    prompt = llm.systems[0]
    assert "Ceramide Barrier Cream" in prompt and "Vitamin C Brightening Serum" not in prompt


def test_dropping_a_sentence_keeps_the_paragraph_break_before_it(aurelle):
    text = "Subject: Your glow, sorted\n\nOur sale is secret. Shop the serum."
    out, result = _suggest(aurelle, text, [claim_f(text, "Our sale is secret.", "restricted")])
    assert (
        out == "Subject: Your glow, sorted\n\nShop the serum." and result.edits_in_flagged_sentences
    )
