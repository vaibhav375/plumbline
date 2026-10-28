# Improvement 3: does a drafted clarification beat the wording it replaces?

Pre-registered before the first run (28 Oct 2026). Results are appended below in the same file.

## Question
When Plumbline drafts a clearer wording for a rule from recorded decisions, does an AI judge given the new
wording agree with those decisions more often than with the old wording, on decisions the draft was **not**
written from?

## Data
The regulator-ruling set (`data/rulings/rulings.jsonl`): 84 advertising claims from 41 ASA and ASCI rulings,
81 upheld and 3 not upheld. Each is a real decision on whether the claim breaks the rules: *upheld* means the
rule should flag it, *not upheld* means it should not.

The rule under test is a claim-substantiation rule, because that is what the rulings decide. The shipping
claim rules (CL-01 to CL-05) are code patterns, not AI wording, so they cannot be reworded; the wording used as
"old" is the Aurelle rulebook's own CL-01 title, as a rule owner would first have written it:
*"Regulated efficacy phrases need a matching fact and compliance sign-off"* (no further instruction).
This tests the rewording loop on real decisions; it does not claim the shipping claim rules improved.

## Method (`services/checker/scripts/eval_clarify.py`)
- Two folds. Fold A writes the draft from the even-numbered claims and scores on the odd ones; fold B swaps.
  Every claim is scored held-out exactly once (n = 84).
- Drafting, replay prompts and the checker are the product's own (`plumbline/learn.py`); nothing is tuned for
  this set. Prompts are frozen at the commit recorded in the results.
- The old wording is scored twice (two independent replays) to show how much the judge's answers move by
  chance alone.
- Run twice. Both runs are published, whatever they show.

## Scoring (fixed now)
- **Primary:** overall agreement = held-out claims where the judge's answer equals the ruling, divided by 84,
  for old and new wording. The draft "helps" if new − old exceeds the old-vs-old difference between the two
  old replays *and* is positive in both runs.
- **Also reported:** recall on upheld claims (n = 81) and agreement on not-upheld claims (n = 3). With only 3
  not-upheld claims, "flag everything" would score 96.4% overall, so a rise in overall agreement without the
  not-upheld number is not claimed as better judgement.

## What would count as failing
The draft does not help if new ≤ old on either run, or if the gain is within the old-vs-old noise. That result
is reported as is, and the "accept" button stays an owner's decision either way (the screen shows both scores).

## Run 1 (28 Oct 2026, 17:5x IST): the draft made the rule worse
Held-out agreement over 84 claims: old wording 63 and 67 (the two replays differ by 4, the judge's own noise),
**drafted wording 44**. Fold B's draft agreed with 14 of 42. Cause, from reading the drafts
(`data/rulings/clarify_run1.json`): each half held only one or two "not upheld" claims, and the drafter invented
exceptions that no case showed ("general, vague or qualitative benefits are allowed"). Regulators uphold many
vague claims, so the judge stopped flagging them and recall on upheld claims fell from about 83% to about 70%
(fold A) and 30% (fold B). The 100% on not-upheld claims (3 of 3) is the over-narrowing showing up, not
good judgement.

## Decision before run 2 (made before seeing any run-2 number)
Product changes, not tuning to this set:
1. The drafting prompt now says an exception may only be added where a "Not upheld" case shows it, and that
   when such cases are few the draft should stay close to the old wording and sharpen it.
2. `evaluate` scores the draft on the cases it was written from before offering it. If it agrees with those
   less often than the old wording does, it drafts once more; if the second draft is no better, it is
   reported as not helping.
Scoring rules above are unchanged. Run 1 stays in the table.

## Run 2 (28 Oct 2026, after the fix above)
Held-out agreement over 84 claims: old wording **63 and 66** (two replays), drafted wording **65**
(`data/rulings/clarify_run2.json`; fold A 31/42, fold B 34/42). Recall on upheld claims: old 32/41, 31/41 and
31/41, 35/40 (A, B replays), drafted 30/41 and 33/40. Not-upheld claims: drafted 1/1 and 1/2, old 0/1 and 0/2.
Neither draft was redrafted: both agreed with the cases they were written from at least as well as the old
wording (35 vs 33 and 33 vs 31 of 42).

## Result against the pre-registered rule
**The draft did not help.** Run 1: 44 against 63/67 (worse). Run 2: 65 against 63/66 (the same). The rule
required a gain larger than the old-vs-old difference (3 here) in both runs; there was no gain in either.

What the two runs do support: the first version of the drafter harmed the rule when negatives were scarce, and
the fix (exceptions only where a case shows one, plus the check against the cases it was written from) removed
the harm. They do not show that a drafted wording improves agreement. The 3 not-upheld claims are too few to
tell good judgement from "flag everything", and the judge's own run-to-run noise (up to 4 of 84) is as large
as any difference seen.

## What this changes in the product
Nothing is claimed beyond this. Drafts are proposals: the screen always shows both scores on decisions the draft
wasn't written from, labels a draft that didn't beat the current wording, and nothing changes until the rule
owner accepts. The round 2 form's measure ("an accepted clarification must agree more often") is **not met on
this data**; it should be re-run on real reviewer decisions once a brand has enough disagreements, which the
generated demo history can't supply (its decisions are synthetic).
