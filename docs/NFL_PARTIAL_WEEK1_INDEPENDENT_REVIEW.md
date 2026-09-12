# Partial Week 1 starting cohort — independent review

Decision: **Changes required; one P1 blocker.** Approval is limited to the seven-file candidate below, parent `9b8c63dcb86f20eceaa5e20ce2842c97ab10e9e4`. Current authoritative main was verified by the coordinating agent at `2d59b73cad06d979ddd9a446c544fc981b55544b`; its complete AGENTS.md was read for this review. Main's intervening changes are unrelated MLB files.

## Governing scope

Reviewed the original weekly contract-value protocol, the owner-approved partial Week 1 addendum, implementation review and handoff, the complete implementation diff, underlying schedule/outcome validation, and cohort/service/workflow tests. Scope is the fixed 14 unstarted games excluding only NE–SEA and SF–LAR, with actual acquisition chronology, common included-game cutoff, immutable membership, honest 14/16 coverage, fee-free scoring and unchanged Week 2+ behavior. Manual collection, visible missing captures and the deferred results tab remain accepted limitations.

## Blocking finding

**P1 — Already-started game admitted when an in-progress summary lacks startTime.** In `nfl_performance.py`, `starting_members` accepts every included game whose decoded outcome is `awaiting-outcome` and which has no recorded actual start at/before activation. The existing `sources.outcomes` decoder maps a validated `summary.phase=IN_PROGRESS`, `quarter=Q1` to `awaiting-outcome` if `startTime` is absent. If the outer schedule remains SCHEDULED with a future time, initialization therefore succeeds with a third game already in progress.

Independent disposable probe: amended the third synthetic official game with matching game/team IDs, `phase=IN_PROGRESS`, `quarter=Q1`, and no `startTime`, leaving its scheduled kickoff after activation. Initialization succeeded; report returned eligible population 14 and that game's outcome as awaiting-outcome with start null. This is a concrete mismatch between explicit source evidence and enrollment authority, not a request for automatic recovery or more collection availability.

The approved must-hold requires rejection if an additional game has started. Admitting it could capture prices after play has begun while labeling the sample as collected before all included games. Missing precise start time does not negate the explicit in-progress phase. A manual procedure is insufficient because the authorized commissioning command itself grants invalid cohort authority without a visible warning.

Required bounded correction: retain/examine validated game phase at commissioning and reject an included game with evidence of play or unresolved start state even without a timestamp. Do not broaden ordinary outcome scoring semantics unnecessarily. Add a regression for in-progress summary without startTime, and ensure a saved activation is revalidated by the same rule. Re-run the focused tests and request one amendment review before integration.

## Validation and other observations

- Independently ran 40 cohort, service and workflow tests: all passed.
- Independently reproduced the missing-startTime admission above using disposable fixture data; no provider access.
- Inspected source/hash replay, fixed membership exclusion before quote selection/scoring, initial schedule cutoff seeding, missing-member cutoff rejection and normal noncohort paths.
- Existing tests exercise two intentional exclusions, observed actual starts, unknown kickoff, schedule corruption on open/replay, common-cutoff closure, partial coverage/scoring, and unchanged full-week behavior.
- No additional blocking findings identified in this bounded review. No full regression run or live provider/browser validation performed independently.

## State and next gate

No implementation files, branches, production data, activation, live service or GitHub state were changed. Only disposable tests and this review artifact were written. Conditional integration authorization is not satisfied while the P1 remains. Next gate is the bounded correction and amendment review; this is not approval to push, merge or deploy the current candidate.

## Exact reviewed SHA-256 fingerprints

| File | SHA-256 |
|---|---|
| nfl_performance.py | 5c0d4961602c77e3a48eec2621c1a271ccb7f2ddd790173a222d6ff2398b8619 |
| nfl_refresh.py | 0950fe25667e78e33cbc3b2c04471e86c595f5842d15c9275d83b457711ef4ed |
| operate_nfl_performance.py | de2767d2d82b50180911403fa21f87baa5b951cb3d1e8a2ac03cd58243998564 |
| tests/test_nfl_starting_cohort.py | cdd5d7e1db980c8a8f19f4f0b47af80dbae4f6336c7aba86338703e6df17c783 |
| docs/NFL_WEEK1_STARTING_COHORT.md | e499f564be3b43aabdfc35d95d4324d7ba756dc364d89d3d4d319d87016cd259 |
| docs/NFL_MODEL_PERFORMANCE_IMPLEMENTATION.md | 2bfbe03532b0852a3a5d83c6ad8801374e92addfdaac2271c8aa20e653e48b9b |
| docs/NFL_REFRESH_GUIDE.md | 76fa3e7d4a39b3d9d68964864b3b02730407ad237d275907163fea399bbdc6b3 |
