"""Round 3: the second brand. Loads Kora's rulebook and facts from CSV (the same loader as Aurelle's), runs
the labelled posts in data/korapay/posts.jsonl through the production pipeline and scores them.
Scoring rules are in docs/second-brand.md (fixed before the run).

    RESULTS=data/korapay/results.json PACE=12 uv run --env-file .env python scripts/eval_brand2.py
"""

import json
import os
import subprocess
import time
from datetime import date
from pathlib import Path

from rapidfuzz import fuzz

from plumbline.config import Settings
from plumbline.llm import LLM, default_chain
from plumbline.models import Intent
from plumbline.parsers import parse_upload
from plumbline.pipeline import run_check
from plumbline.rules.load import load_seed_dir

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / os.environ.get("RESULTS", "data/korapay/results.json")
PACE = float(os.environ.get("PACE", "0"))


def span_of(text: str, quote: str):
    i = text.lower().find(quote.lower())
    if i >= 0:
        return i, i + len(quote)
    al = fuzz.partial_ratio_alignment(quote.lower(), text.lower())
    return (al.dest_start, al.dest_end) if al and al.score >= 85 else None


def main() -> None:
    s = Settings()
    ctx, errs = load_seed_dir(ROOT / "supabase/seed/korapay", org_id="korapay", version="v1")
    assert not errs, errs
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    posts = [json.loads(x) for x in (ROOT / "data/korapay/posts.jsonl").read_text().splitlines()]
    out = []
    for n, p in enumerate(posts, 1):
        time.sleep(PACE) if n > 1 else None
        doc = parse_upload("post.txt", p["text"].encode(), 1)
        report = None
        for attempt in (1, 2, 3):
            try:
                report = run_check(
                    doc,
                    ctx,
                    Intent(region="IN", channel=p["channel"]),
                    "creator",
                    True,
                    LLM(default_chain(s), lambda e: None),
                    date.today(),
                )
                break
            except Exception as e:  # noqa: BLE001
                err = repr(e)
                time.sleep(8 * attempt)
        if report is None:
            out.append({"id": p["id"], "error": err})
            print(n, p["id"], "FAILED", err)
            continue
        allf = [
            (f, "blocking" if f.severity == "blocking" and not f.advisory else "other")
            for f in report.findings
        ] + [(f, "human") for f in report.needs_human]
        issues = []
        for it in p["issues"]:
            if it["kind"] == "claim":
                sp = span_of(doc.text, it["quote"])
                hit = [
                    (f, k)
                    for f, k in allf
                    if sp and f.span and sp[0] < f.span.end and f.span.start < sp[1]
                ]
            else:
                hit = [(f, k) for f, k in allf if f.rule_id == it["expect"]]
            ok = (
                any(k in ("blocking", "human") for _, k in hit)
                if it["level"] == "blocks"
                else bool(hit)
            )
            issues.append(
                {
                    **it,
                    "caught": ok,
                    "by": [
                        {"rule": f.rule_id, "fact": f.fact_id, "kind": k, "status": f.claim_status}
                        for f, k in hit
                    ][:6],
                }
            )
        blocked = [f.rule_id or f.fact_id for f, k in allf if k in ("blocking", "human")]
        out.append(
            {
                "id": p["id"],
                "clean": p["clean"],
                "ai": report.coverage.ai_status,
                "issues": issues,
                "blocking_or_human": blocked,
                "findings": len(report.findings) + len(report.needs_human),
            }
        )
        print(
            f"{n:2} {p['id']} ai={report.coverage.ai_status} "
            + (
                f"caught {sum(i['caught'] for i in issues)}/{len(issues)}"
                if not p["clean"]
                else f"clean: blocking/human={blocked} all={out[-1]['findings']}"
            )
        )
    ok_runs = [r for r in out if "issues" in r]
    iss = [i for r in ok_runs if not r["clean"] for i in r["issues"]]
    cl = [r for r in ok_runs if r["clean"]]
    summary = {
        "commit": commit,
        "run_at": time.strftime("%Y-%m-%d %H:%M IST"),
        "posts": len(posts),
        "run": len(ok_runs),
        "ai_not_ok": sum(r["ai"] != "ok" for r in ok_runs),
        "issues": len(iss),
        "caught": sum(i["caught"] for i in iss),
        "caught_blocks": [
            sum(i["caught"] for i in iss if i["level"] == "blocks"),
            sum(1 for i in iss if i["level"] == "blocks"),
        ],
        "caught_flag": [
            sum(i["caught"] for i in iss if i["level"] == "flag"),
            sum(1 for i in iss if i["level"] == "flag"),
        ],
        "by_kind": {
            k: [
                sum(i["caught"] for i in iss if i["kind"] == k),
                sum(1 for i in iss if i["kind"] == k),
            ]
            for k in ("rule", "claim")
        },
        "clean_posts": len(cl),
        "false_alarms_blocking_or_human": sum(bool(r["blocking_or_human"]) for r in cl),
        "clean_with_any_finding": sum(r["findings"] > 0 for r in cl),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": out}, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1))


main()
