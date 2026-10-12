# Experiment 03: conditional starter–batter PA probabilities

October 12, 2026. **Approved by Tom for bounded offline acquisition, fitting and verification.**
Read [sample readiness results](../component_readiness/RESULTS.md) and
[feasibility decision](../../../docs/MLB_2027_COMPONENT_FEASIBILITY.md).
Prior failures remain closed. No TabPFN/checkpoint dependency.

## Hypothesis and scope

Joint, partially pooled individual pitcher/batter effects may forecast K/walk
outcomes better than a strong rolling-rate matchup baseline. This tests an
intermediate conditional component, not final-score or winner superiority.
One baseline, one challenger; no pitch telemetry, pair memorization, deep network,
simulation, market inputs or feature-family expansion.

Use Retrosheet 2022–2025 regular-season parsed PA and minimum same-source
metadata. Existing 2023 acquisition is retained; three additional seasons require
explicit approval with execution. Agreed bound: 100 MB additional compressed,
1 GB total extracted and five focused working days for acquisition, fitting and
verification. Stop if bounds or validation fail. Pin every file before fitting.
The information used here was obtained free of charge from and is copyrighted
by Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd.,
Newark, DE 19711.

## Population, target and chronology

Label every valid completed regular-season PA as K, unintentional BB, or other.
Exclude intentional walks by the same predeclared rule from targets and histories;
count all such exclusions. K with safe reach is K, not other. Validate one PA
outcome, correct subsets, stable IDs, hands and starter roles for the full seasons.
Cold/new players remain included with declared fallback; do not replace missing
records with guessed identities. Blocking count/identity/date discrepancies stop
the fit and return a report rather than silently filtering favorable games.

Learn from all valid pitching-role PA; score the primary target on PA against
the recorded initial starter. Show all-role scores as diagnostics only. Pitcher
and batter are conditioning identities; actual matchup occurrence, substitutions,
starter survival and exposure are not predicted or used as features. This is not
an executable pregame totals forecast. Initial-lineup-only starter PA is a fixed
diagnostic; no promotion based on a favorable subset.

For target game original New York date D, admit only histories whose complete-game
availability date is strictly before D. Availability is max(original date,
resumption date, latest documented play date). Freeze matchup features at that
original pregame day for the entire game, including resumed portions. Use no
current-game pitch, score, count, inning, actual duration, outcome or same-day
history. Actual identity/platoon conditioning retains the offline assumption;
historical announcement timing is unknown.

Train through 2023/evaluate 2024, then through 2024/evaluate 2025. All are reused
development. Fitted coefficients remain annual; previously completed games update
history. Inner validation: train 2022/evaluate 2023 for the first outer fit; for
the second, also train through 2023/evaluate 2024, selecting by pooled inner log
loss. Outer labels never select settings. No untouched-holdout claim.

## Shared feature construction and baseline

Use all-role PA histories from trailing 365 calendar days, half-life 180 days.
For class c in {K, BB, other}, compute decayed counts n_c and N for each pitcher
and batter, and equally lagged league class rates q_c. Shrink each player rate:
`r_c = (n_c + 200*q_c)/(N + 200)`.
League q is the normalized three-class counts with symmetric one-count smoothing;
at no league history use [1/3,1/3,1/3]. A player's absent history gives q.

Four continuous predictors: pitcher and batter log(K/other), log(BB/other), each
minus its league log ratio. Training-only scaling; zero variance columns have
scale one. Hand-pair categories use recorded L/R/B batter hand and L/R pitcher
hand, with R/R as reference (five indicator columns). No switch-hitter rule
inferred from names or current metadata. Unknown hand is a blocking source issue
pending explicit resolution, not a silently assigned R/R.

Baseline multinomial logistic, other as reference:
`eta_c = intercept_c + beta_c * x`; `p = softmax(eta_K,eta_BB,0)`.
Minimize summed PA negative log likelihood plus `gamma/2 * sum(beta^2)`;
intercepts unpenalized. Select gamma only from [0.1,1,10] by inner log loss;
ties within 1e-12 choose larger gamma. This is the strong continuation comparator.
Also report the lagged league-only forecast as a diagnostic.

## Single challenger

Keep baseline inputs and add individual pitcher/batter residual effects:
`eta_c = intercept_c + beta_c*x + a[pitcher,c] + b[batter,c]`.
Add fixed `100/2 * (sum(a^2)+sum(b^2))` to the same objective. This is Gaussian
partial pooling with a fixed strength, not an extra hyperparameter search. Use
the same gamma grid/inner chronology separately for the challenger. New IDs have
zero residual effect, preserving baseline cold-start information. Joint softmax
ensures valid three-class probabilities. No pitcher–batter pair interaction table.

Use deterministic zero initialization, float64 CPU computation, analytic sparse
gradient, L-BFGS with max 1,000 iterations and infinity-gradient tolerance 1e-6.
Numerical probabilities use stable log-sum-exp. Require finite converged fits,
gradient check on a synthetic fixture and repeatable saved forecasts; inability
to converge stops the specification rather than switching optimizers/families.
Pin software and finalized implementation before opening outer evaluation scores.

## Measurement and proposed value gate

Primary: per-PA multiclass log loss on identical starter PA each year. Report
multiclass Brier as sum across three classes (no extra 1/3 scaling), class
calibration, all exclusions, player cold starts and lineup/substitute coverage.
Show pooled PA-weighted scores and equal-game sensitivity. Primary continuation
quantity is the equal average of the two annual relative log-loss gains:
`mean((LL_baseline_y - LL_challenger_y)/LL_baseline_y)`.

Agreed gate: gain at least 0.005 (0.5%), lower log loss in both years, no worse
average annual Brier, and primary gain's paired 14-calendar-day 95% interval above
zero. Use 5,000 moving calendar-block replicates, seed 20261012; keep all PA
within game/day together, resample within each year, include empty days and show
7-day sensitivity. Use original game date for block assignment. No post-result
calibration, phase selection, event filtering or threshold tuning. The gate is
a practical component threshold, not an implied wagering return requirement.

Validate full-source game/team/pitcher count reconciliation, PA-key uniqueness
with file hash plus row ordinal, suspended dates and chronology. Same/future-game
mutation must leave prior features unchanged; cold-ID fallback and saved-model
replay must pass. Publish scrubbed aggregates, code, settings and failures; keep
raw player records, per-PA predictions and fitted contexts private.

## Decision after results

Failing the gate ends this specification without automatic tuning or more data.
Passing permits discussion of integration only. Three categories cannot model
contact run values, starter duration, individual reliever selection or baserunning.
A separate richer PA/run model would need those pieces before generating winner
probabilities. That later model must beat the unchanged native reference and
sportsbook proxy on paired proper scores and undergo fresh validation; component
scores are not a substitute. No Kalshi opportunity, net-return or profit claim.

Approval of this protocol would cover only bounded offline acquisition/fitting
and draft documentation, not merge, deployment, collectors, pins, T−6h changes,
credentials, purchases or wagers. The 3.5 inquiry remains unrelated and pending.


## Pre-fit implementation clarifications

History decay and the 365-day window use complete-game availability date, consistently with the conservative delayed release. Continuous columns alone use training-only standardization; handedness indicators keep their category units. Full audits found three zero-completed-PA starters and nine initial batters replaced before their first PA. Pitching starting-role records agree with team starting-fielding metadata; replaced initial batters have no PA in those games. Retain original identities, zero exposure and substitutions rather than substitute first-completed-PA identities. These are reconciled cases, not excluded games. Inner selection uses all-role PA log loss as specified; primary outer continuation remains starter-only.
