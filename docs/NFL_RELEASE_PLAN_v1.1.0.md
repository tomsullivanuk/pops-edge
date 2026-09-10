# Pops' Edge v1.1.0 — NFL comparison workflow

> Superseding NFL workflow amendment: owner authorized inbox-only selection and
> one Refresh Bet Sheet action across every workbook week. No manual Excel
> review/confirmation gate. New Excel records describe automated validation,
> never human attestation; earlier verified records remain unchanged. Week
> selection is a display filter only. Provider collectors remain weekly bounded;
> generation iterates all weeks, reporting per-week failure and original capture
> times. See NFL_REFRESH_GUIDE.md for current workflow and accepted limitations.

> NFL refresh amendment, September 10, 2026: the owner authorized a local
> Excel-based refresh application, all-workbook-week selection, and activity
> settlement display. Explicit per-source/week owner confirmation replaces
> screenshot row checkboxes only for Excel imports. Raw workbook values and
> original source precision are retained; automatic parsing is not verification.
> The inbox is ~/PopsEdge/Downloads/NFL; archives are ~/PopsEdge/Data/NFL.
> See the NFL refresh guide for accepted limitations and operation. This does not
> authorize order execution, research claims, deployment or release.

## Objective and authorization

Reproduce the personal World Cup workflow with weekly owner-supplied ELWAY
screenshots and manually refreshed Kalshi game-winner comparisons. Preserve
World Cup behaviour and parallel MLB work. See the [version amendment](RELEASE_ALLOCATION_2026-09-08.md).

NFL-1 was merged in PR #31. On September 9, 2026, the Product Owner authorized
moving on to Kalshi retrieval (NFL-2A), including the manual public-data smoke
check. That instruction does not authorize commit, push, PR, merge, deployment,
trade or release for NFL-2A.

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

## NFL-2B — Schedule matching and comparison board (current slice)

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
A v1.1.0 release requires completion and review of all slices and separate
release authorization. NFL-1 alone is not a completed NFL board release.
