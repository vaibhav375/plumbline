# Three improvements for Round 3

Each one continues one of the three improvements Round 1 committed to, ships on the live link, and has
a target that one person can measure and anyone can re-run from the repository. None depends on
recruiting outside participants (see [how the evidence plan changed](changes-from-round1.md#how-the-evidence-plan-changed-and-why)).

## 1. Claim watch, tested against real regulator rulings

*Continues "Evidence or silence, and silence is never clearance".*

Round 2 checks a draft against the fact ledger at the moment of writing. But facts change: a price
expires, a study is superseded, an embargo lifts. Round 3 follows a claim after it is published:

- When a fact expires or changes, every published post that used it gets an update-or-withdraw task for
  its owner, with the approved replacement wording if one exists.
- Published URLs are re-checked against the version that was approved, so edits made after approval
  show up.

**Measured on** an evaluation set built from public rulings by India's ASCI and the UK's ASA on beauty and
personal-care ads, where the regulator's verdict is the label. It is independent of the builder and held
out from development. Targets: recall ≥ 80% on the claim issues the regulator upheld, and ≥ 95% of 100
findings' citations correct, checked by the builder against the rule or fact each one cites. The same
measures repeat on a second brand from another sector (a fintech app), loaded only through the rulebook
CSV import and the fact ledger with no code changes, to show the engine is not tied to Aurelle. Results
are published whatever they are.

## 2. Each brand's own checks, in chat and before publishing

*Continues "Fixes that keep intent and never invent claims".*

Round 2 already reaches writers outside the web app: the checker is an Agentverse agent that ASI:One
users can message. But it only knows the demo brand, and nothing stops an unchecked post from going out.
Round 3:

- **Your brand in chat.** A brand links its Agentverse or ASI:One address to its Plumbline organisation
  with a one-time code from the app; from then on, chat checks run against that brand's own rulebook and
  facts. Unlinked callers keep the demo brand.
- **A publish gate.** An API that scheduling and CMS tools call before a post goes out. It answers "not
  yet" while any blocking finding is open, with the reasons and a link to fix them, and "go" once the
  version is approved.

**Measured by** a 200-fix audit by the builder with 0 invented claims, and automated tests that anyone can
run: the gate refuses 100% of versions with an open blocking finding and passes approved ones, and a
caller linked to one brand never receives another brand's rules or facts.

## 3. Self-learning guidelines

*Continues "Guidelines get clearer; rules earn the right to block".*

Round 2 shows which rules reviewers keep overruling and which have earned the right to block, but a
person still edits the rulebook by hand. Round 3 closes the loop:

- **Automatic graduation.** When a brand rule's agreement lower bound (Wilson 95%) reaches 0.80, it moves
  to blocking, with an audit event and one-click undo; if agreement later falls, it drops back to advisory.
- **AI-drafted clarifications.** For a rule that "may be unclear", Plumbline drafts a clearer version from
  the recorded decisions and their reasons, for the rule owner to accept or edit; the change is audited.

**Measured by** replaying recorded decisions, including the regulator rulings above as real upheld and
not-upheld decisions for the claim rules: an accepted clarification must agree with those decisions more
often than the wording it replaces. Automated tests check that no rule graduates below the threshold and
that every graduation can be undone.
