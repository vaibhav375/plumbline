import re

from plumbline.models import Document, ParseError
from plumbline.normalize import normalize


def parse_text(data: bytes, b) -> Document:
    try:
        raw = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ParseError("unsupported") from None
    for para in re.split(r"\n\s*\n", normalize(raw)):
        b.add(para)
    return b.build("text")
