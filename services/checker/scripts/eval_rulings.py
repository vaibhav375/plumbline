"""Round 3: run the regulator-ruling set through the production pipeline and score recall on upheld claims.

    uv run --env-file .env python scripts/eval_rulings.py

Scoring rules are in docs/ruling-set.md (fixed before the first run). Writes data/rulings/results.json.
Nothing is saved to the database: the rulebook is read as the demo agency writer, the check is run in memory.
"""

import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import httpx
from rapidfuzz import fuzz

from plumbline import api, auth, db
from plumbline.config import Settings
from plumbline.llm import LLM, default_chain
from plumbline.models import Document, Intent
from plumbline.parsers import parse_upload
from plumbline.pipeline import run_check

ROOT = Path(__file__).resolve().parents[3]
RULINGS = ROOT / "data/rulings/rulings.jsonl"
OUT = ROOT / "data/rulings/results.json"


def claim_span(text: str, claim: str) -> tuple[int, int] | None:
    i = text.lower().find(claim.lower())
    if i >= 0:
        return i, i + len(claim)
    al = fuzz.partial_ratio_alignment(claim.lower(), text.lower())
    return (al.dest_start, al.dest_end) if al and al.score >= 90 else None


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def main() -> None:
    s = Settings()
    # The demo agency writer's view of the rulebook (read only).
    r = httpx.post(
        f"{s.supabase_url.rstrip('/')}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": s.supabase_anon_key},
        json={"email": s.agent_demo_email, "password": s.demo_user_password},
        timeout=20,
    )
    token = r.raise_for_status().json()["access_token"]
    prof = db.fetch_profile(s, token, auth.verify_token(token, s)["sub"])
    ctx = db.load_org_context(s, token, prof["org_id"])
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    today = date.today()

    ads = [json.loads(line) for line in RULINGS.read_text().splitlines()]
    results, seen_models = [], Counter()
    for n, ad in enumerate(ads, 1):
        doc = parse_upload("ad.txt", ad["ad_text"].encode(), 1)
        events = []
        llm = LLM(default_chain(s), events.append)
        t0 = time.perf_counter()
        report, err = None, None
        for attempt in (1, 2, 3):
            try:
                report = run_check(
                    doc, ctx, Intent(region="IN"), "external_creator", True, llm, today
                )
                break
            except Exception as e:  # noqa: BLE001 - recorded, then retried: a rate limit shouldn't lose an ad
                err = repr(e)
                time.sleep(8 * attempt)
        ms = round((time.perf_counter() - t0) * 1000)
        if report is None:
            print(f"[{n}/{len(ads)}] {ad['id']} FAILED: {err}")
            results.append({"id": ad["id"], "error": err})
            continue
        seen_models.update(report.models_used)
        findings = [
            (f, "blocking" if f.severity == "blocking" and not f.advisory else "advisory")
            for f in report.findings
        ]
        findings += [(f, "human") for f in report.needs_human]
        rows = []
        for c in ad["claims"]:
            span = claim_span(doc.text, c["text"])
            touched = [
                (f, kind)
                for f, kind in findings
                if span and f.span and overlaps(span, (f.span.start, f.span.end))
            ]
            kinds = {k for _, k in touched}
            rows.append(
                {
                    "text": c["text"],
                    "outcome": c["outcome"],
                    "issue": c["issue"],
                    "located": span is not None,
                    "caught": bool(kinds & {"blocking", "human"}),
                    "strict": "blocking" in kinds,
                    "lenient": bool(kinds),
                    "by": [
                        {
                            "rule": f.rule_id,
                            "fact": f.fact_id,
                            "kind": kind,
                            "status": f.claim_status,
                            "quote": f.quote[:80],
                        }
                        for f, kind in touched
                    ],
                }
            )
        results.append(
            {
                "id": ad["id"],
                "source": ad["source"],
                "ms": ms,
                "ai_status": report.coverage.ai_status,
                "findings": len(report.findings),
                "needs_human": len(report.needs_human),
                "claims": rows,
            }
        )
        got = sum(r_["caught"] for r_ in rows)
        print(
            f"[{n}/{len(ads)}] {ad['id']:9} {ms:>6} ms  claims caught {got}/{len(rows)}  ai={report.coverage.ai_status}"
        )

    done = [r_ for r_ in results if "claims" in r_]
    claims = [(r_["id"], c) for r_ in done for c in r_["claims"]]
    up = [c for _, c in claims if c["outcome"] == "upheld"]
    cl = [c for _, c in claims if c["outcome"] == "not_upheld"]
    summary = {
        "commit": commit,
        "run_at": time.strftime("%Y-%m-%d %H:%M IST", time.localtime()),
        "models": dict(seen_models),
        "ads": len(ads),
        "ads_run": len(done),
        "ads_failed": len(ads) - len(done),
        "ai_unavailable": sum(r_["ai_status"] != "ok" for r_ in done),
        "upheld_claims": len(up),
        "caught": sum(c["caught"] for c in up),
        "strict": sum(c["strict"] for c in up),
        "lenient": sum(c["lenient"] for c in up),
        "cleared_claims": len(cl),
        "cleared_flagged": sum(c["caught"] for c in cl),
        "unlocated_claims": sum(not c["located"] for _, c in claims),
        "by_source": {
            src: {
                "upheld": sum(
                    1 for rid, c in claims if c["outcome"] == "upheld" and rid.startswith(src)
                ),
                "caught": sum(
                    1
                    for rid, c in claims
                    if c["outcome"] == "upheld" and rid.startswith(src) and c["caught"]
                ),
            }
            for src in ("ASA", "ASCI")
        },
        "by_issue": {
            i: {
                "upheld": sum(1 for c in up if c["issue"] == i),
                "caught": sum(1 for c in up if c["issue"] == i and c["caught"]),
            }
            for i in sorted({c["issue"] for c in up})
        },
        "ads_with_a_catch": sum(
            any(c["caught"] for c in r_["claims"] if c["outcome"] == "upheld") for r_ in done
        ),
        "median_ms": sorted(r_["ms"] for r_ in done)[len(done) // 2] if done else None,
    }
    OUT.write_text(
        json.dumps({"summary": summary, "results": results}, indent=1, ensure_ascii=False)
    )
    print(json.dumps(summary, indent=1))


main()
