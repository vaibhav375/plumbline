"""Round 3: re-tune the clarification drafter without overfitting. Protocol: docs/clarify-eval.md ("Run 3").

STAGE=tune uv run --env-file .env python scripts/eval_clarify_tune.py          # variants V0-V3 on the TUNE ads only
STAGE=test VARIANT=V2 uv run --env-file .env python scripts/eval_clarify_tune.py   # once, on the untouched TEST ads
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_clarify import OLD

from plumbline.config import Settings
from plumbline.learn import Case, draft, replay
from plumbline.llm import LLM, LLMUnavailable, default_chain

ROOT = Path(__file__).resolve().parents[3]
VARIANTS = ROOT / "data/rulings/clarify_variants"


def cases_for(parity: int) -> list[Case]:
    """Claims of the ads at even (0) or odd (1) positions: the split is by ad, so no ad is in both halves."""
    out = []
    for i, line in enumerate((ROOT / "data/rulings/rulings.jsonl").read_text().splitlines()):
        if i % 2 != parity:
            continue
        claims = json.loads(line)["claims"]
        for c in claims if isinstance(claims, list) else json.loads(claims):
            out.append(
                Case(
                    quote=c["text"],
                    should_flag=c["outcome"] == "upheld",
                    reason=c.get("why") if c["outcome"] != "upheld" else None,
                )
            )
    return out


def template(v: str) -> str | None:
    return None if v == "V0" else (VARIANTS / f"{v}.txt").read_text(encoding="utf-8")


def paced_llm():
    llm = LLM(default_chain(Settings()), lambda e: None)
    call = llm.json

    def paced(*a, **k):
        for wait in (20, 40, 60, 90, 0):
            try:
                time.sleep(3)
                return call(*a, **k)
            except LLMUnavailable:
                if not wait:
                    raise
                time.sleep(wait)

    llm.json = paced
    return llm


def agree(w, cases, llm) -> int:
    up = replay(w, [c for c in cases if c.should_flag], llm)
    down = replay(w, [c for c in cases if not c.should_flag], llm)
    return up["agree"] + down["agree"]


def run_variant(v: str, allc: list[Case], llm) -> dict:
    """The product's method inside one half: draft from one half of the claims, score on the other half, swap."""
    folds, total = [], 0
    for train, held in ((allc[0::2], allc[1::2]), (allc[1::2], allc[0::2])):
        new = draft(OLD, train, llm, template(v))
        a = agree(new, held, llm)
        folds.append({"wording": new.model_dump(), "agree": a, "n": len(held)})
        total += a
    return {"variant": v, "agree": total, "n": len(allc), "folds": folds}


def main():
    stage, llm = os.environ["STAGE"], paced_llm()
    res = {"stage": stage}
    if stage == "tune":
        allc = cases_for(0)
        res["n"] = len(allc)
        res["old_a"], res["old_b"] = agree(OLD, allc, llm), agree(OLD, allc, llm)
        res["variants"] = []
        for v in ("V0", "V1", "V2", "V3"):
            r = run_variant(v, allc, llm)
            res["variants"].append(r)
            print(v, r["agree"], "of", r["n"], "| old", res["old_a"], res["old_b"], flush=True)
    else:
        allc = cases_for(1)
        res["n"] = len(allc)
        res["old_a"], res["old_b"] = agree(OLD, allc, llm), agree(OLD, allc, llm)
        res["variants"] = [run_variant(v, allc, llm) for v in ("V0", os.environ["VARIANT"])]
        print(
            [(r["variant"], r["agree"]) for r in res["variants"]],
            "old",
            res["old_a"],
            res["old_b"],
            "of",
            res["n"],
        )
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    res["run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    (ROOT / f"data/rulings/clarify_run3_{stage}.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
