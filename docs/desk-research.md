# Desk research for hypotheses H1–H6

**This is desk research, not primary research.** Round 1 (§3.5) planned 6–8 interviews and a survey with
30+ responses before the window, with results reported in Round 2. These, and the other studies that need
recruited participants (human raters for the style-guide audit, a held-out set labelled by practitioners,
a back-test labelled by testers, counterbalanced user tests), were not run: Plumbline is built by a
one-person team, and recruiting outside participants does not fit a hackathon's build windows. See
[how the evidence plan changed](changes-from-round1.md#how-the-evidence-plan-changed-and-why).

In their place, each Round 1 hypothesis was checked against published surveys and reports, retrieved
on 24 October 2026. Every figure below was read at its source. Most sources are vendors, small or
regional samples, or adjacent fields, so they can support or weaken a hypothesis but cannot confirm it.
No AI-simulated personas were used as evidence here: Round 1's synthetic panel (Appendix E) stays what
it was, a design critique.

| | Hypothesis (Round 1 §3.5) | Verdict from public evidence |
|---|---|---|
| H1 | Reviewers spend most review time on mechanical issues | **Partly supported, indirectly** |
| H2 | Creators prefer an editable suggested fix to a list of violations | **Weak support, by analogy** |
| H3 | Brand owners can name at least three rules their teams interpret differently | **Supported indirectly** |
| H4 | Claim evidence lives in email and spreadsheets, not a system | **No evidence found** |
| H5 | Brand owners would pay per organisation, not per seat | **No evidence on preference; the market does both** |
| H6 | The synthetic panel's conditions matter to real reviewers | **Partly supported (privacy, accuracy)** |

## H1. Reviewers spend most review time on mechanical issues

- **Review dominates the cycle.** In a September 2023 online survey of 48 marketing and 59 compliance
  leaders at US financial institutions, marketers said a piece of content takes 10 working days, of
  which six to eight are compliance review; 58–71% of content goes to compliance.
  ([Saifr](https://saifr.ai/blog/perception-vs.-reality-workflow-gaps-between-marketing-and-compliance), a
  compliance-AI vendor.)
- **Violations are often mechanical and fixable.** ASCI's February 2025 study of India's "Top 100
  Digital Stars" found 69% non-compliant with disclosure guidelines: 56.8% of violations had no
  disclosure label and 43.2% buried it in hashtags; 59 of the 69 corrected their posts without contest.
  ([ASCI press release](https://www.ascionline.in/wp-content/uploads/2025/02/Press-Release-Influencer-Disclosure-Guidelines-ASCI-Report.pdf))
- **Limits:** neither source splits reviewer time into mechanical and substantive work; one is a US
  financial-services vendor survey, the other a sample of influencer posts, not reviewers.
- **What it changes:** nothing yet. Code-first checks for mechanical issues (required labels, banned
  phrases, contrast) stay first in the pipeline; the time split stays an open question.

## H2. Creators prefer an editable suggested fix to a list of violations

- **By analogy from software:** in GitHub's public beta (May–July 2024), developers resolved code-scanning
  alerts with an AI-suggested fix in a median of 28 minutes, against 1.5 hours to resolve the same alerts
  manually; developers can dismiss, edit or commit each fix.
  ([GitHub blog](https://github.blog/news-insights/product-news/secure-code-more-than-three-times-faster-with-copilot-autofix/))
- **Limits:** vendor data, a different profession, and it measures speed, not preference.
- **What it changes:** keeps the Round 1 design (suggestions are editable and never applied without a
  click); fix acceptance with real writers is not measured; Round 3 measures fix safety instead (a 200-fix audit and automatic intent checks).

## H3. Brand owners can name at least three rules their teams interpret differently

- **Off-brand content is common.** 81% of brand-management respondents from 200+ organisations said
  their organisations deal with off-brand content (Lucidpress, *2019 State of Brand Consistency*, as
  reported by [ASI Central](https://members.asicentral.com/news/newsletters/promogram/december-2019/survey-brand-consistency-can-boost-sales/);
  a vendor survey, and dated).
- **A written rule still gets read differently.** In the ASCI study above, 43.2% of violations were
  disclosures that existed but were buried in hashtags, against a guideline that requires them upfront.
- **Round 1's own audit:** 15–20% of the 114 rules in a public style guide give no threshold or example
  (§3.2; AI-rated, not yet checked by human raters).
- **Limits:** evidence that guidelines are applied inconsistently, not that brand owners can name the
  rules.
- **What it changes:** supports building guideline health (shipped in Round 2 with labelled synthetic
  history); Round 3 replays regulator rulings as real decisions instead of the "name three rules" test.

## H4. Claim evidence lives in email and spreadsheets, not a system

- **No public survey found.** In pharma, dedicated claims libraries exist and are sold as the norm
  (for example [Veeva PromoMats claims management](https://www.veeva.com/products/veeva-promomats/claims-management/)),
  so H4 is probably false there; for consumer brands no data was found either way.
- **What it changes:** Round 2's fact ledger imports CSV, which works whether evidence lives in a
  spreadsheet or is exported from a system; syncing with an existing source stays on the roadmap.

## H5. Brand owners would pay per organisation, not per seat

- **The market prices both ways.** Software-directory listings show per-user pricing for Templafy
  ([ZoftwareHub](https://zoftwarehub.com/products/templafy/pricing)) and Brandworkz
  ([Gartner Peer Insights](https://www.gartner.com/reviews/product/brandworkz)), a flat rate for BrandHalo
  ([GetApp](https://www.getapp.com/all-software/a/brandhalo/)) and token-based pricing on the Acrolinx
  listing ([G2](https://www.g2.com/products/acrolinx/pricing)). Not checked against vendors' own pages or
  sales quotes.
- **Limits:** what vendors charge says nothing about what buyers prefer.
- **What it changes:** nothing in the product; pricing remains an untested hypothesis.

## H6. The synthetic panel's conditions matter to real reviewers

- **"Confidential facts never reach an AI":** in Salesforce's *State of Marketing* (4,800+ marketing
  leaders in 29 countries, 250 in India), 41% of CMOs named data exposure their top AI concern, against
  29% of VPs and 32% of team leads (as reported by
  [Entrepreneur India](https://india.entrepreneur.com/news-and-trends/79-of-indian-marketers-embrace-ai-amid-challenges/474652),
  May 2024; it is unclear whether these figures are India-only).
- **"Silence is not clearance" (accuracy before speed):** of 1,000+ marketers Salesforce surveyed, 31%
  ranked accuracy and quality as their top concern about generative AI, ahead of trust (20%)
  ([Salesforce](https://www.salesforce.com/news/stories/generative-ai-statistics/); survey date not given).
- **Not checked:** the accessibility, agency and design conditions; no public source tested them.
- **What it changes:** supports two design choices already built (confidential facts matched in code
  only, with an egress log; evidence or silence with a "not checked" list).

## What happens in Round 3

No interviews, survey or user study are part of the Round 3 commitments, so each verdict above stays
desk research, labelled as such. Round 3 adds independent evidence where one person can gather it: public
ASCI and UK ASA rulings become a held-out evaluation set (the regulator's verdict is the label) and real
decisions for guideline health. See [the three Round 3 improvements](round3-improvements.md).
