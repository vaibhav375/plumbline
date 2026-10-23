"""Live evaluation of fixes (Task 13): every sample post through code rules, claims and the
judge, then the suggested version with real AI rewrites. Spends real model calls; run with
`uv run --env-file .env python scripts/eval_fixes.py`."""

import json
import sys
import time
from collections import Counter
from datetime import date

sys.path.insert(0, ".")
from plumbline.claims import check_claims
from plumbline.config import Settings
from plumbline.fixes import Intent, suggested_version
from plumbline.judge import judge_document
from plumbline.llm import LLM, default_chain
from plumbline.models import Document
from plumbline.rules.engine import run_rules
from plumbline.rules.load import load_seed_dir
from plumbline.validate import validate_findings
from tests.conftest import SEED

TODAY = date(2026, 10, 23)
ctx, _ = load_seed_dir(SEED)
rules = {r.id: r for r in ctx.rules}
facts = {f.id: f for f in ctx.facts}
terms = {t.id: t for t in ctx.terms}
allow = {"Aurelle"} | {t.preferred for t in ctx.terms}
events = []
llm = LLM(default_chain(Settings()), events.append)
passed = 0
for s in json.loads((SEED / "contents.json").read_text()):
    d = Document(format="text", text=s["text"], blocks=[], images=[])
    t0 = time.perf_counter()
    code = run_rules(d, ctx.rules, ctx.terms)
    claim_findings, claims = check_claims(d, ctx, llm, "IN", s["channel"], TODAY, allow)
    raw, _ = judge_document(d, ctx.rules, llm, facts=ctx.facts, today=TODAY, allow=allow)
    judged, _ = validate_findings(raw, d, rules, facts, terms)
    findings = code + claim_findings + judged
    intent = (
        Intent(**{k: v for k, v in s.get("intent", {}).items() if k in Intent.model_fields})
        if s.get("intent")
        else Intent(channel=s["channel"])
    )
    n0 = len(events)
    text, result = suggested_version(
        d, findings, intent, llm, ctx.rules, ctx.terms, claims=claims, allow=allow
    )
    rewrites = Counter(e.status for e in events[n0:] if e.task == "rewrite")
    before = Counter(f.rule_id for f in code)  # same comparison suggested_version uses
    after = run_rules(
        Document(format="text", text=text, blocks=[], images=[]), ctx.rules, ctx.terms
    )
    new = sorted(r for r, n in Counter(f.rule_id for f in after).items() if n > before[r])
    left = sorted({f.rule_id for f in after})
    passed += result.passed
    print(f"\n== {s['key']}  ({time.perf_counter() - t0:.1f} s, rewrite calls {dict(rewrites)})")
    print("   before:", s["text"].replace("\n", " / ")[:230])
    print("   after: ", text.replace("\n", " / ")[:230])
    print(
        f"   intent passed: {result.passed} {'' if result.passed else result.model_dump()} | new findings: {new} | code findings left: {left}"
    )
print(f"\nintent lock passed on {passed}/10 posts")
