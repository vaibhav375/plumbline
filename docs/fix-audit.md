# Fix audit: do suggested versions invent claims?

Target (Round 2 form): 0 invented claims in 200 fixes, checked by the builder. Script: `services/checker/scripts/fix_audit.py`;
sheet: `data/fixes/sheet.csv`; builder's preferences and the assistant's drafted verdicts: `data/fixes/review.csv`.

## What was measured
Every sentence the suggested version changed or dropped, for the 41 regulator-ruling ads and 30 Kora posts. A fix is
"safe" when the new sentence adds no claim, number or promise beyond the original and the approved wording; "invented"
otherwise. Dropped sentences are safe by construction.

**The test posts yield 49 fixes, not 200** (34 changed sentences and 15 dropped). A first count of 64 included 15
sentences that differed from the original only in spacing, from how I split the text; they are not fixes and were
removed. Padding to 200 by duplicating or inventing posts was not done.

## Result
**Run 1: 2 of 49 fixes invented a claim. Target (0 invented): not met.** (Run 2 and run 3 follow below.)
- A suggestion for "gives you pimple-free pure skin / Prevents pimples" added "Shop the **serum** that…": a product type the
  original never states.
- A suggestion for a Kora Save deposit claim added "by our partner bank" to "fully protected, up to any amount",
  attributing the protection to the bank, while keeping an absolute claim the ledger only supports as DICGC
  insurance up to ₹5,00,000. (Judgment call; the builder agreed.)
The other 47 only add a call to action, swap in approved wording and its footnote, drop text, or change case.
Verdicts were drafted by the assistant with a reason per row and agreed by the builder: one person's judgment.

## Separate finding: would the builder publish the suggestion?
On the 34 changed sentences the builder preferred the suggestion 17 times and the original 17 times. The originals
were preferred where the fix cut a long sentence to a fragment, produced a broken rewrite, or only added "Shop now".
So half of the suggested versions are not ones the builder would publish unedited: the product shows them as a
proposal the person edits, and nothing is applied without acceptance.

## Not done
A rule that stops a rewrite adding nouns the original lacks (the first error) is not built. The second error comes from
merging a required disclosure into a claim sentence and is not fixed either.

## Run 2: decided before running (29 Oct 2026)
Run 1's two errors had one cause: an AI rewrite brought in words of its own ("serum"; "by our partner bank, as Kora is
not a bank"). The change, made once and not tuned further after seeing run 2:
- A rewrite is now thrown away if it contains any word of 4+ letters that the original sentence lacks (ignoring
  inflections, product names, and a short list of call-to-action verbs and plain function words:
  `plumbline/fixes.py`, `_new_content_words`). A finding whose rewrite is thrown away stays for a person, as before.
  Required disclosures therefore reach a post only as approved footnotes, never through an AI rewrite.
- The sample adds the 40-post Round 2 dev set to the 41 ruling ads and 30 Kora posts, to get closer to 200 fixes.
  Every fix those 111 posts produce is audited; nothing is dropped from the sheet to improve the number, and the
  count is whatever it is (200 is not reachable by padding).
- Same scoring: a fix is invented when the new sentence adds a claim, number or promise beyond the original and the
  approved wording; the assistant drafts verdicts with reasons and the builder reviews every row; target 0 invented.
- Run 1 stays published. If run 2 finds an invented claim, that is the result.
- Side effect to report, not hide: the guard will also throw away good rewrites, so fewer sentences get an AI fix.

## Run 3: decided before running (29 Oct 2026)
Run 2 had one invented claim (drafted verdict; the builder's review is separate): a rewrite for "lead with the main point"
put the product name in front of "skincare has a long and interesting history", so the sentence said the product has that
history. The guard let it through because product names were exempt. The change, made once:
- A product name may be brought into a sentence by a rewrite only for the naming rules (`CTA-02`, terminology), where
  that is the point ("click here" becomes the product's name). For every other rule a name the sentence lacks now counts
  as new content and the rewrite is thrown away.

**Sample.** All 111 posts of runs 1 and 2 were used to find these errors, so run 3 does not reuse them. It uses 48 new
posts (24 Aurelle, 24 Kora) written by the assistant before the run (`data/fixes/posts_run3.jsonl`), with the usual
mistakes of marketing copy (efficacy claims, invented numbers, missing "#ad", "click here", shouting, "Rs.", guaranteed
returns, "no credit check"). No labels are needed: every fix those posts produce is audited. The posts are not tuned
after seeing results and none is dropped.
Scoring is unchanged (target 0 invented); run 1 and run 2 stay published, and if run 3 finds an invented claim that is the result.
Caveat: the new posts are written by the same author as the guard, so they are no more independent than the dev set.

## Run 2 and run 3 results (29 Oct 2026)
Verdicts for both runs were drafted by the assistant with a reason per row and agreed by the builder (`data/fixes/sheet_run2.csv`,
`sheet_run3.csv`); one person's judgment, not an independent check.

| Run | Code | Posts | Fixes | Invented | Target (0) |
|---|---|---|---|---|---|
| 1 | original | 71 | 49 | 2 | not met |
| 2 | + rewrites may not add words | 111 (adds the dev set) | 73 | 1 | not met |
| 3 | + product names only for naming rules | 48 new | 43 | **0** | **met** |

- **Run 2's one error:** the "lead with the main point" rule's rewrite put the product name in front of "skincare has a long
  and interesting history", so the sentence said the product has that history. Fixed for run 3.
- **Limits of run 3's 0:** the posts were written by the assistant, the same author as the guard; 43 fixes is small; the guard
  also throws away good rewrites, and many outputs are still broken sentences ("Gifted by Kora:. Open Kora.", "Why not start?").
  They add no claims and are shown as proposals the person edits; the builder preferred the suggestion on only half of the
  run-1 changed sentences.
- **Fixes with approved wording from another product** (run 2, row 52) count as safe under the criterion, because approved
  wording is allowed, but come from testing other brands' ads against Aurelle's ledger.
- **Never 200:** each run audited every fix its posts produced; 200 was not reachable without padding.

## Run 4: decided before running (30 Oct 2026)
Goal: reach the 200 fixes the Round 2 form asked for, with the final code, by auditing more posts. **No code change since
run 3** (commit `f775d73`), so this is an audit of the engine as shipped, not a new tuning round.
- **Posts:** every post we have: the 41 ruling ads, 30 Kora posts, 40 dev posts, the 48 run-3 posts, plus **120 new posts**
  (60 Aurelle, 60 Kora) written by the assistant before the run (`data/fixes/posts_run4.jsonl`; written before any run 4
  output was seen; none dropped afterwards). 279 posts in all. Earlier posts were used to find run 1 and run 2 errors, so
  run 4's number is not a clean held-out test for them; the 120 new posts are.
- **Fixes:** every sentence the suggested version changes or drops (spacing-only differences excluded). Up to 200 are drawn
  at random (seed 11) for the sheet; if fewer exist, all are audited and the count is reported as it is.
- **Scoring:** unchanged. Verdicts drafted by the assistant with a reason per row, every row reviewed by the builder.
  Target: 0 invented in 200. If run 4 finds an invented claim, that is the result and run 3's 0 stays alongside it.
- **Reported separately:** how many fixes come from the 120 new posts alone, and how many invented ones are in that part.
- Same caveats: one author for guard and posts; a rewrite dropped by the guard leaves the finding for a person.
