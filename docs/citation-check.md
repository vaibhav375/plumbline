# Citation check: are Plumbline's cited reasons the right ones?

Target (Round 2 form): at least 95 of 100 findings cite a rule or fact that really fits the quoted words,
judged by the builder. Method and sheet: `services/checker/scripts/citation_sheet.py`, `data/citations/`.
A row is `y` when the cited rule or fact is genuinely about the quoted words, `n` otherwise. It does not judge
whether the finding is a good catch.

## Run 1 (28 Oct 2026, code at commit 8a9acf3)
100 findings drawn at random (seed 7): 70 from the regulator-ruling ads, 30 from Kora's posts. Scored by the
builder in `data/citations/sheet.csv`. **Result: 93 of 100 correct (95% interval about 86–97%), target 95%: not met.**
Verdicts were drafted by the assistant with a reason per row and accepted by the builder, who applied one policy: a
whole-post rule such as the missing call to action counts as correct (14 rows). Without that policy the figure is 79 of 100.

What went wrong (the 21 rows first drafted `n`; the 14 call-to-action rows were then accepted, leaving the 7 counted wrong):
1. **14 rows: a whole-post rule pinned on unrelated words.** "Every post has one clear call to action" fires on
   a post that lacks one, but the engine attached the finding to the first sentence it found, so the quote
   was e.g. "grows new hair". The finding was right; its quote was arbitrary.
2. **The wrong neighbouring rule.** For any brand whose rulebook has no CL-0x ids, the claim check cited the
   alphabetically first claim rule (Kora: FN-C1, "financial claims need a matching fact") for every claim,
   including rankings ("India's most trusted") and regulator endorsements ("RBI approved"), which have their
   own rules (FN-C3, FN-C2).
3. Not fixed, and reported as limits: rows where an AI tone or style rule is stretched (TN-01 on a claim,
   TN-05 on an already-active sentence), CL-01 on a price boast ("Rs 2 ka kamaal"), "LED" counted as an
   all-caps word, and urgency/exclamation findings under the nearer of two tone rules.

## Run 2: decided before running
Changes, made once, in the engine (not in the sample):
- A `required` rule may set `"anchor": "end"`; its finding then quotes the **last** sentence of the post,
  where the missing thing belongs. Set on Aurelle's CTA-01 and Kora's FN-S2. Other required rules (study
  footnotes) keep anchoring on the words that triggered them.
- When a rulebook has no CL-0x ids, the claim check cites the claim rule whose title names the claim's kind
  (endorsement, superlative, environmental) and only otherwise the first claim rule.

Measurement: the same two test sets are re-run with the fixed code (Aurelle's rulebook is read from the seed
files, which are the same rules as production, because production carries the old CTA-01 until the owner
approves updating it). A **new** random 100 are drawn (seed 8, 70 and 30) from that new pool; run 1's rows are
not reused. Same scoring. Both runs are published whatever they show, and the fixes are not tuned further
after seeing run 2's sample. If run 2 is below 95%, that is the result.

## Run 2 results (28 Oct 2026, fixed code, new sample)
**98 of 100 correct (95% interval about 93–99%), target 95%: met.** Raw: `data/citations/pool_run2.json`, sheet
`data/citations/sheet_run2.csv` (each uncertain row has its reason in `note`). The same standard as run 1 was
applied: a citation is correct when the cited rule genuinely applies to the quoted words, even if another rule
would fit better. The 2 wrong rows: "LED" counted as an all-caps word (not fixed), and "14% to 36% APR!!!"
cited under the urgency rule where the exclamation-mark rule fits.

What this does and does not show:
- The claim-rule fix worked where it applied: ranking and regulator-endorsement claims for Kora now cite the
  matching rule (FN-C3, FN-C2).
- The call-to-action fix only helps multi-sentence posts. Nine of the 100 rows are one-line ads where the
  closing sentence is the whole ad, so the quote is still a claim phrase; they are counted correct under run 1's
  policy. Under the strict reading (they are not), run 2 is 89 of 100.
- 20 rows were judgment calls (the cited rule applies but a better one exists, or the quote is a single
  word); they are listed with reasons in the sheet. Counting every one of them wrong would give 78 of 100.
- The improvement from 93 to 98 is partly the fixes and partly a different sample: the two intervals overlap.
- Security and loan-approval claims for Kora still fall back to the generic financial-claims rule.

The builder reviewed and accepted every verdict; the assistant drafted them. This is one person's judgment, not
an independent check.
