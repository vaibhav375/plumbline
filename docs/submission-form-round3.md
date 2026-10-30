# Round 3 submission: answers to paste

Numbers match the live app, the README, docs/testing.md and the Round 3 PDF. Figures come from the runs
recorded in docs/build-log.md.

## Working link
https://getplumbline.xyz (pick a role on the first screen; no sign-up). Results and method: /about. Health: /status.

## Public repository
https://github.com/vaibhav375/plumbline

## PDF
https://github.com/vaibhav375/plumbline/blob/main/docs/AtoZ_Plumbline_Round3.pdf
(Round 3 section, then the Round 2 progress section, then the Round 1 plan unchanged.)

## Complete feature list
docs/features.md. In short: check pasted text, DOCX, PDF or images with cited findings and a "not checked" list;
claims fixed only with approved wording; private pre-checks, risk-ordered review, a second approver enforced in
the database, a hash-chained audit log; rulebook and fact ledger with CSV import; guideline health; the
Agentverse / ASI:One chat agent; and, new in Round 3: claim watch, a second brand loaded by CSV, per-brand chat
checks with one-time link codes, a publish-gate API with a Connect page, automatic rule graduation with audit
and undo, and drafted rule clarifications that the owner accepts or rejects.

## Architecture and implementation summary
- Web: Next.js 15 and React 19 on Vercel (getplumbline.xyz); Tailwind and shadcn/ui.
- Checker: Python 3.12 and FastAPI on Render (Docker), auto-deployed from main; python-docx, pdfplumber,
  Tesseract OCR, Presidio and spaCy for masking.
- Data: Supabase Postgres (Mumbai) with row-level security for every role. The audit log is written by database
  triggers and is insert-only and hash-chained. Round 3 tables (link codes, chat links, gate keys, watch tasks,
  rule changes, clarifications) are closed to users and reached through `security definer` functions that only
  a narrow `plumbline_checker` role can call; the checker holds no service key. Graduation is a database trigger
  on decisions, so it cannot be skipped by any client.
- Models: open-weight Qwen3.8-27B and GPT-OSS (20B, 120B) on Groq, with Gemini 2.5 Flash and ASI:One (asi1-mini)
  as fallbacks, all through one adapter that logs every call without its content.
- Pipeline: code rules first; AI only for judgement and claims; a finding is shown only if its rule or fact
  exists and its quote is in the text; a second model checks AI findings; fixes use approved wording only.

## Improvements made after Round 2
1. **Claim watch, tested on real rulings:** when a fact is withdrawn, expires or changes, every approved post
   that used it gets an update-or-withdraw task with approved replacement wording; live URLs are re-checked.
   **Recall on upheld claims in 41 ASA/ASCI rulings: 72 of 81 = 88.9% (target 80%, met).** A second brand
   (Kora, fictional fintech) loaded by CSV only: 27 of 30 planted issues caught, 0 of 10 clean posts blocked.
2. **Each brand's own checks, in chat and before publishing:** one-time link codes tie an ASI:One address to a
   brand; a publish-gate API answers go or not yet with reasons. Automated tests: the gate refuses open blocking
   findings and passes approved clean posts; a linked address never receives another brand's rules or facts. Fix audit
   (0 invented claims): run 1 found 2 in 49 fixes, run 2 found 1 in 73, run 3 on 48 new posts found 0 in 43. A live
   ASI:One round trip works: Live in ASI:One on 30 Oct (7:41-7:42 PM IST): `link` with a fresh code answered "Linked to Aurelle Skin", a post got a cited check "against Aurelle Skin's rulebook and facts" (2 blocking, 1 advisory), and `unlink` returned to the demo brand (docs/screenshots/asi-*.webp). A first attempt failed because ASI:One prefixes the agent's @address; fixed in commit 88e0df7.
3. **Self-learning guidelines:** rules graduate to blocking at Wilson lower bound ≥ 0.80 (≥ 10 decisions) with an
   audit entry and undo. Drafted clarifications are proposals scored against the old wording.
   **That measure is not met:** the draft agreed with 65 of 84 rulings against 63 and 66 for the old wording.
   The product shows both scores and leaves the decision to the owner.

## Testing details
docs/testing.md. 321 checker unit tests, 40 database tests, 19 end-to-end tests on the live site; the
regulator-ruling, second-brand and clarification evaluations with both runs published; live checks of the gate,
the claim watch (a fact expiry opened exactly one task) and SSRF refusal. Bugs the tests found are listed there.
Citation check (100 findings, target ≥ 95%): run 1 scored 93 of 100 (not met); after two engine fixes, a fresh
sample scored 98 of 100 (met; docs/citation-check.md; one person's judgment, verdicts drafted by the assistant and
accepted by the builder). Fix audit (target 0 invented): Three runs, each after a fix: run 1 had 2 invented in 49 fixes; run 2 (111 posts) 1 in 73; run 3 (48 new posts) 0 in 43; run 4, the 200-fix audit the target asked for (279 posts), 0 invented in 200, with 4 cross-product rows (approved wording on a different product) counted safe by the stated criterion and 4 of 200 if counted invented. Verdicts were drafted with AI assistance and agreed row by row by the builder; posts written by the same author as the guard; many safe outputs are still awkward sentences. Details in docs/fix-audit.md.

## Product roadmap
docs/roadmap.md. Now: add the missing acronyms (DIY, LED, FDA and others) to TN-03's list, then re-run the clarification measure, widen the ruling set, close
the "shorter than the evidence" gap. Next: paid or self-hosted models, claims in
images, a Hindi and Hinglish evaluation, faster image checks. Later: recruited studies and integrations.

## What does not work yet
- 2 of the 49 suggested fixes invented a claim (an added product noun; a disclosure merged into a deposit claim), and the builder would publish only 17 of 34 suggested rewrites unedited.
- Drafted clarifications did not beat the old wording in the replay, nor on 28 new live decisions on TN-03 (17 of 24 each, three runs): the real cause was an incomplete acronym list, which no rewording fixes.
- Guideline health and graduation use generated reviewer history, labelled in the app.
- Both evaluation sets are small and labelled by regulators or the builder, not independent reviewers.
- The number check accepts "2 minutes" against "under 5 minutes" (found on Kora).
- Free hosting: about 25 s for the first check after the checker sleeps; image checks about 6 s; recall can fall
  toward 80% under heavy simultaneous use because of model rate limits.
- Hindi and Hinglish are spot-tested; claims made only by imagery, video or voice-over are not checked.
- Demo accounts are shared, so judges see each other's submissions.

## Work before the window
Rounds 1 and 2 (the check engine, fixes, review, audit, the Agentverse agent, the first evaluation) were built
before Round 3 opened on 28 Oct. Round 3's additions are in commits from 28 Oct onward.

## AI-use disclosure
Built with Claude Code (Anthropic) as a coding assistant, under my direction; I chose the design and trade-offs,
reviewed the changes, ran and judged the evaluations, and am the sole author of every commit. The ruling set,
Kora's rulebook and the test posts were drafted with the assistant. At runtime Plumbline uses open-weight models
on Groq with Gemini and ASI:One as fallbacks, on fictional data only.
