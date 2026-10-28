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
