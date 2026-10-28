# Completed features (Round 2)

Each feature, the Round 1 section it comes from (§n of the [Round 1 plan](round1/AtoZ_Plumbline_Round1_Plan.pdf)),
the build task and milestone, and its status on the live app. Evidence for every row is in the
[build log](build-log.md) under the task named.

Milestones: **M1** walking skeleton (Tasks 0–7) · **M2** check engine depth (8–14) · **M3** fix and
review loop (15–19) · **M4** images and evaluation (20–21) · **M5** usability and reliability (22–23).

## Checking content

| Feature | Round 1 | Task · milestone | Status |
|---|---|---|---|
| Paste text; upload DOCX, PDF or image (OCR), with plain errors for empty, encrypted or oversized files | §5, §6.2 stage 1 | 4, 6 · M1 | Live |
| Rule engine for class A rules (patterns, word lists, counts, required content, contrast, alt text) | §4.3 A, §6.2 stage 3 | 5 · M1 | Live: 28 runnable rules |
| Rule tiers: mandatory rules block; brand rules start advisory | §4.1-5, §4.3 A | 5 · M1 | Live |
| Rule linter: vague rules classed C and never run | §4.3 A, App. B | 5, 18 · M1, M3 | Live: 4 rules flagged |
| Claims: detect, extract, match to the fact ledger, verify (supported, contradicted, unsupported, outdated, restricted) | §4.3 C, §6.2 stage 4 | 11 · M2 | Live |
| AI judgement for class B rules (tone, voice, structure) | §4.3 B, §6.2 stage 5 | 12 · M2 | Live |
| Evidence or silence: a finding needs a real ID and a real quote; a second model checks AI findings | §4.1-2, §6.2 stage 6 | 10 · M2 | Live: 52/52 citations valid on the dev set |
| Coverage statement: what ran, what didn't, and why | §4.1-2 | 14 · M2 | Live |
| Privacy: names and contacts masked before any model call; confidential facts matched in code only | §4.5, §7 | 9 · M2 | Live |
| Model chain with fallbacks and an egress log with no content field | §6.3, §7 | 8, 23 · M2, M5 | Live |
| Image accessibility floor: contrast (4.5:1, 3:1 large) and missing alt text block; boxes drawn on the image | §4.3, §5 | 20 · M4 | Live |

## Fixing

| Feature | Round 1 | Task · milestone | Status |
|---|---|---|---|
| Approved-wording swaps for claims, with required footnotes; never an invented claim | §4.1-4, §4.4 | 13 · M2 | Live |
| Suggested version with the five-check intent lock | §6.2 stage 7 | 13 · M2 | Live: 10/10 sample posts kept intent |
| Finding cards: accept, edit, dismiss (with reason), ask a reviewer; apply fixes and re-check with a diff | §4.2, §4.4 | 15, 16 · M3 | Live |
| Demo-safe sample: a labelled replay of a real run, plus "Run it live" | §8 risks | 22 · M5 | Live |

## Review, audit and governance

| Feature | Round 1 | Task · milestone | Status |
|---|---|---|---|
| Private pre-checks; agencies see only their own work and never confidential facts | §4.5 | 2, 14 · M1, M2 | Live, enforced by row-level security |
| Review queue ordered by risk; routing (claims → compliance, overruled accessibility → accessibility) | §4.5 | 16 · M3 | Live |
| Second approver must be a different person, enforced in the database | §4.5 | 2, 16 · M1, M3 | Live |
| Hash-chained, insert-only audit log; verify in the app and export a CSV anyone can re-verify | §4.5, §7 | 2, 17 · M1, M3 | Live: 600+ events verify |
| Rulebook page with linter warnings; CSV import (preview first; each function edits only its own rules) | §4.3, §5 | 18, 19 · M3 | Live |
| Fact ledger with expiry, confidentiality and approved wordings; wordings no more visible than their fact | §4.3 C | 18 · M3 | Live |
| Guideline health: agreement per rule, Wilson lower bound, "ready to block", "may be unclear"; groups under 3 people hidden | §4.6, improvement 3 | 19 · M3 | Live (with labelled synthetic history) |

## Proof, usability and operations

| Feature | Round 1 | Task · milestone | Status |
|---|---|---|---|
| Evaluation harness against a one-call baseline, with 95% intervals; public "How I know it works" page | §6.7 | 21 · M4 | Live |
| Role landing, 5 role cards, a 4-step tour, brand colours with checked contrast | §5 | 22 · M5 | Live |
| Status page, request references on every error, waking and retry on cold starts, keep-alive | §6.7 | 6, 22, 23 · M1, M5 | Live |

## Added in Round 3

| Feature | Status |
|---|---|
| Link a chat address to your own brand with a one-time code; chat checks use that brand's rules and facts | Live (improvement 2) |
| Publish gate API: go or not yet, with reasons and an optional approved-text hash | Live (improvement 2) |
| Connect page for the brand owner: codes, linked addresses, gate keys, gate log | Live (improvement 2) |

## Not in Round 2

Committed for Round 3 ([the three improvements](round3-improvements.md)): watching published posts when a
fact changes, a held-out evaluation on public regulator rulings, chat checks against each brand's own
rulebook, a publish-gate API, automatic rule graduation and AI-drafted rule clarifications.

Not committed (ideas only, no date): Slack, a no-login agency link, DOCX tracked changes, logo and palette
checks, claims inside image text, Google Sheets sync and a self-hosted model mode.
