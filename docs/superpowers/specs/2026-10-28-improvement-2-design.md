# Improvement 2: each brand's own checks, in chat and before publishing

Round 3, built 28–30 Oct 2026. Committed in the Round 2 form as: a brand links its ASI:One / Agentverse
address to its Plumbline organisation with a one-time code, so chat checks use its own rules and facts;
a publish-gate API tells scheduling and CMS tools "not yet" while anything blocks.

## Why
Round 2's chat agent only knows the demo brand, and nothing stops an unchecked or since-edited post from
going out through a connected tool. Both gaps are the same problem: Plumbline's checks stop at its own web
app.

## Goals
- A brand owner links a chat address to their organisation in under a minute, with a one-time code.
- A linked address is checked against that organisation's rulebook, as an agency-level writer.
- A tool can ask "may this go out?" and get a definite answer with reasons, and can prove the text it is
  about to publish is the text that was approved.
- Brand A can never receive brand B's rules or facts, through either door.

## Non-goals
- Slack, the no-login link, DOCX tracked changes (not committed).
- Saving chat checks as content, or letting chat callers submit or approve (they only read findings).
- Per-person accounts for gate users: a gate key belongs to an organisation.

## Anti-goals (would make this a failure even if it "works")
- Any path where a caller reaches another organisation's data, or a confidential fact.
- A gate that says "go" for a post with a blocking finding, or for text that differs from what was approved.
- Putting the service key in the checker (Round 2's rule), or secrets in the repo.

## Design

### Where the data lives
Three new tables (migration 0013): `agent_link_codes`, `agent_links`, `gate_keys`, plus `gate_calls`
(insert-only log). Row-level security is on with **no policies**, so signed-in users cannot touch them
through the API. Everything goes through `security definer` functions granted only to the existing narrow
role `plumbline_checker` (the pattern of migration 0006). The checker never gains table access or a
service key. Codes and keys are stored as SHA-256 hashes; the plain value is shown once.

### Linking
1. A brand owner opens **Connect** in the app and creates a link code (8 characters from an unambiguous
   alphabet, 15 minutes, single use). The checker API verifies the caller is `brand_owner`, then calls
   `agent_make_code` as the narrow role.
2. In chat the user sends `link ABCD-2345`. The agent calls `agent_redeem_code`, which atomically marks the
   code used and upserts `agent_links(address → org)`. Re-linking replaces the old link.
3. `unlink` ends it; a brand owner can also revoke any address in the app.
4. Failed redemptions are rate-limited per sender (5 per 10 minutes) so codes can't be guessed.

### Checking as a linked brand
The agent resolves `sender → org` through `agent_link_for`. The rulebook comes from
`agent_org_context(org)`, a function that returns exactly what Round 2's RLS gives an agency writer:
active rules, terms, **non-confidential** facts and the wordings of those facts. Confidential and embargoed
facts come in through the existing `confidential_facts(org)` and are used only for matching, with their
findings withheld (the `external_creator` pre-check behaviour). Nothing is saved, no cache is used (the
cache is read through a user's RLS, and a chat caller has no user). Unlinked senders still get the demo
brand, with one line telling them how to link. The org is always taken from the link row, never from the
message.

### The publish gate
`GET /v1/gate/versions/{version_id}` and `GET /v1/gate/contents/{content_id}` (latest version), with
`Authorization: Bearer plk_…` (a gate key, created in **Connect**). Optional `?text_sha256=` is the SHA-256
of the text the tool is about to publish.

Answer: `{"decision": "go" | "not_yet", "reasons": [...], "version_id", "status", "fix_url"}`.
`go` only if all hold: the version is `approved` or `published`; no blocking, non-advisory finding is open
(its latest reviewer decision is not `overrule`); and, when given, the hash equals the approved text.
Otherwise `not_yet`, each reason in plain words (e.g. "2 blocking findings are open: CL-03, CL-01",
"Text differs from the approved version"). Unknown or other-organisation IDs give 404, not a hint. Every
call is written to `gate_calls`, shown in the app.

### The Connect page
Brand owner only: link codes and linked addresses (with revoke), gate keys (create shows the key once,
revoke), recent gate calls, and a copy-ready `curl` example. Reviewers and others see a plain "ask your
brand owner" state.

### Choices that are mine (not discussed)
- A gate key belongs to the organisation, not a person, so scheduling tools can use one.
- A blocking finding stays blocking unless a reviewer overruled it; "upheld" does not clear it. This is
  stricter than the approval screen, on purpose.
- The hash is over the UTF-8 text with surrounding whitespace trimmed.

## Measured by (from the Round 2 form)
- 200-fix audit with 0 invented claims (builder; done at the end of the window).
- Automated tests: the gate refuses 100% of versions with an open blocking finding and passes approved
  ones; a caller linked to one brand never receives another brand's rules or facts.
  - Unit: reply wording, rate limits, link/unlink flow, org resolved from the link only.
  - Database (cloud test project): single-use and expiry of codes; `agent_org_context` returns only that
    org's non-confidential rows; gate keys scoped to their org; the narrow role still has no table access.
  - Live: link a real address, check in chat, query the gate with an approved and a blocked version.

## Left to the builder
Exact code alphabet and copy, table and column names, the gate's reason wording, page layout.
