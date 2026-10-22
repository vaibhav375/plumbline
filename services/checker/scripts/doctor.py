"""One cheap real call per dependency: prints ✓/✗ and exits 1 on any ✗.

Lists models instead of generating, so it costs no tokens and also confirms the model IDs exist.
"""

import json
import os
import sys

import httpx

from plumbline.llm import GEMINI_MODEL, GROQ_MODELS

ENDPOINTS = {
    "groq": (
        "https://api.groq.com/openai/v1/models",
        "GROQ_API_KEY",
        sorted(set(GROQ_MODELS.values())),
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/models",
        "GEMINI_API_KEY",
        [GEMINI_MODEL],
    ),
}


def check_provider(name: str) -> str:
    url, key_var, wanted = ENDPOINTS[name]
    key = os.getenv(key_var)
    if not key:
        return f"{key_var} not set"
    r = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=15)
    if r.status_code != 200:
        return f"HTTP {r.status_code}"
    ids = {m["id"].removeprefix("models/") for m in r.json()["data"]}
    missing = [m for m in wanted if m not in ids]
    if missing:
        near = sorted(i for i in ids if any(w.split("/")[-1][:6] in i for w in missing))[:8]
        return f"model(s) {missing} not found; similar: {near}"
    return ""


def check_supabase(prefix: str) -> str:
    url, key = os.getenv(f"{prefix}SUPABASE_URL"), os.getenv(f"{prefix}SUPABASE_ANON_KEY")
    if not url or not key:
        return f"{prefix}SUPABASE_URL / {prefix}SUPABASE_ANON_KEY not set"
    r = httpx.get(f"{url.rstrip('/')}/auth/v1/health", headers={"apikey": key}, timeout=15)
    return "" if r.status_code == 200 else f"HTTP {r.status_code}"


def main() -> int:
    chain = json.loads(os.getenv("LLM_CHAIN", '["groq","gemini"]'))
    checks = {f"llm:{p}": lambda p=p: check_provider(p) for p in chain}
    checks["supabase"] = lambda: check_supabase("")
    checks["supabase-test"] = lambda: check_supabase("TEST_")
    failed = False
    for name, fn in checks.items():
        try:
            err = fn()
        except (httpx.HTTPError, KeyError, ValueError) as e:
            err = f"{type(e).__name__}: {e}"
        failed |= bool(err)
        print(f"{'✗' if err else '✓'} {name}{'  ' + err if err else ''}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
