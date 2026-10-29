"""Round 3: the 200-fix audit for improvements 1 and 2 ("0 invented claims").

    PACE=10 uv run --env-file .env python scripts/fix_audit.py pool    # runs both test sets; data/fixes/pool.json
    python3 scripts/fix_audit.py draw                                  # data/fixes/sheet.csv (200 rows, seed 11)
    python3 scripts/fix_audit.py score                                 # reads the 'verdict' column

A fix is one sentence of the original that the suggested version changed or dropped. Verdict: y = the new
sentence adds no claim, number or promise that is not in the original or in the approved wording shown;
n = it invents one. Dropped sentences are safe by construction and are listed (verdict pre-filled 'y').
"""

import csv
import difflib
import json
import os
import random
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "data/fixes"
COLS = [
    "n",
    "set",
    "post",
    "kind",
    "original",
    "suggested",
    "approved_wording_available",
    "verdict",
    "note",
]


def pool():
    sys.path.insert(0, str(Path(__file__).parent))
    from citation_pool import aurelle_ctx

    from plumbline.config import Settings
    from plumbline.llm import LLM, default_chain
    from plumbline.models import Intent
    from plumbline.normalize import sentences
    from plumbline.parsers import parse_upload
    from plumbline.pipeline import run_check
    from plumbline.rules.load import load_seed_dir

    s = Settings()
    pace = float(os.environ.get("PACE", "0"))

    def rd(p):
        return [json.loads(x) for x in (ROOT / p).read_text().splitlines()]

    sets = [
        (
            "ruling-set",
            aurelle_ctx(s),
            "external_creator",
            rd("data/rulings/rulings.jsonl"),
            "ad_text",
        ),
        (
            "kora",
            load_seed_dir(ROOT / "supabase/seed/korapay", org_id="korapay", version="v1")[0],
            "creator",
            rd("data/korapay/posts.jsonl"),
            "text",
        ),
    ]
    out, n = [], 0
    for name, ctx, role, items, key in sets:
        code_only = {f.id for f in ctx.facts if f.code_only}
        wordings = " | ".join(w.text for w in ctx.wordings if w.fact_id not in code_only)
        for it in items:
            n += 1
            time.sleep(pace) if n > 1 else None
            doc = parse_upload("t.txt", it[key].encode(), 1)
            rep = None
            for a in (1, 2, 3):
                try:
                    rep = run_check(
                        doc,
                        ctx,
                        Intent(region="IN"),
                        role,
                        True,
                        LLM(default_chain(s), lambda e: None),
                        date.today(),
                    )
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(8 * a)
            if rep is None or not rep.suggested_text:
                continue
            old = [doc.text[x.start : x.end].strip() for x in sentences(doc.text)]
            new = [
                x.strip() for x in rep.suggested_text.replace("\n", " \n").split(" \n") if x.strip()
            ]
            sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op == "equal":
                    continue
                o, w = " ".join(old[i1:i2]), " ".join(new[j1:j2])
                if o.split() == w.split():
                    continue  # spacing-only difference from how the text was split, not a fix
                out.append(
                    dict(
                        set=name,
                        post=it["id"],
                        kind="dropped" if not w else "changed",
                        original=o,
                        suggested=w,
                        approved_wording_available=wordings,
                    )
                )
            print(n, it["id"], len(out), "fixes so far")
    D.mkdir(exist_ok=True)
    (D / "pool.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("pool:", len(out))


def draw():
    p = json.loads((D / "pool.json").read_text())
    random.Random(11).shuffle(p)
    p = [x for x in p if x["original"].split() != x["suggested"].split()][
        :200
    ]  # up to 200; fewer if the posts yield fewer
    with (D / "sheet.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for i, r in enumerate(p, 1):
            w.writerow(
                {
                    **r,
                    "n": i,
                    "orig_n": "",
                    "verdict": "y" if r["kind"] == "dropped" else "",
                    "note": "",
                }
            )
    print("wrote", len(p), "rows to", D / "sheet.csv")


def score():
    rows = list(csv.DictReader((D / "sheet.csv").open(encoding="utf-8")))
    v = [r["verdict"].strip().lower() for r in rows]
    y, n, blank = v.count("y"), v.count("n"), len(v) - v.count("y") - v.count("n")
    print(f"safe {y}, invented {n}, unmarked {blank}, of {len(v)}")
    if n:
        print("invented in rows:", [r["n"] for r in rows if r["verdict"].strip().lower() == "n"])
    print(
        "target: 0 invented, every fix marked ->",
        "MET" if n == 0 and blank == 0 else "NOT MET" if n else "NOT YET",
    )
    print("note: the Round 2 target said 200 fixes; the test posts yield", len(v))


if __name__ == "__main__":
    {"pool": pool, "draw": draw, "score": score}[sys.argv[1]]()
