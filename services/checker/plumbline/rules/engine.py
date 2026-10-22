"""Class A rule engine: deterministic checks only. Class C rules and AI rules never run here."""

import re

from plumbline.models import Document, Finding, Fix, OcrBlock, Rule, Span, Term

LARGE_PX = 24  # WCAG large text: >= 24 px, or >= 18.66 px bold
LARGE_BOLD_PX = 18.66
ALT_TEXT_PROMPT = (
    'No alt text. Plumbline asks: "What must someone who can\'t see this image learn from it?" '
    "It writes no alt text itself."
)


def _finding(
    rule: Rule,
    quote: str,
    span: Span | None,
    explanation: str,
    *,
    rule_id: str | None = None,
    image_id: str | None = None,
    fix: Fix | None = None,
) -> Finding:
    rid = rule_id or rule.id
    where = image_id or (span.start if span else 0)
    return Finding(
        id=f"{rid}@{where}",
        category=rule.category,
        # Mandatory or graduated rules block go-live; advisory ones never show as blocking.
        severity="blocking"
        if rule.blocks
        else ("major" if rule.severity == "blocking" else rule.severity),
        advisory=not rule.blocks,
        rule_id=rid,
        fact_id=None,
        quote=quote,
        span=span,
        image_id=image_id,
        explanation=explanation,
        basis_excerpt=rule.source_ref,
        method="code",
        fix=fix,
    )


def _span(m: re.Match) -> Span:
    return Span(start=m.start(), end=m.end())


def _words_regex(words: list[str], case_sensitive: bool) -> re.Pattern:
    alts = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alts})(?!\w)", 0 if case_sensitive else re.IGNORECASE)


def _scoped_text(rule: Rule, doc: Document) -> str:
    """params.scope == "copy": text read from images by OCR is blanked with spaces, so the rule
    sees only the copy and every offset still points into doc.text."""
    if rule.params.get("scope") != "copy":
        return doc.text
    text = doc.text
    for b in doc.blocks:
        if b.kind == "ocr_text":
            text = text[: b.start] + " " * (b.end - b.start) + text[b.end :]
    return text


def _matches(rule: Rule, doc: Document, rx: re.Pattern) -> list[re.Match]:
    return [m for m in rx.finditer(_scoped_text(rule, doc)) if m.group()]


def _pattern(rule: Rule, doc: Document) -> list[Finding]:
    rx = re.compile(rule.params["regex"])
    return [_finding(rule, m.group(), _span(m), rule.title) for m in _matches(rule, doc, rx)]


def _word_list(rule: Rule, doc: Document) -> list[Finding]:
    rx = _words_regex(rule.params["words"], rule.params.get("case_sensitive", False))
    return [_finding(rule, m.group(), _span(m), rule.title) for m in _matches(rule, doc, rx)]


def _terms(rule: Rule, doc: Document, terms: list[Term]) -> list[Finding]:
    out = []
    for term in terms:
        if not term.variants:
            continue
        for m in _words_regex(term.variants, rule.params.get("case_sensitive", False)).finditer(
            doc.text
        ):
            out.append(
                _finding(
                    rule,
                    m.group(),
                    _span(m),
                    f'Use "{term.preferred}", not "{m.group()}".',
                    rule_id=term.id,
                    fix=Fix(kind="replace_term", text=term.preferred, ref_id=term.id),
                )
            )
    return out


def _count(rule: Rule, doc: Document) -> list[Finding]:
    matches = _matches(rule, doc, re.compile(rule.params["regex"]))
    limit = int(rule.params["max"])
    if len(matches) <= limit:
        return []
    # Quote the longest run of back-to-back matches ("!!!"), the clearest thing to fix.
    runs: list[list[re.Match]] = []
    for m in matches:
        if runs and runs[-1][-1].end() == m.start():
            runs[-1].append(m)
        else:
            runs.append([m])
    run = max(runs, key=len)
    span = Span(start=run[0].start(), end=run[-1].end())
    explanation = f"{rule.title}: found {len(matches)}, the limit is {limit}."
    return [_finding(rule, doc.text[span.start : span.end], span, explanation)]


def _required(rule: Rule, doc: Document) -> list[Finding]:
    text = _scoped_text(rule, doc)
    when = re.search(rule.params["when_regex"], text)
    if not when or re.search(rule.params["must_regex"], text):
        return []
    explanation = rule.params.get("message") or rule.title
    return [_finding(rule, when.group(), _span(when), explanation)]


def _luminance(hex_: str) -> float:
    c = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2 contrast ratio, rounded to 2 decimals."""
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _is_large(block: OcrBlock) -> bool:
    return block.px_height >= LARGE_PX or (block.bold and block.px_height >= LARGE_BOLD_PX)


def _ocr_span(doc: Document, image_id: str, text: str) -> Span | None:
    for b in doc.blocks:
        if b.image_id == image_id and doc.text[b.start : b.end] == text:
            return Span(start=b.start, end=b.end)
    return None


def _contrast(rule: Rule, doc: Document) -> list[Finding]:
    out = []
    for image in doc.images:
        for block in image.ocr:
            if block.busy_background:  # colours unreliable: coverage reports it as not checked
                continue
            ratio = contrast_ratio(block.fg_hex, block.bg_hex)
            large = _is_large(block)
            minimum = rule.params["min_large"] if large else rule.params["min_normal"]
            if ratio >= minimum:
                continue
            explanation = (
                f'Text "{block.text}" is {ratio:.2f}:1 ({block.fg_hex} on {block.bg_hex}); '
                f"the minimum for {'large' if large else 'normal'} text is {minimum:g}:1."
            )
            out.append(
                _finding(
                    rule,
                    block.text,
                    _ocr_span(doc, image.id, block.text),
                    explanation,
                    image_id=image.id,
                )
            )
    return out


def _alt_text(rule: Rule, doc: Document) -> list[Finding]:
    return [
        _finding(rule, "", None, ALT_TEXT_PROMPT, image_id=image.id, fix=Fix(kind="none"))
        for image in doc.images
        if not image.decorative and not image.alt_text
    ]


def run_rules(doc: Document, rules: list[Rule], terms: list[Term]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if rule.cls == "C" or rule.check_type == "ai_rule":
            continue
        if rule.check_type == "pattern":
            findings += _pattern(rule, doc)
        elif rule.check_type == "word_list":
            findings += (
                _terms(rule, doc, terms)
                if rule.params.get("source") == "terms"
                else _word_list(rule, doc)
            )
        elif rule.check_type == "count":
            findings += _count(rule, doc)
        elif rule.check_type == "required":
            findings += _required(rule, doc)
        elif rule.check_type == "contrast":
            findings += _contrast(rule, doc)
        elif rule.check_type == "alt_text":
            findings += _alt_text(rule, doc)
    return findings
