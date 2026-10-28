# The regulator-ruling evaluation set

Round 3, improvement 1. The Round 2 evaluation used 40 posts the builder wrote. This set is different:
the labels are decisions made by advertising regulators about real ads, so they are independent of the
builder and of any recruited person.

## What is in it (`data/rulings/rulings.jsonl`)
- **ASA** (UK Advertising Standards Authority) rulings on beauty, skincare, haircare and personal-care
  ads, 2022–2026, from asa.org.uk.
- **ASCI** (Advertising Standards Council of India) Consumer Complaints Council decisions on
  personal-care ads from three press releases (Oct 2017, Aug–Sep 2018, Oct–Nov 2018), from ascionline.in.

Each record: the ruling's URL and date, advertiser and product, the ad's claims as printed in the
ruling (`ad_text`), and for each challenged claim the regulator's decision (`upheld` or `not_upheld`),
a short reason, and an issue type (substantiation, comparison, medicinal, misleading implication,
responsibility).

**Current size:** 41 rulings (15 ASA, 26 ASCI), 84 claims: 81 upheld, 3 not upheld.

## How it was made
1. Rulings were found by searching each regulator's site and press releases for personal-care and
   beauty ads, then each ruling or release was read in full. Entries were chosen for having a clearly
   quoted claim and a clear decision, not for how Plumbline would score on them. None was run through
   Plumbline before the set was frozen.
2. Claims are copied verbatim as printed in the ruling (a few words are dropped only where the ruling
   itself abbreviates). Nothing is paraphrased from the ad.
3. The label is the regulator's: a claim is `upheld` if the regulator found it in breach (usually
   unsubstantiated or misleading), `not_upheld` if it examined the claim and cleared it. ASCI's press
   releases list only upheld complaints, so every ASCI claim is `upheld`; the not-upheld claims come
   from ASA rulings that decided issues one by one.
4. `data/rulings/verify.py` re-reads every source (ASA pages, ASCI PDFs) and checks that each quoted
   claim appears in it, ignoring case, spacing and punctuation. **All 84 claims pass.** It found one
   mismatch while building (a "[sic]" the ruling prints), which was fixed in the data, not the check.
5. Entries are stored as short quotations with the source link; the full rulings stay on the
   regulators' sites.

## What it measures, and what it cannot
- **Recall on upheld claims:** of the claims a regulator found in breach, how many does Plumbline flag
  at those words? This is the Round 2 form's target (≥ 80%).
- **Claims the regulator cleared:** a handful, because regulators publish upheld rulings far more
  often than cleared ones. Plumbline has no access to the advertiser's evidence, so it is *not* expected
  to agree with a clearance; these are reported separately and not counted as errors.
- **Not tested:** whether Plumbline's fix wording is acceptable to a regulator, and whether the set
  represents all ads (it is a sample of ads that drew a complaint or an ASCI review).
- **Evidence for Plumbline's rulebook:** the check runs against Aurelle's rulebook and a generic fact
  ledger with no facts about these advertisers. So a claim like "clinically proven to reduce wrinkles in
  4 weeks" is flagged because nothing in the ledger supports it, which is the situation a regulator
  describes ("not substantiated"), and the result says so.

## Disclosure
The set was collected on 28 Oct 2026, inside the Round 3 window. It uses public regulator material only.

## How it is scored (written before the first run, 28 Oct 2026)

- Each ad's `ad_text` is checked once by the production pipeline (`run_check`) with Aurelle's rulebook as
  an agency writer would see it, using the live model chain, nothing saved. The checker, rulebook and
  prompts are **frozen at the commit recorded in the results**: nothing is tuned after seeing a result.
- A finding **touches** a claim if its text span overlaps the claim's span in `ad_text`.
- A claim is **caught** if it is touched by a finding that blocks publishing, or by a finding sent to a
  person (needs human eyes). **Strict** recall counts blocking findings only; **lenient** recall also
  counts advisory findings. The headline number is *caught*, the Round 2 form's "recall".
- **Recall** = caught upheld claims ÷ upheld claims. The target is ≥ 80%. A claim-level miss is a miss
  even if another claim in the same ad was caught.
- Cleared (`not_upheld`) claims are reported separately: how many Plumbline flagged, which is expected
  where it cannot see the advertiser's evidence.
- Misses are listed in full with the claim and what Plumbline said instead. The result is published
  whatever it is.

## Run log (decided in this order; the checker, rulebook and prompts are the same in both runs)
- **Run 1** (28 Oct 17:17 IST, commit `d563614`): ads submitted back to back. 15 of 41 ads hit the free
  model tiers' rate limits and ran with the AI checks unavailable or partial, which lowers recall for a
  reason that is about quota, not about Plumbline's rules. Kept as `results_run1.json`.
- **Run 2**: the same ads, the same code, paced at 12 s between ads so the AI checks run. Decided after
  seeing that 15 ads were affected, **before** seeing any run-2 number. Both are published; the headline
  is run 2, and run 1 shows what happens under rate limiting.
