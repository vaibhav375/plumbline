# Build log: per-task evaluation

After every task: check the result against the plan and the Round 1 spec (§n), with evidence from
real runs, not assumptions. When something that was assumed turns out wrong, record the alternative
chosen and why. Newest last.

## Task 0: accounts, keys, tools (22 Oct)

| Check | Evidence | Result |
|---|---|---|
| Keys work | `make doctor`: Groq ✓, Gemini ✓, Supabase ✓, Supabase-test ✓ (model listing, no tokens spent) | Pass |
| Local tools | node 25, pnpm 9.15, Python 3.12.6, uv 0.12, tesseract 5.5 | Pass |

**Assumptions that failed, and the alternatives chosen**
- *Groq `qwen/qwen3-32b` and `llama-3.1-8b-instant` exist.* Both are retired; the key's model list
  has neither. Replaced with `qwen/qwen3.8-27b` (judge, rewrite; still Qwen, so the "self-hosted Qwen"
  production story holds) and `openai/gpt-oss-20b` (extract, support; small and fast). Doctor now
  checks these IDs by name.
- *The project can live on the USB stick.* It works but is slow (pnpm install 20 min, one hang) and
  the stick unmounted twice. Kept for now; the internal disk now has about 5 GB free, enough to move
  if it gets worse. Everything is pushed to GitHub after each task.

## Task 1: scaffold, CI, doctor

| Check | Evidence | Result |
|---|---|---|
| `Settings` defaults (plan Task 1 interface) | `test_settings_defaults`, `test_llm_chain_from_env` | Pass |
| CI green | GitHub Actions run 39731443700: ruff, pytest, web typecheck + build | Pass |
| No secrets in git | staged-file scan for key prefixes; `.env`, `.env.local` ignored | Pass |
| Typecheck works without `next-env.d.ts` (as in CI) | ran tsc with it moved away | Pass |

## Task 2: schema, RLS, hash-chained audit

| Check | Evidence | Result |
|---|---|---|
| Plan's 6 DB tests | `make test-db` against `plumbline-test` | Pass |
| Wilson lower bound correct | 8/10 → 0.490, 95/100 → 0.888 (matches the formula in Python) | Pass |
| anon has no access | `information_schema.role_table_grants` for anon: 0 rows; REST call without login: 401 | Pass |
| Both projects on the same migrations | `schema_migrations`: 0001–0003 on both | Pass |

**Deviations from the plan, with reasons**
- *No local `supabase start`* (no Docker space): tests run in a rolled-back transaction on the cloud
  test project, switching to the `authenticated` role with forged JWT claims as PostgREST does.
- *One global audit chain → one chain per org.* An org's auditor can only read its own rows under RLS,
  so a global chain could never be verified by them.
- *`at::text` in the hash → explicit UTC ISO text.* `at::text` depends on the session time zone, so
  verification could fail for reasons unrelated to tampering.
- *Append-only enforced twice*: privileges revoked and a trigger that raises on update/delete, so
  even the table owner can't edit history silently.

## Task 3: Aurelle seed data and demo users

| Check | Evidence | Result |
|---|---|---|
| Worked example verbatim (§4.4) | `test_worked_example_present`; text copied from the spec | Pass |
| Banner matches §4.4 numbers | WCAG ratio `#B8B2A7` on `#FBF6EC` = **1.96:1**; Ink `#2D2A27` on Cream = **13.24:1** (computed) | Pass |
| Banner readable by OCR | `tesseract banner_v1.png` → "GLOW IN 2 WEEKS AURELLE" | Pass |
| Idempotent seed | run 1: all inserted; run 2: **0 inserted, 0 updated**, all unchanged | Pass |
| Demo logins | password grant for all 5 users through Supabase Auth | Pass |
| Confidential facts hidden (§4.5) | creator/agency see 35 facts, FACT-031 hidden; reviewer roles see 40 | Pass |
| Health labels in `history.json` true | live `rule_health`: TN-02 0.855 (≥ 0.80, ready), GM14 0.912, CTA-02 0.654, GM07 n = 5 (too few), TN-03 0.145 | Pass |
| Small groups hidden | `insights_by_origin` shows employee/agency/ai_tool (3 authors), hides freelancer (2) | Pass |
| Audit chain over seeded data | 368 events: every hash recomputes, every link holds | Pass |
| Rules backed by sources | each rule cites a brand-book section or a real Indian code (ASCI, CCPA 2024, D&C Act, WCAG 2.2) | Pass |
| Pattern rules agree with their own examples | `test_pattern_rules_agree_with_their_own_examples` | Pass |

**Problems the evaluation caught, and fixes**
- *Term variants that match their own preferred name* ("rice cleanser" inside "Gentle Rice Cleanser",
  "glow oil", "Barrier Cream", "daily sunscreen", "vitamin c brightening serum"): these would flag
  correct copy. Removed; `test_no_term_variant_matches_its_own_preferred_name` guards it.
- *RLS was wider than §4.5 allows*: creators and agencies could read the whole org's audit log, and
  agencies could read every version. Migration 0004: audit events carry `subject_user`; creators see
  only events about their own work; agencies see only their own versions and contents. Two new DB
  tests; live re-check: agency versions 184 → 0, creator audit 368 → own only.

**Open items**
- §4.5 says creators see insights for their own work; `rule_health` is still org-wide for internal
  creators. Decide in Task 19 (insights page), where the view is used.
- TN-02 in the plan covers "! max 1, plus all-caps words". Split into TN-02 (count `!`) and TN-03
  (all-caps pattern) because one `count` rule can't express both. Superset of the tests' IDs.
