"""Write rulings.jsonl from the hand-extracted entries. Run: python build.py (then python verify.py)."""
import json
from collections import Counter

from asa_part1 import ASA
from asa_part2 import ASA2
from asci_rulings import ASCI

# Part 1 entries predate the per-claim `issue` field; set it here (comparison/medicinal where the ruling says so).
SPECIAL = {("ASA-005", 1): "comparison", ("ASA-006", 0): "medicinal"}


def rows():
    for r in ASA + ASA2 + ASCI:
        r = json.loads(json.dumps(r))
        for i, c in enumerate(r["claims"]):
            c.setdefault("issue", SPECIAL.get((r["id"], i), "substantiation"))
        r["period"] = r.get("period", r["date"][:7])
        yield r


def main():
    out = list(rows())
    with open("rulings.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    claims = [c for r in out for c in r["claims"]]
    print(len(out), "rulings,", len(claims), "claims")
    print("by source:", dict(Counter(r["source"] for r in out)))
    print("by outcome:", dict(Counter(c["outcome"] for c in claims)))
    print("by issue:", dict(Counter(c["issue"] for c in claims)))


main()
