# Changes from Round 1

What the Round 1 plan said, what Round 2 actually did, and why. Changes made during the build, with
the evidence behind each, are in the [build log](build-log.md).

## Planned changes (decided at the start of the window)

| Round 1 said | Round 2 does | Reason |
|---|---|---|
| Anthropic Claude API (Haiku to extract claims, Opus to judge) | Open-weight Qwen3.8-27B and GPT-OSS (20B, 120B) on Groq, with Gemini 2.5 Flash as a fallback | ₹0 budget; open weights make the Round 3 self-hosted mode possible |
| A paid model API, sent redacted spans, rules and public and internal facts | Free model tiers, so the demo uses fictional data only (the app says so on every page) | Free tiers may use inputs; no real data is ever sent |
| Supabase Pro (US$25 a month) during judging | Supabase free tier, kept awake by a database cron job every 10 minutes | ₹0 budget |
| A worker on a paid 2 GB instance (US$10–25 a month) | Render's free tier (512 MB, shared CPU) | ₹0 budget; the cost is image checks at about 6 s instead of under 5 s |
| Daily audit chain head e-mailed as an external anchor | Hash chain verified in the app and exportable; no external anchor yet | Later; not one of the three Round 3 commitments |
| Postgres full-text search to match claims to facts | In-memory fuzzy matching against the fact ledger | The ledger is small (40 facts); full-text search when it grows |
| ASCI decisions as an evaluation set | Not used yet | The core of the Round 3 evaluation, with UK ASA rulings |

## How the evidence plan changed, and why

Round 1 planned to prove Plumbline with recruited people: interviews, a survey, practitioners labelling a
test set, raters re-scoring the guideline audit, testers labelling a back-test, and user tests. Plumbline
is built by a one-person team, and recruiting, scheduling and running studies with outside participants
does not fit a hackathon's build windows. So the evidence plan changed from panels the builder would
recruit to evidence anyone can verify. The competition asks that everything be openable, runnable and
checkable, and a private panel is none of those.

The new plan keeps each question Round 1 asked, and answers it with a source independent of the builder,
or with a check one person can do and anyone can re-run:

| Round 1 promised | Instead | What it proves |
|---|---|---|
| A test set labelled by two recruited marketers (κ reported) | Public rulings by India's ASCI and the UK ASA on beauty and personal-care ads, the regulator's verdict as the label (Round 3) | Whether Plumbline catches what regulators actually act on, on labels independent of the builder and of anyone recruited |
| 100 citations checked by a person | 100 citations checked by the builder against the rule or fact each cites (Round 3) | That every finding points at real evidence |
| User tests: ≥ 70% of fixes accepted by writers | A 200-fix audit (0 invented claims), plus automatic checks that every fix keeps the message and re-checks clean (Round 3) | That fixes are safe and keep intent |
| Testers name the most confusing rules | Replaying recorded decisions, including regulator rulings as upheld or not-upheld decisions: a clarified rule must match them more often than the old wording (Round 3) | That clarifications reduce disagreement, measured on real decisions |
| Testers label a 60-post back-test for guideline health | The same regulator rulings, replayed as reviewer decisions for the claim rules (Round 3); the demo keeps its labelled synthetic history meanwhile | Guideline health on real, external decisions |
| Interviews and a survey | Desk research on published surveys, labelled as such ([desk research](desk-research.md)) | That the problem exists at scale; not new primary research |
| Human raters re-score the 114-rule style-guide audit | Not run; the audit stays AI-rated and labelled so | Nothing new; the label says what it is |

**What this does not show.** Regulator rulings test whether Plumbline finds the right problems, not whether
writers enjoy using it. No user study is claimed, and none is simulated with AI personas. Every number can
be re-run from the public repository.

## Round 1 commitments for Round 2, and where each stands

| Round 1 said | What happened | What replaces it |
|---|---|---|
| §3.5: 6–8 interviews and a 30+ response survey before the window, results reported in Round 2 | Not run (one-person team; see above) | [Desk research](desk-research.md) on published surveys for H1–H6, labelled as such: H1, H3 and H6 partly supported, H2 weakly, H4 and H5 no evidence |
| §3.2: human raters re-classify the 114-rule style-guide audit blind; repeat it on a D2C brand book | Not run | The audit stays AI-rated, and labelled so |
| §6.7: a held-out set of 50 items (~120 issues) labelled by two recruited marketing practitioners (κ reported), scored at Round 2 | Not run | A 40-post dev set written for this project, labels frozen before any model run, against a one-call AI baseline; in Round 3, a held-out set from public ASCI and ASA rulings |
| §4.6: guideline health fed by testers labelling a back-test of 60 past posts | Not run | Synthetic reviewer history, labelled "Includes synthetic demo history" in the app; in Round 3, regulator rulings replayed as decisions |
| §8, §10: counterbalanced tests with 6 users (matched sets of 20 posts, brand-book PDF vs Plumbline) | Not run | An automated baseline: Plumbline found 31/33 problems, the one-call baseline 18/33. No usability study is claimed |
| §6.7 Round 2 target: ≥ 90/100 citations correct, checked by a person (n = 100) | Checked automatically only: 52/52 valid (ID exists, quote at its place) | 100 citations checked by the builder in Round 3 |
| Improvement 2 target: 0 invented claims in a 200-fix audit; ≥ 70% of fixes accepted in user tests | 10 live posts audited: 0 invented claims, intent kept 10/10. No user test | The 200-fix audit and automatic intent checks in Round 3 |
| Improvement 3 target: testers name the confusing rules before seeing the list | Not run; guideline health ships with labelled synthetic history | Decision replay in Round 3 |
| §6.7 Round 2 target: recall ≥ 80% on seeded claim issues in the held-out set | No held-out set; on the dev set, 13/14 claim and fact labels found (93%), a small sample | Re-measured on the regulator-ruling set in Round 3 |

## Changes made during the build

| Round 1 assumed | Round 2 found and did | Evidence |
|---|---|---|
| Creators may see org-wide insights | The spec's own permissions table says creators see their own work only; the views now scope by role in the database | Task 19 |
| Any rule owner edits any rule | "Each function edits only its own" is now enforced in the database and in CSV import | Task 19 |
| Facts hidden by row-level security are hidden everywhere | Approved wordings restate their fact, so they now follow the fact's visibility | Task 18 |
| Writers submit only when nothing blocks | Writers can "ask a reviewer" about a blocking finding with a note; a reviewer must still decide it | Task 16 |
| Code findings in under 5 s (§6.7) | Text checks 1.8–3.6 s; image checks about 6 s on the free CPU (OCR alone ~3.8 s) | Task 23 |
| A free checker that sleeps is only a cold-start problem | The first check after any wake-up also loaded the privacy model (~18 s); it now loads at startup | Task 23 |
| The PDF's single Next.js and FastAPI service | Same split, plus a public status page, request references on every error and phase timings on every response | Task 23 |
