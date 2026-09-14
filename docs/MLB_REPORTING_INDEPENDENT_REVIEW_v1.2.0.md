# Independent acceptance — MLB archive-to-report delivery

Decision: **Accepted for the bounded local archive-to-report workflow, including the corrected simple principal presentation. No P0/P1 blocking findings remain.** This is an independent implementation acceptance, not a claim that acquired-data reports have already been generated or that v1.2, study closure, or a deployment is complete.

Reviewed by the separately delegated independent-review agent, independently of the author's implementation and self-review conclusions. Review completed 2026-09-14T00:21:16.284217+00:00.

## Exact scope and authority

The local candidate is based on `3001ee9cd4d95519567e0e4567ff71be0465a6a0`, parent `a658233dd218638025232630540c8044afb65a35`. Local HEAD and the refreshed `origin/main` resolve to the same base. The initiating agent refreshed main before delegation; the reviewer independently checked both references and inspected the working changes.

Acceptance covers the following **15 implementation, test and documentation files**, at these SHA-256 identities. It includes delivery, projections, presentation, the manual CLI, the narrow original capture-validator extraction, focused tests, and the governing/API/author receipts accompanying them. `forecast_reporting_source.py` and `forecast_reporting_analysis.py` remain the accepted main implementations; they are dependencies, not modified candidates.

| Accepted file | SHA-256 |
|---|---|
| `docs/MLB_REPORTING_CONTRACT_v1.2.0.md` | `11bb6bc75ebc733881b3bd0787674620e4ab180504ea783ea19433608942b06d` |
| `docs/MLB_REPORTING_DELIVERY_API_v1.2.0.md` | `09d44324b5640cfab0cfc806576032f6eb7283e80ce412c86d3b43ac94ab8b4f` |
| `docs/MLB_REPORTING_DELIVERY_IMPLEMENTATION_v1.2.0.md` | `544a9734c2313ea5cc870186bd383c16bb496f4b67817029f801e6d3c7f35873` |
| `docs/MLB_REPORTING_DELIVERY_REVIEW_v1.2.0.md` | `2f927a2d169799fe59ccb59aa45c1d457681ba56f8f0aa979608cc47f5d9b92e` |
| `docs/MLB_SIMPLE_REPORT_DECISION_v1.2.0.md` | `e7e20f18ed2e572d93b0850e3be0a49bd6332323e65c42bc399c2caf74228943` |
| `docs/MLB_SIMPLE_REPORT_IMPLEMENTATION_v1.2.0.md` | `9818299108ddd6687495c9ffead8e0ca63e9898a66cc174562ff7853f8c12591` |
| `docs/MLB_SIMPLE_REPORT_REVIEW_v1.2.0.md` | `079bdbc6f8ec4892cf002a1b627b16c4cc208dc4da4c2ee76020db247a5a493a` |
| `docs/PRODUCT.md` | `0d74a9d4d780526375e9eed81c5dcd7d0dfaa7ef12982621877783e13abd2781` |
| `docs/RELEASE_PLAN_v1.2.0.md` | `a0fbd4c290a9e0b2e8646584806668288f47f422a8639a06c0502d81b51e3247` |
| `forecast_reporting_delivery.py` | `61b1ef8a6739d1649d1ec8fa5038d5648c16af26edd2f914391b70ce99c6d1aa` |
| `forecast_reporting_presentation.py` | `86f4f8bc8b66f465152f0408744e9798a83054d75a303afd356cb8edabb010d2` |
| `forecast_reporting_projections.py` | `146febeb3a92354a0f062d8e2abe3e45c8766af944de9b8b16da081520e33f19` |
| `forecast_standalone_research.py` | `27ed25caa35688466076d6e83ba3689f8fb5b6c7d354bb0dabe1a962c5c85317` |
| `operate_forecast_reporting.py` | `9b34ef5f9e194c4731a7ba96745ba3a83975adbed82fd4b2d7fc72d0efbe074d` |
| `tests/test_forecast_reporting_delivery.py` | `a72e05506894f48b03f8c73916587a62e307d883f40d7fee8664c85b46ad679b` |

The two planning handoffs, aggregate patch, examples, logs and other planning evidence are review references, **excluded from the intended local commit**. This independent review artifact is the sixteenth intended file. Its addition records acceptance and the latest authorized gate without changing the reviewed implementation. The original inventory has 29 entries; all 29 sizes and digests matched during this review. Its own SHA-256 is `4ced2d1ac7888d31fdf5b81d514e25a8bd48bb0b44b52689667e887968805794`; aggregate patch SHA-256 is `7d916b2a1356a1ebe167cf7b1dcd4c935f8eba70523b6b130533fda04f01e956`.

The governing boundary applied was Methodology → Product → Architecture → release decisions and reporting contract → implementation. In particular: the MLB reporting amendment in `EMPIRICAL_RESEARCH_METHODOLOGY.md`, `docs/PRODUCT.md`, the report-delivery section of `ARCHITECTURE.md`, September 12 release direction, [reporting contract](MLB_REPORTING_CONTRACT_v1.2.0.md), [simple-report decision](MLB_SIMPLE_REPORT_DECISION_v1.2.0.md), and original archive-to-report acceptance handoff. The accepted source and Analysis API boundaries and their unchanged code were inspected. The simple-report amendment changes presentation hierarchy only.

The latest Product Owner instruction explicitly authorizes independent review, necessary bounded corrections, a local commit of accepted files, a clean isolated reporting checkout at that commit, and actual-clock historical/live report generation and saved verification from already acquired data. This later instruction supersedes the older no-commit/stop-at-readiness authorization language in earlier candidate decisions and handoffs **for this bounded sequence only**. It does not supersede scientific safeguards or authorize push, PR, merge, collector deployment, provider acquisition, operational-state mutation, study closure or release.

## Independent findings and acceptance basis

No blocking findings were identified. No implementation correction was requested by this review.

- **Source authority and false results:** generation freezes the actual namespace through the accepted source API, retains an independent anchor before calculation and reads that anchor for subsequent acceptance. Saved verification reconstructs Analysis and projections from that pinned source. Rehashed projection/HTML changes, missing/extra payloads and mixed-study material are rejected semantically, not merely by digest. Packages and presentation remain derived Analysis, with no Policy or Governance authority.
- **Population and Coverage:** separate canonical protocols and accepted cumulative/bounded scopes remain in force. Captured membership uses the original validated candle or Snapshot/observation stages, independently of scored results. The required subset hierarchy is checked. Complete reconciliation remains inspectable; due, future, missing, unresolved and unknown-calendar cases are not converted into successful observations. Historical absent mapping is explicitly unknown, with required rates withheld; conflicting mappings fail closed.
- **Statistics and chronology:** the constant 50% reference uses each exact scored Measurement set; empty scores stay absent. Detailed calibration preserves the fixed bins and underlying original statistics. Original constructor arithmetic and IDs remain intact after the narrow helper extraction. The default operational path requires actual wall time and a clean exact revision, before and after calculation. Freeze, anchor retention, analytical calculation, projection, rendering, package completion and later verification remain separately dated. Display rounding does not alter saved scientific values or dates.
- **Local workflow and preservation:** completed candidates undergo full verification before immutable publication, receipts and current selection. The entry retains separate historical/live references and records failures. A newly unreadable live package cannot replace the preceding reference. Partial/interrupted candidates are not selected by discovery. Missing historical output does not prevent later valid live work. Output guards exclude the source checkout and configured archive roots. The only lock is delivery-local; no collector mutation is introduced.
- **Reader:** the principal view presents period/status, eligible/captured/scored opportunities, material gaps, rounded Brier versus the same-population reference, and sampling/sufficiency cautions. Exact provenance, log loss, bounded results and calibration remain in collapsed Details. Empty, singleton, zero-width, unknown-calendar and impossible-result caveats stay visible. The prior renderer remains available for exact old-package replay, and opening saved output performs no acquisition, scoring, verification or date refresh.

These conclusions concern the approved local/manual deployment model. They do not require automatic recovery, a server, a generalized publication service, comprehensive availability or favorable performance.

## Validation evidence and limitations

The reviewer independently executed:

```text
/Users/tom/pops-edge/venv/bin/python -m unittest \
  tests.test_forecast_reporting_delivery \
  tests.test_forecast_reporting_analysis \
  tests.test_forecast_reporting_source \
  tests.test_forecast_standalone_research \
  tests.test_forecast_standalone_publication -q
```

**123 tests passed in 25.597 seconds**, including the 26 new delivery tests. The run exercised both studies, source immutability and forbidden acquisition/mutation interfaces, source anchoring, fresh-process verification, post-cutoff corrections and session completion, legacy record compatibility, rehashed tampering, Decimal/input-order replay, independent historical selection, failure stages, missing historical output, offline open, simple/technical separation, display-only rounding and original-renderer preservation. The reviewer also independently recomputed all 29 recorded file sizes/hashes with zero mismatches and read the implementation paths and targeted regression fixtures.

The author's full-suite result of **899 passing tests in 93.203 seconds** is attributed author evidence, checked against the retained hashed log; it was not rerun independently. Source readiness on the acquired archive is also attributed prior evidence, not this review's acquired-data execution.

The Product Owner's inspection of `/Users/tom/Downloads/Performance Report_3.pdf` is accepted as **Owner-provided visual evidence** that the corrected principal hierarchy shows period/status, counts, rounded Brier/50%, cautions and technical Details. It represents synthetic data. The reviewer did not independently open or render that PDF and does not claim observed browser interactions. The recorded browser local-file restriction was respected; no alternate browser/server workaround or repeated export request was used. Automated structure/content checks supplement that observation; comprehensive responsive/accessibility testing and broader subjective polish are not claimed.

Actual acquired-data report computation, clean-checkout operational execution, measured acquired populations and completion receipts remain the next execution gate. Fixture success does not certify those outcomes, current collector health, calendar completeness, empirical sufficiency or final study status. Retained archive files and the independently trusted anchor remain prerequisites for future exact verification. Local trusted clocks/filesystem and documented manual recovery are accepted limitations; deliberate concurrent replacement of both package and trust anchor is outside the stated trust model.

## State changed and next authorized gate

Review changed only this independent Markdown artifact and temporary test outputs; it did not alter implementation, source Evidence, indexes, checkpoints, collector/scheduler configuration, existing report packages or external repository state. No network/provider acquisition, commit, branch, push, PR, merge, deployment, activation, closure or release was performed by the reviewer.

The implementing agent may now execute the Owner's already authorized sequence: commit exactly the accepted 15 files plus this review locally, preserve planning evidence untracked, establish a clean isolated reporting checkout at that exact commit, generate a fresh historical interim package and explicitly select it, generate/update a separate live in-progress package, and verify both saved packages using their independently retained anchors. All runs must use actual clocks and the unchanged operational revision guard, outside source/archive roots, with no synthetic bypass. Preserve acquired sources and all previous output bytes, and return actual report links, scopes, cutoffs, populations, limitations and completion evidence.

Successful execution completes that bounded report request; it does not itself authorize push/PR/merge, collector deployment, new data acquisition, study closure or release. A concrete scientific or core-workflow failure encountered during that execution must remain visible and be resolved within the approved boundary before claiming completion.
