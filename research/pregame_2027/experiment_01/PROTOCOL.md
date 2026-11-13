# Experiment 01 execution protocol

Frozen October 12, 2026 before any challenger fitting or scoring. Tom authorized
the proposed single comparison, five focused working-day effort cap and
continuation gate in the dedicated 2027 pregame conversation. This grants offline
research execution, not alert implementation, wagers or production changes.

## Inputs and reference prerequisite

`input_manifest.json` pins 32 retained files by SHA-256, using source-relative
paths. Direct source hashes were checked against original package/dataset/archive
checksum lists. No download or new provider access is used. The manifest pins
features, labels, canonical outcomes, official schedules and retained reference
predictions. Raw/row-level provider-derived inputs and outputs stay private.

The ten-input reference has been refitted in the original chronological order:
2024 (2,426), 2025 (2,426), 2026 (2,428). Maximum absolute probability differences
against retained annual-reference predictions are exactly zero for all three.
This is a fit-and-score reproduction, not a full replay of raw player-feature
acquisition. Overlapping retained 2024/2025 feature versions agree within 1e-12.

## Rating equation and chronology

For each New York target date d in year Y, use all valid canonical outcomes with
season Y or Y−1 and available_day strictly before d. 2021 is team warm-up only.
No target or same-day game is admitted; resumed history enters after completion.
An invalid required historical outcome blocks the rating, rather than being
silently skipped. Current pinned outcomes contain no invalid records.

Minimize the **unnormalized sum**

`sum_g w_g * [RD_g − (r_home(g) − r_away(g) + h*H_g)]² + 20*sum_t r_t²`

subject to `sum_t r_t = 0`, where RD is home runs minus away runs,
`w_g = 2^(−calendar_age_days/60) * (1 if season Y else 0.5)`, and H is one
for a non-neutral designated home game and zero for a neutral venue. Solve the
equality-constrained normal equations, with the home-advantage term unpenalized.
No optimization of half-life, penalty or carryover is allowed. The target feature
is r_home−r_away; h is a nuisance adjustment in the rating fit, not an extra
target predictor. Logistic intercept models designated home advantage.

Archived schedules lack an explicit neutral-site flag. Before challenger scoring,
neutral venues are fixed to official IDs: 5445 Field of Dreams, 2735 Williamsport,
5340 Mexico City, 5381 London Stadium, 5150 Gocheok Sky Dome, 3949 Rickwood Field,
2397 Tokyo Dome, 6130 Bristol Motor Speedway. Other designated home venues retain
H=1, including relocated home grounds. This source-based classification is an
accepted limitation, not an outcome-optimized park feature. No park-effect fit.
Final official schedule states establish historical venue identity. The one
changed-venue resumed game (633224) moves between two non-neutral venues, so H
is unchanged; its later available_day controls admission.

Fixed 30 official franchise IDs constrain the rating dimension; franchise
identity is structural, not estimated from outcomes. With no historical games,
ratings are zero; the final logistic intercept uses training-only home advantage.
No target in this retained population is expected to require that fallback.

## Annual logistic fits

Train 2022–2023/evaluate 2024; train 2022–2024/evaluate 2025; train
2022–2025/evaluate 2026. Build every training row's rating from its own prior-day
history, exactly as for evaluation. Earlier completed evaluation games may update
later ratings; logistic coefficients remain fixed for that annual fold.

Challenger inputs: rating difference, centered season progress and retained
starter_kbb, starter_hr, starter_ip. Retain starter shrinkage/fallbacks unchanged.
Training-only StandardScaler; L2 logistic C=1, intercept, no class weights,
lbfgs, tol=1e-8, max_iter=10000, l1_ratio=0. No calibration transformation.
Require gradient max abs below 1e-6 and finite probabilities strictly between
zero and one. No probability clipping is needed; invalid probabilities fail.

Actual historical starters remain assumed identities, not authenticated pregame
announcements. Historical corrections and conservative same-day exclusion remain
accepted limitations. No markets, target performance, batting, bullpen, weather
or injuries enter the fit. All examined seasons are reused development.

## Measurements and stop/go

One paired forecast per retained eligible game; preserve the exact reference
population. Brier is mean (p−y)^2; log loss is mean natural-log Bernoulli loss.
Primary gain is the equal-weight mean of annual reference-minus-challenger Brier.
Report annual and pooled scores, diagnostic calibration intercept/slope and fixed
ten bins, target counts and rating-history/fallback coverage.

Continuation requires all: primary gain >=0.001; positive annual Brier point gain
in >=2 of 3 years; pooled challenger log loss <=reference; unchanged target
coverage; no new hindsight dependence. Failure preserves the existing reference
or pauses accuracy work, without launching a second variant. Success permits
consideration of forward paper testing; no Kalshi or return claim follows.

Paired moving-calendar-block percentile 95% intervals: 5,000 replicates, NumPy
default_rng seed 20261012, primary length 14 days, sensitivity 7 days. For each
replicate and year separately, draw contiguous non-circular blocks from its
first-to-last target-date calendar, include empty days, truncate concatenation to
that year's calendar length and divide sampled loss sums by sampled game counts.
Resampling never crosses annual boundaries. Average the three annual Brier gains
equally per replicate. Report annual Brier/log-loss intervals. Intervals condition
on the selected fitted forecasts; they do not account for model selection,
training uncertainty or reused-season exposure.

No sportsbook/Kalshi fit, selected-entry simulation or policy threshold is part
of this comparison. The existing review remains the secondary opening-consensus
context; changing it into a contemporaneous Kalshi comparator would be invalid.

## Verification and record

Before fitting, exercise future/same-day/target mutation independence, resumed
availability, invalid-history failure, shrinkage, sum-zero and neutral-site
handling on synthetic cases. Require exact retained reference replay. Store code
and protocol hashes, model/scaler coefficients, per-date source IDs and ratings,
predictions, aggregate scores and environment versions privately. Publish only
scrubbed code/specification, aggregate results and checksum provenance. Run exact
offline replay after the comparison. Record failures and the Owner decision in
the linked product record; leave PR #86 draft and unmerged.
