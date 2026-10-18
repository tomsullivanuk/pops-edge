# P05: actual starting-nine WAR, six-arm protocol

October 18, 2026. Tom approved the lineup-WAR plan on October 17 CDT (“sounds like a plan”). Authority covers auditing retained data, documenting this bounded design and executing only if a fair test is supported. **Data gate is blocked; zero model fits.** This is not an execution freeze or a completed model campaign. Material data/definition/chronology changes must be discussed before substitution. Existing v2/v3.5, payroll, production and T−6h studies remain separate.

## Question and representations

Does information about the actual starting nine's all-around player quality replace or add to recent team results? Frozen preseason ratings are a reference arm, not the only representation. Use one documented family: **FanGraphs position-player WAR (fWAR)**, with projected WAR from the retained FanGraphs/Steamer-labelled batting exports and an explicitly compatible observed position-player WAR definition/version. Exclude pitching WAR, including for two-way players; existing starter features remain fixed. No undefined “WAR+,” alternative WAR provider or offense-only index substitution.

For each player i, season s and target t, projected rate P_i=600×projected WAR_i/projected PA_i. Observed rate O_i(t)=600×season-to-date position-player WAR_i(t)/season-to-date PA_i(t). Only information strictly available before the target game is admitted. To match the existing reference conservatively, use the latest admissible prior-New-York-calendar-day cutoff; no same-day performance, including doubleheader game one. Current-season observed accumulation resets each year; preseason source is fixed within that season.

Blend each player before aggregation: B_i(t)=(1−w_i)P_i+w_i O_i(t), with w_i=n_i/(n_i+k) and n_i=that player's strictly prior current-season PA. This is not a blend based on lineup-average PA. k is selected using training years only as below. The only added game input is the home-minus-away difference between **unweighted sums of the nine player rates**. No batting-order weighting: it would improperly weight the defense/baserunning content too. Sum-of-rates is a coarse all-around quality proxy, not literal lineup WAR accumulated in one day, projected team wins, or an assumption all nine will play a full game. Season WAR also reflects a player's past/projected position mix, which may differ from today's defensive assignments/DH role.

## Six challengers and matched baseline

| Representation | Replacement role | Addition role |
| --- | --- | --- |
| Frozen preseason P | R-P | A-P |
| Raw observed O | R-O | A-O |
| Player-level blend B | R-B | A-B |

Baseline: unchanged ten-input starter logistic. Replacement removes exactly x_win60,x_rd60,x_rd10 and their three progress interactions. Keep progress_centered, starter_kbb,starter_hr,starter_ip; add the one lineup-rate difference (five predictors plus intercept). Addition retains the full baseline and adds that one difference (eleven predictors plus intercept). Retain the same intercept/home-field specification and season-progress main effect in every arm, with coefficients refitted per arm. No extra home-field/park indicators or role-specific home advantage treatment.

All logistic fits use training-only StandardScaler, C=1 L2, fit_intercept=True, class_weight=None, lbfgs, tol=1e-8, max_iter=10000, one BLAS thread, existing reference conventions. Starter values and missing-history fallbacks are bit-identical across baseline/six arms; coefficients can refit as usual, not the input calculation. No TabPFN, feature sweep, added PA/exposure predictor, hand adjustment or calibration. PA controls the blend weight and denominator only. Replacement also removes information about bullpen quality embedded in recent team results; an adverse result cannot isolate the quality of lineup WAR alone. Starting nine excludes substitute/bullpen performance and models no playing-time substitutions.

## Missing and low-PA rules, fixed before any evaluation

- Valid negative projected/observed WAR is retained. For positive observed PA, raw O is exactly 600×WAR/PA: no pseudo-PA, shrinkage, clipping, minimum-PA exclusion or winsorization. Record small-sample extremes and predefined n<50,50–199,≥200 diagnostics; these do not change the raw arm or become new inputs.
- For **confirmed zero observed PA**, O is undefined: encode 0 as an explicit replacement-level fallback for raw arms, with separate coverage accounting. Do not assert that earned defensive WAR itself equals 0; zero batting PA can coexist with fielding value. Blend weight is 0, so B=P. This encoding is a declared modeling fallback, not an observed WAR estimate.
- Missing projected player or projected PA≤0 uses P=0, visibly counted as replacement-level fallback; unidentified source rows never join by name. No unknown ID, duplicate initial starter or unresolved game join is silently repaired or dropped. Exact actual-nine identity must be reconciled first.
- Missing dated WAR/PA record or a missing required fielding component is **not** evidence of zero PA or zero WAR. Block the data build until resolved. An absent provider row is not automatically a debut; debut/no-exposure status needs independent evidence. Do not route around the current dataset-wide observed-WAR gap using fallback values.
- Known zero/low exposure stays in every eligible game. Report all missing-projection/zero-PA counts by season, role and phase; same flags need not yield identical numeric fallbacks across different representations. No missingness flag is an extra learner input in this design.

## Population and data-admission gate

Retained actual nines/projected exports cover 2022–2025, not 2026. Use train 2022–2023/evaluate 2024 (4,852/2,426 games), then train 2022–2024/evaluate 2025 (7,278/2,426). Target 4,852 evaluation games; original common sportsbook cohort 2,291/2,425, total 4,716. No historical 13-game exclusion. Both roles/all representations/baseline must score identical eligible IDs; no complete-case projection filtering. Retain the reference's existing resumed-target exclusion. 2021 remains team warm-up only; the current-season WAR arm needs no invented 2021 player history. No third 2026 fold is silently claimed without its additional projection/lineup/WAR audit.

Before fitting, pin source bytes, player IDs, game/initial-nine reconciliation, release/revision metadata, dated WAR+PA cutoffs, component definitions and all missingness/phase counts. Baseline replay must match saved annual probabilities within1e−9. **Current data-admission failure:** observed dated WAR is not present in inspected inputs and compatible prior-game fielding/baserunning components have not been established; preseason release dates and WAR-definition revisions remain unverified. [Audit findings](FINDINGS.md) govern this stop.

Separate evidence levels explicitly:

1. True as-of: source publication/snapshot and all components demonstrably available before each game, with correct historical WAR definition/version.
2. Exploratory historical reconstruction: corrected historical inputs/revised definitions may describe only prior games but do not prove contemporaneous publication. A consistent component-level reconstruction and absence of future-season information still need demonstration and an explicit qualification/decision before use.
3. Current retrospective date filters that prorate final-season defense or use future-season normalization are not admitted as strictly prior-game observed WAR merely because the start/end dates look correct. Final-season WAR/PA scaled by elapsed PA is not an observed-to-date substitute.

Do not assert archived release dates or fielding availability from the presence of an old season selector. A provider-confirmed daily source or a valid component reconstruction could resolve the gap; this protocol does not claim no such dataset exists.

## Training-only blend selection

Fixed k grid={50,200,600} PA. For outer 2024, train 2022/validate 2023; for outer 2025 additionally train 2022–2023/validate 2024. For each k and inner fold, form player-level B using only prior observations and fit the two blend roles on earlier seasons. Select one shared k for the outer fold by the lowest equal-weight mean validation Brier across the two roles and inner years; exact ties use the listed grid order. Refit each outer blend role on all admitted outer training rows using that shared k. This keeps the blend representation identical between replacement/addition and avoids outer-label tuning. k values are modest fixed design choices, not asserted optimal. All inner candidate results must be retained. No additional grid after inspection.

## Primary measurement, practical gate and phases

Each arm's primary metric is equal-weight mean annual baseline-minus-arm Brier gain, positive favors the arm. Report all six, all years and pooled Brier/natural-log loss, with saved baseline and sportsbook opening consensus on exact paired populations. Six related hypotheses are development comparisons; do not select a favorable winner and treat its pointwise interval as fresh discovery.

Continuation information gate per arm, consistent with experiment04: mean annual Brier gain≥0.001, positive Brier gain in both years, pooled log loss no worse, paired 14-day 95% Brier-gain interval above 0, unchanged target coverage and no new hindsight dependence. Report pointwise intervals for all six and additionally Bonferroni 95% familywise percentile intervals (each two-sided tail 0.025/6, same paired draws); selection-aware intervals are a cautionary supplement, not an invented post-result gate. Any favorable arm remains exploratory; no automatic promotion or winner-only reporting.

Separate market-competitiveness gate per arm: lower pooled common-population Brier and log loss than sportsbook, with no worse annual Brier in either year. Opening consensus is the agreed historical proxy, not actual Kalshi or a synchronized executable price. Proper-score gains cannot establish net return after depth/fees/response delay.

Predefine **April–May versus remainder** using target New York date: April 1–May 31 inclusive versus all other regular-season dates (March is in remainder). Report per-year counts, baseline/arm proper scores and paired gains in both strata for every arm. These are diagnostics, not separate phase fits, threshold searches or permission to ignore unfavorable months.

Uncertainty: 5,000 paired moving-calendar-block replicates, seed 20261012, 14-day primary / 7-day sensitivity, no cross-year blocks, full first/last annual date grids including empty dates. Same sampled dates across all arms and both roles; stratum results apply fixed phase masks to the same calendar draws. Zero-sampled-stratum replicates, if any, remain visible with counts and declared handling before scoring. Equal-year primary averages annual paired losses; pooled results weight games separately. Calibration/reliability diagnostics never alter forecasts.

## Verification and stop boundary

Before execution freeze code/settings/data/cutoffs after the data gate passes. Independently reconstruct each player's WAR/PA and aggregation; assert same predictor rows/pitcher values/targets, train-only selection/scalers and no same/future-game dependence using mutation checks. Check unknown/debut/zero-PA paths, all six arms, saved coefficient/probability replay, scalar proper scores and paired block arithmetic. Arrange independent review of definitions, provenance, cohorts and all conclusions. Preserve failures; no automatic tuning or substitution.

Effort cap: five focused working days after data readiness; no waiting for the calendar to pass and no expensive computation required for these fixed logistics. Missing data, unverified chronology, incompatible WAR definitions, new credentials/payments or a materially revised experiment stops dependent execution and returns to Tom. Today's permitted work is audit/protocol only. No model, blend-weight fit, return study, provider dataset acquisition, deployment or merge has occurred.
