"""All shared pydantic types. Offsets are Python string indices (Unicode code points) into
Document.text; the web converts them to UTF-16 before highlighting."""

from typing import Literal

from pydantic import BaseModel


class Span(BaseModel):
    start: int
    end: int


class OcrBlock(BaseModel):
    text: str
    bbox: tuple[int, int, int, int]  # left, top, right, bottom in original image pixels
    confidence: float
    px_height: int
    bold: bool
    fg_hex: str
    bg_hex: str
    # Read by the sparse fallback over a photo-like background: the text is usable for claims,
    # but the box and colours are not reliable, so contrast is reported as not checked.
    busy_background: bool = False


class ImageAsset(BaseModel):
    id: str
    width: int
    height: int
    alt_text: str | None
    decorative: bool = False
    ocr: list[OcrBlock] = []


class Block(BaseModel):
    id: str
    kind: Literal["paragraph", "heading", "caption", "ocr_text"]
    start: int
    end: int
    image_id: str | None = None


class Document(BaseModel):
    format: Literal["text", "docx", "pdf", "image"]
    text: str
    blocks: list[Block]
    images: list[ImageAsset]


ParseCode = Literal["empty", "too_large", "unsupported", "encrypted", "no_text_layer"]

PARSE_MESSAGES: dict[str, str] = {
    "empty": "This file is empty. Paste some text or upload a file with content.",
    "too_large": "This file is larger than {max_mb} MB. Upload a smaller file.",
    "unsupported": "This file type can't be checked. Use plain text, DOCX, PDF, PNG or JPG.",
    "encrypted": "This PDF is password-protected. Remove the password and upload it again.",
    "no_text_layer": (
        "This PDF has no text layer (it looks scanned). "
        "Upload the original document or paste the text."
    ),
}


class ParseError(Exception):
    def __init__(self, code: ParseCode, max_mb: int = 10):
        self.code = code
        super().__init__(PARSE_MESSAGES[code].format(max_mb=max_mb))
