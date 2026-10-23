"""Class B rules (§6.2 stage 5): AI judgement on tone and other rules code can't check.

Returns raw findings only. Severity, citations and quotes are enforced afterwards by
validate.validate_findings, and a second model checks them (validate.support_check).
"""

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from plumbline.llm import LLM, LLMUnavailable
from plumbline.models import Document, Fact, Rule
from plumbline.privacy import mask_confidential, redact

PROMPT = (Path(__file__).parent / "prompts" / "judge.txt").read_text(encoding="utf-8")
JUDGE_PROMPT_VERSION = hashlib.sha256(PROMPT.encode()).hexdigest()[:8]
SECTION_CHARS = 1_500


class _Raw(BaseModel):
    rule_id: str
    quote: str
    explanation: str


class _Judgement(BaseModel):
    findings: list[_Raw]


def _rules_text(rules_b: list[Rule]) -> str:
    lines = []
    for r in rules_b:
        lines.append(f"[{r.id}] {r.title}")
        if instruction := r.params.get("instruction"):
            lines.append(f"  How to judge: {instruction}")
        lines += [f"  Follows the rule: {ex}" for ex in r.examples_good]
        lines += [f"  Breaks the rule: {ex}" for ex in r.examples_bad]
    return "\n".join(lines)


def _copy_text(doc: Document) -> str:
    """The copy only: text read from images by OCR is blanked (same length, offsets kept)."""
    text = doc.text
    for b in doc.blocks:
        if b.kind == "ocr_text":
            text = text[: b.start] + " " * (b.end - b.start) + text[b.end :]
    return text


def sections(text: str, limit: int = SECTION_CHARS) -> list[tuple[int, str]]:
    """Paragraphs (split on blank lines) packed into sections of about `limit` characters."""
    out: list[tuple[int, str]] = []
    start, chunk = 0, ""
    for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]*)*", text):
        para = m.group()
        if not para.strip():
            continue
        if chunk and len(chunk) + len(para) + 2 > limit:
            out.append((start, chunk))
            chunk = ""
        if not chunk:
            start = m.start()
            chunk = para
        else:
            chunk = text[start : m.end()]
    if chunk.strip():
        out.append((start, chunk))
    return out


def judge_section(
    section_text: str,
    offset: int,
    rules_b: list[Rule],
    llm: LLM,
    restore: dict[str, str] | None = None,
) -> list[dict]:
    """One section (already masked and redacted). Quotes come back with placeholders restored."""
    system = PROMPT.format(rules=_rules_text(rules_b))
    result, used = llm.json("judge", system, f"<content>\n{section_text}\n</content>", _Judgement)
    raw = []
    for f in result.findings:
        quote = f.quote
        for placeholder, original in (restore or {}).items():
            quote = quote.replace(placeholder, original)
        raw.append(
            {"rule_id": f.rule_id, "quote": quote, "explanation": f.explanation, "model": used}
        )
    return raw


def judge_document(
    doc: Document,
    rules: list[Rule],
    llm: LLM,
    *,
    facts: list[Fact],
    today: date,
    allow: set[str],
    max_workers: int = 4,
) -> tuple[list[dict], str | None]:
    """All sections in parallel. Returns (raw findings, reason if any section's AI call failed)."""
    rules_b = [r for r in rules if r.cls == "B" and r.check_type == "ai_rule"]
    if not rules_b:
        return [], None
    copy = _copy_text(doc)

    def run(section: tuple[int, str]) -> list[dict]:
        start, text = section
        safe, restore = redact(mask_confidential(text, facts, today)[0], allow)
        return judge_section(safe, start, rules_b, llm, restore)

    parts = sections(copy)
    raw: list[dict] = []
    reasons: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(run, p) for p in parts]
        for fut in futures:
            try:
                raw += fut.result()
            except LLMUnavailable as e:
                reasons.append(e.reason)
    return raw, (reasons[0] if reasons else None)
