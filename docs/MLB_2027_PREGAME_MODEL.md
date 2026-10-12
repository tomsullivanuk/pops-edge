# 2027 pregame model: experiment 01 proposal

October 12, 2026. Status: **approved offline comparison completed October 12; continuation gate failed**.
Repository inspected at main `9564b12dcd80f0b3347b4860b95984763f2e3061`.

## Goal and authority

Agreed direction: an in-house regular-season baseball winner model, eventually identifying selective, understandable opportunities at Kalshi executable prices for small manual wagers. Paper alerts come first. Tom approved the proposed single offline comparison, five focused working-day effort cap and continuation gate after discussion. No trading, purchases, new credentials, production changes or merge are authorized. No release is assigned.

Existing postseason collection, its T−6h protocol, regular-season collection and historical evidence remain intact. T−6h does not constrain this new product. Assume services will provide lineups before first pitch while observed timing is investigated separately; the already-running bounded postseason observer is not duplicated. Its findings cannot establish regular-season availability by themselves.

## Evidence and reason for this experiment

The October 9 independent model review and October 11 pregame design addendum were read from their original local artifacts. They report native starter 2026 Brier 0.246136 versus sportsbook **opening** consensus 0.243581 on 2,428 paired games, with native-minus-consensus difference +0.002555 and retained 14-day 95% interval [+0.000467,+0.004207]. This is not a Kalshi comparison. Actual-nine additions did not generalize in 2025; calibration, regularization and the tested market overlay did not establish improvement. These results are inherited verified evidence, not a new computation in this task.

2024, 2025 and 2026 have all informed prior development and are reused development seasons. Chronological reconstruction does not make them fresh holdouts. We will not repeat the actual-nine substitution, generic feature sweep or market overlay. The hypothesis is that opponent-adjusted, dynamically weighted team strength is a better representation than the existing short-window summaries. Late-season errors motivate testing it but do not prove their cause.

Source provenance: independent review sections “What is actually built”, “Verified performance”, “Validity limits”, and “Bounded next program”; addendum sections “Existing model verdict”, “Data feasibility” and “Achievable gates”. Underlying retained artifacts include `native_starter_2026-09-28/PROTOCOL.md`, `native_2026_evaluation_2026-09-30/RESULTS_REPORT.md`, `native_market_diagnostic_2026-10-01/RESULTS_REPORT.md` and the frozen 2025 actual-nine comparison. Public record contains aggregate findings and lineage names only; licensed raw provider payloads stay private.

## One concrete comparison

Compare the retained ten-input starter logistic reference with **one** challenger. Replace its six rolling team-strength/season-interaction inputs with one home-minus-away opponent-adjusted run rating. Retain the three starter inputs and centered season progress; fit the logistic intercept/home advantage using training data. Retain L2 C=1, training-only scaling, no class weights and the reference probability/fallback conventions. No post-fit calibration, market inputs, added batting, bullpen, weather or injury features.

For each target date, use only games admitted by the reference prior-New-York-calendar-day rule from the current and immediately preceding season. Fit weighted ridge least squares to home-minus-away runs: home advantage plus home team rating minus away team rating. Constrain team ratings to sum zero. Weight by a fixed 60-day half-life measured in calendar days, with an additional 0.5 weight for previous-season games. Penalize each team rating by a fixed 20 unit-weight-game ridge penalty toward league average; leave home advantage unpenalized. Neutral-site games have zero home-advantage indicator. No available history yields zero team ratings and the training-only home-advantage fallback. Preserve resumed-game handling and target eligibility from the reference. These constants are proposed design choices, not claimed optimal settings. Do not optimize them after seeing fold results.

Inputs: retained official schedule/outcome IDs and lagged runs, retained starter identities and pitcher histories. Preserve reference starter shrinkage and missing-history fallbacks. Audit identity reconciliation, resumed games and source chronology before fitting. Historical actual starter identities remain an explicit assumed-identity limitation; target-game performances never enter predictors. Confirmed batting lineups are a proposed product-readiness condition, not an extra feature in this first test.

Reproduce reference annual fits and scores first; unexplained disagreement stops the comparison. Train through 2023 and evaluate 2024, through 2024/evaluate 2025, through 2025/evaluate 2026. Generate training ratings with the same rolling rule as evaluation, never using the full training season to construct an earlier game's rating. Earlier completed evaluation-season games may update later features; annual logistic coefficients stay fixed. Use 2021 team warm-up as in the reference. No random split, new search or outcome-driven exclusions.

Before execution, pin input manifests/checksums, exact equations/penalty normalization, fold populations, reference artifacts, bootstrap seed/resample count and code version in an execution protocol. This freezes implementation details without expanding the one-challenger scope. Proposed budget: at most five focused working days, existing archives only; stop and report any source blocker rather than buying data or inventing history.

## Evaluation and continuation

Primary: equal-weight mean of the three annual paired Brier gains (reference minus challenger). Also report pooled and annual Brier, pooled natural-log loss, calibration intercept/slope, full counts and fallback coverage. Use 14-day paired moving-calendar-block 95% intervals with 7-day sensitivity, annual boundaries preserved; these are conditional descriptive uncertainty, not correction for reused holdouts or model selection.

Proposed continuation gate: average annual Brier gain at least 0.001; positive Brier point gain in at least two of three years; pooled log loss no worse; unchanged target coverage and no new hindsight dependence. Missing/invalid inputs remain visible. Report every fold and failure. Passing earns consideration for a frozen forward paper test, not superiority to Kalshi or a betting policy. Failure means retain the reference or pause this accuracy track; no automatic second challenger.

## Decision time and later Kalshi test

Propose T−90, T−60 and T−30 checks against the latest admitted official start, using the first check with both confirmed lineups and identified starters. No qualifying check means no paper alert. One candidate per game; pitcher/lineup or start-status changes invalidate it. These times remain a proposal, to agree before a paper implementation; they are not an offline timestamp claim.

For a later separately approved 2027 trial, save model and Kalshi midpoint forecasts at the same qualifying check and compare Brier/log loss on identical games, with an independent official opportunity denominator and visible missed inputs/markets. Historical final lineups lack validated publication times paired with buyable Kalshi depth in our acquired data. This limits retrospective operational claims, not offline modeling or the possible existence of other datasets.

Separately score selected paper entries at depth-adjusted executable asks, applicable contemporaneous fees and a frozen human-response delay. A proposed pilot delay is 60 seconds, to be checked against actual manual latency before confirmation. Missing delayed depth or a violated limit cap means unfilled, not an immediate synthetic fill. Paper size, selection threshold, forecast-error allowance, price cap and practical return/risk criteria must be fixed before that trial; they are not authorized here.

For quantity N, probability p and total acquisition cost C, net expected profit is Np−C−fees; expected return divides this by C+fees. Probability minus per-contract ask is a percentage-point difference, not net return. Model uncertainty may erase that difference; a sensitivity allowance is not a validated per-game confidence interval. No edge or profitability guarantee. New matched observations are needed before considering manual-wager recommendations; postseason cannot replace regular-season confirmation.

## Decision record

- Agreed: regular-season focus, paper first, existing studies preserved, GitHub documentation, lineup availability working assumption.
- Proposed: the single rating challenger, five-day cap, development gate and three-check product window.
- Authorized now: the one offline comparison and documentation updates in draft PR #86.
- Owner decision October 12: “Yes, let’s move forward as you propose.” This authorizes the single comparison, cap and gate; paper-alert implementation, collection and wagering remain separate.
- Results October 12: single challenger completed and failed the gate. Average annual Brier gain 0.000334 versus required 0.001; improved 2025/2026, worsened 2024. Existing reference retained; no automatic next model experiment. Timing observer findings remain separate.

## Authorized finite availability observation — separate work

The coordinating parent designated task `01a12310-a072-73b1-8a79-0812ada4e0ed` as the single runner and authorized launch on October 12. This task has read its observation specification and code, but does not launch or duplicate it. The parent reports one active finite process, session 77609, with first successful HTTP 200 polls October 12 13:00:56–57 UTC. Both scheduled starts remained 21:00/00:00 UTC, both probable pitchers were present and batting orders absent. Launch receipt is retained privately as `LINEUP_RUN_START_RECEIPT.json`; final availability results remain pending.

The observer reports successful official MLB live-feed baseline reads shortly after 12:55 UTC: game 849812 Dodgers at Brewers scheduled 21:00 UTC and game 849820 Guardians at Rays scheduled October 13 00:00 UTC. Both had probable pitchers and empty batting orders. This is an aggregate report from saved live pregame snapshots, not our independent live recheck or evidence of confirmed starters.

Finite scope: 15-minute polling more than three hours before start, five-minute polling within three hours; maximum 240 requests; hard stop October 13 00:30 UTC; each game stops at first observed live/final/postponed/canceled state. Record complete unique nine-player orders with agreeing slot codes, first observed availability and previous absence interval, left censoring, order/probable-pitcher changes, schedule revisions and latency/missing intervals. Exact publication and explicit confirmation times remain unknown when not supplied. BDL trial access is unavailable to that runner; no purchases or credential changes are authorized.

### Interim observation — October 12, 18:05 UTC

The coordinating parent supplied this verified checkpoint from the single observer's MLB feed polls for game `849812` (Milwaukee–Los Angeles), scheduled for 21:00 UTC:

| Batting order | Previous observed absence | First observed complete order | Time before scheduled start |
| --- | --- | --- | --- |
| Milwaukee | 17:05:28 UTC | 17:20:28 UTC | 3 hours 40 minutes |
| Los Angeles | 17:20:28 UTC | 17:35:28 UTC | 3 hours 25 minutes |

Both orders remained complete at 18:05:29 UTC. These are polling bounds on feed availability, not exact announcement times or evidence of an explicit confirmation field. Probable pitchers were present; their explicit confirmation remains unknown. This supports the working assumption of pregame lineup availability for one observed postseason game only. It does not establish regular-season reliability, availability through our eventual provider, or paired executable Kalshi depth.

Guardians–Rays orders remained absent at this checkpoint. The parent reported the observer alive with 38 requests and zero HTTP failures, a recorded 13:00:57–13:50:24 UTC observation gap, and five-minute cadence for the first game. The finite run is still underway; its final record will supersede this checkpoint. No additional observer, training run or product-timing change follows from this observation.

Raw responses stay private. Finite results will be added as aggregate findings with truthful observation times and limitations. Two playoff games cannot establish 2027 regular-season completeness. Source-history linkage: [MLB source research](MLB_SOURCE_RESEARCH_v1.1.0.md).

## Approved execution record — October 12

The [frozen protocol](../research/pregame_2027/experiment_01/PROTOCOL.md), [source manifest](../research/pregame_2027/experiment_01/input_manifest.json) and [offline runner](../research/pregame_2027/experiment_01/run.py) make the approved comparison reproducible. The earlier proposal text records the decision presented to Tom; this dated authorization supersedes its pending-execution statements only. Paper window and policy details remain proposals. No release or production state changes.

## Experiment 01 result — October 12

The [completed result and verification](../research/pregame_2027/experiment_01/RESULTS.md) records all three folds, the failed practical gate and reused-development limitations. Average annual Brier gain was 0.000334; conditional 14-day 95% interval [−0.000257, +0.000790]. Pooled log loss improved and coverage stayed identical, but the agreed 0.001 gain threshold was not met. Retain the existing reference; do not promote this challenger, retune it or start a second variant automatically. No same-time Kalshi or selected-return experiment has been run. The effort cap is satisfied; this is a completed negative continuation decision, not unfinished work waiting five calendar days.

## Next-step proposal — October 12, after failed challenger

The [unchanged-reference matched-measurement proposal](MLB_2027_MATCHED_PAPER_PILOT_PROPOSAL.md) recommends a two-focused-day offline rehearsal before any separately approved finite live pilot. It addresses live player-ID/count compatibility, contemporaneous model/market pairing, executable depth, fees and delayed paper probes. It is not a model variant, challenger promotion or selection-policy approval. Implementation and live capture remain unapproved. Playoff data can verify plumbing but cannot establish regular-season accuracy or profitability.

## Owner clarification and revised priority — October 12

Tom clarified that sportsbook consensus is the intended historical proxy for unavailable Kalshi history; there is no evidence materially different Kalshi prices would rescue the weak model. Improving native probability estimates remains the priority. This supersedes the preceding matched-measurement proposal as the recommended next step; its notes stay as background and no collector is authorized. The [one score-model proposal](MLB_2027_SCORE_MODEL_PROPOSAL.md) assesses a materially different final-score likelihood using existing lagged team/starter inputs, with the sportsbook proxy as the main winner-probability comparator. It is a discussion proposal, not an approved experiment. The failed challenger remains closed and unpromoted.

## Modern-ML hypothesis and current next proposal — October 12

Tom hypothesizes that recent AI/mathematical advances could offer an advantage against well-resourced sportsbooks. This is a research hypothesis, not an edge claim or blanket implementation approval. The [modern-ML assessment and single learner-comparison proposal](MLB_2027_MODERN_ML_PROPOSAL.md) reconciles primary research with our actual game/player-count data and prior additive-GAM failures. It recommends a conditional, bounded TabPFN core comparison with a competent boosting baseline on the frozen game table. Access/license/hardware and pretraining provenance must be resolved explicitly; no installation, weight download, credential or fit is authorized. The earlier score-model proposal is now a structural alternative, and quote-capture notes remain background. Sportsbook consensus stays the historical proxy; the failed experiment is closed.

## Verified setup due diligence — October 12

The [read-only access/compute review](MLB_2027_MODEL_ACCESS_COMPUTE_REVIEW.md) found a material 3.5 eligibility blocker: the actual weight terms exclude consumers, and hosted-service terms do likewise. Personal hobby research/use of predictions for manual wagers is not automatically covered. Direct permission is needed before pursuing 3.5; the more permissive standalone v2 license is an explicit alternative, not an adopted version switch. Local CPU/MPS hardware/software compatibility was investigated privately, matching wheels and current cloud list prices were checked, but no runtime benchmark or model download occurred. No account, acceptance, installation, purchase, data upload or fit is authorized by this investigation.

## Licensing inquiry sent — October 12

The parent confirms the Owner-approved personal-research licensing inquiry was sent. The [access review](MLB_2027_MODEL_ACCESS_COMPUTE_REVIEW.md) records its narrow performance-analytics research scope and pending permission; correspondence details remain private. The parent will handle the reply. No access acceptance, installation, acquisition, new fit or v2 switch has been authorized.

## TabPFN-v2 authorized and ready — October 12

Tom approved proceeding with v2 while the separate 3.5 inquiry is pending. The parent confirmed isolated local setup, synthetic capacity checks, then the bounded v2/reference/boosting comparison, without paid compute. The official v2 default checkpoint/license was pinned and checked; local dependencies installed separately from production. CPU/Metal small synthetic tests and the complete 9,704-row Metal capacity test passed; model use has network access disabled. No 3.5 weights, new account/credential or model API is used.

The [experiment 02 protocol](../research/pregame_2027/experiment_02/PROTOCOL.md) and [settings](../research/pregame_2027/experiment_02/SETTINGS.json) freeze the comparison before baseball fitting. Four intrinsic v2 estimators, eight training-only boosting configurations, original ten columns, unchanged populations, no post-fit calibration and original development gate. Sportsbook opening consensus stays the historical proxy. Setup and full comparison are now authorized solely within this bounded protocol; production/policy/merge remain unchanged. Results pending.


## Completed bounded v2 comparison — October 12

The authorized local comparison is complete; this supersedes earlier pending-status entries. [Experiment 02 results](../research/pregame_2027/experiment_02/RESULTS.md) record exact reference replay, 7,280 chronological development forecasts, and independent score/bootstrap verification. TabPFN-v2 improved average annual Brier by 0.000057915 versus the required 0.001; CatBoost worsened it by 0.000479901. Both fail their frozen gates. Sportsbook opening consensus remains better on both proper scores in each year on the original common population. These are reused development seasons, not untouched holdouts. Retain the reference and promote neither learner; no further tuning is authorized automatically.

The pinned v2 checkpoint worked on local Metal without paid compute or model-service uploads. The separate 3.5 licensing inquiry remains pending. Existing collectors, T−6h studies, production pins and schedules remain intact; draft PR 86 remains for review and is not approved for merge.

## Post-experiment component assessment — October 12

Tom authorized a bounded read-only data/design assessment. The [completed feasibility review](MLB_2027_COMPONENT_FEASIBILITY.md) finds extensive player-game counts but only four distinct PA/pitch games. It recommends one conditional starter–batter K/unintentional-walk/other PA component against a strong shrunk-rate matchup baseline, subject to validated PA data and a frozen protocol. This tests individual matchup structure rather than another summary feature added to the winner model. Prior starter diagnostics support starting here, without establishing pitching as the largest missing source of information.

The proposed immediate gate is a one-day, one-season Retrosheet readiness pass with a deterministic 100-game audit, followed by a concrete protocol for agreement. [Its handoff](MLB_2027_COMPONENT_READINESS_HANDOFF.md) remains unapproved for execution. No acquisition or training occurred. Component improvement would justify only a later integration discussion; winner probabilities must still face the sportsbook proxy and fresh validation. The 3.5 inquiry is not a dependency.


## Approved readiness pass completed — October 12

Tom approved the one-season pass. [Results](../research/pregame_2027/component_readiness/RESULTS.md): 100 frozen games, 7,496 PA, exact sampled count reconciliation, usable IDs/labels and distinct suspended-play dates; 17.44 MB transferred. Sample-level feasibility passes, with whole-season/multi-season validation still required. This supersedes preceding unapproved-readiness status, without changing prior failed experiments. The [concrete experiment 03 protocol](../research/pregame_2027/component_experiment/PROTOCOL.md) is proposed for agreement before additional seasons or fitting. No model fit occurred.
