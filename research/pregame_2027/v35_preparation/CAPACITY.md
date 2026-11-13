# v3.5 core: acceptance verified and local capacity passed

October 16, 2026. This follow-up supersedes the initial pending-access status in [preparation](PLAN.md) and its historical readiness receipt. After Tom personally completed the review, Safari's official `platform.priorlabs.ai/account/licenses` page visibly showed **TabPFN-3.5 — Accepted**. No additional acceptance, eligibility representation, account creation or credential action was performed by the agent. This verifies displayed acceptance, not a legal-status determination or production-use permission.

## Acquisition

Used the [officially documented manual checkpoint route](https://github.com/PriorLabs/TabPFN#readme) at the pinned Hugging Face revision. No token, new grant or persistent credential was needed or configured. [Acquisition receipt](acquisition.json): default core file 876,027,932 bytes, actual SHA-256 `ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3`, matching the advertised LFS checksum. Weights remain private outside Git. V2 files and its baseline results remain unchanged.

## Synthetic checks

Same installed isolated environment; explicit local V3_5 checkpoint, four intrinsic estimators, float32 Metal, cached context, seed 20261012, one preprocessing worker, 128 prediction rows. Native checkpoint temperature resolved to **1.0**; do not carry v2's 0.9 temperature into this comparison silently. MPS fraction fixed at 0.5; process deadline 1,800 seconds. Model processes forbid network/DNS. No baseball inputs or evaluation labels were read.

| Check | 128 training rows | 9,704 training rows |
| --- | ---: | ---: |
| Features / prediction rows | 10 / 128 | 10 / 128 |
| Fit/context seconds | 2.605 | 25.176 |
| First prediction seconds | 0.411 | 0.543 |
| Repeat prediction maximum difference | 0 | 0 |
| Later-test-row mutation effect on earlier predictions | 0 | 0 |
| Batch versus isolated maximum difference | 1.19e-7 | 5.36e-7 |
| Driver memory after checks, decimal GB | 0.963 | 4.512 |
| Status | Pass | Pass |

All probabilities finite and strictly inside (0,1); replay/mutation/batch differences below the prior 1e-6 device tolerance. No network attempts occurred during model use. Driver readings are after-check allocation, **not measured peak memory**. These synthetic results establish practical capacity for the largest planned context under this configuration, not full-season runtime, baseball accuracy or market edge. [Smoke receipt](capacity_mps_128.json), [full-context receipt](capacity_mps_9704.json), [exact executed synthetic script](capacity.py).

## Next step

Freeze a v3.5-specific execution protocol/settings/runner and exact source/configuration hashes before any baseball evaluation, using the existing ten inputs, three annual folds, saved v2/CatBoost comparisons, original sportsbook cohort and unchanged continuation gate from [the prepared scope](PLAN.md). Preserve the four-estimator configuration and resolved native temperature 1.0. No new checkpoint family, payroll/WAR inputs, tuning, calibration, paid compute or uploads. No baseball evaluation has run in this follow-up. Documentation is prepared locally; no commit, push, merge or production change occurred.
