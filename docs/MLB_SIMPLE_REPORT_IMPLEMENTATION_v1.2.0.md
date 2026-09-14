# Simple report correction — implementation receipt

September 13, 2026. **Presentation correction implemented; acquired MLB source
readiness verified. Acquired-data report generation awaits an accepted clean code
revision.** No synthetic data is presented as acquired results. This receipt is
author-run evidence, not independent implementation acceptance.

Start with the [corrected principal preview — synthetic data](</Users/tom/PopsEdgeReports/mlb/examples/simple-report-final-2026-09-13/reports/entry.html>).
Its small historical link opens the separately retained historical study. Technical
records, exact values, bounded/calibration/log-loss detail, provenance and downloads
are under collapsed Details. The [PM self-review](MLB_SIMPLE_REPORT_REVIEW_v1.2.0.md)
and [next acceptance handoff](../planning/SIMPLE_REPORT_ACCEPTANCE_HANDOFF.md) are
separate artifacts.

## Authority and scope

Re-fetched main and read its complete AGENTS.md. HEAD and origin/main remain
`3001ee9cd4d95519567e0e4567ff71be0465a6a0` (PR #50), parent
`a658233dd218638025232630540c8044afb65a35`. Preserved the existing uncommitted
candidate, original synthetic packages, PDF evidence and prior validation records.
The [Owner's durable correction](MLB_SIMPLE_REPORT_DECISION_v1.2.0.md), Product
amendment and reporting-contract amendment now record the principal-view hierarchy
and acquired-data authorization. Governing Methodology/scientific rules are unchanged.

The complete external correction handoff and companion decision were read unchanged.
Local presentation/tests/docs, already acquired MLB source reads and local generation
are authorized. No new acquisition, collector/scheduler/Evidence/index/checkpoint
mutation, study closure, commit, push/PR/merge, deployment or release was authorized
or performed. No review delegation was initiated.

## Implementation

`forecast_reporting_presentation.py` is display-only renderer `mlb-reporting-html-2`.
The principal view shows period and incomplete status, friendly Eastern dates,
eligible/captured/scored counts, material missing/awaiting/future counts, Brier versus
the same-population 50% reference, governed uncertainty and interpretation cautions.
It explains lower error and zero error without inventing percentage accuracy or
significance. Three-decimal Brier and one-decimal percentage coverage use fixed
half-even display rounding; exact values remain unchanged in Details. Singleton,
zero-width, empty, unknown-calendar and impossible-result limitations remain visible.

`forecast_reporting_delivery.py` retains the original v1 renderer and dispatches by
saved envelope version. New package HTML uses the simple hierarchy; old package
bytes and verification semantics remain unchanged. The one atomic mutable entry is
now the principal live report, projected from its exact selected saved package,
with the independent historical link. Package digests are checked before displaying
saved results. Failed attempts use a plain-language notice and retained date; raw
metadata and diagnostic reasons are in Details. Source/Analysis/projection science,
canonical arithmetic, seeds, populations and chronology were not modified.

A failure-path review found and corrected a new-entry issue before final validation:
if the just-generated package became unreadable while constructing the principal
entry, the update could otherwise select it while showing an unavailable notice.
This now fails through the existing rollback and retains the prior live reference.
A dedicated test injects that exact failure and checks the retained report/result.
No subsystem or broader recovery infrastructure was added.

The clean-revision and actual-clock guards remain intact. They were explicitly
checked early: the uncommitted candidate is rejected, and current main contains
neither delivery module nor operator command. The synthetic seam was used only
with disposable dry-run examples, never with acquired data.

## Acquired source readiness — real data, no report computation

The installed prospective and lifecycle job references both identify:

- Configuration: `/Users/tom/Library/Application Support/PopsEdge/pr17c1/activated.json`.
- Active namespace: `kalshi-mlb-prospective`, mode `activated`, with both canonical
  historical/prospective Protocol IDs configured.
- Primary archive: `/Users/tom/PopsEdgeData/activated/kalshi-mlb-prospective/primary`.
- Collector revision in those job references: `3142428b968b232f19f9568b8f8d43589dd3d2dd`.

Only relevant paths/configuration fields were reported; no credentials or unrelated
NFL archive was read. No job was invoked, repointed or modified.

[Real-source readiness receipt](</Users/tom/PopsEdgeReports/mlb/readiness/2026-09-13-simple-report/readiness.json>)
records a fresh trusted freeze, separately retained anchor and successful independent
source verification under the accepted API. Evidence cutoff:
`2026-09-13T23:41:13.318346+00:00`; verification completed
`2026-09-13T23:48:57.035278+00:00`. This is readiness verification from the working
candidate, not operational Analysis/report generation from an accepted code revision.

- 4,925 frozen manifests; file integrity reports no missing, corrupt, orphaned,
  malformed, incompatible or partial material.
- Both study Protocols resolve. The verified graph contains 2,171 opportunities,
  1,952 historical manifests, 8,195 candles, 610 attempts and 122 snapshots.
  These are **source-object counts**, not eligible/captured/scored report totals.
- Six supporting sessions are verified complete; four incomplete sessions and one
  conflicting session remain explicitly excluded by original rules. No invalid
  material was admitted or repaired.
- All 12,987 before/after source-file hashes agree: no additions, removals or changes.
  Network, archive-write and collector-lock interfaces were forbidden in the readiness
  script. The source boundary/anchor/receipt were written outside archive/checkouts.
- No actual Analysis, Measurement totals or performance report was generated; no
  empirical score or report-level coverage is claimed from this readiness result.

[Readiness script](../planning/CHECK_ACQUIRED_REPORT_READINESS.py),
[file-integrity receipt](../planning/SIMPLE_REPORT_ACQUIRED_INTEGRITY.json),
[frozen source](</Users/tom/PopsEdgeReports/mlb/readiness/2026-09-13-simple-report/frozen-source/source.json>).
Source readiness took about 7 minutes 47 seconds on this archive. Actual report
runtime is not yet measured. A future generation requires a new actual-time freeze;
do not backdate computation or relabel this readiness run as an operational report.

## Validation and presentation evidence

The existing Python 3.14.5 environment and pinned dependencies were used without
installation or upgrade. New tests check simple default content versus retained
Details, fixed rounding/exact values, no technical IDs on the principal view,
failure notices and retained dates/results, empty/degenerate/infinite/unknown cases,
v1 package replay without rewriting, and the new-entry read-failure rollback.
Final focused result: **123 tests passed in 38.175 seconds**. Final full repository
result: **899 tests passed in 93.203 seconds**, including NFL/World Cup and original
scientific serialization/identity/seed regressions. Earlier 122/898 passes preceded
the new-entry failure correction and remain historical receipts, not final acceptance.

```text
/Users/tom/pops-edge/venv/bin/python -m unittest tests.test_forecast_reporting_delivery tests.test_forecast_reporting_analysis tests.test_forecast_reporting_source tests.test_forecast_standalone_research tests.test_forecast_standalone_publication -q
/Users/tom/pops-edge/venv/bin/python -m unittest discover -s tests -q
```

[Final focused log](../planning/SIMPLE_REPORT_FINAL_FOCUSED_TESTS.log),
[final full log](../planning/SIMPLE_REPORT_FINAL_FULL_TESTS.log),
[static principal/Details checks](../planning/SIMPLE_REPORT_STATIC_QA.json),
[principal text](../planning/SIMPLE_REPORT_ENTRY_TEXT.txt).
Static checks verify collapsed Details, local link resolution, visible rounded
values/uncertainty/data-origin notices, hidden technical identifiers and no remote
resources. Earlier v1 package identities and payload digests still match. Final
candidate code reverified both corrected preview packages with new dated receipts;
scientific bytes and original package dates were unchanged.

The corrected preview is **synthetic presentation evidence only**, held in a separate
durable local report location. It shows one scored live observation with exact Brier
0.2025 (display 0.202 by half-even rounding) versus reference 0.250, and visible
sample/gap cautions. It is not a substitute for the requested acquired-data report.
The historical preview independently displays its four-observation example.

No new browser rendering, PDF or subjective Owner acceptance is claimed for v2.
The recorded browser security restriction remains in force; no alternate browser or
server workaround was attempted and no repeated exports were requested. Prior PDF
assessments describe v1 and cannot establish usability of the new renderer. Current
evidence is the inspectable corrected HTML, extracted principal content, static checks
and automated regressions, with those visual limits explicit.

## Exact candidate and remaining prerequisite

[Current complete patch](../planning/SIMPLE_REPORT_CANDIDATE.patch) and
[code/file inventory](../planning/SIMPLE_REPORT_FILE_INVENTORY.json) identify the
uncommitted corrected candidate, including earlier delivery work and new presentation,
tests, Product/contract/decision/operator/release-plan amendments and review receipts.
Earlier DELIVERY patch/hash receipts remain unchanged as historical evidence.

**Minimum next gate:** independent acceptance of the corrected bounded implementation,
then explicit authorization to record it as a local commit and make a clean separate
reporting checkout at that exact revision. Current main cannot generate the report
because the delivery implementation is absent; this candidate cannot generate it
operationally while dirty. A local accepted commit/clean reporting checkout suffices
for code provenance; push, PR/merge, collector changes and a full deployment are not
technically required merely to satisfy this guard, and remain unauthorized.

Already authorized acquired-data reads/generation do not need to be reapproved.
Once the clean accepted reporting revision exists, generate/verify the separate
historical and live packages in a new local report root, select historical explicitly
and update live under the unchanged guard. Until then, do not use fixtures or the
synthetic seam to manufacture acquired results. No integration/deployment prompt is
issued for an independently unaccepted candidate.
