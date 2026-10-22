import io
import re

import pdfplumber
from pdfminer.pdfdocument import PDFEncryptionError, PDFPasswordIncorrect
from pdfplumber.utils.exceptions import PdfminerException

from plumbline.models import Document, ParseError


def _encrypted(e: BaseException) -> bool:
    causes = [e, *e.args, e.__cause__, e.__context__]
    return any(isinstance(c, PDFPasswordIncorrect | PDFEncryptionError) for c in causes)


def parse_pdf(data: bytes, b) -> Document:
    # Images inside PDFs are not extracted in Round 2: reading their alt text needs the tagged
    # structure tree. The coverage statement says so instead of guessing.
    has_images = False
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                has_images |= bool(page.images)
                for para in re.split(r"\n\s*\n", page.extract_text() or ""):
                    b.add(para)
    except PdfminerException as e:
        raise ParseError("encrypted" if _encrypted(e) else "unsupported") from None
    except (PDFPasswordIncorrect, PDFEncryptionError):
        raise ParseError("encrypted") from None
    if not b.blocks:
        raise ParseError("no_text_layer" if has_images else "empty")
    return b.build("pdf")
