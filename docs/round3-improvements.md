# Three improvements for Round 3

Each one continues one of the three improvements Round 1 committed to, and each has a target that Round 3
can measure.

## 1. Claim recall and live-post watch

*Continues "Evidence or silence, and silence is never clearance".*

Round 2 checks a draft against the fact ledger at the moment of writing. But facts change: a price
expires, a study is superseded, an embargo lifts. Round 3 follows a claim after it is published:

- When a fact expires or changes, every published asset that used it gets an update-or-withdraw task,
  assigned to its owner, with the approved replacement wording if one exists.
- Published URLs are re-checked against the version that was approved, so edits made after approval
  show up.
- Claims inside image text (already read by OCR in Round 2) go through the same claim checks.

**Measured on** the held-out, human-labelled set (replacing the builder's dev set) and on public ASCI
decisions: recall ≥ 90% on seeded claims and ≥ 80% on ASCI-upheld complaints, with citations checked by
a person (≥ 95% correct). The same measures run on a second brand from another sector (a fintech app),
loaded only through the rulebook CSV import and fact ledger with no code changes, to show the engine
is not tied to Aurelle.

## 2. Fixes where creators work

*Continues "Fixes that keep intent and never invent claims".*

Round 2 fixes live in the Plumbline web app. Most writers are elsewhere: an agency's document, a
chat thread, a scheduling tool. Round 2 already took the first step: the checker is an Agentverse agent,
so anyone in ASI:One chat can paste a post and get the cited findings and approved wording back (checked
as an agency writer, nothing saved). It only knows the demo brand. Round 3 takes the same checks and
fixes to where creators work, each caller checked against their own brand:

- The ASI:One agent and Slack: paste a draft, get the findings and the suggested version in the chat,
  checked against the caller's brand (linked to their Plumbline organisation).
- A no-login link for agencies, with expiry and rate limits, so an outside writer can pre-check without
  an account.
- A publish-gate API that scheduling and CMS tools can call before a post goes out.
- DOCX tracked changes, so fixes arrive as redlines the writer accepts one by one.

**Measured by** a 200-fix audit with 0 invented claims, and ≥ 70% of fixes accepted in user tests with
real writers.

## 3. Self-learning guidelines and confidential mode

*Continues "Guidelines get clearer; rules earn the right to block".*

Round 2 shows which rules reviewers keep overruling and which have earned the right to block, but a
person still edits the rulebook. Round 3 closes the loop:

- Automated graduation: when a brand rule's agreement lower bound reaches 0.80, it moves to blocking,
  with an audit event and a one-click undo.
- AI-drafted clarifications: for a rule that "may be unclear", Plumbline drafts a clearer version from
  the real decisions and their reasons, for the rule owner to accept or edit.
- A self-hosted mode on open-weight Qwen, so confidential launches never leave the customer's servers
  (the model chain already speaks the same API to a local server).

**Measured by** whether the top-5 "may be unclear" rules include at least 2 of the 3 rules testers name
as most confusing before they see the list, and by the share of rules that graduate.
