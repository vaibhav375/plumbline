import io
import zipfile

from docx import Document as open_docx
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image, UnidentifiedImageError

from plumbline.models import Document, ParseError

EMU_PER_PX = 9525  # at 96 dpi


def _kind(p: Paragraph) -> str:
    name = (p.style.name if p.style is not None else "") or ""
    if name.startswith(("Heading", "Title")):
        return "heading"
    return "caption" if name == "Caption" else "paragraph"


def _images(doc, el, b) -> None:
    for drawing in el.iter(qn("wp:inline"), qn("wp:anchor")):
        pr = drawing.find(qn("wp:docPr"))
        if pr is None:
            continue
        decorative = 'decorative val="1"' in pr.xml if hasattr(pr, "xml") else False
        extent = drawing.find(qn("wp:extent"))
        width = int(extent.get("cx", 0)) // EMU_PER_PX if extent is not None else 0
        height = int(extent.get("cy", 0)) // EMU_PER_PX if extent is not None else 0
        img = None
        blip = drawing.find(".//" + qn("a:blip"))
        rid = blip.get(qn("r:embed")) if blip is not None else None
        if rid in doc.part.related_parts:
            try:
                img = Image.open(io.BytesIO(doc.part.related_parts[rid].blob))
                img.load()
                width, height = img.size
            except (UnidentifiedImageError, OSError):  # EMF/WMF and friends: no OCR
                img = None
        b.add_image(img, width, height, pr.get("descr"), decorative)


def parse_docx(data: bytes, b) -> Document:
    try:
        doc = open_docx(io.BytesIO(data))
    except (zipfile.BadZipFile, PackageNotFoundError, KeyError, ValueError):
        raise ParseError("unsupported") from None
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            p = Paragraph(el, doc)
            b.add(p.text, _kind(p))
            _images(doc, el, b)
        elif el.tag == qn("w:tbl"):
            for row in Table(el, doc).rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        b.add(p.text)
    return b.build("docx")
