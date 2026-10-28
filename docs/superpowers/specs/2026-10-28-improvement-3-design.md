# Improvement 3: self-learning guidelines

Round 3, built 28–30 Oct 2026. Committed in the Round 2 form as: a brand rule whose reviewer agreement has a
Wilson 95% lower bound of at least 0.80 moves to blocking by itself, with an audit event and one-click undo
(and drops back if agreement falls); for a rule that "may be unclear", Plumbline drafts a clearer version
from the recorded decisions and their reasons, for the rule owner to accept or edit.

## Why
Round 2 shows which rules reviewers keep overruling and which have earned the right to block, but a person
still edits the rulebook by hand, and nobody can say whether an edit helped.

## Goals
- A brand rule graduates to blocking on evidence alone, and every graduation is visible, audited and
  undoable in one click.
- A rule reviewers disagree with gets a drafted rewording the owner can accept, edit or reject; accepting is
  audited and undoable.
- Whether a rewording helps is measured on recorded decisions, not asserted.

## Non-goals
- Changing mandatory (regulatory) rules: they already block, and are never edited automatically.
- Changing a rule's check type, params other than the wording, or severity.
- Learning new rules from nothing; this only moves and rewords existing ones.

## Anti-goals (a failure even if it "works")
- Any rule blocking with a Wilson lower bound below 0.80, or on fewer than 10 decisions.
- A change nobody can see, or cannot reverse. Auto-graduation after an owner undid it.
- A drafted wording that goes live without the owner accepting it. Drafts never change checks.
- Drafts that quote a private version's text or a confidential fact.

## Design

### Graduation (database, migration 0015)
A trigger on `decisions` recomputes the affected rule's counts with the same rule as the health page (upheld
= accept/edit/uphold; disagreed = overrule/dismiss; non-private versions). For an active **brand-tier** rule
that is not pinned:
- advisory → blocking when n ≥ 10 and `wilson_lower(upheld, n) ≥ 0.80`;
- blocking → advisory when it was graduated by this mechanism and the lower bound falls below 0.70. The gap
  is deliberate, so a rule near the line doesn't flip on single decisions.
Each move writes `rule_changes` (rule, from, to, why, n, upheld, lower bound, who = system) and, in the same
transaction, an `audit_events` row through the existing chain. `rules.pinned` is set when an owner undoes a
graduation or demotes by hand: the mechanism then leaves the rule alone until the owner clicks "let
Plumbline decide again". Undo works for owners of that function (same rule as editing, migration 0012).

### Clarifications
`rule_clarifications` (rule, status draft/accepted/rejected/reverted, the old and new wording, the evidence
used, replay result). Only rules flagged "may be unclear" (Wilson lower bound of disagreement ≥ 0.25, n ≥ 10)
can be drafted for. The checker gathers the rule's disputed decisions (finding quote, decision, reviewer
reason; quotes of private versions excluded), asks the model for a reworded title, instruction and good/bad
examples (it may only reword, it must keep the rule's id and intent), and stores the draft. The owner sees it
beside the current wording with the evidence, then accepts (optionally edited), or rejects. Accepting writes
the wording, a `rule_changes` row and an audit event; revert restores the old wording.

### Replay (the measure)
Both wordings are judged on the same recorded cases: each case is a quote plus what happened (upheld → the
rule should flag it; overruled/dismissed → it should not). The model gets only the wording and the quote and
answers flag/no flag. Score = share of cases where the answer agrees with the decision, for old and new.
Cases: the org's recorded decisions on that rule, and for claim rules the 84 claims of the regulator-ruling
set (upheld → should flag, not upheld → should not). The draft is shown with both scores, and a rewording
that doesn't beat the old one is labelled so. A held-out half of the cases (alternate, fixed) scores the
draft; the other half is what the draft was written from, so the claim is not graded on its own homework.

### Where it shows
Guideline health gets a "Changes" strip (graduations and demotions with undo) and, on a "may be unclear" rule, a
"Draft a clearer version" button, the draft with both scores, and accept/edit/reject.

### Choices that are mine (not discussed)
- Demotion threshold 0.70, not 0.80 (hysteresis); only mechanism-graduated rules demote automatically.
- The mechanism counts the same decisions the health page shows (including seeded sample history, which the
  page already labels); the audit payload records n and the bound so a reader can judge.
- Replay uses a single yes/no model call per case, not the full pipeline: it tests the wording, nothing else.

## Measured by (from the Round 2 form)
- Replay: an accepted clarification agrees with recorded decisions more often than the wording it replaces,
  on held-out cases; both numbers published, including drafts that did not help.
- Automated tests: no rule graduates below the threshold or below 10 decisions; every graduation can be
  undone; an undone rule is not re-graduated; drafts never change a live rule; mandatory rules are untouched.
  - Unit: threshold and hysteresis; replay scoring; draft evidence excludes private text.
  - Database (cloud test project): trigger moves the rule once, writes `rule_changes` and one audit event
    (chain still verifies); pinned rules stay; owner scoping on undo/accept.

## Left to the builder
Table and column names, prompt wording, page layout.
