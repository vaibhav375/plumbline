from pathlib import Path

import pytest

from plumbline.models import ParseError
from plumbline.parsers import parse_upload

FIX = Path(__file__).parent / "fixtures"


def parse(name: str, max_mb: int = 10):
    return parse_upload(name, (FIX / name).read_bytes(), max_mb)


def code_of(fn) -> str:
    with pytest.raises(ParseError) as e:
        fn()
    return e.value.code


def lab(hex_: str) -> tuple[float, float, float]:
    rgb = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)
    x, y, z = (
        (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047,
        0.2126 * r + 0.7152 * g + 0.0722 * b,
        (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883,
    )
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def delta_e(a: str, b: str) -> float:  # CIE76
    return sum((p - q) ** 2 for p, q in zip(lab(a), lab(b), strict=True)) ** 0.5


def test_parse_text_keeps_offsets_and_blocks():
    doc = parse_upload("post.txt", b"First para.\r\n\r\nSecond para.", 10)
    assert doc.format == "text"
    assert doc.text == "First para.\n\nSecond para."
    assert [doc.text[b.start : b.end] for b in doc.blocks] == ["First para.", "Second para."]


def test_parse_docx_alt_text():
    doc = parse("post.docx")
    assert doc.format == "docx"
    assert "clinically proven" in doc.text
    assert doc.images[0].alt_text is None
    assert doc.images[1].alt_text == "Aurelle logo"
    assert any(b.kind == "heading" for b in doc.blocks)


def test_parse_pdf_text():
    doc = parse("post.pdf")
    assert doc.format == "pdf"
    assert "clinically proven" in doc.text


def test_scanned_pdf():
    assert code_of(lambda: parse("scanned.pdf")) == "no_text_layer"


def test_encrypted_pdf():
    assert code_of(lambda: parse("encrypted.pdf")) == "encrypted"


def test_empty():
    assert code_of(lambda: parse("empty.txt")) == "empty"
    assert code_of(lambda: parse_upload("blank.txt", b"  \n\t ", 10)) == "empty"


def test_too_large():
    assert code_of(lambda: parse_upload("big.txt", b"a" * (11 * 1024 * 1024), 10)) == "too_large"


def test_unsupported_and_corrupt():
    assert code_of(lambda: parse_upload("deck.pptx", b"PK\x03\x04", 10)) == "unsupported"
    assert code_of(lambda: parse_upload("fake.pdf", b"not a pdf", 10)) == "unsupported"
    assert code_of(lambda: parse_upload("fake.docx", b"not a zip", 10)) == "unsupported"


def test_parse_error_has_plain_message():
    with pytest.raises(ParseError) as e:
        parse("encrypted.pdf")
    assert "password" in str(e.value).lower()


def test_png_ocr():
    doc = parse("banner_v1.png")
    assert doc.format == "image"
    image = doc.images[0]
    assert image.alt_text is None and (image.width, image.height) == (1080, 1080)
    block = next(b for b in image.ocr if "GLOW IN 2 WEEKS" in b.text)
    assert delta_e(block.fg_hex, "#B8B2A7") <= 5, block.fg_hex
    assert delta_e(block.bg_hex, "#FBF6EC") <= 5, block.bg_hex
    assert block.px_height >= 24
    ocr = next(
        b for b in doc.blocks if b.kind == "ocr_text" and "GLOW" in doc.text[b.start : b.end]
    )
    assert ocr.image_id == image.id


def test_text_over_busy_background_is_still_read():
    """Default Tesseract layout analysis finds nothing on photo-like backgrounds; the sparse
    fallback must still read the overlaid text, without background noise."""
    import io
    import random

    from PIL import Image, ImageDraw, ImageFont

    rnd = random.Random(1)
    img = Image.new("RGB", (4000, 3000))
    d = ImageDraw.Draw(img)
    for _ in range(3000):
        x, y = rnd.randrange(4000), rnd.randrange(3000)
        box = (x, y, x + rnd.randrange(20, 200), y + rnd.randrange(20, 200))
        d.ellipse(box, fill=tuple(rnd.randrange(256) for _ in range(3)))
    d.rectangle((300, 300, 2600, 700), fill="#FBF6EC")
    d.text((340, 360), "SALE ENDS SUNDAY", font=ImageFont.load_default(size=220), fill="#222222")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    doc = parse_upload("photo.jpg", buf.getvalue(), 10)
    assert "SALE" in doc.text
    assert all(any(c.isalnum() for c in w) for w in doc.text.split())
    assert all(b.busy_background for b in doc.images[0].ocr)


def test_clean_banner_is_not_marked_busy():
    assert not any(b.busy_background for b in parse("banner_v1.png").images[0].ocr)
