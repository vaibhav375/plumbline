import json
from datetime import date
from pathlib import Path

import pytest

from plumbline.privacy import mask_confidential, redact

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 23)


def facts_by_id(aurelle):
    return {f.id: f for f in aurelle.facts}


def brand_allow(aurelle) -> set[str]:
    return {"Aurelle", "Meera"} | {t.preferred for t in aurelle.terms}


# ---- redaction ---------------------------------------------------------------------------


def test_aadhaar_pan_phone_redacted():
    text = "Aadhaar 2345 6789 0123, PAN ABCDE1234F, call +91 98765 43210 or 98201 55678."
    out, mapping = redact(text, set())
    for pii in ("2345 6789 0123", "ABCDE1234F", "+91 98765 43210", "98201 55678"):
        assert pii not in out and pii in mapping.values()
    assert "⟦IN_AADHAAR_1⟧" in out and "⟦IN_PAN_1⟧" in out


def test_brand_names_not_redacted(aurelle):
    out, mapping = redact(
        "Meera from Aurelle loved the Vitamin C Brightening Serum.", brand_allow(aurelle)
    )
    assert out == "Meera from Aurelle loved the Vitamin C Brightening Serum." and mapping == {}


def test_numbers_dates_kept():
    text = (
        "Shown to reduce dark spots by 32% in 8 weeks. Launching in Mumbai on 15 Nov 2026 at ₹899."
    )
    out, _ = redact(text, set())
    for keep in ("32%", "8 weeks", "15 Nov 2026", "Mumbai", "₹899"):
        assert keep in out


def test_placeholders_are_consistent_and_reversible():
    text = "Priya Sharma loved it. Ask Priya Sharma or Rohan Mehta."
    out, mapping = redact(text, set())
    assert out.count("⟦PERSON_1⟧") == 2 and "⟦PERSON_2⟧" in out
    restored = out
    for placeholder, original in mapping.items():
        restored = restored.replace(placeholder, original)
    assert restored == text


def _recall(path: Path) -> tuple[float, list[str]]:
    hit, total, missed = 0, 0, []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        out, _ = redact(row["text"], set())
        for pii in row["pii"]:
            total += 1
            if pii in out:
                missed.append(pii)
            else:
                hit += 1
    return hit / total, missed


@pytest.mark.parametrize("name", ["pii_eval.jsonl", "pii_heldout.jsonl"])
def test_pii_recall_meets_spec(name):
    """Spec §7 target: PII redaction recall (Indian names, phone, Aadhaar, PAN) >= 90%."""
    recall, missed = _recall(FIX / name)
    assert recall >= 0.90, (f"{recall:.0%}", missed)


def test_no_false_redactions_on_brand_samples(aurelle, samples):
    for key, sample in samples.items():
        out, mapping = redact(sample["text"], brand_allow(aurelle))
        assert mapping == {}, (key, mapping)
        assert out == sample["text"]


# ---- confidential masking ----------------------------------------------------------------


def test_embargo_exact_and_paraphrase(aurelle):
    facts = list(facts_by_id(aurelle).values())
    exact = "Meet the new serum. Launching with our Mumbai flagship on 15 Nov. Click here to shop!"
    masked, hits = mask_confidential(exact, facts, TODAY)
    assert "Mumbai flagship" not in masked and "15 Nov" not in masked
    assert "⟦RESTRICTED⟧" in masked and [fid for _, fid in hits] == ["FACT-031"]
    assert masked.startswith("Meet the new serum.") and masked.endswith("Click here to shop!")
    span = hits[0][0]
    assert exact[span.start : span.end] == "Launching with our Mumbai flagship on 15 Nov."

    para = "Big news: our first Mumbai store opens mid-November!"
    masked, hits = mask_confidential(para, facts, TODAY)
    assert "Mumbai" not in masked and [fid for _, fid in hits] == ["FACT-031"]


def test_expired_embargo_is_not_masked(aurelle):
    facts = list(facts_by_id(aurelle).values())
    text = "Launching with our Mumbai flagship on 15 Nov."
    masked, hits = mask_confidential(text, facts, date(2026, 12, 2))  # embargo ended 1 Dec
    assert masked == text and hits == []


def test_confidential_codename_masked(aurelle):
    masked, hits = mask_confidential(
        "Project Saffron is almost here — stay tuned.", list(facts_by_id(aurelle).values()), TODAY
    )
    assert "Saffron" not in masked and [fid for _, fid in hits] == ["FACT-023"]


def test_public_facts_are_never_masked(aurelle):
    text = "Made with 94% naturally derived ingredients. Up to 72 hours of hydration."
    masked, hits = mask_confidential(text, list(facts_by_id(aurelle).values()), TODAY)
    assert masked == text and hits == []


def test_short_numeric_alias_needs_an_exact_match(aurelle):
    """FACT-033 (embargoed) has the alias "20% off"; "10% off" must not fuzzy-match it."""
    facts = list(facts_by_id(aurelle).values())
    assert mask_confidential("Enjoy 10% off this weekend.", facts, TODAY)[1] == []
    assert [f for _, f in mask_confidential("Enjoy 20% off this weekend.", facts, TODAY)[1]] == [
        "FACT-033"
    ]


def test_masked_text_never_contains_an_alias(aurelle, samples):
    facts = [f for f in aurelle.facts if f.code_only]
    for sample in samples.values():
        masked, _ = mask_confidential(sample["text"], facts, TODAY)
        for f in facts:
            for alias in f.aliases:
                assert alias.lower() not in masked.lower(), (sample["key"], alias)


def test_masking_hits_only_the_intended_samples(aurelle, samples):
    """Precision: fuzzy matching must not mask ordinary copy (e.g. "Brightening Serum" is not
    the confidential "retinal serum")."""
    expected = {
        "worked-example": ["FACT-031"],
        "diwali-offer": ["FACT-033"],
        "codename-leak": ["FACT-023"],
    }
    for key, sample in samples.items():
        _, hits = mask_confidential(sample["text"], aurelle.facts, TODAY)
        assert sorted({fid for _, fid in hits}) == expected.get(key, []), key
