# Results: Plumbline against real regulator rulings

Data: [the ruling set](ruling-set.md) (41 ads, 81 upheld claims, 3 cleared). Scoring rules were written
before the first run and are in that file. Raw results: `data/rulings/results.json` (run 2) and
`results_run1.json` (run 1). Harness: `services/checker/scripts/eval_rulings.py`. Checker, rulebook and
prompts were frozen at commit `d563614` for both runs.

## Headline (run 2, AI checks available on all 41 ads)

| Measure | Result | Target |
|---|---|---|
| **Recall on upheld claims (caught)** | **72 of 81 = 88.9%** | ≥ 80% |
| Strict recall (blocking findings only) | 59 of 81 = 72.8% | n/a |
| Lenient recall (any finding, incl. advisory) | 78 of 81 = 96.3% | n/a |
| Ads with at least one upheld claim caught | 37 of 41 = 90.2% | n/a |
| Recall, ASA rulings (UK) | 33 of 38 = 86.8% | n/a |
| Recall, ASCI rulings (India) | 39 of 43 = 90.7% | n/a |

"Caught" means a finding that blocks publishing, or sends the claim to a person, overlaps the claim's
words. 70 of the 72 catches came from the claim check (the claim had nothing in the fact ledger to
support it); 2 came from a rule alone. A 95% interval for 72/81 is roughly 80–94% (Wilson), so the
target is met but the margin is not wide.

By issue type (caught / upheld): substantiation 54/60, medicinal 8/10, comparison 4/4, misleading
implication 5/6, responsibility 1/1.

## Run 1, for honesty
The first run submitted ads back to back and hit the free model tiers' rate limits: 15 of 41 ads ran with
the AI checks unavailable or partial. Result: **65 of 81 = 80.2%** caught (strict 54, lenient 75). The rules
and prompts were identical; the difference is quota. That is also what a judge would see if several people
used the free-tier demo at once, so it is worth knowing: **under heavy load recall can fall toward 80%
because the AI claim extraction is the part that is rate-limited.** The code rules still run.

## The 9 claims Plumbline missed (run 2), in full
| Ad | Claim | What Plumbline did |
|---|---|---|
| ASA-002 | "innovative microspicule delivery system which helps enhance the absorption of the active ingredients" | Nothing on these words |
| ASA-007 | "I've decided to finally go Wild" | Advisory only (CTA-01); the ruling concerned an *implied* link to cancer |
| ASA-010 | "Thicker hair goals" | Nothing |
| ASA-012 | "Non-hormonal menopause solution" | Advisory only; medicinal claim for an unlicensed product |
| ASA-013 | "targeted solutions for acne, rosacea" | Nothing; medicinal claim |
| ASCI-003 | "That's Why Dentist Recommended" | Advisory only; the ruling was about an outdated survey |
| ASCI-005 | "Hair Fall ka Sahi Solution" | Advisory only |
| ASCI-017 | "Eh damaged baloonko nourish karkehairfallkamkare" (Hinglish/Hindi transliteration) | Advisory only |
| ASCI-019 | "A skin care treatment formulated with 5000 years of Ayurvedic wisdom from the granthas" | Advisory only |

Pattern: the misses are short, soft or implied claims ("goals", "solution", "wisdom"), claims whose
problem is *context* the text doesn't show (an outdated survey, an unlicensed product), and one
transliterated-Hindi line. Plumbline does best on explicit efficacy claims with numbers or "clinically
proven"-style wording. No tuning was done to fix these; they are the honest gap.

## Claims the regulators cleared (3)
Plumbline flagged 1 of 3. It flagged "N1 DERMATOLOGIST RECOMMENDED BRAND IN THE UK" as unsupported, which
is what it should do without the advertiser's survey in the fact ledger; the ASA cleared it because the
advertiser held robust survey evidence. The other two ("a new mode of action", "advanced medical-grade
scar treatment") were not flagged. Three claims are too few to say anything about false alarms: the
better evidence for that is the Round 2 clean-post test (1 of 10 clean posts got a false alarm), and the
second-brand run (next).

## What this does and doesn't show
- **Shows:** on independent, regulator-labelled claims, Plumbline catches about nine in ten, and the
  catches are mostly real claim-check findings, not noise from style rules.
- **Doesn't show:** that its fix wording would satisfy a regulator; behaviour on ads that no regulator
  looked at; a false-alarm rate. The ads are ones that drew a complaint or a review, so they are likelier
  to be problematic than average.
- **Approach limit:** the fact ledger held nothing about these advertisers, so "unsupported" is the
  expected verdict for most of them, which is also how regulators describe most of them ("not
  substantiated"). That makes this a test of *spotting claims that need evidence*, not of weighing
  evidence.
