"""Live evaluation of the class B judge (Task 12): 24 labelled posts plus the 10 samples, through
judge -> citation validator -> second-model check. Spends real model calls; run with
`uv run --env-file .env python scripts/eval_judge.py`."""

import json
import sys
import time
from collections import Counter
from datetime import date

sys.path.insert(0, ".")
from plumbline.config import Settings
from plumbline.judge import judge_document
from plumbline.llm import LLM, default_chain
from plumbline.models import Document
from plumbline.rules.load import load_seed_dir
from plumbline.validate import support_check, validate_findings
from tests.conftest import SEED

ctx, _ = load_seed_dir(SEED)
rules = {r.id: r for r in ctx.rules}
facts = {f.id: f for f in ctx.facts}
terms = {t.id: t for t in ctx.terms}
allow = {"Aurelle"} | {t.preferred for t in ctx.terms}
LABELLED = [  # (text, rules that should fire)
    (
        "Hurry! Only 2 hours left before this deal disappears forever. Don't miss out like everyone else will.",
        {"TN-01"},
    ),
    ("This serum will CHANGE YOUR LIFE overnight. Act now or regret it.", {"TN-01"}),
    ("Everyone is talking about it and you'll be left behind if you wait. Buy today.", {"TN-01"}),
    (
        "Meet the Vitamin C Brightening Serum: a lighter, brighter routine for busy mornings. Shop the serum.",
        set(),
    ),
    ("Your skin deserves a little sunshine. Try the Hyaluronic Water Gel this week.", set()),
    ("New in: Ceramide Barrier Cream for dry winter skin. Discover it today.", set()),
    (
        "If you still haven't figured out sunscreen, honestly, what are you doing? Stop wrecking your skin.",
        {"TN-04"},
    ),
    (
        "Most people use moisturiser wrong. Let us explain it slowly so you finally get it.",
        {"TN-04"},
    ),
    ("Ugh, dull skin again? You really should know better by now.", {"TN-04"}),
    ("Your routine, your rules. Here's one more step that might help on dry days.", set()),
    ("Not sure where to start? We'll walk you through it, one step at a time.", set()),
    ("You choose the shade; we'll make sure it lasts all day.", set()),
    (
        "The serum was tested by our team and it was loved by everyone who was given a sample.",
        {"TN-05"},
    ),
    (
        "Mistakes were made in last week's order emails, and refunds will be processed by the team.",
        {"TN-05"},
    ),
    ("The new formula has been developed and is being shipped to stores.", {"TN-05"}),
    ("We tested the serum on 48 people over 8 weeks.", set()),
    ("Our chemists developed the new formula, and we ship it next week.", set()),
    ("You can track your order from the link in your email.", set()),
    (
        "We've been thinking a lot about mornings lately, and about what they mean to all of us, and about light. Anyway, our serum is out.",
        {"TN-06"},
    ),
    (
        "Skincare has a long and interesting history across many cultures and centuries. Today there's a new gel.",
        {"TN-06"},
    ),
    (
        "Some days feel longer than others, don't they? Rain, traffic, deadlines. Also: new lip balm shades.",
        {"TN-06"},
    ),
    ("Meet the Tinted Lip Balm in six shades. Each one adds a soft wash of colour.", set()),
    ("The SPF 50 Daily Sunscreen is here: no white cast, all day. Find your bottle today.", set()),
    ("New: the Gentle Rice Cleanser, soap-free with a pH of 5.5. Try it tonight.", set()),
]
events = []
llm = LLM(default_chain(Settings()), events.append)
tp = fp = fn = 0
per = Counter()
misses = []
extras = []
t0 = time.perf_counter()
for text, want in LABELLED:
    d = Document(format="text", text=text, blocks=[], images=[])
    raw, reason = judge_document(
        d, ctx.rules, llm, facts=ctx.facts, today=date(2026, 10, 23), allow=allow, max_workers=1
    )
    kept, dropped = validate_findings(raw, d, rules, facts, terms)
    kept, human = support_check(kept, llm, rules, facts)
    got = {f.rule_id for f in kept}
    for r in want & got:
        tp += 1
        per[(r, "tp")] += 1
    for r in got - want:
        fp += 1
        per[(r, "fp")] += 1
        extras.append((r, text[:60]))
    for r in want - got:
        fn += 1
        per[(r, "fn")] += 1
        misses.append((r, text[:60]))
    if dropped:
        print("   dropped:", [(x.reason, x.finding.get("rule_id")) for x in dropped])
    if reason:
        print("   unavailable:", reason)
el = time.perf_counter() - t0
print(
    f"precision {tp}/{tp + fp} = {tp / max(1, tp + fp):.0%}   recall {tp}/{tp + fn} = {tp / max(1, tp + fn):.0%}   ({el:.0f} s)"
)
for r in ("TN-01", "TN-04", "TN-05", "TN-06"):
    print(f"   {r}: tp {per[(r, 'tp')]} fp {per[(r, 'fp')]} fn {per[(r, 'fn')]}")
print("missed:", misses)
print("false alarms:", extras)
print("calls:", dict(Counter((e.provider, e.status) for e in events)))
print("\n--- the 10 sample posts (real copy) ---")
for s in json.loads((SEED / "contents.json").read_text()):
    d = Document(format="text", text=s["text"], blocks=[], images=[])
    raw, reason = judge_document(
        d, ctx.rules, llm, facts=ctx.facts, today=date(2026, 10, 23), allow=allow, max_workers=1
    )
    kept, dropped = validate_findings(raw, d, rules, facts, terms)
    kept, human = support_check(kept, llm, rules, facts)
    bad = [
        f
        for f in kept + human
        if "approv" in f.explanation.lower() and "approv" not in f.quote.lower()
    ]
    print(
        f"{s['key']:25} shown={[(f.rule_id, f.quote[:34], f.support) for f in kept]} needs_human={[(f.rule_id, f.quote[:30]) for f in human]} declares-approval={len(bad)} {reason or ''}"
    )
