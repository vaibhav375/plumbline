# Round 2 submission: answers to paste

Every number here matches the live app, the README and the Round 2 PDF (checked 24 Oct 2026). The
evaluation figures come from the run on 23 Oct 2026, 23:43 IST, at commit a7beb93.

## Working link
https://getplumbline.xyz
(Pick a role on the first screen; no sign-up. Results and method: /about. Health: /status.)
Backup address (same app, in case the new domain hasn't reached your network): https://plumbline-pes1ug23cs665s-projects.vercel.app

## Public repository
https://github.com/vaibhav375/plumbline

## Updated PDF
https://github.com/vaibhav375/plumbline/blob/main/docs/AtoZ_Plumbline_Round2.pdf
(A Round 2 progress section, then the Round 1 plan unchanged.)

## Completed features
Plumbline works end to end from the public link, on fictional data:
- Check pasted text, DOCX, PDF or an image (OCR). 28 code rules run first; AI handles only judgement
  and claims. A finding is shown only if its rule or fact exists and its quote is really in the text, and
  a second model checks every AI finding. Every report lists what wasn't checked; there is no pass badge.
- Claims are checked against a fact ledger (supported, contradicted, unsupported, outdated, restricted)
  and fixed only with approved wording; other rewrites must pass five intent checks.
- Privacy: names and contacts are masked before any model call; confidential facts are matched in code
  only; every model call is logged without its content; agencies never see confidential facts.
- Private pre-checks, submission, a risk-ordered review queue with routing to compliance, a second
  approver enforced in the database, and a hash-chained audit log you can verify and export.
- Rulebook with a linter and CSV import; fact ledger with expiry and approved wording; guideline health
  showing which rules reviewers keep overruling and which are ready to block.
- Image accessibility floor: low-contrast text and missing alt text block, with boxes on the image.
- The same check from chat: the checker is registered on Fetch.ai's Agentverse ("Plumbline Brand
  Checker"), so ASI:One users can paste a post and get cited findings back (checked as an agency
  writer, nothing saved).
- A public results page comparing Plumbline with a one-call AI baseline, a status page, and a tour.
Full list with the Round 1 section for each: docs/features.md.

## Technology and implementation
- Web: Next.js 15 and React 19 on Vercel; Tailwind and shadcn/ui.
- Checker: Python 3.12 and FastAPI on Render (Docker); python-docx, pdfplumber, Tesseract OCR, Presidio
  with spaCy for personal-data masking.
- Data: Supabase Postgres (Mumbai) with row-level security for every role; audit log written by
  database triggers, insert-only and hash-chained; a database cron job keeps the checker awake.
- Models: open-weight Qwen3.8-27B and GPT-OSS (20B, 120B) on Groq, with Gemini 2.5 Flash as a fallback,
  all through one adapter that logs every call.
- Quality: 240 checker unit tests, 17 database tests, 18 end-to-end tests run against the live site;
  every task evaluated against real runs in docs/build-log.md.
- Results on a 40-post dev set written for this project: Plumbline found 31 of 33 labelled problems
  (94%, 95% CI 80–98%) against 18 of 33 (55%) for a one-call baseline with the whole brand book;
  79% of its findings were right (31 of 39) against 49%; 1 of 10 clean posts got a false alarm against
  4 of 10.

## Changes from Round 1
- Models: Anthropic Claude → open-weight Qwen and GPT-OSS on Groq with a Gemini fallback (₹0 budget;
  enables self-hosting). Free tiers mean the demo uses fictional data only.
- Hosting: Supabase Pro and a paid worker → free tiers kept awake by a database cron job; the cost is
  image checks at about 6 s instead of under 5 s.
- Moved to Round 3: the interviews and survey, human raters, a held-out set labelled by practitioners, a
  tester back-test and user tests. They need recruited participants, so Round 2 put its hours into
  building and measuring the product; they were not run in Round 2, and no AI-simulated persona stands in
  for them. Meanwhile, hypotheses H1–H6 were checked against published surveys, labelled as desk research
  (H1, H3 and H6 partly supported; H2 weakly; H4 and H5 no evidence).
- Found during the build and fixed: creators now see insights for their own work only, and each
  function edits only its own rules, as Round 1's permissions table required; the second approver
  shipped a round early.
Full table: docs/changes-from-round1.md.

## Three improvements for Round 3
1. **Claim recall and live-post watch:** when a fact expires or changes, every published asset using it
   gets an update-or-withdraw task; published URLs are re-checked against the approved version; claims
   inside images are checked. Measured on a human-labelled held-out set and ASCI decisions, and repeated
   on a second brand from another sector (loaded by CSV import only) to show the engine isn't tied to
   Aurelle.
2. **Fixes where creators work:** builds on the ASI:One agent shipped in Round 2 (which knows only the
   demo brand): checks in ASI:One and Slack against the caller's own brand, a no-login agency link with
   expiry and rate limits, a publish-gate API, and DOCX tracked changes. Measured by a 200-fix audit (0 invented claims) and fix
   acceptance with real writers (≥ 70%).
3. **Self-learning guidelines and confidential mode:** automated rule graduation with undo, AI-drafted
   clarifications for unclear rules from real decisions, and a self-hosted open-weight Qwen mode so
   confidential launches never leave the customer's servers.

## AI-use disclosure
Built with Claude Code (Anthropic) as a coding assistant, under my direction; I chose the design and
trade-offs, reviewed the changes, ran and judged the evaluations, and am the sole author of every commit.
The dev set and the fictional Aurelle data were drafted with the assistant. At runtime Plumbline uses
open-weight models on Groq with Gemini as a fallback, on fictional data only.
