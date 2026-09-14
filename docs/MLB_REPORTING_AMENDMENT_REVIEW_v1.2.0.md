# Independent amendment and integration review — MLB reporting

Decision: **Accepted for the bounded complete reporting integration and local display activation. No blocking findings remain.** This independently delegated amendment review reuses the [original independent acceptance](MLB_REPORTING_INDEPENDENT_REVIEW_v1.2.0.md). It does not reopen accepted scientific or operational limitations or claim that integration or activation has already occurred.

## Scope and governing boundary

Refreshed GitHub main is `3001ee9cd4d95519567e0e4567ff71be0465a6a0`; original accepted local commit is `20c1a009c59dd88c5796e933adc5b62adf509195`. The implementing agent refreshed main; this reviewer independently checked both local references. Complete root AGENTS.md, original acceptance, the local two-decimal correction receipt, reporting contract, latest display decision, Architecture activation amendment and integration handoff were read. Methodology > Product > Architecture > reporting contract/decisions > implementation governs. The full intended integration inventory below includes the original accepted delivery plus the amendment, not merely the formatting diff. Planning receipts, generated pages, logs and scratch remain excluded.

The Owner explicitly authorized commit, push, PR, merge and bounded normal-entry activation. That authority supersedes earlier no-integration wording only for this work; it does not authorize acquisition, collector changes, source mutation, closure, Policy or a whole-v1.2 release.

## Independent conclusions

- Scientific source, Analysis, projection and research files are byte-identical to the original accepted local commit. Original delivery acceptance therefore remains applicable. The v2 presentation module is byte-identical to the previously accepted renderer. v1 remains available, and dispatch admits v1/v2/v3 for saved verification.
- V3 formats all readable numeric metrics to at most two decimals, leaves integer counts intact, gives friendly dates, preserves exact downloadable payloads and uses readable calendar/reconciliation/performance/provenance/status disclosures. Rounded score ties do not claim a visible higher/lower difference; coincident interval endpoints do not imply certainty. Calendar gaps do not become an invented count of missing games.
- Local activation reads selected packages, retained anchors and matching previous verification receipts. Package digests and saved HTML reconstruction are checked without source acquisition, source replay or new scoring. Its display provenance explicitly attributes the earlier scientific verification, and preserves the original calculation/cutoff/status dates.
- Activation preserves the exact parseable delivery-state selection and last-attempt object, uses the existing delivery-local writer lock, prepares new readable live/historical pages, backup and digest-conditional receipt, and atomically replaces only the mutable entry. Rollback checks both active-entry and backup digests before restoring the previous bytes. Old immutable packages, anchors and verification receipts are not rewritten.
- One issue found during this review was resolved: activation initially omitted the principal failed/running-attempt notice while retaining it in Details. The shared notice is now used by delivery and activation, with a regression check. A test-only missing exception qualification was also corrected. Neither issue remains outstanding.

No P0/P1 finding remains; no extra resilience subsystem or broad scientific re-review is required. Local trusted files/clocks, manual recovery and dependence on retained source for future full scientific verification remain accepted. Display activation intentionally requires both selected reports; ordinary scientific live generation retains its original independent historical behavior.

## Independent validation and limits

The reviewer ran `python -m unittest tests.test_forecast_reporting_delivery -q` using `/Users/tom/pops-edge/venv/bin/python`: **33 tests passed in 23.694 seconds** on the final candidate. Coverage includes saved v1/v2 compatibility, v3 precision/ties/readable details, historical/live and empty states, canonical precision retention, exact state/package/anchor/receipt preservation, blocked science calls during activation, exact rollback, missing prior verification rejection, failed/running principal notices and prepublication failure preservation. An earlier 30-test amendment run also passed; one intermediate 33-test run exposed the corrected test-only NameError.

Independently checked byte preservation of source/Analysis/projection/research and original v2; `git diff --check` passed. Independently parsed all three previously produced actual-data corrected preview pages: no readable machine dumps or metrics beyond two decimals, and all 12 report/evidence links on each page resolved. This is structural/content evidence, not an observed browser interaction or new scientific verification. The recorded browser restriction was respected.

The original accepted full-review evidence and author's prior actual acquired-data exact verification remain attributed evidence. The author's final full compatibility run passed **906 tests in 78.457 seconds**, confirmed against `planning/REPORTING_INTEGRATION_FULL_TESTS.log`; this full run is attributed author evidence, not an independent rerun. The integrating agent remains responsible for the exact pushed/merged head and actual normal-entry activation checks. This review does not claim hosted CI, successful merge or activation in advance.

## Exact reviewed integration inventory

SHA-256 hashes below identify the final accepted files relative to main. This review artifact is the additional review-only file and is excluded from its own digest inventory.

| File | SHA-256 |
|---|---|
| `ARCHITECTURE.md` | `27abc2c2f6b2d0138606da1a9075b519496cdfda027055adbafccb5cd6cda89b` |
| `docs/MLB_REPORTING_CONTRACT_v1.2.0.md` | `df82971da3abdad93137a37d0bb4424a189e971c717729fa3ea375e8f510b965` |
| `docs/MLB_REPORTING_DELIVERY_API_v1.2.0.md` | `0f68c3489cb95657854b60ea118cc8b598790ba20dcdc5adda4b26b790b36a34` |
| `docs/MLB_REPORTING_DELIVERY_IMPLEMENTATION_v1.2.0.md` | `544a9734c2313ea5cc870186bd383c16bb496f4b67817029f801e6d3c7f35873` |
| `docs/MLB_REPORTING_DELIVERY_REVIEW_v1.2.0.md` | `2f927a2d169799fe59ccb59aa45c1d457681ba56f8f0aa979608cc47f5d9b92e` |
| `docs/MLB_REPORTING_INDEPENDENT_REVIEW_v1.2.0.md` | `a6a32007c50e6d847b8858a37f99727da68b8760d5d56a6e3903551788092f59` |
| `docs/MLB_REPORTING_INTEGRATION_ACTIVATION_v1.2.0.md` | `a75d107f7c064a37248265ad4967849c7b37e707163b7e4b02a38adfc5f9e97d` |
| `docs/MLB_SIMPLE_REPORT_DECISION_v1.2.0.md` | `c71211fd98267525108805220b5ea5d0731c74fce61942fe644d54a367fdb79d` |
| `docs/MLB_SIMPLE_REPORT_IMPLEMENTATION_v1.2.0.md` | `9818299108ddd6687495c9ffead8e0ca63e9898a66cc174562ff7853f8c12591` |
| `docs/MLB_SIMPLE_REPORT_REVIEW_v1.2.0.md` | `079bdbc6f8ec4892cf002a1b627b16c4cc208dc4da4c2ee76020db247a5a493a` |
| `docs/PRODUCT.md` | `540ae5389cebb96e1a27f755f732d41679af9a8594b2cda03105000e1e21f64c` |
| `docs/RELEASE_PLAN_v1.2.0.md` | `8d94ae0ace324aa741f06154742f212c590acd226ed28e679c4806f226a7fa1a` |
| `forecast_reporting_activation.py` | `204b7018ee380f1ee56fa0af1fb83163dacb4b3e8c58d7cfed2917a893dc4948` |
| `forecast_reporting_delivery.py` | `1de0498ef1da14a20c9f90d38edb39c5258aa150779b185082338db2248e46b6` |
| `forecast_reporting_presentation.py` | `a18fea63b001aa94714a7c95331806190c9ec436b1b514781f0ec6e93de369a0` |
| `forecast_reporting_presentation_v2.py` | `86f4f8bc8b66f465152f0408744e9798a83054d75a303afd356cb8edabb010d2` |
| `forecast_reporting_projections.py` | `146febeb3a92354a0f062d8e2abe3e45c8766af944de9b8b16da081520e33f19` |
| `forecast_standalone_research.py` | `27ed25caa35688466076d6e83ba3689f8fb5b6c7d354bb0dabe1a962c5c85317` |
| `operate_forecast_reporting.py` | `9937769e13684940087c430e5a95bfb914946343401c3c371c3535188ad670b3` |
| `tests/test_forecast_reporting_delivery.py` | `436154d77dcf132008a6d03f002ed3f01084665b6a8ab0788c63ac76b74f450a` |

## State changed and next authorized gate

This reviewer changed only this Markdown review and local temporary test outputs. No implementation, acquired Evidence, prior report, collector configuration, remote branch, PR or operational entry was changed by the reviewer.

Proceed with the already authorized [integration and activation handoff](MLB_REPORTING_INTEGRATION_ACTIVATION_v1.2.0.md): commit the accepted inventory plus this review, preserve planning evidence, push/open the complete PR against current main, inspect checks/head/base, merge the accepted head and activate from a clean checkout at the exact merged revision. Verify the actual active digest, unchanged selection/status and immutable prior files, readable live/historical links and clean revision. Record those execution outcomes in a separate activation/completion receipt. No repeat approval is required for that bounded sequence.
