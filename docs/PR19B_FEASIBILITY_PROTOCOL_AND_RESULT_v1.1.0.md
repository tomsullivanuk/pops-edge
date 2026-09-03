# PR19B Development-Only Native MLB Feasibility Protocol and Result

**Result:** **NO BASIC SIGNAL**  
**Status:** one-look development-only feasibility evaluation complete  
**Decision authority:** Product Owner amendment dated 2026-09-01  
**Protocol identity:** `pr19b-feasibility-2026-v1`  
**Authority:** development-only Derived Analysis; no Probability Source or dataset admitted

## 1. Decision and relationship to PR19A

PR19B answers one bounded question: under a precommitted 2026 chronological
split, does the deliberately simple native MLB Model 0 show BASIC SIGNAL,
CREDIBLE SIGNAL, or NO BASIC SIGNAL?

This is a Product Owner amendment to the current entry posture, not a rewrite of
the historical [PR19A Model 0 protocol](PR19A_MODEL_0_PROTOCOL_v1.1.0.md). PR19A's
strict rights-cleared 2021–2025 point-in-time protocol remains the historical
formal-admission design. Its failed entry gate does not block this separate,
private, local, noncommercial feasibility look; conversely, feasibility cannot
satisfy formal admission, establish prospective validity, or activate a model.

The [PR19A rights decision](PR19A_RIGHTS_DECISION_v1.1.0.md) clean-room exclusion
continues unchanged. No code, data, model, asset, prose, schema, lock, or behavior
from `gmalbert/baseball-predictions` or another unlicensed implementation enters
this work.

## 2. Fixed feasibility contract

The estimand is the home team's probability of winning an eligible 2026 MLB
regular-season game. The nominal boundary is scheduled start minus six hours.
Because the retrospectively retrieved archive does not establish historical
outcome publication time, a prior decisive game can update team state only when
its scheduled start is at least eight hours before the target boundary. This is
an explicit development proxy, not a point-in-time Evidence claim.

The three features are exactly the PR19A home-minus-away differences:

1. `(same-season wins + 1) / (same-season games + 2)`;
2. `same-season run differential / (same-season games + 10)`; and
3. `(wins in the latest at most ten same-season games + 1) / (recent games + 2)`.

An equal scheduled-start tie that straddles the recent-ten cutoff fails closed.
The target outcome is physically separated from feature construction.

The fixed date splits, by scheduled date in `America/New_York`, are:

| Split | Dates | Authority |
|---|---|---|
| Training | 2026-03-25 through 2026-06-30 | scaler and primary estimator only |
| Validation | 2026-07-01 through 2026-07-31 | two-parameter sigmoid calibrator only |
| Test | 2026-08-01 through 2026-08-27 | one evaluation after the model bundle is sealed |

The primary estimator is one L2 logistic regression with `C = 1`, an unpenalized
intercept, training-only population-standard-deviation scaling, no class weights,
and no search. The implementation pins a deterministic damped Newton binary64
solver with tolerance `1e-12` and 200 iterations. The validation calibrator is
the fixed unpenalized two-parameter sigmoid. Failure to converge is a terminal
study result, not permission to change the protocol.

The test baselines are constant `p = 0.5` and the smoothed training home-win rate
`(training home wins + 1) / (training games + 2)`. Reported metrics are Brier,
extended-real Log Loss, the fixed ten-bin Calibration table, WACE, Coverage, and
10,000-resample deterministic paired-bootstrap 95% percentile intervals for
per-game Brier improvement against each baseline.

Classification is mechanical:

- **BASIC SIGNAL:** model Brier is strictly lower than both baselines and model
  Log Loss is no greater than both baselines.
- **CREDIBLE SIGNAL:** BASIC SIGNAL holds and both paired-bootstrap lower bounds
  are strictly greater than zero.
- **NO BASIC SIGNAL:** BASIC SIGNAL does not hold.

WACE, Coverage, and subgroups cannot override this classifier. No alternate
model, feature, split, threshold, refit, repair, or second test look is permitted.

## 3. Market independence and source boundary

The source allowlist contains only immutable existing archive pages whose
provider is `mlb-stats-api` and purpose is `schedule`. The adapter extracts only
canonical game/team identity, schedule, game type, status, score, and winner
facts. It verifies the content-addressed raw and normalized bytes and scans both
transitive source fields and derived rows for prohibited market terms.

Kalshi availability, mapping, ticker, candle, price, probability, liquidity,
volume, payout, and outcome material cannot affect population membership,
missingness, features, labels, preprocessing, fitting, calibration, metrics, or
classification. The broader archive remains untouched.

## 4. Pre-evaluation seal

Authoritative repository base:
`29aebcc3ec8e2302014f54d8e842341d8997be82`  
Authoritative tree:
`22988010fc53f840185019c84f055761178f452a`

- protocol digest: `d00d3c6ca9166e06d0ec0b65b283123c73687d758540309057435f6c1c313b58`;
- dataset digest: `50f9d5265a29fba359a0fb976e239b98b09da62e0a5865ecd153b3832f669e58`;
- sealed test-row identity/label digest:
  `87123bb82eea9e9d7d32c47fdcdae48f4d3665797f3e2c44816f2f99410acf3e`.

The protocol manifest was written at sequence 1. The test-row identity/label
digest was frozen without a label aggregate at sequence 2. No fit, test score,
or test aggregate existed at that seal.

## 5. Frozen population and Coverage

The market-independent schedule universe contains 2,016 games. It reconciles to
1,987 measured feature/label rows: 1,270 training, 361 validation, and 356 sealed
test rows. All 30 franchises appear in each split.

Visible exclusions are:

| Disposition | Count |
|---|---:|
| Ambiguous identity | 18 |
| Ambiguous schedule evolution | 6 |
| Postponed | 4 |
| Unsupported game type | 1 |

The complete game-level reconciliation is retained locally in the sealed
Coverage artifact. No excluded game disappears from the schedule universe.

## 6. Result

**NO BASIC SIGNAL.** The fixed classifier fails because the model did not beat
the smoothed training-home-rate baseline on Brier Score or Log Loss. No repair,
refit, alternative model, or second test evaluation was performed.

The test population is 356 games. Baseline probabilities are `0.5` and
`0.52594339622641506` for the smoothed training home-win rate.

| Source | Brier Score | Log Loss | WACE |
|---|---:|---:|---:|
| Model 0 | 0.24824815789596828011462149504304157584269662921348 | 0.68968363791382095919585282599548251917166735200278 | 0.057311410986174247078651685393258426966292134831459 |
| Constant 0.5 | 0.25 | 0.69314718055994530941723212145817656807550013436 | 0.05898876404494382022471910112359550561797752808989 |
| Smoothed training home rate | 0.24761232205071179942234231063075865617977528089888 | 0.68836813757510797513332399648259730524279575158278 | 0.03304536781852876022471910112359550561797752808989 |

Paired per-game Brier improvement is baseline Brier minus Model 0 Brier:

| Baseline | Mean improvement | Deterministic 95% paired-bootstrap interval |
|---|---:|---:|
| Constant 0.5 | 0.001751842104031719885378504954 | [-0.0024496680362020156717858296402501474719101123595505, 0.0059372367631287193643212803312277738764044943820225] |
| Smoothed training home rate | -0.0006358358452564806922791844174 | [-0.0048994793157810605449766702695056109550561797752809, 0.0035309777058708467688399581959112640449438202247191] |

The complete fixed ten-bin Calibration tables remain in the sealed result
artifact. Model 0 populated bins 3 through 6; no omitted or post hoc filtered
test subset was substituted.

- model-bundle digest:
  `a2d74f8dfd01055f49fb8b6a659c5529aba7c9d51333fa12c6c4cdaff2e05672`;
- prediction digest:
  `dc4379a64edc60b8a8ccfe8e82d021e1ceba942ead7ccac46ba9f564fb8b971b`;
- sealed-test evaluations: exactly one.

## 7. Limitations and authority

This study uses one partial 2026 season, material retrieved retrospectively,
uncertain source rights for formal model training, an eight-hour proxy rather
than proven publication chronology, and one deliberately simple team-level
model. It makes no claim of prospective performance, stationarity, market
advantage, supplier replacement, production fitness, or rights admission.

Every output is private development-only Derived Analysis. Nothing here is MLB
Evidence, an admitted dataset, an admitted Probability Source, Forecast
Observation Evidence, Forecast Intelligence authority, a Market Edge, Policy,
Governance, wagering authority, deployment authority, or production behavior.
Future rights-cleared point-in-time admission and prospective collection require
separate Product Owner decisions and protocols.
