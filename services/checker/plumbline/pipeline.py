"""run_check: one content check end to end (§6.2), and the coverage statement that goes with it.

Order: code rules (timed separately) → claims and AI judgement in parallel → validators and the
second-model check → withhold confidential findings from external pre-checks → suggested version
and intent lock → coverage. A check never changes a version's status.
"""

import hashlib
import json
import time
import uuid
from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from plumbline.claims import check_claims
from plumbline.fixes import code_fix, suggested_version
from plumbline.judge import judge_document
from plumbline.llm import LLM
from plumbline.models import (
    DEFAULT_NOT_CHECKED,
    CheckReport,
    Coverage,
    Document,
    Finding,
    Intent,
    OrgContext,
    Rule,
)
from plumbline.privacy import redact
from plumbline.rules.engine import run_rules
from plumbline.validate import support_check, validate_findings

PROBLEM = {"contradicted", "unsupported", "outdated", "restricted"}
EXTERNAL_PRECHECK_NOTE = "Confidential checks run on submission."
IMAGES_NOTE = "Claims inside images and palette and logo checks arrive in Round 3."
BUSY_NOTE = "Contrast of text over photo-like backgrounds (its colours can't be measured reliably)."
PDF_IMAGES_NOTE = "Images inside PDFs (their alt text and contrast) aren't checked yet."


def _code_version() -> str:
    """Hash of the package's code, prompts and data, so a cached report never outlives them."""
    h = hashlib.sha256()
    root = Path(__file__).parent
    for p in sorted(root.rglob("*")):
        if p.suffix in (".py", ".txt") and "__pycache__" not in p.parts:
            h.update(p.relative_to(root).as_posix().encode() + p.read_bytes())
    return h.hexdigest()[:12]


CODE_VERSION = _code_version()


class _Recorder:
    """Wraps the LLM to remember which provider/model answered each call."""

    def __init__(self, llm: LLM):
        self.llm, self.chain, self.used = llm, getattr(llm, "chain", []), set()

    def json(self, task, system, user, schema):
        result, used = self.llm.json(task, system, user, schema)
        self.used.add(used)
        return result, used

    def model_for(self, task):
        return self.llm.model_for(task)


def build_coverage(
    rules: list[Rule],
    ran: set[str],
    ai_status: str,
    ai_note: str | None,
    viewer_role: str,
    is_precheck: bool,
    doc: Document | None = None,
) -> Coverage:
    not_checked = [DEFAULT_NOT_CHECKED]
    if viewer_role == "external_creator" and is_precheck:
        not_checked.append(EXTERNAL_PRECHECK_NOTE)
    if doc is not None and doc.images:
        not_checked.append(IMAGES_NOTE)
        if any(b.busy_background for i in doc.images for b in i.ocr):
            not_checked.append(BUSY_NOTE)
    if doc is not None and doc.format == "pdf":
        not_checked.append(PDF_IMAGES_NOTE)
    note = None
    if ai_status == "unavailable":
        note = f"AI checks did not run: {ai_note or 'no model was available'}. Code checks above are complete."
        not_checked.append(note)
    elif ai_status == "partial":
        note = f"Some AI checks did not run: {ai_note}. Code checks above are complete."
        not_checked.append(note)
    not_run: dict[str, str] = {}
    for r in rules:
        if r.cls == "C":
            not_run[r.id] = "Judgement only (class C): stays in the rulebook, never run."
        elif r.id not in ran and r.check_type == "ai_rule":
            not_run[r.id] = "AI rule: the AI check didn't run for this content."
    by_id = {r.id: r for r in rules}
    return Coverage(
        rules_run=sorted(ran),
        rules_advisory=sorted(i for i in ran if i in by_id and not by_id[i].blocks),
        rules_not_run=not_run,
        not_checked=not_checked,
        ai_status=ai_status,
        ai_note=note,
    )


def _overlap(a: Finding, b: Finding) -> bool:
    return bool(a.span and b.span and a.span.start < b.span.end and b.span.start < a.span.end)


def _dedupe(code: list[Finding], claims: list[Finding]) -> list[Finding]:
    """A code rule and the claims check flagging the same words under the same rule: keep the
    claim finding, which carries the fact and the approved fix."""
    return [
        c for c in code if not any(c.rule_id == k.rule_id and _overlap(c, k) for k in claims)
    ] + claims


def cache_key(doc: Document, ctx: OrgContext, intent: Intent, scope: str, today: date, llm) -> str:
    chain = [(p.name, sorted(p.models.items())) for p in getattr(llm, "chain", [])]
    payload = json.dumps(
        [
            doc.model_dump(mode="json"),
            ctx.model_dump(mode="json"),
            intent.model_dump(mode="json"),
            scope,
            today.isoformat(),
            chain,
            CODE_VERSION,
        ],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def run_check(
    doc: Document,
    ctx: OrgContext,
    intent: Intent | None,
    viewer_role: str,
    is_precheck: bool,
    llm: LLM,
    today: date,
    cache: MutableMapping[str, str] | None = None,
) -> CheckReport:
    started = time.perf_counter()
    intent = intent or Intent()
    withhold = viewer_role == "external_creator" and is_precheck
    key = cache_key(doc, ctx, intent, "external_precheck" if withhold else "full", today, llm)
    if cache is not None and key in cache:
        cached = CheckReport.model_validate_json(cache[key])
        return cached.model_copy(update={"replay": True, "run_id": str(uuid.uuid4())})

    rules = {r.id: r for r in ctx.rules}
    facts = {f.id: f for f in ctx.facts}
    terms = {t.id: t for t in ctx.terms}
    allow = {t.preferred for t in ctx.terms}
    code = run_rules(doc, ctx.rules, ctx.terms)
    ms_code = round((time.perf_counter() - started) * 1000)

    rec = _Recorder(llm)
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims_job = pool.submit(
            check_claims,
            doc,
            ctx,
            rec,
            intent.region,
            intent.channel,
            today,
            allow,
            failures=failures,
        )
        judge_job = pool.submit(
            judge_document, doc, ctx.rules, rec, facts=ctx.facts, today=today, allow=allow
        )
        claim_findings, claims = claims_job.result()
        raw, judge_reason = judge_job.result()

    judged, dropped = validate_findings(raw, doc, rules, facts, terms)
    judged, needs_human = support_check(
        judged, rec, rules, facts, redactor=lambda s: redact(s, allow)[0]
    )
    claim_problems = [f for f in claim_findings if f.claim_status in PROBLEM]
    needs_human += [f for f in claim_findings if f.claim_status == "needs_human"]
    # Deterministic fixes from rule data travel with the finding, so a writer can accept them one by one.
    code = [f if f.fix else f.model_copy(update={"fix": code_fix(f, rules)}) for f in code]
    findings = _dedupe(code, claim_problems) + judged
    tiers = {r.id: r.tier for r in ctx.rules}
    findings = [f.model_copy(update={"tier": tiers.get(f.rule_id or "")}) for f in findings]
    if withhold:
        # The agency never learns that its text matched something confidential (§4.5).
        findings = [f for f in findings if f.category != "confidential"]
        claim_findings = [f for f in claim_findings if f.category != "confidential"]
    elif viewer_role == "external_creator":
        # On submission the agency sees that something is restricted, never what (§4.4).
        findings = [
            f.model_copy(
                update={
                    "fact_id": None,
                    "explanation": "Mentions restricted information.",
                    "basis_excerpt": "Restricted information",
                }
            )
            if f.category == "confidential"
            else f
            for f in findings
        ]

    supported = [f for f in claim_findings if f.claim_status not in PROBLEM]
    text, intent_result = suggested_version(
        doc, findings + supported, intent, rec, ctx.rules, ctx.terms, claims=claims, allow=allow
    )

    reasons = failures + ([judge_reason] if judge_reason else [])
    has_ai_rules = any(r.cls == "B" and r.check_type == "ai_rule" for r in ctx.rules)
    stages = 1 + has_ai_rules  # claim extraction, plus the judge when there are AI rules
    ai_status = "ok" if not reasons else ("unavailable" if len(reasons) >= stages else "partial")
    ran = {r.id for r in ctx.rules if r.cls != "C" and r.check_type != "ai_rule"}
    if not judge_reason:
        ran |= {r.id for r in ctx.rules if r.cls == "B" and r.check_type == "ai_rule"}
    coverage = build_coverage(
        ctx.rules,
        ran,
        ai_status,
        reasons[0] if reasons else None,
        viewer_role,
        is_precheck,
        doc=doc,
    )

    report = CheckReport(
        run_id=str(uuid.uuid4()),
        version_id=None,
        findings=findings,
        needs_human=needs_human,
        dropped_count=len(dropped),
        coverage=coverage,
        suggested_text=text,
        intent=intent_result,
        models_used=sorted(rec.used),
        ms_code=ms_code,
        ms_total=round((time.perf_counter() - started) * 1000),
    )
    if cache is not None:
        cache[key] = report.model_dump_json()
    return report
