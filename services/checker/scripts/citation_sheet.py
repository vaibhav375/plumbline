"""Draw the 100-finding sample for the human citation check and write the sheet, or score a filled-in one.

    python scripts/citation_sheet.py draw     # data/citations/sheet.csv (seed 7: 70 ruling-set, 30 Kora)
    python scripts/citation_sheet.py score    # reads the 'verdict' column: y = citation correct, n = wrong
"""

import csv
import json
import random
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[3] / "data/citations"
COLS = ["n", "set", "post", "post_text", "quote", "cites", "rule_or_fact_text", "checker_said", "verdict", "note"]

if sys.argv[1:] == ["draw"]:
    pool = json.loads((D / "pool.json").read_text())
    rnd = random.Random(7)
    pick = rnd.sample([x for x in pool if x["set"] == "ruling-set"], 70) + rnd.sample([x for x in pool if x["set"] == "kora"], 30)
    rnd.shuffle(pick)
    with open(D / "sheet.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for i, x in enumerate(pick, 1):
            w.writerow({
                "n": i, "set": x["set"], "post": x["post"], "post_text": x["text"], "quote": x["quote"],
                "cites": " · ".join(filter(None, [x["rule_id"], x["fact_id"]])),
                "rule_or_fact_text": " | ".join(filter(None, [x["rule_title"] and f'{x["rule_title"]} ({x["rule_source"]})', x["fact_statement"]])),
                "checker_said": f'[{x["severity"]}] {x["explanation"]}', "verdict": "", "note": "",
            })
    print("wrote", D / "sheet.csv")
else:
    rows = list(csv.DictReader(open(D / "sheet.csv")))
    v = [r["verdict"].strip().lower() for r in rows]
    y, n = v.count("y"), v.count("n")
    print(f"{y} correct, {n} wrong, {len(v) - y - n} unmarked of {len(v)}")
    if y + n:
        print(f"correct: {y / (y + n):.1%} (target 95%)")
