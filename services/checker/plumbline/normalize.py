import re
import unicodedata

from plumbline.models import Span

_SPACES = re.compile("[\u00a0\u2007\u202f]")
_DOUBLE = '"“”„‟«»'
_SINGLE = "'‘’‚‛`"


def normalize(raw: str) -> str:
    """NFC, CRLF/CR → LF, non-breaking spaces → space, BOM dropped. Curly quotes are kept, so
    the stored text is what the user sees and offsets map 1:1."""
    text = unicodedata.normalize("NFC", raw).lstrip("\ufeff")
    return _SPACES.sub(" ", text.replace("\r\n", "\n").replace("\r", "\n"))


def _pattern(quote: str) -> str:
    out = []
    for ch in quote:
        if ch.isspace():
            if not out or out[-1] != r"\s+":
                out.append(r"\s+")
        elif ch in _DOUBLE:
            out.append(f"[{_DOUBLE}]")
        elif ch in _SINGLE:
            out.append(f"[{_SINGLE}]")
        else:
            out.append(re.escape(ch))
    return "".join(out)


def quote_in(text: str, quote: str) -> Span | None:
    """Find quote in text ignoring case, whitespace runs and straight/curly quotes."""
    quote = normalize(quote).strip()
    if not quote:
        return None
    m = re.search(_pattern(quote), text, re.IGNORECASE)
    return Span(start=m.start(), end=m.end()) if m else None
