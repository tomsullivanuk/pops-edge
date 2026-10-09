# Pops | MLB | Phase evaluation | Independent review handoff

## Candidate

Authoritative repository: https://github.com/tomsullivanuk/pops-edge.
Baseline main verified October 9: `50790ad82d7080553ca11a16eba28897bf4a290a`.
Isolated local clone: `/Users/tom/Documents/Codex/2026-10-02/task/pops-edge-mlb-phases`.
Branch: `codex/mlb-phase-evaluation`. Changes remain uncommitted; no PR exists.
Read full root AGENTS, [decision](MLB_PHASE_EVALUATION_2026-10-09.md), [author review](MLB_PHASE_EVALUATION_2026-10-09_REVIEW.md) and the exact exported patch/inventory before review. Reverify authoritative main before integration; avoid the unrelated dirty legacy checkout `/Users/tom/pops-edge`.

## Approved implementation and review criteria

Regular-season and postseason winner-probability evaluation; new postseason prospective cohort from October 11, 2026 midnight America/Chicago. Original regular-season lineage, source Evidence and selected packages survive unchanged. T−6h/five slots/five minutes and established home YES probability/scoring/uncertainty remain. Phase is authoritative, populations and reports are separate, no duplicate capture and no historical backfill. Review initialization against existing future schedule histories, failure-inclusive Coverage, post-update failure visibility and saved/download phase routing.

Use `.venv/bin/python -m unittest tests.test_mlb_phase_evaluation -q` for dedicated acceptance; full regression command/results and screenshots are supplied in `../mlb-phase-evaluation-evidence/`. Dependencies are the existing repository requirements. Browser regression uses bundled Node/Playwright and installed Chrome with every request intercepted. No real provider credentials or network acquisition is required for these tests.

## Commissioning plan — proposed, not executed or authorized here

**Resume gate:** no collector, lifecycle/maintenance job, web reader/update action or report worker may resume against the expanded archive until every component is pinned to verified compatible code and the upgraded graph, projection and replicas pass verification. An old worker must never be allowed to replay new authority while pins are being corrected.

1. Obtain separate integration authorization and produce a clean immutable candidate revision from reverified current main. Record the intended compatible revision and executable/checkout/configuration path for **collector, lifecycle, shared web application and report worker separately**. Deployment and archive changes are not authorized by code acceptance.
2. Recheck the complete official October 11 slate and calculate its earliest admitted T−6h target. The October 9 21:17:52 UTC public recheck returned one game: Dodgers at Brewers (849809), October 11 19:00 CDT, target 13:00 CDT / 18:00 UTC. Retain URL, retrieval receipt and body digest; this remains provisional. An admitted midnight Central start would imply October 10 18:00 CDT. Finish commissioning before the earliest actual target; never reconstruct a missed capture.
3. Record prior component pins and configuration. **Quiesce collector, lifecycle/supporting maintenance and manual reporting together**, prevent new manual update requests, and drain existing report/collection work and writer locks. Quiesce the shared web application or keep its update entry point unavailable during transition. Verify a consistent independent archive/replica backup after work is drained. Do not change archive identity/paths or the September 5 activation record.
4. **While all affected components remain quiescent, stage and verify the compatible collector, lifecycle, web and report-worker pins before changing cohort configuration or appending authority.** Check actual executable paths, launchd arguments, configured worker checkout/revision and checkout cleanliness against each intended approved pin. Remove stale paths to older binaries from the proposed configuration. Retain a four-component pin verification table. Any missing, dirty or incompatible pin blocks the upgrade and all restart/update actions; keep components stopped.
5. With all compatible pins verified and components still quiescent, add the canonical postseason Protocol ID to the existing activated configuration, retaining original regular-season and any accepted retrospective ID. Invoke **the compatible candidate's initializer explicitly**, using the actual clock and its exact clean revision:

   ```text
   <candidate-python> <compatible-candidate-checkout>/operate_forecast_standalone_activation.py --config <activated-config> --expected-revision <clean-candidate-sha> initialize-activation
   ```

   This appends protocol/opportunity authority from already known schedules without constructing quotes. Do not invoke a prior checkout, fixture override or backdated clock.
6. Keep components stopped while verifying canonical graph, rebuilt projection, replicated archive integrity and retained original regular-season authority/packages with compatible code. Reconfirm all four staged pins and the actual proposed launch/configuration paths. Any failure or incomplete inspection keeps the **resume gate closed**; use the functional rollback below rather than restarting an old binary.
7. Only after both pin and archive checks pass, resume the compatible shared web application and **one existing collector/lifecycle arrangement**, then verify actual running paths/revisions match the staged pins. Make the compatible report worker eligible for separately authorized manual reporting only after the same gate passes. No second collector, overlapping monitor or automatic report regeneration is introduced. Verify supporting schedule/catalog freshness, admitted opportunity identity and T−6h due time. Observe the first real capture and its Evidence, failures and terminal status honestly; a healthy process is not complete Coverage.
8. Separately authorize any manual report regeneration. Regular-season remains at its existing report root; postseason uses `<reports>/postseason`. The existing Update Performance Report action prepares both when the new protocol is configured. Manual CLI alternative: `operate_forecast_reporting.py --output <reports>/postseason update-live --config <activated-config> --expected-revision <clean-candidate-sha> --phase postseason`. Never pass retrospective postseason or synthetic overrides to production.
9. Verify phase selection and saved downloads read retained packages without provider calls. Confirm old regular-season packages/anchors remain valid and no phase-pooled summary exists.

## Rollback plan

Before any archive upgrade, an ordinary rollback can retain all prior pins/configuration and stop commissioning. After postseason authority is appended, remove its ID from capture configuration while retaining original IDs and the compatible phase-aware binary. This stops new postseason calls while preserving immutable evidence and schedule obligations; supporting replay continues maintaining archived cohorts. Keep the prior valid reports selected and return the default reader to Regular season. Failed/missed postseason work remains visible. Do not delete protocol records, rewrite opportunities, restore over newer evidence or run the old single-prospective validator against the expanded archive. A full binary rollback would require a separately reviewed archive isolation/migration plan.

No push, PR creation, merge, deployment, activation, live data/configuration mutation, live report generation, vendor contact, monitor change or native-model experiment is authorized by this handoff. Independent review accepted the local code scope; its P2 commissioning-order correction is now incorporated. The next approval is bounded candidate publication (commit, push and PR creation). Merge and controlled commissioning remain separate approvals; no version bump or release publication is implied.

## Execution authorization amendment — October 9, 2026

Tom subsequently authorized all remaining bounded publication, merge and controlled commissioning/reporting steps, without further routine confirmation. Earlier statements of unauthorized future actions describe the original handoff gate and are superseded solely for this accepted change. The mandatory resume gate and serious-issue pause remain. See [Owner authorization amendment](MLB_PHASE_EVALUATION_2026-10-09.md#owner-authorization-amendment--october-9-2026). Record execution receipts outside immutable checkouts; preserve old/new pin records and raw/archive/report baselines.
