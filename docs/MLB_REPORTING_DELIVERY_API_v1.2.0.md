# Manual archive-to-report delivery

## v1.3 read-only browser access candidate

The [Performance reader](PERFORMANCE_READERS_v1.3.md) exposes the existing saved output through the local application, preserving bytes and relative evidence/history links. It does not run delivery, scoring, activation or collection refresh. Earlier publication-pending wording is historical: v1.2.0 was published independently of deployment pins and study closure.

Current status — September 14, 2026: reporting delivery (PR #51) and collection
status (PR #53) are independently accepted, merged and locally activated.
Earlier candidate/authorization statements below are dated history, not pending
implementation gates. See [release record](MLB_RELEASE_RECORD_v1.2.0.md).
v1.2.0 is published; opening a saved page does not refresh it.

PR #51 merged this reporting delivery and readable display at
`0d8e18248d190a0bf4bf30185ece4427dd371a9f`. The normal local entry was activated
September 14, 2026 from that clean revision using previously verified historical
and live packages. The local completion receipt is
`/Users/tom/PopsEdgeReports/mlb/activation/2026-09-14-pr51/COMPLETION.md`.
Collection-status completion below retains its original candidate-era wording;
PR #53 integration/activation and v1.2.0 publication subsequently completed.

Apply the [reporting contract](MLB_REPORTING_CONTRACT_v1.2.0.md), accepted
[source API](MLB_REPORTING_SOURCE_API_v1.2.0.md) and
[Analysis API](MLB_REPORTING_ANALYSIS_API_v1.2.0.md). The original analytical root,
its limitations, dates, arithmetic and seeds are preserved byte-for-byte. A typed
`DeliveryEnvelope` describes the added projection and rendering capabilities.

## Operator commands

For authorized report operations, use a clean checkout at the
exact accepted revision and an existing compatible Python environment. Outputs
must be outside **every source checkout**, and must not overlap either configured
archive root, including aliases and ancestor paths. Commands read the existing
`DeploymentConfig`; its provider endpoint is never called. No provider credentials
are needed. Do not use the singleton retrospective publication command.

```sh
python operate_forecast_reporting.py --output /absolute/report-output generate-historical \
  --config /absolute/archive-config.json --expected-revision FULL_COMMIT --status interim
python operate_forecast_reporting.py --output /absolute/report-output select-historical \
  --config /absolute/archive-config.json --package PACKAGE_DIGEST --anchor RETAINED_ANCHOR_KEY
python operate_forecast_reporting.py --output /absolute/report-output update-live \
  --config /absolute/archive-config.json --expected-revision FULL_COMMIT
python operate_forecast_reporting.py --output /absolute/report-output verify \
  --config /absolute/archive-config.json --package PACKAGE_DIGEST --anchor RETAINED_ANCHOR_KEY
python operate_forecast_reporting.py --output /absolute/report-output open
python operate_forecast_reporting.py --output /absolute/report-output open --package PACKAGE_DIGEST
python operate_forecast_reporting.py --output /absolute/report-output status
```

`generate-historical` and `generate-live` save a package without selecting it.
`select-historical` explicitly verifies and selects one historical package.
`update-live` generates and verifies a new live package before replacing only the
live reference. It never regenerates or selects a historical report. The printed
result records the exact package digest, anchor key, report ID, status and original
generation time. Retain that result; the local entry also retains selected references
and the last successful generation result. No newest-directory selection occurs.

Only `in-progress` and `interim` are supported. Final reports, closure records and
formal correction publications require another approved workflow. Later source
corrections can support a new, separately identified in-progress/interim package.
They cannot change an earlier package or reconstruct missed live quotes.

`open` opens a local file in the default browser, with no source reads, network
requests, scientific verification, scoring or date refresh. Opening is viewing,
not acceptance of a copied or altered package. `verify` requires retained sources
and a separately retained anchor and emits a **new receipt** outside the package.
Verification does not update report dates, historical selection or current live
selection. Verification failures return a failed command outcome directly.

## Storage and trust

```text
output/
  anchors/<independent-key>.json
  candidates/<attempt-key>/       # interrupted/non-current material
  packages/<package-digest>/      # immutable after validation
    source.json
    analysis.json
    projections.json
    protocol.json
    envelope.json
    report.html
    REPRODUCE.txt
    package.json
  receipts/<receipt-key>.json
  entry.html                     # one atomic mutable entry/attempt record
  .delivery.lock                 # output-local writer lock only
```

A fresh trusted freeze returns the boundary ID. An exclusive new anchor record
retains it outside the candidate **before** computation. Generation and saved
verification read the expected ID from this record. Saved verification requires
an explicit anchor key obtained from the retained entry/result/receipt; the package
cannot supply its own expected ID. Package symlinks and anchor symlinks are rejected.
An independent trusted handoff may retain the anchor separately when moving a
package. Copying a package alone does not establish scientific verification.

Trust is local and explicit: retained anchor records and truthful clocks are
trusted; hashes do not authenticate an adversary replacing both package and anchor.
No signature service, database or generalized trust store is supplied. Retain the
source archive, anchor and package. The source archive remains a replay dependency;
its bytes are not duplicated in the package. Namespace-wide integrity validation
still applies, even to corruption outside the original contributing graph.

The seven payload files have a fixed, exact inventory. `package.json` contains
that inventory, delivery version and actual package-completion timestamp. SHA-256
of the canonical manifest material **excluding its own package_id field** is the
package identity. The manifest itself must have canonical bytes. The HTML displays
the scientific report ID, avoiding a circular package digest. Integrity includes
HTML and reproduction instructions. Exact saved verification reconstructs all
seven payloads through the accepted source/Analysis validators and new projections;
recomputed hashes alone do not admit changed content or omitted/extra references.

New projection start/completion, rendering start and package completion are actual
aware wall times after original report creation, never backdated to K or R.
Operational generation checks a clean checkout at the explicit executing revision
before and after computation. The API-only `synthetic_validation=True` seam permits
injected clocks and an uncommitted implementation **only with a dry-run archive**;
outputs are prominently labelled synthetic and identify the supplied revision as
the validation base. This is not an operational CLI option. Exact validation file
hashes and the candidate diff identify that synthetic implementation separately.

## Scientific projections

`forecast_reporting_projections.create_reporting_projections` first admits the
saved root and source graph through the existing public validators. Its canonical
`mlb-reporting-projections-1` objects bind the report, source, exact performance,
Coverage and Measurement identities. `verify_reporting_projections` reconstructs
and compares every field, not just identities.

Original capture-stage helpers are shared with the existing derivation constructors.
They independently validate the selected candle or Snapshot/MarketObservation.
Captured is not inferred from a request, successful manifest, score or final outcome.
The immutable original reconciliation remains visible even when capture validation
and the later derivation stage differ. Exact identity sets enforce
`scored ⊆ valid probability ⊆ captured ⊆ eligible due`; unscored is eligible minus
scored. Future obligations, not-yet-due and ineligible categories remain separate.

Each performance uses `constant-home-probability-0.5:1`, adopted 2026-09-12 after
commencement. Nonempty sets have Brier 0.25 and log loss ln(2), with the exact same
Measurement IDs and sample size as Kalshi. Empty values are absent. Calibration
detail uses the governed fixed ten bins and original scored Measurements. All
arithmetic uses 50-digit half-even Decimal. No new estimator, fitted comparison,
uncertainty procedure, significance or Market Edge is introduced.

Historical offered membership uses positive qualifying home-team mapping authority
in the frozen source graph. Multiple or conflicting qualifying mappings fail
closed. Absent mapping remains unknown; a missing retrieval is never interpreted
as “no market.” Offered/eligible and scored-offered/offered are withheld if any
eligible membership is unknown; overall scored/eligible remains separate. Zero
denominators yield unavailable values. The numerator for the second offered rate
is **scored** opportunities, explicitly labelled. No negative catalog-completeness
inference is added. Unknown calendar dates stay outside known-game counts.

## Failures and manual recovery

Only a fully written, exactly validated candidate may enter `packages/`. Files
become read-only and the directory is published before a receipt and current
reference are saved. `entry.html` carries both references and last attempt as
one atomically replaced file, preventing a new current reference with stale success
status. Its JSON record is inert; the page requires no script, server or network.
A nonblocking output-local lock prevents competing delivery commands from losing
historical selection. No collector lock is taken.

Generation errors preserve the prior live/historical references and all old package
bytes/dates, record a visible failed attempt, and return failure. If there was no
prior report, the entry states “No validated report available.” A successful empty
report instead has a package, exact scope and zero sample with unavailable scores.
If attempt-status persistence fails, the command reports **ATTEMPT STATUS COULD
NOT BE SAVED** and never returns success. Path rejection or configuration failure
before a safe output location is established is reported directly without writes.

A killed process can leave a running attempt, candidate directory or valid unselected
package. These never become current by discovery. Confirm no delivery command is
running, inspect the last command error/entry, retain diagnostics as useful, and
manually remove only identified interrupted candidates or temporary `entry-*.partial`
files. Never edit anchors to make verification pass, modify immutable packages,
repair Evidence or backfill missed observations. Correct storage/configuration
issues and start a new independent attempt. Read-only package directories may need
the owner's explicit filesystem permission change before manual relocation or
cleanup on macOS; generation does not remove earlier packages.

Missing historical output is shown on the next entry update while its selected
identity/dates remain intact; it does not block a valid live update. A saved entry
is frozen between commands, so external file removal can also be seen as a failed
link/open. Original immutable package pages retain their original status text.
The current display activation path can attach separately dated collection
observations, as described below; this does not certify present health or release
readiness. Local trusted-filesystem operation and manual recovery are accepted;
malicious concurrent filesystem edits, automatic recovery and high availability
are not new delivery guarantees.

## Simple principal report amendment — September 13, 2026

The [Owner's simple-report decision](MLB_SIMPLE_REPORT_DECISION_v1.2.0.md) supersedes
the original technical-export hierarchy. `mlb-reporting-html-2` leads with friendly
study/report dates (Eastern timezone), eligible/captured/scored counts, material gaps,
Brier versus 50% on the same scored observations, and governed sampling uncertainty.
Brier uses three display decimals and coverage one percentage decimal, with fixed
half-even rounding. This never changes canonical values or converts Brier to accuracy.
Technical evidence, exact statistics, log loss, calibration/bounded detail, timestamps,
identities and supporting links remain under collapsed Details. Important incomplete,
empty, unknown, singleton/zero-width, impossible-result and failure notices stay visible.

The saved `entry.html` is now the principal live Performance Report, populated from
the exact selected saved package, with a small independent historical link. It checks
that package's retained digest before projecting the view, and performs no source
access, new scoring or acquisition. Missing/damaged selected output remains visible;
metadata and diagnostic reasons stay in Details. Atomic entry/reference behavior is
unchanged. Saved package HTML is immutable; its own simple view links back to the
principal saved entry. Original v1 technical HTML remains available to exact package
verification and is never rewritten. Existing synthetic packages remain v1.

Already acquired MLB source reads and local report generation are now authorized,
subject to unchanged source validation and clean explicit executing-revision checks.
The old blanket no-real-source-read/report-generation restriction no longer applies
to this bounded request. There is no synthetic bypass for acquired data. No commit,
push/PR/merge, new acquisition, collector/scheduler/Evidence/index/checkpoint mutation,
full deployment or release authority is implied. Readiness-only source verification
is distinguished from operational Analysis/report generation.

### Two-decimal readable renderer amendment

`mlb-reporting-html-3` is the current renderer. v1 and v2 remain accepted for exact
saved-package replay. Readable Details no longer embed machine-record dumps: they
show two-decimal metrics, integer counts, friendly chronology, calendar date ranges,
and named saved-report/update status. Exact evidence remains downloadable.
`planning/RENDER_READABLE_ACTUAL_REPORTS.py` is a local one-off preview recipe, not an
acquisition or new scientific publication API. It checks saved package digests,
retained prior verification references and original renderer bytes, then records
new presentation timing/hashes separately without source replay or changing the
accepted output's current pointer.

### Activate or roll back the readable local entry

The later Owner authorization permits normal-entry activation as documented in the
[integration/activation handoff](MLB_REPORTING_INTEGRATION_ACTIVATION_v1.2.0.md).
From a clean reporting checkout at the accepted merged revision:

```text
python operate_forecast_reporting.py --output REPORT_ROOT activate-display --expected-revision MERGED_COMMIT
python operate_forecast_reporting.py --output REPORT_ROOT rollback-display --expected-revision MERGED_COMMIT --activation ACTIVATION_ID
```

These commands take no acquisition config and never access the source archive.
Activation requires both selected studies and matching independently retained source
anchors and previous package verification receipts. It checks payload digests and
saved renderer bytes without replaying science, builds readable displays under
`displays/ACTIVATION_ID/`, saves `previous-entry.html` and `activation.json`, then
atomically replaces `entry.html` with identical machine-readable selection/attempt
state. Actual display time is separate and the existing failed/running notice stays
visible. Verification dates are attributed to the retained verification, not today.

The activation record is prepared before publication; it is active exactly while
its recorded digest matches the actual entry. An interruption leaves the old entry
or a complete new one. Inspect the digest after an uncertain command result. Rollback
only restores the retained bytes if both current entry and backup match that record;
a later report update prevents accidentally rolling it back. Backup relative links
are intended to work once restored to the original entry location. Old immutable
package pages remain frozen with their original renderers; reopen the normal entry
to see the active display. This has no collector or release effect.


### Frozen collection observations — local correction candidate

From a clean accepted reporting checkout, after separate activation authorization:

```sh
python operate_forecast_reporting.py --output /absolute/report-output activate-display \
  --expected-revision FULL_COMMIT \
  --operational-state /absolute/configured-log-root/operational-state
```

This is also the manual **status-display refresh**. It reads existing sanitized
invocation records only; it does not execute the collector or `health-report`
(the latter writes an operational heartbeat). Do not run a collection or health
command merely to populate this display. The directory is explicitly selected
from the deployment's log root; use the matching MLB deployment. No configuration,
provider credentials, source freeze, scoring or full scientific replay is needed.

The page records the read time independently of report generation and evidence
cutoff, the latest recorded completion, last valid command completions, current
invocation blockers, superseded failures, recent skipped cycles and last recorded
health-check outcome. Cadence and supersession use the same pure observation rules
as existing health evaluation, including the skipped-hour supporting grace. An old
health outcome is dated history; no overall readiness is inferred from invocation
success. Archive integrity, checkpoint state, storage and secondary consistency are
not audited by this path. Healthy operations never establish complete Coverage.

Omitted/absent/inaccessible/malformed/ambiguous/future-dated operational records
produce a visible unavailable notice. Stale or missing required completions remain
visible under existing cadence rules. A concurrent append that falls after the
recorded read boundary can yield unavailable status; a later manual refresh is
sufficient. No operational lock, retry service or automatic recovery is introduced.

Each activation saves `collection-status.json` and its digest in the activation
record, plus an offline `recovery.html` and copies of the reporting/collection/
pinned-deployment guides. The download describes the frozen observation and a
digest of the parsed invocation records; it is not Evidence or scientific authority.
The original operational records remain in their existing log directory.

Both selected reports, all immutable packages/anchors/verification receipts and
`delivery-state` including the last scientific generation attempt remain unchanged.
A failed or missing status read cannot invalidate a scientifically valid saved
report. Original v1/v2/v3 package bytes remain replayable. Ordinary report generation
continues to use the original immutable renderer; attach fresh status afterward
with this separate display command. `open` performs no status refresh or writes.

Use `update-live` above only when intentionally generating a new scientific live
report from existing acquired sources; it preserves historical selection but gives
the new live report its actual new calculation/cutoff dates. An ordinary live update
replaces the display, so explicitly repeat status-display refresh if wanted. Status
refresh alone does not update those dates or the last scientific attempt.

For collection failures, follow [existing health and recovery rules](../operations/PROSPECTIVE_PROJECTION.md)
and [pinned deployment guidance](../operations/PINNED_DEPLOYMENT.md). Preserve failed
records and unknown publication markers; do not fabricate missed quotes or retry
unknown calls. Use the bounded activation rollback above if the new display itself
needs reverting. Collector recovery and job changes require their own authority.


## v1.3 explicit browser update candidate

[Manual Performance update](MLB_PERFORMANCE_UPDATE_v1.3.md) composes scientific generation and package-bound match preparation before selection, followed by an optional separately dated collection observation. Existing manual CLI operations and immutable replay retain their behavior. Original static readers keep their own frozen status; the new observation belongs to the app reader. See the workflow guide for clean pinned worker configuration and bounded interruption recovery.
