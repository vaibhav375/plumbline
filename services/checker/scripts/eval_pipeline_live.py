"""Live end-to-end check of the API (Task 14): real logins, real models, real database rows.

uv run --env-file .env python scripts/eval_pipeline_live.py http://localhost:8000
"""

import json
import os
import sys
import time

import httpx
import psycopg

API = sys.argv[1].rstrip("/")
U, A, P = (
    os.environ["SUPABASE_URL"].rstrip("/"),
    os.environ["SUPABASE_ANON_KEY"],
    os.environ["DEMO_USER_PASSWORD"],
)
SAMPLE = json.load(open("../../supabase/seed/aurelle/contents.json"))[0]
INTENT = json.dumps({"key_phrases": ["dark spots"], "cta": "Shop"})


def login(email):
    r = httpx.post(
        f"{U}/auth/v1/token?grant_type=password",
        headers={"apikey": A},
        json={"email": email, "password": P},
        timeout=20,
    )
    return {"Authorization": f"Bearer {r.raise_for_status().json()['access_token']}"}


def check(h, text, **extra):
    t0 = time.perf_counter()
    r = httpx.post(
        f"{API}/v1/checks",
        headers=h,
        timeout=180,
        data={"text": text, "channel": "instagram", "region": "IN", "intent_json": INTENT, **extra},
    )
    return r, (time.perf_counter() - t0) * 1000


def summary(rep):
    ids = sorted(
        {f.get("rule_id") or "" for f in rep["findings"]}
        | {f.get("fact_id") or "" for f in rep["findings"]} - {""}
    )
    return (
        f"findings {len(rep['findings'])} (blocking {sum(f['severity'] == 'blocking' for f in rep['findings'])}), "
        f"needs human {len(rep['needs_human'])}, ai {rep['coverage']['ai_status']}, replay {rep['replay']}, "
        f"ms_code {rep['ms_code']}, ms_total {rep['ms_total']}, models {rep['models_used']}\n      ids {ids}"
    )


asha, sana = login("asha@aurelle.example"), login("sana@agency.example")
print("1) creator checks the worked example")
r, wall = check(asha, SAMPLE["text"])
rep = r.json()
print(f"   HTTP {r.status_code}, {wall:.0f} ms wall; {summary(rep)}")
print(
    f"   intent passed: {rep['intent'] and all(rep['intent'].values())}; suggested: {rep['suggested_text'][:150]!r}"
)
version_id = rep["version_id"]

print("2) the same check again")
r2, wall2 = check(asha, SAMPLE["text"])
print(f"   HTTP {r2.status_code}, {wall2:.0f} ms wall; {summary(r2.json())}")

print("3) agency pre-checks the same text")
r3, wall3 = check(sana, SAMPLE["text"])
rep3 = r3.json()
print(f"   HTTP {r3.status_code}, {wall3:.0f} ms wall; {summary(rep3)}")
print(
    "   withheld:",
    "FACT-031" not in json.dumps(rep3["findings"]),
    "| note:",
    "Confidential checks run on submission." in rep3["coverage"]["not_checked"],
    "| sentence kept in suggestion:",
    "Mumbai flagship" in (rep3["suggested_text"] or ""),
)

with psycopg.connect(os.environ["DATABASE_URL"]) as c:
    agency_content = c.execute(
        "select content_id from versions where id = %s", (rep3["version_id"],)
    ).fetchone()[0]
print("4) agency submits its content")
r4 = httpx.post(f"{API}/v1/contents/{agency_content}/submit", headers=sana, timeout=180)
rep4 = r4.json()
restricted = [f for f in rep4["findings"] if f["category"] == "confidential"]
print(f"   HTTP {r4.status_code}; {summary(rep4)}")
print("   restricted findings:", [(f["fact_id"], f["explanation"]) for f in restricted])

print("5) a content id you can't see")
print(
    "   HTTP",
    httpx.post(
        f"{API}/v1/checks",
        headers=sana,
        timeout=60,
        data={
            "text": "Hi",
            "channel": "instagram",
            "region": "IN",
            "content_id": "00000000-0000-0000-0000-000000000000",
        },
    ).status_code,
)

print("6) rows in the database")
with psycopg.connect(os.environ["DATABASE_URL"]) as c:
    for vid, who in (
        (version_id, "creator"),
        (rep3["version_id"], "agency precheck"),
        (rep4["version_id"], "agency submit"),
    ):
        v = c.execute("select private, status, n from versions where id = %s", (vid,)).fetchone()
        runs = c.execute(
            "select count(*), max(cache_key is not null::int) from check_runs where version_id = %s",
            (vid,),
        ).fetchone()
        f = c.execute(
            "select count(*) from findings f join check_runs r on r.id = f.run_id where r.version_id = %s",
            (vid,),
        ).fetchone()[0]
        e = c.execute(
            "select count(*) from egress_events e join check_runs r on r.id = e.run_id where r.version_id = %s",
            (vid,),
        ).fetchone()[0]
        a = c.execute(
            "select count(*) from audit_events where entity = 'versions' and entity_id = %s",
            (str(vid),),
        ).fetchone()[0]
        print(
            f"   {who:16} version private={v[0]} status={v[1]} n={v[2]} | check_runs {runs[0]} | findings {f} | egress {e} | audit {a}"
        )
    leaked = c.execute(
        "select count(*) from egress_events where created_at > now() - interval '30 minutes'"
        if False
        else "select 1"
    ).fetchone()
