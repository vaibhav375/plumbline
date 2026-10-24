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
- Models: open-weight Qwen3.8-27B and GPT-OSS (20B, 120B) on Groq, with Gemini 2.5 Flash and Fetch.ai
  ASI:One (asi1-mini) as fallbacks, all through one adapter that logs every call.
- Quality: 251 checker unit tests, 17 database tests, 18 end-to-end tests run against the live site;
  every task evaluated against real runs in docs/build-log.md.
- Results on a 40-post dev set written for this project: Plumbline found 31 of 33 labelled problems
  (94%, 95% CI 80–98%) against 18 of 33 (55%) for a one-call baseline with the whole brand book;
  79% of its findings were right (31 of 39) against 49%; 1 of 10 clean posts got a false alarm against
  4 of 10.

## Changes from Round 1
- Models: Anthropic Claude → open-weight Qwen and GPT-OSS on Groq, with Gemini and ASI:One as fallbacks
  (₹0 budget; enables self-hosting). Free tiers mean the demo uses fictional data only.
- Hosting: Supabase Pro and a paid worker → free tiers kept awake by a database cron job; the cost is
  image checks at about 6 s instead of under 5 s.
- The evidence plan changed. Round 1 planned recruited studies (interviews, a survey, practitioners
  labelling a test set, raters, testers, user tests). Plumbline is built by one person, and recruiting
  outside participants doesn't fit a hackathon, so the plan moved to evidence anyone can verify: a
  held-out set from public ASCI and UK ASA rulings (the regulator's verdict is the label), citations and
  a 200-fix audit checked by the builder, and recorded decisions replayed for guideline health. Published
  surveys stand in for interviews, labelled as desk research. No user study is claimed, and none is
  simulated with AI personas.
- Added: Fetch.ai Agentverse / ASI:One chat access to the checker, a custom domain, public results and
  status pages.
- Found during the build and fixed: creators now see insights for their own work only, and each
  function edits only its own rules, as Round 1's permissions table required; the second approver
  shipped a round early.
Full table: docs/changes-from-round1.md.

## What does not work yet
- Not built yet: watching published posts, the publish gate, per-brand chat checks, automatic rule
  graduation (Round 3), and Slack, DOCX tracked changes, claims inside images and an external audit
  anchor (not committed).
- The evaluation uses a 40-post dev set written for this project, for one fictional brand.
- Guideline health runs on generated reviewer history, labelled in the app.
- The ASI:One agent knows only the demo brand, checks as an agency writer and saves nothing.
- Free hosting: about 25 s for the first check after the checker sleeps; image checks about 6 s;
  slower replies under simultaneous use while the AI falls back.
- The AI tone check sometimes flags a soft line as an unsupported claim (1 of 10 clean dev posts).
- Hindi and Hinglish are spot-tested, not evaluated; claims made only by imagery, video or voice-over
  aren't checked.
- Demo accounts are shared, so judges see each other's submissions.

## Three improvements for Round 3
None of these needs anyone but the builder; every measure can be re-run from the repository.
1. **Claim watch, tested against real regulator rulings:** when a fact expires or changes, every
   published post that used it gets an update-or-withdraw task with the replacement wording; published
   URLs are re-checked against the approved version. Measured on a held-out set from public ASCI and UK
   ASA rulings (recall ≥ 80% on upheld claims; ≥ 95% of 100 citations correct, checked by the builder),
   repeated on a second brand loaded by CSV only.
2. **Each brand's own checks, in chat and before publishing:** a brand links its ASI:One address to its
   Plumbline organisation with a one-time code, so chat checks use its own rules and facts; a publish-
   gate API tells scheduling and CMS tools "not yet" while anything blocks. Measured by a 200-fix audit
   by the builder (0 invented claims) and automated tests (the gate refuses 100% of versions with an
   open blocking finding; no brand ever receives another brand's rules or facts).
3. **Self-learning guidelines:** brand rules graduate to blocking automatically at a Wilson lower bound
   ≥ 0.80, with an audit entry and undo; for each "may be unclear" rule, Plumbline drafts a clearer
   version from recorded decisions for the owner to accept. Measured by replaying recorded decisions,
   including regulator rulings: an accepted clarification must agree with them more often than the old
   wording.

## AI-use disclosure
Built with Claude Code (Anthropic) as a coding assistant, under my direction; I chose the design and
trade-offs, reviewed the changes, ran and judged the evaluations, and am the sole author of every commit.
The dev set and the fictional Aurelle data were drafted with the assistant. At runtime Plumbline uses
open-weight models on Groq with Gemini and ASI:One as fallbacks, on fictional data only.
