# Pops | NFL | Simple refresh | Independent review

Decision: **Approved with no blocking findings.** Scope is the five-file local candidate below, based on `1dc1cc25cc6ed214553705caf353d8c785f84d61`. Current authoritative main is `3142428b968b232f19f9568b8f8d43589dd3d2dd`; its complete root AGENTS.md was read. Review was independent of implementation.

## Governing boundaries

Applied owner-approved automatic next-eligible-week workflow, NFL_MODEL_PERFORMANCE_PROTOCOL.md, the fixed NFL_WEEK1_STARTING_COHORT.md addendum, and NFL_REFRESH_GUIDE.md. Automatic targeting remains operational convenience; the existing research service determines chronology, population, quote eligibility and freeze. No protocol/addendum content changes or active-store migration occur. Unknown valid schedule dates block selection rather than skip; absent workbook target is visible. Previously enrolled outcomes continue updating even when selection cannot proceed. Manual override retains strict validation. No results tab or automatic retry is added.

## Validation

- Independently ran 46 focused workflow, starting-cohort and service tests; all passed.
- Additional offline probes exercised the actual automatic resolver through the workflow (without mocking target resolution), repeat automatic refresh preserving the original market event and value, unresolved target isolation while the operational board completes, and seven malformed override values rejected.
- Fixed partial-cohort test verifies selection remains Week 1 after the first two games and retains both exclusions. Existing cohort/service tests cover common cutoff, freeze, correction, retries and chronology.
- Reviewed HTML request/default handling, collapsed Advanced options, disabled controls while busy, explicit capture status and reload warning visibility. No browser visual QA claimed.
- `git diff --check` passed. No provider requests, production modifications, initialization, activation, commits, pushes or deployment occurred during this review. Only temporary offline fixtures and this review artifact were written.

## Nonblocking finding

**P2 — Fresh schedule acquisition failure can use older valid schedule history without an explicit selection warning.** In `automatic_comparison_week`, the return event from `observe_results` is not checked before `report`. An offline 503 probe after a valid capture confirmed the failed event is archived but Week 1 can still resolve from its older valid schedule. This is a diagnostics/robustness limitation: failure evidence remains inspectable, unknown dates in a valid schedule still block, and the unchanged service independently validates all new captures and cutoff chronology. A later valid refresh or explicit Advanced override is a reasonable local recovery path. A future refinement can surface the acquisition failure in selection status. This does not justify a generalized recovery subsystem or block this workflow simplification.

## Next authorized gate

The owner conditionally authorized commit, push, PR, merge and deployment after approval; approval is satisfied. Integrator should verify these hashes, integrate against current main, run appropriate regression validation, and deploy while preserving the existing production performance store and activation byte-for-byte. No new collection is necessary merely to deploy these controls.

## Reviewed SHA-256 fingerprints

- `nfl_refresh.py`: `00494d293272a6a407d345eec10d19a7c96317bb7e175795b78a61beb722b77c`
- `nfl_refresh.html`: `dafd6c4c005c1b781c3352d435fe10a601f83658d43963a5073a90c2ea69fbd8`
- `docs/NFL_REFRESH_GUIDE.md`: `dcb223b919f7f44f1666aa93e5e6eb707c9dce1cdf8e23174682d24951ece2f9`
- `tests/test_nfl_performance_workflow.py`: `2ec532335011075f5db05302f6c0a3e2948cd3d93c7d85444343950eded711fa`
- `tests/test_nfl_starting_cohort.py`: `7199b39fd0e9634a508233475176ac8d18b169200aa771c6bda7525cfc084c37`
