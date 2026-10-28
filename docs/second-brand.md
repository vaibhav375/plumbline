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
