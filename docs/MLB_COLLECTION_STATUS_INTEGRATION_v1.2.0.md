# Codex handoff — accepted collection-status integration and deployment

September 14, 2026. The Owner requested independent review and explicitly
instructed: if acceptable, proceed with commit, merge through a PR and deployment.
The [independent review](MLB_COLLECTION_STATUS_INDEPENDENT_REVIEW_v1.2.0.md)
accepted the exact 14-file candidate with no blockers. This satisfies the condition.
Earlier pending-review/integration wording in candidate-era documents is historical;
this record governs the authorized next gate. It does not declare completion of
that gate before the actual PR and deployment receipt exist.

## Exact authority and scope

Repository: https://github.com/tomsullivanuk/pops-edge, baseline main/PR #51
`0d8e18248d190a0bf4bf30185ece4427dd371a9f`. Candidate checkout:
`/private/tmp/pops-edge-collection-status`. The independent review retains all
14 accepted file hashes. Include its own artifact and this integration handoff;
exclude planning scratch, preview output, runtime records and credentials.

Commit the accepted correction on a `codex/` branch; push it to the canonical
repository, create the focused PR, verify its exact head/base and checks, and merge
that head. The repository has no hosted workflows; do not claim hosted CI passed.
Independent validation is 101 collection/delivery/activation passes plus 19
lifecycle passes, with the corrected initial test-module naming error disclosed.
Prior broad scientific/compatibility evidence remains applicable. Review the final
inventory and do not expand the change into collector or NFL work.

## Reporting deployment

Fetch the actual merged main revision and create a separate clean detached
reporting checkout at `/Users/tom/PopsEdgeReporting/<merged-prefix>/pops-edge`.
Leave the existing collector and old reporting checkouts unchanged. Execute the
accepted `activate-display --expected-revision FULL_MERGED_COMMIT` command against
`/Users/tom/PopsEdgeReports/mlb/real/2026-09-13-accepted/reports`, supplying
`--operational-state /Users/tom/Library/Logs/PopsEdge/pr17c1/operational-state`.
The latter is the log directory of the configured MLB prospective deployment.

Before activation, retain original report-file hashes and exact parsed entry state.
Afterward verify the active entry digest against the activation record, identical
selection/last-scientific-attempt state, every original file unchanged except the
explicit mutable entry, and functional live/historical/recovery/download links.
Check the saved collection-observation digest and separate observation time.
Status may honestly be unavailable or stale without blocking the valid report.
Do not manufacture healthy status or invoke health/collection commands to fill it.

Record actual PR, merged revision, checkout, activation identifier, comparisons,
limitations and exact rollback command in a local receipt under
`/Users/tom/PopsEdgeReports/mlb/activation/2026-09-14-collection-status/`.
Use the existing digest-guarded rollback if a material deployment check fails.
Opening remains frozen; no browser interaction is claimed by static validation.

## Must hold and exclusions

Preserve immutable scientific packages, anchors, verification receipts, scientific
dates and last generation-attempt state. Reuse retained verification and default
legacy renderer replay; no new scoring, source replay or provider acquisition is
needed. Collection status has presentation authority only; it does not certify
current overall health or complete Coverage.

Accepted limitations remain local/manual/frozen operation, explicit matching log
selection, truthful status absence/staleness and bounded manual recovery. No server,
automatic refresh/recovery, collector repin/restart, scheduler/configuration change,
source/archive/index/checkpoint mutation, NFL/World Cup change, study closure,
Policy/wagering, v1.2 tag or hosted release is authorized by this integration.
VERSION remains 1.1.0. Whole-release readiness remains a separate decision.
