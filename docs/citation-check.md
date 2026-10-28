# Citation check: are Plumbline's cited reasons the right ones?

Target (Round 2 form): at least 95 of 100 findings cite a rule or fact that really fits the quoted words,
judged by the builder. Method and sheet: `services/checker/scripts/citation_sheet.py`, `data/citations/`.
A row is `y` when the cited rule or fact is genuinely about the quoted words, `n` otherwise. It does not judge
whether the finding is a good catch.

## Run 1 (28 Oct 2026, code at commit 8a9acf3)
100 findings drawn at random (seed 7): 70 from the regulator-ruling ads, 30 from Kora's posts. Scored by the
builder in `data/citations/sheet.csv`. **Result: @@RUN1@@**

What went wrong (my own draft of the verdicts, before the builder's review: 21 of 100 wrong or doubtful):
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
