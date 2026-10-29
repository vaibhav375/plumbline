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
**2 of 49 fixes invented a claim. Target (0 invented): not met.**
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
