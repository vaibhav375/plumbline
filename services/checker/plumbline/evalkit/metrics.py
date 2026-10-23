"""Scoring. A prediction hits a label when it carries the label's ID (rule, term or fact) and its
span overlaps the label's quote. A label with an empty quote is document-level (something required
is missing) and matches on the ID alone."""

from plumbline.health import wilson_lower
from plumbline.models import Finding


def wilson_interval(k: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval. The upper bound is the mirror of the lower bound for n - k."""
    if n == 0:
        return (0.0, 1.0)
    return (wilson_lower(k, n), 1 - wilson_lower(n - k, n))


def resolve_labels(text: str, labels: list[dict]) -> list[dict]:
    out = []
    for lab in labels:
        quote = lab["quote"]
        start = text.find(quote) if quote else None
        if start == -1:
            raise ValueError(f"label quote {quote!r} not in the text")
        end = None if start is None else start + len(quote)
        out.append({"id": lab["rule_or_fact_id"], "start": start, "end": end})
    return out


def _ids(f: Finding) -> set[str]:
    return {i for i in (f.rule_id, f.fact_id) if i}


def _hits(f: Finding, lab: dict) -> bool:
    if lab["id"] not in _ids(f):
        return False
    if lab["start"] is None:
        return True
    return f.span is not None and f.span.start < lab["end"] and lab["start"] < f.span.end


def score(predicted: list[Finding], labels: list[dict]) -> dict[str, int]:
    """A second prediction on an already-matched label is a duplicate: neither a hit nor a false
    alarm (the reader sees the same problem twice)."""
    matched: set[int] = set()
    tp = fp = dup = 0
    for f in predicted:
        hit = next((i for i, lab in enumerate(labels) if _hits(f, lab)), None)
        if hit is None:
            fp += 1
        elif hit in matched:
            dup += 1
        else:
            matched.add(hit)
            tp += 1
    return {"tp": tp, "fp": fp, "fn": len(labels) - len(matched), "dup": dup}


def citation_valid(f: Finding, text: str, known_ids: set[str]) -> bool:
    """Every cited ID exists in the rulebook, term list or fact ledger, and the quote is really at
    its span (image and document-level findings have no quote to check)."""
    if not _ids(f) or not _ids(f) <= known_ids:
        return False
    if not f.quote:
        return True
    return f.span is not None and text[f.span.start : f.span.end] == f.quote
