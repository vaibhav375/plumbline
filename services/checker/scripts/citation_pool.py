"""Round 3: collect every finding (with the rule or fact it cites, in full) from the two test sets, as the pool
for the 100-citation human check. Aurelle's regulator-ruling ads use the production rulebook as an agency
writer sees it; Kora's posts use its CSV rulebook. Nothing is saved to the database.

    PACE=10 uv run --env-file .env python scripts/citation_pool.py
"""

import json
import os
import time
from datetime import date
from pathlib import Path

import httpx

from plumbline import auth, db
from plumbline.config import Settings
from plumbline.llm import LLM, default_chain
from plumbline.models import Intent
from plumbline.parsers import parse_upload
from plumbline.pipeline import run_check
from plumbline.rules.load import load_seed_dir

ROOT = Path(__file__).resolve().parents[3]
PACE = float(os.environ.get("PACE", "0"))


def aurelle_ctx(s):
    r = httpx.post(
        f"{s.supabase_url.rstrip('/')}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": s.supabase_anon_key},
        json={"email": s.agent_demo_email, "password": s.demo_user_password},
        timeout=20,
    )
    tok = r.raise_for_status().json()["access_token"]
    prof = db.fetch_profile(s, tok, auth.verify_token(tok, s)["sub"])
    return db.load_org_context(s, tok, prof["org_id"])


def main():
    s = Settings()
    sets = [
        (
            "ruling-set",
            aurelle_ctx(s),
            "external_creator",
            [json.loads(x) for x in (ROOT / "data/rulings/rulings.jsonl").read_text().splitlines()],
        ),
        (
            "kora",
            load_seed_dir(ROOT / "supabase/seed/korapay", org_id="korapay", version="v1")[0],
            "creator",
            [
                dict(id=p["id"], ad_text=p["text"])
                for p in map(
                    json.loads, (ROOT / "data/korapay/posts.jsonl").read_text().splitlines()
                )
            ],
        ),
    ]
    pool, n = [], 0
    for name, ctx, role, items in sets:
        rules = {r.id: r for r in ctx.rules}
        facts = {f.id: f for f in ctx.facts if not f.code_only}
        for it in items:
            n += 1
            time.sleep(PACE) if n > 1 else None
            doc = parse_upload("t.txt", it["ad_text"].encode(), 1)
            rep = None
            for attempt in (1, 2, 3):
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
                    time.sleep(8 * attempt)
            if rep is None:
                continue
            for f in rep.findings + rep.needs_human:
                rule, fact = rules.get(f.rule_id or ""), facts.get(f.fact_id or "")
                pool.append(
                    {
                        "set": name,
                        "post": it["id"],
                        "text": doc.text,
                        "quote": f.quote,
                        "category": f.category,
                        "method": f.method,
                        "severity": "needs a person"
                        if f in rep.needs_human
                        else (
                            "blocking"
                            if f.severity == "blocking" and not f.advisory
                            else "advisory"
                        ),
                        "rule_id": f.rule_id,
                        "rule_title": rule.title if rule else None,
                        "rule_source": rule.source_ref if rule else None,
                        "fact_id": f.fact_id,
                        "fact_statement": fact.statement if fact else None,
                        "explanation": f.explanation,
                        "claim_status": f.claim_status,
                        "quote_in_text": f.quote in doc.text,
                    }
                )
            print(n, it["id"], len(pool), "findings so far")
    (ROOT / "data/citations").mkdir(exist_ok=True)
    (ROOT / "data/citations/pool.json").write_text(json.dumps(pool, indent=1, ensure_ascii=False))
    print("pool:", len(pool))


main()
