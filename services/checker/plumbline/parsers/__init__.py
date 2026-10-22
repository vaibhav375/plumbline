"""parse_upload: bytes in, one Document out, or a ParseError with a plain-words message."""

from pathlib import Path

from PIL import Image

from plumbline.models import Block, Document, ImageAsset, ParseError
from plumbline.normalize import normalize

KINDS = {
    ".txt": "text",
    ".md": "text",
    ".docx": "docx",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
}


class DocBuilder:
    """Joins blocks with blank lines and records each block's offsets into the final text."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.blocks: list[Block] = []
        self.images: list[ImageAsset] = []
        self.pos = 0

    def add(self, text: str, kind: str = "paragraph", image_id: str | None = None) -> None:
        text = normalize(text).strip()
        if not text:
            return
        if self.parts:
            self.parts.append("\n\n")
            self.pos += 2
        self.blocks.append(
            Block(
                id=f"b{len(self.blocks) + 1}",
                kind=kind,
                start=self.pos,
                end=self.pos + len(text),
                image_id=image_id,
            )
        )
        self.parts.append(text)
        self.pos += len(text)

    def add_image(
        self,
        img: Image.Image | None,
        width: int,
        height: int,
        alt_text: str | None,
        decorative: bool = False,
    ) -> None:
        from plumbline.parsers.image import ocr_image

        asset = ImageAsset(
            id=f"img{len(self.images) + 1}",
            width=width,
            height=height,
            alt_text=(alt_text or "").strip() or None,
            decorative=decorative,
            ocr=ocr_image(img) if img is not None else [],
        )
        self.images.append(asset)
        for block in asset.ocr:
            self.add(block.text, "ocr_text", asset.id)

    def build(self, fmt: str) -> Document:
        if not self.blocks and not self.images:
            raise ParseError("empty")
        return Document(
            format=fmt, text="".join(self.parts), blocks=self.blocks, images=self.images
        )


def parse_upload(filename: str, data: bytes, max_mb: int) -> Document:
    if not data:
        raise ParseError("empty")
    if len(data) > max_mb * 1024 * 1024:
        raise ParseError("too_large", max_mb)
    kind = KINDS.get(Path(filename).suffix.lower())
    if kind is None:
        raise ParseError("unsupported")
    if kind == "text":
        from plumbline.parsers.text import parse_text as parse
    elif kind == "docx":
        from plumbline.parsers.docx import parse_docx as parse
    elif kind == "pdf":
        from plumbline.parsers.pdf import parse_pdf as parse
    else:
        from plumbline.parsers.image import parse_image as parse
    return parse(data, DocBuilder())
