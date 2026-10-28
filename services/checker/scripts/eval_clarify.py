"""Improvement 3 evaluation: does a drafted clarification beat the old wording on held-out regulator rulings?
Scoring rules are fixed in docs/clarify-eval.md.

    RUN=1 uv run --env-file .env python scripts/eval_clarify.py
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from plumbline.config import Settings
from plumbline.learn import Case, Wording, draft, replay
from plumbline.llm import LLM, LLMUnavailable, default_chain

ROOT = Path(__file__).resolve().parents[3]
OLD = Wording(
    title="Regulated efficacy phrases need a matching fact and compliance sign-off",
    instruction="Regulated efficacy phrases need a matching fact and compliance sign-off.",
)


def cases() -> list[Case]:
    out = []
    for line in (ROOT / "data/rulings/rulings.jsonl").read_text().splitlines():
        ad = json.loads(line)
        claims = ad["claims"]
        for c in claims if isinstance(claims, list) else json.loads(claims):
            out.append(
                Case(
                    quote=c["text"],
                    should_flag=c["outcome"] == "upheld",
                    reason=c.get("why") if c["outcome"] != "upheld" else None,
                )
            )
    return out


def main():
    s = Settings()
    llm = LLM(default_chain(s), lambda e: None)
    call = llm.json

    def paced(*a, **k):  # free-tier limits: wait and retry rather than lose the run
        for wait in (20, 40, 60, 90, 0):
            try:
                time.sleep(3)
                return call(*a, **k)
            except LLMUnavailable:
                if not wait:
                    raise
                time.sleep(wait)

    llm.json = paced
    allc = cases()
    folds = [(allc[0::2], allc[1::2]), (allc[1::2], allc[0::2])]
    res = {"folds": []}
    for train, held in folds:
        new = draft(OLD, train, llm)
        base, mine = replay(OLD, train, llm), replay(new, train, llm)
        redrafted = mine["agree"] < base["agree"]
        if redrafted:
            new = draft(OLD, train, llm)
        row = {
            "new_wording": new.model_dump(),
            "held_n": len(held),
            "redrafted": redrafted,
            "written_from": {"old": base, "first_draft": mine},
        }
        for name, w in (("old_a", OLD), ("old_b", OLD), ("new", new)):
            up = replay(w, [c for c in held if c.should_flag], llm)
            down = replay(w, [c for c in held if not c.should_flag], llm)
            row[name] = {
                "upheld": up,
                "not_upheld": down,
                "agree": up["agree"] + down["agree"],
                "n": up["n"] + down["n"],
            }
        res["folds"].append(row)
        print({k: row[k]["agree"] for k in ("old_a", "old_b", "new")}, "of", len(held))
    tot = {k: sum(f[k]["agree"] for f in res["folds"]) for k in ("old_a", "old_b", "new")}
    res["total"] = tot | {"n": len(allc)}
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    res["run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    (ROOT / f"data/rulings/clarify_run{os.environ.get('RUN', '1')}.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False)
    )
    print(res["total"])


main()
