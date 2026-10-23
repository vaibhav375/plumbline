from plumbline.models import Document, ImageAsset, OcrBlock, Rule
from plumbline.rules.engine import run_rules


def by_rule(findings, rule_id):
    return [f for f in findings if f.rule_id == rule_id]


def test_exclamation_count(aurelle, worked_example):
    found = by_rule(run_rules(worked_example, aurelle.rules, aurelle.terms), "TN-02")
    assert len(found) == 1
    assert found[0].quote == "!!!"
    assert worked_example.text[found[0].span.start : found[0].span.end] == "!!!"
    assert found[0].advisory and found[0].severity == "minor"


def test_term_variant(aurelle, worked_example):
    found = by_rule(run_rules(worked_example, aurelle.rules, aurelle.terms), "TM-007")
    assert len(found) == 1
    assert found[0].quote == "Vitamin-C serum"
    assert found[0].fix.kind == "replace_term"
    assert found[0].fix.text == "Vitamin C Brightening Serum"


def test_preferred_term_does_not_fire(aurelle):
    doc = Document(
        format="text", text="Shop the Vitamin C Brightening Serum.", blocks=[], images=[]
    )
    assert by_rule(run_rules(doc, aurelle.rules, aurelle.terms), "TM-007") == []


def test_cta_click_here(aurelle, worked_example):
    found = by_rule(run_rules(worked_example, aurelle.rules, aurelle.terms), "CTA-02")
    assert [f.quote for f in found] == ["Click here"]


def test_contrast_banner(aurelle, worked_example):
    found = by_rule(run_rules(worked_example, aurelle.rules, aurelle.terms), "A11Y-CONTRAST")
    assert len(found) == 1
    f = found[0]
    assert f.severity == "blocking" and not f.advisory
    assert next(r for r in aurelle.rules if r.id == f.rule_id).tier == "mandatory"
    assert "1.96:1" in f.explanation
    assert f.image_id == worked_example.images[0].id
    assert f.quote == "GLOW IN 2 WEEKS"
    block = next(b for b in worked_example.images[0].ocr if b.text == "GLOW IN 2 WEEKS")
    assert f.bbox == block.bbox  # original pixels, for the overlay on the thumbnail


def _image_doc(**block) -> Document:
    ocr = OcrBlock(text="BIG TEXT", bbox=(0, 0, 100, 40), confidence=90, bold=False, **block)
    image = ImageAsset(id="img1", width=100, height=100, alt_text="Big text", ocr=[ocr])
    return Document(format="image", text="BIG TEXT", blocks=[], images=[image])


def test_large_text_uses_3_to_1(aurelle):
    # #949494 on white is 3.03:1: passes the large-text minimum, fails the normal one.
    large = _image_doc(px_height=30, fg_hex="#949494", bg_hex="#FFFFFF")
    small = _image_doc(px_height=12, fg_hex="#949494", bg_hex="#FFFFFF")
    assert by_rule(run_rules(large, aurelle.rules, aurelle.terms), "A11Y-CONTRAST") == []
    assert len(by_rule(run_rules(small, aurelle.rules, aurelle.terms), "A11Y-CONTRAST")) == 1


def test_busy_background_contrast_not_guessed(aurelle):
    doc = _image_doc(px_height=12, fg_hex="#949494", bg_hex="#FFFFFF")
    doc.images[0].ocr[0].busy_background = True
    assert by_rule(run_rules(doc, aurelle.rules, aurelle.terms), "A11Y-CONTRAST") == []


def test_alt_text_missing_blocking(aurelle, worked_example):
    found = by_rule(run_rules(worked_example, aurelle.rules, aurelle.terms), "A11Y-ALT")
    assert len(found) == 1
    assert found[0].severity == "blocking" and found[0].image_id == "img1"
    assert found[0].fix is None or found[0].fix.kind == "none"  # Plumbline never writes alt text


def test_decorative_image_no_alt_ok(aurelle):
    image = ImageAsset(id="img1", width=10, height=10, alt_text=None, decorative=True)
    doc = Document(format="image", text="", blocks=[], images=[image])
    assert by_rule(run_rules(doc, aurelle.rules, aurelle.terms), "A11Y-ALT") == []


def test_class_c_never_runs(aurelle):
    rule = Rule(
        id="X-C",
        title="Be delightful",
        category="tone",
        cls="C",
        check_type="pattern",
        params={"regex": "."},
        severity="minor",
        tier="brand",
        source_ref="t",
        owner_function="brand",
    )
    doc = Document(format="text", text="anything at all", blocks=[], images=[])
    assert run_rules(doc, [rule], []) == []


def test_ai_rules_are_not_run_by_code(aurelle, worked_example):
    ids = {f.rule_id for f in run_rules(worked_example, aurelle.rules, aurelle.terms)}
    assert not ids & {r.id for r in aurelle.rules if r.check_type == "ai_rule" or r.cls == "C"}


def test_mandatory_major_still_blocks(aurelle):
    doc = Document(format="text", text="The best serum. Shop now.", blocks=[], images=[])
    found = by_rule(run_rules(doc, aurelle.rules, aurelle.terms), "CL-04")
    assert found and found[0].severity == "blocking" and not found[0].advisory


def test_every_span_slices_to_its_quote(aurelle, samples):
    from tests.conftest import sample_doc

    for sample in samples.values():
        doc = sample_doc(sample)
        for f in run_rules(doc, aurelle.rules, aurelle.terms):
            if f.span:
                assert doc.text[f.span.start : f.span.end] == f.quote, (sample["key"], f.rule_id)


def _ids_and_quotes(aurelle, text):
    doc = Document(format="text", text=text, blocks=[], images=[])
    return [(f.rule_id, f.quote) for f in run_rules(doc, aurelle.rules, aurelle.terms)]


def test_study_footnote_only_for_study_claims(aurelle):
    """Found in the Task 5 evaluation: plain percentages are not study claims."""
    plain = _ids_and_quotes(
        aurelle, "A bottle made with 30% recycled glass. Diwali: 20% off. Shop now."
    )
    assert not [q for r, q in plain if r == "DL-REQ"]
    study = _ids_and_quotes(aurelle, "Shown to reduce dark spots by 32% in 8 weeks. Shop now.")
    assert [r for r, _ in study].count("DL-REQ") == 1
    noun = _ids_and_quotes(aurelle, "A 32% reduction in visible dark spots. Shop now.")
    assert [r for r, _ in noun].count("DL-REQ") == 1
    product = _ids_and_quotes(
        aurelle, "Our Vitamin C Brightening Serum moved to a bottle made with 30% recycled glass."
    )
    assert not [q for r, q in product if r == "DL-REQ"]


def test_uppercase_url_flagged_by_gm06_not_tn03(aurelle):
    found = _ids_and_quotes(aurelle, "Visit WWW.Aurelle.example/Diwali to shop.")
    assert ("GM06", "WWW.Aurelle.example/Diwali") in found
    assert not [q for r, q in found if r == "TN-03"]


def test_brand_voice_rules_skip_image_text(aurelle, worked_example):
    tn03 = by_rule(run_rules(worked_example, aurelle.rules, aurelle.terms), "TN-03")
    assert [f.quote for f in tn03] == ["NEW"]  # not GLOW / WEEKS from the banner


def test_missing_cta_quotes_the_opening_sentence(aurelle):
    found = _ids_and_quotes(aurelle, "Got my PR package today. Obsessed.")
    assert ("CTA-01", "Got my PR package today") in found


def test_double_space_quote_is_just_the_spaces(aurelle):
    assert ("GM31", "  ") in _ids_and_quotes(aurelle, "One sentence.  Two sentences. Shop now.")


def test_cta_rule_reads_copy_not_banner_text(aurelle):
    """Found in the Task 6 live run: an image-only upload was told to add a call to action
    because the banner headline counted as copy."""
    from pathlib import Path

    from plumbline.parsers import parse_upload

    banner = Path(__file__).parents[1] / "fixtures" / "banner_v1.png"
    doc = parse_upload("banner_v1.png", banner.read_bytes(), 10)
    assert by_rule(run_rules(doc, aurelle.rules, aurelle.terms), "CTA-01") == []


def test_standard_identifiers_are_not_numbers_needing_commas(aurelle):
    """Task 13: the approved footnote "Calculated per ISO 16128." was flagged by GM10."""
    assert ("GM10", "16128") not in _ids_and_quotes(aurelle, "Calculated per ISO 16128. Shop now.")
    assert ("GM10", "120000") in _ids_and_quotes(aurelle, "Over 120000 customers. Shop now.")
