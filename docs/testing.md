# Testing details (Round 3)

Everything here can be re-run from the repository by one person. Commands are in the [Makefile](../Makefile).
Results on real runs are in the [build log](build-log.md) under the task named; failures are kept.

## Automated tests (counts at the final commit, 28 Oct 2026)

| Layer | Count | What it covers | Command |
|---|---|---|---|
| Checker unit tests | 321 | rule engine, claims, validators, privacy masking, fixes and the intent lock, audit chain code, gate decisions, chat linking and rate limits, claim-watch scans (SSRF guards, changed numbers), clarification drafting and replay, API errors | `make test` |
| Database tests | 40 | run against a separate test Supabase project: row-level security for every role, hash-chained audit log, second approver, narrow checker role (no table access), link codes (single use, expiry), gate keys, claim-watch tasks, automatic graduation | `make test-db` |
| End-to-end tests | 19 | Playwright against the live site: role landing, check, fix and re-check, submit, review, audit verify, rulebook and fact ledger, guideline health, status, Connect page | `BASE_URL=https://getplumbline.xyz pnpm exec playwright test` |

Round 2 ended with 251 / 17 / 18. Round 3 added 70 checker tests, 23 database tests and 1 end-to-end test.

## Round 3 behaviours, checked on production

| Improvement | Check | Result |
|---|---|---|
| 1 Claim watch | An approved post recorded the fact it relied on; that fact's end date was moved into the past | the next scan opened exactly one task, on the one post that used it; a repeat scan opened none; the date was restored straight away |
| 1 Claim watch | A live URL on an internal address (169.254.169.254) | refused with 422; a creator's scan attempt gets 403 |
| 2 Publish gate | no key / revoked key | 401 |
| 2 Publish gate | submitted version; approved version with open blocking findings; clean approved post | not_yet; not_yet; go |
| 2 Publish gate | right text hash / edited text / unknown id | go / not_yet / 404 |
| 2 Chat linking | one-time code reused or expired; address linked to org A asks for org B's rules | refused (database tests); the org always comes from the link row |
| 3 Graduation | rule at 16 of 16 agreeing decisions (lower bound 0.806) | moves to blocking, one audit row; none under 10 decisions or under the bound; mandatory rules untouched |
| 3 Undo | undo a graduation | rule returns to advisory and stays pinned until the owner releases it |

## Measured evaluations

| Evaluation | Data | Result | Target | Document |
|---|---|---|---|---|
| Round 2 dev set | 40 posts written for the project | 31 of 33 problems found (94%); 1 of 10 clean posts falsely alarmed | none | [README](../README.md) |
| Regulator rulings (improvement 1) | 41 ASA and ASCI rulings, 84 claims, 81 upheld | 72 of 81 upheld claims caught = **88.9%** (run 1, rate-limited: 65 of 81) | ≥ 80% **met** | [ruling-eval.md](ruling-eval.md) |
| Second brand by CSV (improvement 1) | Kora, a fictional fintech app; 20 problem posts, 10 clean | 27 of 30 issues caught; 0 of 10 clean posts blocked | none | [second-brand.md](second-brand.md) |
| Clarification replay (improvement 3) | the 84 ruling claims, scored on claims the draft was not written from | drafted wording 65 of 84 vs old wording 63 and 66 | draft beats old wording: **not met** | [clarify-eval.md](clarify-eval.md) |
| Citation check (improvement 1) | 100 findings drawn from the two sets above | _pending: filled in by the builder_ | ≥ 95% correct | `data/citations/sheet.csv` |
| Fix audit (improvements 1 and 2) | 200 fixes drawn from the same posts | _pending: filled in by the builder_ | 0 invented claims | `data/fixes/sheet.csv` |

## Bugs the tests found (and what changed)

- A rulebook without the ids CL-01/03/04/05 crashed the claim step: found only by loading a second brand. Fixed
  with a fallback and a test.
- "60% in 2 weeks" scored 90+ against "32% in 8 weeks" in fuzzy matching, so a changed number went unnoticed.
  Numbers are now compared separately.
- Revoking a gate key or chat link failed in the browser because CORS allowed only GET and POST.
- The first draft of the clarification writer made a rule worse (44 of 84 against 63–67) by inventing exceptions;
  the fix was decided before run 2 and both runs are published.
- A graduation test expected 20 of 20 but the rule graduated at 16 of 16: the test was wrong, not the trigger.

## Known limits of the testing

- Both evaluation sets were labelled by the builder or by regulators, not by independent reviewers, and are small.
- The model chain runs on free tiers, so a run under load can fall toward the rate-limited result (run 1 above).
- Graduation and guideline health use generated reviewer history, labelled in the app; the clarification
  measure should be re-run on real decisions.
- An end-to-end test that submits to the live site is not repeated in a loop, because demo accounts are shared.
