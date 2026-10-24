"""Fixes and the intent lock (§6.2 stage 7).

Claims are only ever fixed with approved wording; anything else a sentence needs comes from a
deterministic code fix (term swaps, punctuation, case) or, for non-claim findings, a minimal AI
rewrite that is thrown away if it adds a number or a claim, breaks the intent lock, or creates a
new finding. Never invent a claim.
"""

import difflib
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel
from rapidfuzz import fuzz

from plumbline.claims import Claim, detect_claims
from plumbline.llm import LLM, LLMUnavailable
from plumbline.models import (
    CHANNEL_LIMITS,
    Document,
    Finding,
    Fix,
    Intent,
    IntentResult,
    Rule,
    Span,
    Term,
)
from plumbline.normalize import quote_in, sentences
from plumbline.privacy import redact
from plumbline.rules.engine import run_rules

REWRITE_PROMPT = (Path(__file__).parent / "prompts" / "rewrite.txt").read_text(encoding="utf-8")
FLAGGED = {"unsupported", "contradicted", "restricted", "needs_human", "outdated"}
REMOVED = {
    "unsupported",
    "contradicted",
}  # claims without approved wording leave the suggested version


class _Rewrite(BaseModel):
    sentence: str


def _overlaps(a: Span, b: Span) -> bool:
    return a.start < b.end and b.start < a.end


def code_fix(f: Finding, rules: dict[str, Rule]) -> Fix | None:
    """The finding's own fix, or a deterministic one from the rule's `fix` setting."""
    if f.fix and f.fix.kind != "none":
        return f.fix
    rule = rules.get(f.rule_id or "")
    spec = rule.params.get("fix") if rule else None
    if spec == "lowercase":
        return Fix(kind="replace_term", text=f.quote.lower())
    if isinstance(spec, str):
        return Fix(kind="replace_term", text=spec)
    return None


def apply_fixes(text: str, findings: list[Finding], accepted_ids: set[str]) -> str:
    """Span edits, first-listed wins on overlap, applied right to left so offsets stay valid."""
    edits: list[tuple[Span, str]] = []
    for f in findings:
        if f.id not in accepted_ids or f.span is None or f.fix is None or f.fix.kind == "none":
            continue
        if any(_overlaps(f.span, s) for s, _ in edits):
            continue
        edits.append((f.span, "" if f.fix.kind == "remove" else (f.fix.text or "")))
    for span, new in sorted(edits, key=lambda e: e[0].start, reverse=True):
        before, after = text[: span.start], text[span.end :]
        # Keep sentence case at the seams only, so the writer's untouched words never change: a
        # replacement that starts a sentence is capitalised, and so is a word a new full stop starts.
        if new and (not before.strip() or before.rstrip()[-1] in ".!?"):
            new = new[0].upper() + new[1:]
        if new.rstrip()[-1:] in (".", "!", "?"):
            after = re.sub(r"^(\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), after)
        text = before + new + after
    notes = [f.fix.footnote for f in findings if f.id in accepted_ids and f.fix and f.fix.footnote]
    missing = [n for n in dict.fromkeys(notes) if n not in text]
    return _tidy(text) + ("\n" + "\n".join(missing) if missing else "")


def _tidy(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"(?:,\s*)+(?:\b(?:and|or)\s*)?([.!?])", r"\1", text)  # "x, and ." -> "x."
    text = re.sub(r"([.!?])\s*(?:and|or)\b\s*", r"\1 ", text)
    text = re.sub(r"\s+(?:and|or|with)\s*([.!?])", r"\1", text)
    return text.strip()


FRAGMENT_START = {"with", "for", "and", "or", "but", "by", "in", "on", "to", "of", "from", "at"}
FRAGMENT_END = {
    "the",
    "a",
    "an",
    "for",
    "with",
    "and",
    "or",
    "of",
    "to",
    "is",
    "are",
    "in",
    "on",
    "by",
    "at",
    "from",
    "our",
    "your",
}


def _is_fragment(sentence: str) -> bool:
    """What's left after removing a claim clause, if it no longer stands as a sentence."""
    words = re.findall(r"[\w'-]+", sentence.lower())
    return len(words) < 3 or words[0] in FRAGMENT_START or words[-1] in FRAGMENT_END


def _as_sentence(wording: str) -> str:
    """Approved wording as a sentence: capitalised, full stop before any footnote star."""
    w = wording.strip()
    star = w.endswith("*")
    w = w.rstrip("*").rstrip()
    if w and w[-1] not in ".!?":
        w += "."
    return (w[:1].upper() + w[1:]) + ("*" if star else "")


def propose_rewrite(
    sentence: str,
    finding: Finding,
    llm: LLM,
    rule: Rule | None = None,
    product_names: set[str] = frozenset(),
    allow: set[str] = frozenset(),
) -> str | None:
    """A minimal AI edit for a non-claim finding, or None. Claims are never rewritten."""
    if finding.category in ("claim", "confidential") or finding.claim_status:
        return None
    safe, restore = redact(sentence, set(allow) | set(product_names))
    system = REWRITE_PROMPT.format(
        rule_id=finding.rule_id,
        rule_title=rule.title if rule else finding.rule_id,
        explanation=finding.explanation,
        product_names=", ".join(sorted(product_names)) or "none",
    )
    try:
        result, _ = llm.json("rewrite", system, f"Sentence: «{safe}»", _Rewrite)
    except LLMUnavailable:
        return None
    new = result.sentence.strip()
    for placeholder, original in restore.items():
        new = new.replace(placeholder, original)
    if not new or "⟦" in new or len(new) > 2 * len(sentence) + 40:
        return None
    if set(re.findall(r"\d+", new)) - set(re.findall(r"\d+", sentence)):
        return None  # a number the writer never wrote

    def kinds(t: str) -> set[str]:
        return {
            c.kind
            for c in detect_claims(
                Document(format="text", text=t, blocks=[], images=[]), ignore=set(product_names)
            )
        }

    if kinds(new) - kinds(sentence):
        return None  # a new kind of claim
    return new


def check_intent(
    before: str,
    after: str,
    intent: Intent,
    findings: list[Finding],
    claims_before: list[Claim],
    footnotes: list[str] = (),
) -> IntentResult:
    """The five checks. Footnotes the fixes added (required disclaimers) aren't edits to the copy."""
    added = {n.strip() for n in footnotes}

    def copy_only(t: str) -> str:  # footnotes (starred lines and added disclaimers) aren't copy
        return "\n".join(
            ln
            for ln in t.splitlines()
            if ln.strip() not in added and not ln.lstrip().startswith("*")
        )

    body = copy_only(after)
    cta_kept = not intent.cta or bool(re.search(rf"(?i)\b{re.escape(intent.cta)}", body))
    pinned = all(
        quote_in(body, p) or fuzz.partial_ratio(p.lower(), body.lower()) >= 90
        for p in intent.key_phrases
    )

    def accounted(c: Claim) -> bool:
        if quote_in(after, c.text):
            return True
        related = [f for f in findings if f.span and _overlaps(f.span, c.span)]
        if any(
            f.fix
            and f.fix.kind == "approved_wording"
            and f.fix.text
            and quote_in(after, f.fix.text.rstrip("*"))
            for f in related
        ):
            return True
        return any(f.claim_status in FLAGGED or f.category == "confidential" for f in related)

    before_spans = [
        sp for sp in sentences(before) if not before[sp.start : sp.end].lstrip().startswith("*")
    ]
    flagged = [any(f.span and _overlaps(f.span, s) for f in findings) for s in before_spans]
    old = [before[s.start : s.end].strip() for s in before_spans]
    new = [body[s.start : s.end].strip() for s in sentences(body)]
    in_flagged = True
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(
        None, old, new, autojunk=False
    ).get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert" or not all(flagged[i1:i2]):
            in_flagged = False
    return IntentResult(
        cta_kept=cta_kept,
        pinned_phrases_kept=pinned,
        no_claim_dropped=all(accounted(c) for c in claims_before),
        channel_limits_ok=len(after) <= CHANNEL_LIMITS[intent.channel],
        edits_in_flagged_sentences=in_flagged,
    )


def _fix_sentence(
    doc: Document, s: Span, findings: list[Finding], rules: dict[str, Rule]
) -> tuple[str | None, list[str]]:
    """Deterministic fixes for one sentence: (new sentence or None to drop it, footnotes)."""
    text = doc.text
    inside = [f for f in findings if f.span and _overlaps(f.span, s)]
    if any(
        f.claim_status == "restricted"
        or (f.fix and f.fix.kind == "remove" and f.category == "confidential")
        for f in inside
    ):
        return None, []
    claim_fs = [f for f in inside if f.category == "claim" and f.claim_status]
    edits: list[tuple[Span, str]] = []
    footnotes: list[str] = []
    for f in claim_fs:
        if f.fix and f.fix.kind == "approved_wording" and f.fix.text:
            edits.append((f.span, f.fix.text))
            if f.fix.footnote:
                footnotes.append(f.fix.footnote)
        elif f.claim_status in REMOVED:
            edits.append((f.span, ""))
    claimed = [f.span for f in claim_fs]
    rest = "".join(
        ch
        for i, ch in enumerate(text[s.start : s.end], s.start)
        if not any(sp.start <= i < sp.end for sp in claimed)
    )
    removed_claim = any(new == "" for _, new in edits)
    if edits and not re.search(r"(?i)\b(?!and\b|or\b|with\b|the\b)[a-z]{3,}", rest):
        # The sentence is only claims: rebuild it from its approved wordings and kept claims.
        parts = []
        for f in sorted(claim_fs, key=lambda f: f.span.start):
            if f.fix and f.fix.kind == "approved_wording" and f.fix.text:
                parts.append(_as_sentence(f.fix.text))
            elif f.claim_status not in REMOVED:
                parts.append(_as_sentence(text[f.span.start : f.span.end]))
        return (" ".join(parts) or None), footnotes
    for f in inside:
        if f in claim_fs or any(_overlaps(f.span, sp) for sp, _ in edits):
            continue
        if fix := code_fix(f, rules):
            edits.append((f.span, "" if fix.kind == "remove" else (fix.text or "")))
    out = text[s.start : s.end]
    for span, new in sorted(edits, key=lambda e: e[0].start, reverse=True):
        out = out[: span.start - s.start] + new + out[span.end - s.start :]
    out = _tidy(out)
    if removed_claim and _is_fragment(out):
        return None, footnotes  # e.g. "Ceramide Barrier Cream is the." after removing the claim
    if out and out[0].islower() and text[s.start].isupper():
        out = out[0].upper() + out[1:]
    return (out or None), footnotes


def suggested_version(
    doc: Document,
    findings: list[Finding],
    intent: Intent,
    llm: LLM,
    rules: list[Rule],
    terms: list[Term],
    claims: list[Claim] | None = None,
    allow: set[str] = frozenset(),
) -> tuple[str, IntentResult]:
    """Every fix applied: approved wordings, code fixes, then minimal rewrites for what's left.
    Rewrites that break the intent lock or add a finding are discarded."""
    rule_map = {r.id: r for r in rules}
    names = {t.preferred for t in terms}
    low = doc.text.lower()
    mentioned = {
        t.preferred for t in terms if any(n.lower() in low for n in [t.preferred, *t.variants])
    }
    claims = claims if claims is not None else detect_claims(doc, ignore=names | set(allow))
    spans = sentences(doc.text)
    fixed: list[str | None] = []
    rewritten: dict[int, str] = {}
    footnotes: list[str] = []
    for i, s in enumerate(spans):
        sentence, notes = _fix_sentence(doc, s, findings, rule_map)
        footnotes += [n for n in notes if n not in footnotes]
        fixed.append(sentence)
        original = doc.text[s.start : s.end].strip()
        if sentence is None or sentence != _tidy(original):
            continue  # removed, or already fixed in code: no AI rewrite on top
        for f in findings:
            if f.span and _overlaps(f.span, s) and not code_fix(f, rule_map):
                if new := propose_rewrite(
                    sentence, f, llm, rule_map.get(f.rule_id or ""), mentioned, set(allow) | names
                ):
                    rewritten[i] = new
                    break

    def assemble(use_rewrites: set[int]) -> str:
        """Fixed sentences joined by their original separators (line breaks stay line breaks)."""
        body, gap = "", ""
        for i, span in enumerate(spans):
            sep = doc.text[spans[i - 1].end : span.start] if i else ""
            if sep.count("\n") > gap.count("\n"):
                gap = sep  # a dropped sentence's paragraph break carries over to the next one
            part = rewritten[i] if i in use_rewrites else fixed[i]
            if not part:
                continue
            body += ((gap if "\n" in gap else " ") + part) if body else part
            gap = ""
        notes = [n for n in footnotes if n not in body]
        return body + ("\n" + "\n".join(notes) if notes else "")

    keep = set(rewritten)
    # "No new findings" by rule count: quotes change whenever their sentence is fixed.
    before = Counter(f.rule_id for f in run_rules(doc, rules, terms))
    for _ in range(len(keep) + 1):
        text = assemble(keep)
        after = run_rules(Document(format="text", text=text, blocks=[], images=[]), rules, terms)
        grown = {r for r, n in Counter(f.rule_id for f in after).items() if n > before[r]}
        new = [f for f in after if f.rule_id in grown]
        culprits = {
            i for i in keep for f in new if f.quote and f.quote.lower() in rewritten[i].lower()
        }
        result = check_intent(doc.text, text, intent, findings, claims, footnotes)
        if not result.passed:
            culprits |= {
                i
                for i in keep
                if not check_intent(
                    doc.text, assemble(keep - {i}), intent, findings, claims, footnotes
                ).model_dump()
                == result.model_dump()
            }
        if not culprits:
            return text, result
        keep -= culprits
    text = assemble(keep)
    return text, check_intent(doc.text, text, intent, findings, claims, footnotes)
