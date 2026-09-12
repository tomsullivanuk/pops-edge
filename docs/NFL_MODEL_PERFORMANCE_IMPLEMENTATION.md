# Weekly capture and scoring — local implementation

Implementation modules: `nfl_performance.py` (explicit local service and replay),
`nfl_performance_sources.py` (versioned outcome/market adapters), and
`operate_nfl_performance.py` (command entry point). They implement the
[weekly protocol](NFL_MODEL_PERFORMANCE_PROTOCOL.md). They are not connected to
the existing Bet Sheet refresh handler or activated on a production data store.
The Model Performance tab is a later presentation/integration slice.

## Interface

`Performance.initialize(root, authorization)` commissions an empty dedicated
store, pinning the protocol digest, schema and actual effective time. Do this
only after separate activation authorization. `Performance(root)` opens an
existing compatible store; opening/importing the module never initializes one.

`refresh(raw, name, season, week, retry=False)` requires an explicit week. New
valid semantic forecasts receive an import record and associated schedule/market
capture. Identical imports record their provenance but do not retrieve new
research books. `retry=True` is an explicit missing-observation attempt; it cannot
replace an earlier successful observation. The existing public transports are
injectable for offline fixtures. Neither this service nor the CLI executes orders.

`observe_results(season, week)` captures official weekly schedule/summary
responses independently of the workbook or owner's wagers. `report(season,
week, boundary)` derives coverage and squared errors without network or writes.
`save_report` stores the derived report under its content identity.
`replay_report(path)` re-evaluates its pinned event prefix so even equal-time
later corrections do not change it. A later report may reflect corrected results.

The CLI requires `--store` and an explicit subcommand: `initialize`, `capture`,
`outcomes`, `report`, or `replay`. Capture additionally requires a workbook,
`--season` and `--week`; only `--retry-missing` requests a retry. `report` requires
`--boundary`. See command help for argument placement. No default production
store or automatic commissioning is supplied.

## Storage and boundaries

A dedicated store contains activation metadata, content-addressed raw blobs,
an ordered hash-linked event journal and derived reports. Operations take a
nonblocking local file lock. New imports and attempt starts are written before
provider acquisition. Interrupted attempts remain visible and do not grant
capture authority. Original acquisition receipts and raw bytes are preserved
and revalidated with the existing replay adapters; old NFL bundles are unchanged.

The journal and raw hashes detect corruption; this is a local integrity design,
not a signed or adversary-proof audit service. Manual backups remain necessary.
An unreferenced blob has no measurement authority. A terminal capture can contain
independent valid observations even if another request failed. Eligibility uses
each request's original timestamps, not the later time a report is rendered.

The weekly view retains missing and removed schedule identities, flags identity
conflicts, and excludes changed kickoff/neutral-site mappings. Unknown cutoff
means no qualifying baseline. Official FINAL summary IDs and totals govern the
supported outer-SCHEDULED discrepancy. Unsupported final markers/statuses remain
unresolved/excluded. No source is replaced with user activity or synthetic results.

Reports expose selected forecast, publication time, original import reference,
request times, retry markers, attempt states, score inputs, source IDs, coverage
and means. No fees enter the calculation. Values retain decimal precision.
Missing samples return null means. No statistical significance or Market Edge
claim is emitted. Time-boundary reports cannot be requested in the future.

## Validation and next slice

Focused tests run complete fixture capture lifecycles with no provider requests.
They exercise cutoff boundaries, semantic reimports, newer partial forecasts,
failed books with valid independent observations, retries, missing populations,
ties, final summary identity, corrections and saved-report replay, bad workbooks,
source tampering and exact error arithmetic.

Next: independently review this implementation, then authorize integration and
commissioning separately. The subsequent tab/refresh integration must explicitly
select a target week, show partial/missing states and consume the report's common
paired population. It must not reset research prices with ordinary Bet Sheet
refreshes. No running app or live source history was changed by implementation.

## Refresh connection follow-on

The local workflow candidate connects the existing service before operational
season refresh, requires an explicit target week when commissioned, provides an
explicit retry control, and records/replays results for enrolled weeks. See the
[refresh guide](NFL_REFRESH_GUIDE.md). This supersedes the earlier statement that
no refresh caller is installed in source; no production activation follows.
`record_schedule_capture` retains and validates the operational capture's raw
receipt rather than reinterpreting old schedule derivations. Comparison errors
are recorded separately from operational board errors.
