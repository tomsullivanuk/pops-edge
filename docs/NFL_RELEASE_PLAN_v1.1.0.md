# Pops' Edge v1.1.0 — NFL comparison workflow

## Objective and authorization

Reproduce the personal World Cup workflow with weekly owner-supplied ELWAY
screenshots and manually refreshed Kalshi game-winner comparisons. Preserve
World Cup behaviour and parallel MLB work. See the [version amendment](RELEASE_ALLOCATION_2026-09-08.md).

The Product Owner authorized NFL-1 implementation in this task. No commit,
push, PR, merge, deployment, provider collection, trade or release is authorized
by that implementation instruction.

## NFL-1 — Verified screenshot import (current slice)

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

## NFL-2 — Kalshi comparison command (deferred)

Add authoritative schedule mapping, validated full-game settlement semantics,
applicable fee model and read-only price/book retrieval, followed by the ranked
local board. A half-payout on ties requires explicit payoff derivation separate
from win probabilities. Preserve source precision and quote chronology. Resolve
schedule source, actual market rules/fees, and comparison-surface policy status
before implementation; do not silently extend MLB binary assumptions.

Spreads, totals, futures, bankroll/Kelly advice, automatic execution, hosted
services, scheduled scraping, research activation and PELE analysis are excluded.
A v1.1.0 release requires completion and review of both slices and separate
release authorization. NFL-1 alone is not a completed NFL board release.
