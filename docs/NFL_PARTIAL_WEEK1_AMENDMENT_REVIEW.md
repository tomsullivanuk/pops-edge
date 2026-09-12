# Partial Week 1 starting cohort — independent amendment review

Decision: **Approved. No blocking findings remain.** This supersedes the rejection of the original candidate in NFL_PARTIAL_WEEK1_INDEPENDENT_REVIEW.md for the exact seven-file amended scope fingerprinted below. Parent remains `9b8c63dcb86f20eceaa5e20ce2842c97ab10e9e4`; authoritative main reviewed is `2d59b73cad06d979ddd9a446c544fc981b55544b`.

## Scope and authority

Applied the complete current-main AGENTS.md, original weekly contract-value protocol, owner-approved Week 1 addendum, implementation handoff and first independent review. Approval covers the fixed 14-game prospective starting cohort, two visible intentional exclusions, preserved chronology and raw source evidence, common included-game cutoff, fee-free scoring, explicit commissioning and unchanged normal behavior from Week 2 onward. Manual collection, visibly incomplete captures and the deferred results tab remain accepted limits.

## Amendment acceptance

The original P1 is corrected. Cohort membership now examines original source summary phase and quarter in addition to validated outcome/start evidence. An included game with a present phase or quarter is rejected before activation is written, including IN_PROGRESS without startTime. The same membership function is called when opening an initialized store and during report replay, so validation is not limited to first creation.

This is a conservative bounded source rule. If the provider begins supplying an explicit pregame phase, commissioning will visibly reject it until that marker receives support. That is an acceptable fail-closed collection limitation, not silent scientific admission or a requirement for generalized phase mapping.

## Independent validation

- 41 cohort, performance-service and workflow tests passed independently.
- Original missing-startTime reproduction now raises ValueError and leaves no activation.json.
- Built a disposable legacy-invalid activation by bypassing only membership validation during fixture setup; both reopening and report generation then rejected it under the amended validator.
- Inspected the amended diff and regression test. No unrelated scope expansion or scoring changes found.
- Original bounded review inspected raw source replay, common-cutoff and fixed-member behavior, coverage and normal-mode compatibility. Those findings carry forward; no additional blocker identified.

No independent full-suite or live provider/browser validation was performed. The coordinating agent will validate the integrated current-main tree before completing deployment. Approval does not assert that real collection has begun or that all 14 markets will be available.

## External state and next gate

No implementation, branch, GitHub, production data, activation or live service was changed by this review. Only disposable local fixtures and this report were written. The owner's conditional integration authorization is now satisfied: proceed with commit, push, PR creation, merge and deployment after ordinary integration checks. Deployment remains distinct from actual commissioning and provider capture under their applicable authorization.

## Exact approved SHA-256 fingerprints

| File | SHA-256 |
|---|---|
| nfl_performance.py | c2b46b70d04b354358196245796df2a0561103688b28d07418cfd87ee6192fe7 |
| nfl_refresh.py | 0950fe25667e78e33cbc3b2c04471e86c595f5842d15c9275d83b457711ef4ed |
| operate_nfl_performance.py | de2767d2d82b50180911403fa21f87baa5b951cb3d1e8a2ac03cd58243998564 |
| tests/test_nfl_starting_cohort.py | 97c13ca354791333b566cc648c746c467ed2c8be21afff033df67eb61d0bfccb |
| docs/NFL_WEEK1_STARTING_COHORT.md | e499f564be3b43aabdfc35d95d4324d7ba756dc364d89d3d4d319d87016cd259 |
| docs/NFL_MODEL_PERFORMANCE_IMPLEMENTATION.md | 2bfbe03532b0852a3a5d83c6ad8801374e92addfdaac2271c8aa20e653e48b9b |
| docs/NFL_REFRESH_GUIDE.md | 76fa3e7d4a39b3d9d68964864b3b02730407ad237d275907163fea399bbdc6b3 |
