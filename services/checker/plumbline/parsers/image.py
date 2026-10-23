import io
from statistics import median

import pytesseract
from PIL import Image, UnidentifiedImageError

from plumbline.models import Document, OcrBlock, ParseError

MAX_SIDE = 2000
SPARSE_MIN_CONF = 60.0


def _otsu(hist: list[int]) -> int:
    total = sum(hist)
    sum_all = sum(i * h for i, h in enumerate(hist))
    w_bg = sum_bg = 0
    best_var, best_t = -1.0, 0
    for t, h in enumerate(hist):
        w_bg += h
        if w_bg == 0:
            continue
        w_fg = total - w_bg
        if w_fg == 0:
            break
        sum_bg += t * h
        var = w_bg * w_fg * (sum_bg / w_bg - (sum_all - sum_bg) / w_fg) ** 2
        if var > best_var:
            best_var, best_t = var, t
    return best_t


def _hex(pixels: list[tuple[int, int, int]]) -> str:
    return "#" + "".join(f"{int(median(p[i] for p in pixels)):02X}" for i in range(3))


def text_colours(crop: Image.Image) -> tuple[str, str]:
    """Binarise with Otsu; text is the minority class, background the majority."""
    rgb = list(crop.get_flattened_data())
    gray = list(crop.convert("L").get_flattened_data())
    t = _otsu(crop.convert("L").histogram())
    dark = [p for p, g in zip(rgb, gray, strict=True) if g <= t]
    light = [p for p, g in zip(rgb, gray, strict=True) if g > t]
    if not dark or not light:
        return _hex(rgb), _hex(rgb)
    fg, bg = (dark, light) if len(dark) < len(light) else (light, dark)
    return _hex(fg), _hex(bg)


def ocr_image(img: Image.Image) -> list[OcrBlock]:
    img = img.convert("RGB")
    scale = min(1.0, MAX_SIDE / max(img.size))
    if scale < 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)))
    # Default layout analysis keeps multi-line headlines together but finds nothing on busy,
    # photo-like backgrounds; sparse mode (psm 11) then reads them, so fall back to it and keep
    # only confident words that contain a letter or digit.
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    min_conf = 0.0
    if not any(
        w.strip() and float(c) >= SPARSE_MIN_CONF
        for w, c in zip(data["text"], data["conf"], strict=True)
    ):
        data = pytesseract.image_to_data(
            img, config="--psm 11", output_type=pytesseract.Output.DICT
        )
        min_conf = SPARSE_MIN_CONF
    groups: dict[tuple[int, int], list[int]] = {}
    for i, word in enumerate(data["text"]):
        if any(ch.isalnum() for ch in word) and float(data["conf"][i]) >= min_conf:
            groups.setdefault((data["block_num"][i], data["par_num"][i]), []).append(i)
    blocks = []
    for idx in groups.values():
        left = min(data["left"][i] for i in idx)
        top = min(data["top"][i] for i in idx)
        right = max(data["left"][i] + data["width"][i] for i in idx)
        bottom = max(data["top"][i] + data["height"][i] for i in idx)
        fg, bg = text_colours(img.crop((left, top, right, bottom)))
        blocks.append(
            OcrBlock(
                text=" ".join(data["text"][i] for i in idx),
                bbox=tuple(round(v / scale) for v in (left, top, right, bottom)),
                confidence=round(sum(float(data["conf"][i]) for i in idx) / len(idx), 1),
                # ponytail: word-box height (≈ cap height) stands in for font size; it under-reads
                # size, so large text is judged against 4.5:1 more often than strictly needed.
                px_height=round(max(data["height"][i] for i in idx) / scale),
                # Tesseract can't tell weight; treating text as regular is the strict side.
                bold=False,
                fg_hex=fg,
                bg_hex=bg,
                busy_background=min_conf > 0,
            )
        )
    return blocks


def parse_image(data: bytes, b, alt_text: str | None = None, decorative: bool = False) -> Document:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Image.DecompressionBombError:
        raise ParseError("too_large") from None
    except (UnidentifiedImageError, OSError):
        raise ParseError("unsupported") from None
    b.add_image(img, img.width, img.height, alt_text=alt_text, decorative=decorative)
    return b.build("image")
