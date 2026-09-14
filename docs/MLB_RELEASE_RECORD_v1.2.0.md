# MLB v1.2.0 release record

Status: **ready for Product Owner publication approval; unpublished**. Reconciled September 14, 2026. This is a documentation/release-metadata candidate, not a release receipt.

## Scope and baseline

The September 12 release direction narrows v1.2 to Kalshi MLB collection, honest coverage, separate historical/live baseline reports, understandable local presentation and documented manual operation. The authority hierarchy and scientific invariants remain unchanged.

Preparation baseline is main `3a152ba53a91941e427db8fad54ae7e6b5f062a6`. The subsequent-to-MLB PR #54 changes NFL sorting only; its three-file diff introduces no MLB reporting changes. This record does not review or deploy NFL maintenance. A repository release necessarily includes already merged history; it is not a claim that all capabilities share one runtime deployment.

## Completed gates

| Gate | Completion evidence |
|---|---|
| Reporting authority | PR #48; reporting contract and governing amendments |
| Frozen source and successor Analysis | PR #49 and PR #50; retained independent acceptance |
| Actual historical/live reporting and readable display | PR #51, merge `0d8e18248d190a0bf4bf30185ece4427dd371a9f`; real acquired packages independently anchored and exactly verified before display activation |
| Dated collection status | PR #53, merge `adcce3a7da66fd9c851f657b3737cf6b16f92f34`; independent correction acceptance and local activation |
| Owner usability acceptance | Owner inspected the current report and said “okay. it looks good.” in the coordinating conversation |
| Remaining operational concern | Dated read-only follow-up at 2026-09-14T19:36:18.551972Z found no current invocation blockers after the natural lifecycle completion |

Original reporting independent review passed 123 focused tests; amendment review passed 33. The author's 906-test compatibility suite is reused, not represented as newly rerun. Collection-status independent review passed 101 actual focused tests and 19 lifecycle tests; an initial nonexistent module-name loader error was disclosed and corrected. See [reporting acceptance](MLB_REPORTING_INDEPENDENT_REVIEW_v1.2.0.md), [amendment acceptance](MLB_REPORTING_AMENDMENT_REVIEW_v1.2.0.md) and [collection acceptance](MLB_COLLECTION_STATUS_INDEPENDENT_REVIEW_v1.2.0.md).

PR #51 activation checked 39 links and immutable-file preservation. PR #53 activation checked 48 links across four HTML pages and preserved all 29 other original files plus exact selection and last scientific-attempt state. No hosted CI pass is claimed; the integration receipts record no configured hosted workflows. No new broad suite or browser automation was performed for this documentation reconciliation. The prior review's 123 Python-file and eight shell-file syntax checks are dated evidence, not claims for later NFL code.

## Operational observation and limitations

The saved status observation at 18:48:05 UTC showed supporting integrity failure/staleness and a dependent projection skip. Read-only inspection found no persistent structural/digest damage. Concurrent publication was a supported hypothesis, not a proven root cause. The later existing cycle completed supporting refresh at 19:06:47 UTC, projection at 19:06:56 and health/lifecycle at 19:07:11. At the 19:36 observation those invocation blockers were superseded. No repair, restart or cleanup was performed.

This is dated evidence of continued operability, not perpetual health certification. The active page retains the older observation until explicitly refreshed. Owner layout acceptance is not evidence that the saved status was refreshed. No new status refresh is required to publish this release under the accepted frozen/manual model.

Accepted limitations include early missed captures, incomplete studies, insufficient samples, local trusted files/clocks, manual report/status refresh, visible failures and safe manual recovery. Health observations never establish scientific coverage. Retrospective and prospective populations remain separate; release publication does not close either study or eliminate final-report obligations. Exact replay still requires retained source and independent anchors. The unknown exact predicate behind the superseded transient failure is not promoted into a release blocker.

External suppliers, native-model expansion, automatic recovery/refresh, hosting, shared NFL/MLB shell, policy and wagering are deferred. NFL issues are handled separately.

## Deployment and publication boundary

MLB reporting is activated at `adcce3a7da66fd9c851f657b3737cf6b16f92f34`. The collector was observed clean at `3142428b968b232f19f9568b8f8d43589dd3d2dd` during the investigation. Both pins remain independent of the forthcoming release tag. No repin or restart is needed for this documentation release.

The candidate sets repository source VERSION to `1.2.0`. Existing pinned NFL, reporting and collector checkouts retain their version/files. This is source-release metadata, not a request to redeploy or relabel those running applications.

Proposed tag: `v1.2.0`. Proposed title: **Pops’ Edge v1.2.0 — MLB collection and baseline reporting**. Target is the exact merged documentation/metadata commit after approval, based on the reviewed baseline and any explicitly checked intervening changes. No v1.2 tag existed when remote tags were checked during preparation. Do not tag moving main blindly, replace an existing tag, or claim publication in advance.

## Review outcome

The prior collection-status release gap is closed by accepted implementation and actual activation. Documentation status is reconciled by this candidate. No known blocking finding remains against the narrowed MLB acceptance boundary. Recommendation: approve the prepared documentation/metadata integration and release publication, retaining the listed limitations. Publication actions still require Product Owner authorization.

Operator procedures: [report delivery and status refresh](MLB_REPORTING_DELIVERY_API_v1.2.0.md), [pinned operation](../operations/PINNED_DEPLOYMENT.md), [health interpretation and recovery](../operations/PROSPECTIVE_PROJECTION.md). Dated local receipts are retained by the operator; raw account data, logs, reports and local paths need not be attached to the public release.
