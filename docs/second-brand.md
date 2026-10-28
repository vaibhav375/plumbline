# The second brand: Kora (a fictional fintech app)

Round 3, improvement 1: "repeated on a second brand from another sector, loaded only through CSV, to
show the engine isn't tied to one brand."

**Kora** is a fictional Indian payments, savings, credit and investing app. Its rulebook, fact ledger,
approved wordings and terms are four CSV files in `supabase/seed/korapay/`, in the same format as
Aurelle's, read by the same loader (`plumbline.rules.load.load_seed_dir`). The rules cover what a fintech
actually gets wrong: assured returns, regulator-endorsement claims, security claims, loan-approval promises,
the market-risk disclaimer, APR disclosure, "p.a." on rates, the "not a bank" statement, offer T&Cs, and
creator-post disclosure; plus tone and style rules and an AI tone rule. The facts include rates, limits,
insurance cover, a user count, an expired offer and an embargoed launch.

**Authorship, stated plainly.** The rulebook, facts and the test posts were written by the builder with an
AI assistant. The rules cite public regimes (SEBI's mutual-fund advertisement code, RBI's digital-lending
directions, ASCI's Code) in their `source_ref`, but Kora's own policy numbers are fictional. No real company
or real figure is used.

## What loading it taught us (the engine was not fully brand-agnostic)
Loading a second brand found one coupling: the claim check cited the rule ids `CL-01`, `CL-03`, `CL-04` and
`CL-05` directly, so a rulebook without those ids would have crashed on its first claim. Kora deliberately
uses its own ids (`FN-C1`…). The fix is small and in the engine: if those ids are absent, the claim check
cites the first rule in the `claim` category, and a rulebook with no claim rule gets a clear error. With
that fix, Kora needed no other change: the pipeline, validators, fixes, review and gate are unchanged.

## The test (`data/rulings` style, labels frozen before the run)
`data/korapay/posts.jsonl`: 20 problem posts with 30 labelled issues, and 10 clean posts written to the
rulebook. Scoring is fixed in advance:
- An issue is **caught** if Plumbline raises the expected thing at that place: for a *claim* issue, a
  blocking finding or one sent to a person that overlaps the quoted words; for a *rule* issue, a finding
  from the named rule. Issues marked `blocks` must be a blocking finding (or sent to a person); issues
  marked `flag` count any finding, because those rules are advisory or minor by design.
- A **false alarm** is a clean post that gets a blocking finding or one sent to a person. Advisory notes on
  clean posts are reported separately.
- The checker, rules and prompts are not changed after seeing results.

## Run log
- **Run 1** (28 Oct 18:22 IST, commit `e504548`): 27 of 30 issues caught; 0 of 10 clean posts blocked, but
  9 of 10 clean posts carried advisory "TM-K1" notes. Cause: my own data error, not the engine: the term
  list gave "KORA" as a wrong variant of the preferred name "Kora", and matching ignores case, so the
  correct name flagged itself. Kept as `results_run1.json`.
- **Run 2**: after removing that variant from `terms.csv`, nothing else changed (rules, facts, labels, code).
  This was decided after seeing run 1, as a data fix, so both runs are published and run 1 is not hidden.

## Results (run 2; code `e504548`, terms fixed; raw: `data/korapay/results.json`, run 1: `results_run1.json`)

| Measure | Result |
|---|---|
| Labelled issues caught | **27 of 30 = 90.0%** (run 1: also 27 of 30) |
| Issues that must block: caught | 19 of 22 |
| Issues that only need flagging (tone, style, offers): caught | 8 of 8 |
| By kind: rule issues / claim issues | 20 of 21 / 7 of 9 |
| Clean posts that were blocked or sent to a person | **0 of 10** |
| Clean posts with any finding at all (run 2) | 0 of 10 (run 1: 9 of 10, all caused by the data error above) |
| AI checks available | on all 30 posts |

Both brands go through the same engine: Aurelle's 31 of 33 (Round 2 dev set) and 72 of 81 (regulator rulings),
Kora's 27 of 30. These are different tests with different authors of the labels, so they are not one
number; what they show together is that the engine is not tuned to one rulebook.

### The 3 misses, in full
1. **KP-05, "Need cash? Kora Credit gives instant approval, no credit check. Apply now."**, expected rule
   FN-R2 (credit offers must state the APR). **Caught the two "instant approval" / "no credit check" issues
   (FN-C5); missed the APR rule.** This one is partly my labelling error: FN-R2 triggers on the words
   "loan", "credit line", "EMI" or "borrow", and this post says "Kora Credit" only, so the rule never
   fired. The label stays as written (rewriting it after the run would be cheating); the cause is the rule's
   trigger being too narrow, a rulebook fix a brand owner would make.
2. **KP-02, "Open an account in 2 minutes."** The fact says "under 5 minutes". Plumbline judged the claim
   *supported* and raised nothing on it. A regulator would ask for evidence of 2 minutes. This is a real
   engine gap: the number check treats a time shorter than the evidence as consistent with "under N".
   (It did catch the other issue in that post, "RBI approved".)
3. **KP-09, "Join with zero joining fee on KoraCard."** The fact for this offer ended on 30 Sep 2026.
   Plumbline found no claim in the sentence at all (code detection needs a number or a keyword, and the AI
   extraction did not pick it up), so it never compared it with the expired fact. A real miss: "zero" /
   "free" offers without a number are a known blind spot.

### What this does and doesn't show
- **Shows:** a brand from another sector, with different rules and facts, was loaded from four CSV files with
  the same loader and checked by the same engine, with no clean post blocked and 9 in 10 issues caught.
  Loading it found one real coupling (claim rule ids), fixed and tested.
- **Doesn't show:** performance on real fintech ads: the 30 posts were written by the builder with an AI
  assistant, with labels fixed before the run, so they are easier than ads written by others. This is
  evidence the engine generalises, not a benchmark. The regulator-ruling run is the independent test.
