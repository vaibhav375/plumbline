"""Check every ruling's quoted claims against the source text. ASA: the ruling page is fetched; ASCI: the
press-release PDF is downloaded and read. A claim passes if its letters and digits appear, in order, in the
source (quotes, dashes, spacing and case ignored). Prints failures; exits 1 if any."""
import re
import sys
import httpx
from io import BytesIO

from asci_rulings import ASCI
from asa_part1 import ASA
from asa_part2 import ASA2


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9%]", "", s.lower().replace("&amp;", "&"))


def page_text(url: str) -> str:
    # httpx, not urllib: it ships its own CA bundle (the system store is missing on some machines).
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (verification)"}, timeout=60, follow_redirects=True)
    r.raise_for_status()
    raw = r.content
    if url.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() for p in PdfReader(BytesIO(raw)).pages)
    html = raw.decode("utf-8", errors="replace")
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    import html as h
    return h.unescape(re.sub(r"<[^>]+>", " ", html))


def main() -> int:
    cache: dict[str, str] = {}
    bad = 0
    for r in ASA + ASA2 + ASCI:
        if r["url"] not in cache:
            try:
                cache[r["url"]] = norm(page_text(r["url"]))
            except Exception as ex:  # noqa: BLE001
                cache[r["url"]] = ""
                print(f"{r['id']}: could not read {r['url']}: {ex}")
        src = cache[r["url"]]
        for c in r["claims"]:
            if norm(c["text"]) not in src:
                bad += 1
                print(f"{r['id']}: NOT FOUND in source: {c['text'][:90]!r}")
    print(f"checked {sum(len(r['claims']) for r in ASA + ASA2 + ASCI)} claims in {len(ASA + ASA2 + ASCI)} rulings; {bad} not found")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
