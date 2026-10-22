from plumbline.normalize import normalize, quote_in


def test_quote_in_curly_vs_straight():
    text = "He said “clinically proven”"
    span = quote_in(text, '"clinically proven"')
    assert span is not None
    assert text[span.start : span.end] == "“clinically proven”"


def test_quote_in_emoji_and_hindi():
    text = "✨ नया Vitamin C serum ✨"
    span = quote_in(text, "Vitamin C serum")
    assert span is not None
    assert text[span.start : span.end] == "Vitamin C serum"


def test_quote_in_ignores_case_and_whitespace_runs():
    text = "Clinically   proven\nto fade"
    span = quote_in(text, "clinically proven to fade")
    assert span is not None and text[span.start : span.end] == text


def test_quote_in_apostrophes():
    text = "Aurelle’s new serum"
    span = quote_in(text, "Aurelle's new serum")
    assert span is not None and span.start == 0


def test_quote_in_missing_returns_none():
    assert quote_in("Meet the new serum", "clinically proven") is None
    assert quote_in("anything", "   ") is None


def test_normalize_crlf_nbsp_nfc_and_keeps_curly_quotes():
    raw = "﻿Café\r\nprice ₹899\r“quoted”"
    assert normalize(raw) == "Café\nprice ₹899\n“quoted”"


def test_normalize_then_quote_offsets_land_on_the_right_characters():
    """Review Focus 4: offsets into the stored (normalised) text must slice back to the quote."""
    raw = "Dhoop mein bhi no tension 😎\r\nSPF 50 Daily Sunscreen — “no white cast”"
    text = normalize(raw)
    for q in ("SPF 50 Daily Sunscreen", '"no white cast"', "no tension 😎"):
        span = quote_in(text, q)
        assert span is not None, q
        assert text[span.start : span.end].replace("“", '"').replace("”", '"').lower() == q.lower()
