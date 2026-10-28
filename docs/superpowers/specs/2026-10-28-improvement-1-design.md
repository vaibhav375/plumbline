# Improvement 1: claim watch, tested against real regulator rulings

Round 3, built 28–30 Oct 2026. Committed in the Round 2 form as: when a fact expires or changes, every
published post that used it gets an update-or-withdraw task with the replacement wording; published URLs
are re-checked against the approved version. Measured on a held-out set from public ASCI and UK ASA
rulings (recall ≥ 80% on upheld claims; ≥ 95% of 100 citations correct, builder-checked), repeated on a
second brand loaded by CSV only.

## Why
Round 2 checks a claim once, while the post is written. Facts then change (a price ends, a study is
superseded, an embargo lifts, a fact is withdrawn) and live posts keep saying the old thing. The brand
only finds out when a regulator or a customer does.

## Goals
- Know, for every approved post, which facts it rests on, and what those facts looked like at the time.
- When a fact later expires, changes, loses verification or disappears, open a task for the post's owner:
  update (with the approved replacement wording when one exists) or withdraw.
- When a post has a live URL, re-read the page and flag approved sentences that are gone or altered.
- Measure claim detection on independent labels (regulator rulings) and show the engine works for a
  second, differently-shaped brand with no code changes.

## Non-goals
- Taking posts down or editing live pages (Plumbline only raises tasks).
- Crawling the web. Only URLs a person registers for an approved version.
- Claims inside images (not committed).

## Anti-goals
- A task for a post that didn't use the fact, or the same task opened twice.
- A scan that can be pointed at internal addresses (the URL check must not become a request proxy).
- Showing confidential facts to roles that can't see them: a task for a confidential fact says only
  "a restricted fact changed".

## Design

**What a post relied on.** The check report gets `claims_used`: each *supported* claim with its fact id
and a digest of the fact (statement, number, unit, product, market, dates, confidentiality, verified).
Posts checked before this change have none; they are covered by re-checking them.

**The scan** (`watch.compute_tasks`, pure): for each approved or published version's latest report, compare
each used fact with the fact now.
- missing → `removed`; `valid_until` passed since → `expired`; no longer verified → `unverified`; digest
  differs otherwise → `changed`; embargo newly in force → `changed`.
- A replacement is suggested only from an approved wording of that fact in the claim's market and channel.
Tasks live in `watch_tasks` (open → done or dismissed, with who and when). A partial unique index on open
`(version, fact, reason)` makes a re-scan idempotent. The task is assigned to the content's creator.
The scan runs when the Watch page is opened and from a "Scan now" button, as the narrow checker role (the
facts it needs include confidential ones; the page hides their text from non-reviewers).

**Published URLs.** The owner (or brand owner) registers a URL against an approved version. A check fetches
it with SSRF guards (http/https only; every hop's host resolved and refused if private, loopback or
link-local; 3 redirects, 1 MB, 8 s), strips markup to text, and compares sentence by sentence with the
approved text using fuzzy matching (≥ 90). Approved sentences that are missing or altered open a `drift`
task listing up to three. Extra text on the page (navigation, other copy) is ignored.

**The Watch page** lists open tasks (post, owner, fact, why, replacement wording, "Mark done" / "Dismiss"
with a reason) and registered URLs with "Check now". Visible to reviewers, compliance, brand owner and
auditor; creators see their own tasks.

## Measured by
- Unit tests: every change reason, idempotence, replacement choice, no task for unrelated posts, SSRF
  refusals, drift detection, confidential facts redacted in tasks.
- Database tests: org isolation and task state changes.
- Live: expire a fact in the demo org, scan, see the task for exactly the posts that used it; edit a
  served page, re-check, see drift.
- Evaluation (separate section): a held-out set of ASCI and UK ASA rulings, recall on upheld claims, false
  alarms on cleared ads, and the same on a second brand loaded from CSV.

## Choices that are mine
- Approved or published versions count as "live"; there is no separate "published" action.
- One task per (post, fact, reason); a fact that both changed and expired gives two tasks.
- The scan on page open is the trigger; a scheduled run is roadmap.
