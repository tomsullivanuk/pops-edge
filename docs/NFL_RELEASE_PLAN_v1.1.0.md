# Pops' Edge v1.1.0 — NFL comparison workflow

## NFL v1.1.0 — current scope

The NFL workflow is merged through PR #33 (`d94e171`). It is a local personal
comparison surface: validated ELWAY Excel input, official NFL schedules, public
Kalshi prices, recorded activity and replayable weekly comparisons. Import &
Refresh selects files from `~/PopsEdge/Downloads/NFL/`; one **Refresh Bet Sheet**
action processes every workbook week. The Bet Sheet filters the resulting view.
Excel records attest automated validation, never human review. Earlier manually
verified records remain supported with their original provenance. Raw inputs
and captures are preserved under `~/PopsEdge/Data/NFL/`.

TBD games remain in their official week without requiring attention. Filters
cover week, team, completion and strict after-fee thresholds. Recorded wagers
show each contract and purchase amount including fees; they do not establish
current holdings. The surface creates no research, Market Edge, Forecast Policy
or order-execution authority. World Cup and MLB contracts remain unchanged.

Product/source version is v1.1.0; tag publication and deployment are separate
from the code merge. MLB remains allocated to v1.2.0. Historical MLB v1.1.0
filenames, PR identifiers and contract-version descriptions retain their original
meaning; this allocation does not change schemas or scientific rules.

See [refresh guide](NFL_REFRESH_GUIDE.md),
[comparison boundary](NFL_BOARD_SLICE.md), and
[independent review](NFL_PR33_INDEPENDENT_REVIEW.md).

## Objective and authorization

Reproduce the personal World Cup workflow with weekly owner-supplied ELWAY
Excel workbooks or manually verified screenshots and manually refreshed Kalshi game-winner comparisons. Preserve
World Cup behaviour and parallel MLB work. See the [version amendment](RELEASE_ALLOCATION_2026-09-08.md).

NFL-1 merged in PR #31, NFL-2A in PR #32, and the comparison/refresh workflow
in PR #33. Each integration received separate owner authorization. The earlier
screenshot slice below remains a supported alternative to automated Excel
validation. No release tag, deployment or order execution follows from these merges.

## NFL-1 — Verified screenshot import (merged)

Deliver a local PNG/JPEG importer using Apple Vision, an editable local HTML
review beside the original image, immutable source/verification records and
explicit correction history. No provider network access. Store defaults to
`~/PopsEdgeData/NFL`; inbox defaults to `~/Downloads/PopsEdge/NFL`.

Identity here is source digest and source season/week/matchup, not authoritative
NFL schedule identity. Verification establishes faithful source transcription;
it does not establish game mapping, kickoff eligibility, model accuracy,
Forecast Policy or Market Edge. A complete original and visible update timestamp
are required; the user verifies the visible game count. Do not assume 16 games
for every week. Neutral site designation remains separate from home/away roles.

States: original received → candidate extraction → visually checked review →
validated verified record. Invalid/incomplete rows block this small snapshot's
verification, remain visible, and can be edited in the review. Original bytes and
raw OCR remain unchanged. A correction appends a record with `supersedes`; no
implicit latest/current selection is implemented. Duplicate verification of the
same review/reviewer/predecessor returns the existing record unchanged. OCR
failure retains the source and a failure diagnostic for a later retry.

Must hold: exact original image preserved; source update/import/review times
separate; all rows visually checked; explicit metadata verification; valid teams
and percentages without normalization; duplicate teams rejected within a week;
no future source timestamp; no unverified export; corrections append; unrelated
files and current World Cup/MLB workflows untouched.

Accepted limitations: Mac with Xcode Command Line Tools/Swift; local OCR can miss
coloured team badges; manual corrections and one review of every row per new
image; complete screenshot required; regular season weeks 1–18; local-machine
storage and manual backups; no automatic inbox selection when multiple images
exist. Plain verified percentages are evidence, not exact inferred tie values.

Validation: exercise actual Week 1 image; unit tests for OCR role handling,
neutral marker, omitted rows, unverified rows, metadata, invalid values, duplicate
teams, timestamps, source tampering, idempotency and correction retention; inspect
rendered review; run existing baseline tests and syntax checks offline.

## NFL-2A — Public Kalshi retrieval (merged PR #32)

Collect a manually selected provider-rule date window of full-game winner
markets, preserving series metadata, paginated catalogs, raw order books and
request chronology. Replay derived offers offline. See the
[acceptance boundary](NFL_RETRIEVAL_SLICE.md) and [guide](NFL_RETRIEVAL_GUIDE.md).
This is a separate acquisition slice; complete retrieval does not establish
schedule coverage, pregame eligibility or comparison authority.

## NFL-2B — Schedule matching and comparison board (merged PR #33)

The owner authorized this slice on September 9, 2026. Add official NFL.com
weekly schedule mapping, supported full-game settlement semantics, a bounded
one-contract fee illustration and a ranked personal comparison board using
explicit verified forecasts and retrieved runs. See
[acceptance boundary](NFL_BOARD_SLICE.md) and [board guide](NFL_BOARD_GUIDE.md).
A half-payout on ties requires explicit payoff derivation separate
from win probabilities. Preserve source precision and quote chronology.
NFL.com supplies official game IDs and kickoff data; exact inspected market
rules and published standard taker fees govern the bounded illustration. This
is a manual comparison surface, not an executable Forecast Policy, demonstrated
Market Edge or wagering recommendation. Do not extend MLB binary assumptions.

Spreads, totals, futures, bankroll/Kelly advice, automatic execution, hosted
services, scheduled scraping, research activation and PELE analysis are excluded.
All three slices are merged through PR #33 (`d94e171`), whose independent
review found no blocking issues. Product/source version is v1.1.0. Release-tag
publication and deployment remain separate authorization steps; neither follows
automatically from the merge.

## Model Performance follow-on — authorized documentation slice

The owner approved the [weekly protocol](NFL_MODEL_PERFORMANCE_PROTOCOL.md):
fee-free squared contract-value error, import-triggered Kalshi capture and
a weekly baseline frozen before the first game. This follow-on supersedes the
blanket outcome-scoring exclusion only for the approved design scope. It does
not activate research or change the deployed v1.1.0 release.

Sequence: documentation/source feasibility; evidence and scoring; presentation.
The first slice is locally implemented for review. Later code, integration and
activation remain separate gates. No release version or PR number is assigned;
MLB stays v1.2. Wager History is independent.
