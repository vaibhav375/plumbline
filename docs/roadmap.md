# Product roadmap

Plumbline is built and run by one person. This roadmap says what comes next, in order, and what is deliberately
not planned. Dates are intentions, not promises.

## Now: finish what Round 3 started

| Item | Why | Done when |
|---|---|---|
| Re-run the clarification measure on real reviewer decisions | The rulings-based run showed no gain; synthetic history can't settle it | a brand has at least 100 recorded overrules and the replay shows a gain larger than the judge's own noise |
| Wider ruling set (more ASA and ASCI rulings, other categories) | 84 claims is small; the interval on 88.9% is about 80–94% | 300+ claims, recall reported with its interval |
| Check the claim "shorter than the evidence" gap | The second-brand test showed "2 minutes" accepted against "under 5 minutes" | a number check that treats a stricter-than-evidence claim as unsupported, with tests |
| Link a live chat address for a real brand | Linking is tested in the database and in the API; no real ASI:One address is linked yet | one brand linked and checked from ASI:One chat |

## Next (about 3 months)

- **Paid, no-training model tier or self-hosted Qwen** for any brand using real content; the demo stays on free tiers
  with fictional data.
- **Claims inside images and video captions**: OCR already reads image text; the claim check does not yet use it.
- **Hindi and Hinglish evaluation**: spot-tested now; needs a labelled set.
- **Faster image checks**: about 6 s on a shared free CPU against a 5 s target.
- **Rule suggestions from rulings**: propose new brand rules from upheld regulator rulings in the brand's category,
  for the owner to accept (same accept-or-edit pattern as clarifications).
- **Watch more than one URL per post and re-check on a schedule** (today a scan is run on demand or by the database
  cron job).

## Later (needs more than one person, or real customers)

- Studies with recruited participants: interviews, a labelled test set by practitioners, user tests.
- An external anchor for the audit chain (a published hash).
- Slack and CMS integrations beyond the publish-gate API; DOCX tracked changes; Google Sheets sync.

## Not planned

- A pass badge. Every report lists what was not checked; silence is never clearance.
- Auto-fixing a claim with anything but approved wording.
- Simulated user research. No user study is claimed, and none is faked with AI personas.
