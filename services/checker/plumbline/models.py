"""All shared pydantic types. Offsets are Python string indices (Unicode code points) into
Document.text; the web converts them to UTF-16 before highlighting."""

from datetime import date
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


class Rule(BaseModel):
    id: str
    title: str
    category: Literal[
        "claim",
        "tone",
        "terminology",
        "accessibility",
        "visual",
        "confidential",
        "required",
        "style",
    ]
    cls: Literal["A", "B", "C"]
    check_type: Literal[
        "pattern", "word_list", "count", "required", "contrast", "alt_text", "ai_rule"
    ]
    params: dict
    severity: Literal["blocking", "major", "minor"]
    tier: Literal["mandatory", "brand"]
    maturity: Literal["advisory", "blocking"] = "advisory"
    examples_good: list[str] = []
    examples_bad: list[str] = []
    source_ref: str
    owner_function: Literal["brand", "compliance", "accessibility"]

    @property
    def blocks(self) -> bool:
        """Mandatory rules block from go-live; brand rules only once they've graduated."""
        return self.tier == "mandatory" or self.maturity == "blocking"


class Term(BaseModel):
    id: str
    preferred: str
    variants: list[str]


class Fact(BaseModel):
    id: str
    statement: str
    value: float | None
    unit: str | None
    product: str | None
    market: str
    population: str | None
    duration: str | None
    owner: str
    valid_from: date
    valid_until: date | None
    confidentiality: Literal["public", "internal", "confidential", "embargoed"]
    embargo_until: date | None
    verified: bool
    aliases: list[str] = []

    @property
    def code_only(self) -> bool:
        return self.confidentiality in {"confidential", "embargoed"}


class ApprovedWording(BaseModel):
    id: str
    fact_id: str
    market: str
    channel: str
    text: str
    disclaimer: str | None


class OrgContext(BaseModel):
    org_id: str
    rulebook_version: str
    rules: list[Rule]
    facts: list[Fact]
    wordings: list[ApprovedWording]
    terms: list[Term]


class Fix(BaseModel):
    kind: Literal["approved_wording", "rewrite", "remove", "replace_term", "none"]
    text: str | None = None
    ref_id: str | None = None
    note: str | None = None


class Finding(BaseModel):
    id: str
    category: str
    severity: str
    advisory: bool
    rule_id: str | None
    fact_id: str | None
    quote: str
    span: Span | None
    image_id: str | None
    explanation: str
    basis_excerpt: str
    method: Literal["code", "ai", "ai+code"]
    model: str | None = None
    support: Literal["agree", "disagree", "n/a"] = "n/a"
    fix: Fix | None = None
