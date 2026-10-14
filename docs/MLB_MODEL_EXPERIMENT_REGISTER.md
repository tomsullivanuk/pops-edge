# MLB native-model experiment register

Canonical index for discussion of the in-house regular-season winner model and its supporting research. Updated October 14, 2026; documentation only. Main verified at `9564b12dcd80f0b3347b4860b95984763f2e3061`; this record is proposed on draft PR #86 and is not merged product authority.

**Current decision: retain the ten-input starter reference and pause further model experiments.** Four recent comparisons failed their agreed continuation gates; the subsequent information-chain diagnostic was inconclusive and explicitly stopped. Earlier positive and uncertain findings remain evidence. No new experiment, paper-alert implementation, trading, purchase, credential, production collector, pin or schedule change is authorized by this register. Existing postseason T−6h studies remain separate and intact.

## How to read and count this record

There are **23 completed entries: 15 winner-model comparison campaigns (M01–M15), one player component study (C01), four diagnostics (D01–D04), and three annual evaluation/refit campaigns (V01–V03)**. “Completed” describes execution, not successful improvement. A campaign can contain several predeclared arms. Diagnostic D02 contains deletion refits; V02 contains three annual refits. They are classified by their scientific question, not the number of optimizer calls. The shared source for D03/M12 contains two distinct questions and is indexed twice, without treating their evidence as independent.

This reconciles 17 original `native_*/RESULTS_REPORT.md` packages (18 entries after splitting diagnostic/overlay) plus recent experiments 01–04 and their information-chain diagnostic (five entries). Supporting availability/readiness work, proposals, numerical retries and replay verification are indexed separately below and are **not** included in 23. This is an inventory of the inspected retained native-model reports, not a claim that every idea ever discussed was executed or that every older exploratory calculation has a separate row. Stable IDs describe these campaigns; the original experiment 01–04 labels remain unchanged.

For winner comparisons, lower Brier and natural-log loss are better. A **gain** is comparator loss minus candidate loss: positive favors the candidate. Tables explicitly label adverse differences, deletion effects and market gaps when they use another direction. C01 reports relative log-loss reduction in percent; D04 reports event-value MSE. Neither is a winner Brier gain. Unless otherwise stated, intervals below are retained paired **14-calendar-day block 95% intervals**; they are descriptive uncertainty conditional on the chosen models and reused seasons, not selection-adjusted discovery evidence. Seven-day sensitivity matters where the sign classification changes.

2024–2026 have repeatedly informed development. Chronological fitting, training-only selection and annual refitting prevent particular leakage mechanisms; they do not restore untouched holdouts. Retrospective actual lineup/starter identities do not establish their live publication time. The historical sportsbook **opening consensus** is the agreed development proxy, not Kalshi, a same-time executable quote or a closing-price guarantee. The 2024 market subset varies: original 2,291 games; several later studies used 2,278 after 13 post-inspection exclusions. Those suspected quote artifacts were not independently established errors. Do not silently carry those exclusions into a new study. Recent comparisons retain the original common cohort where stated.

The recent 0.001 average annual Brier gate and C01's 0.5% component gate were campaign-specific engineering continuation decisions. Do not apply them retrospectively to older “promising” rules or interpret them as return thresholds. Probability advantage in percentage points, net expected return after price/depth/fees/delay, and forecast uncertainty are separate quantities. None of the entries establishes profitable selection or superiority to Kalshi.

## Overview

| ID | Question / change | Principal retained result | Outcome |
| --- | --- | --- | --- |
| [M01](#m01-team-logistic-and-season-interactions) | Team logistic; season interactions | Seasonal vs constant Brier gain +0.004937; vs fixed +0.000034953 | Useful baseline; added seasonal complexity uncertain |
| [M02](#m02-team-gam) | Additive team splines | Fixed logistic minus GAM −0.000238326 | Selection rule failed |
| [M03](#m03-starter-features) | Lagged starter quality/workload | Seasonal minus starter +0.001480 | Promising; interval spans zero; retained reference |
| [M04](#m04-bullpen-quality-and-workload) | Four relief features | Starter minus extension +0.00008517 | Directional rule passed; too uncertain to promote |
| [M05](#m05-separate-offense-and-prevention) | Separate runs scored/allowed | Extension minus starter +0.000469 (adverse) | Rule failed; significance block-sensitive |
| [M06](#m06-opponent-strength-features) | Four prior-opposition features | Starter minus candidate +0.000135 | Promising but uncertain |
| [M07](#m07-projected-batting-unit) | Usage-weighted batting/hand proxy | Starter minus candidate +0.000254 | Promising but uncertain; invalid attempt retained |
| [M08](#m08-combined-starter-opponent-and-batting) | Combine 17 inputs | Starter minus combined +0.000321 | Best local point estimate; uncertain |
| [M09](#m09-actual-nine-substitution) | Replace batting proxy with actual nine | Proxy minus actual +0.000106615 | Promising in 2024; later did not generalize |
| [M10](#m10-regularization-and-transferred-calibration) | Four regularization/calibration arms | C=1 minus C=.01 raw +0.000128384 | Small uncertain gain; calibration worsened |
| [M11](#m11-starter-gam) | Three starter splines | Linear minus GAM −0.000370078 | No promotion |
| [M12](#m12-native-market-overlay) | Native disagreement in fitted market model | Market-control minus combination −0.000071622 | Rule failed |
| [M13](#m13-experiment-01-strength-rating) | Opponent-adjusted ridge rating | Mean annual gain +0.000334224 | Continuation gate failed |
| [M14](#m14-experiment-02-modern-learners) | Fixed-input TabPFN-v2 / CatBoost | Mean gains +0.000057915 / −0.000479901 | Both continuation gates failed |
| [M15](#m15-experiment-04-steamer-offense) | Preseason Steamer vs lagged offense | Mean annual gain +0.000474075 | Information and market gates failed |
| [C01](#c01-experiment-03-pitcher-batter-component) | Partial pooling for K/BB/other | Mean relative log-loss reduction 0.095041% | Small gain; 0.5% gate failed |
| [D01](#d01-original-market-comparison) | Existing forecasts vs opening consensus | Seasonal minus market +0.002895 (adverse) | Market better point estimate; interval spans zero |
| [D02](#d02-deletions-and-calibration) | Conditional feature deletions/calibration | Removing starter raises Brier +0.001539213 | Starter contribution supported; others uncertain |
| [D03](#d03-market-disagreement-diagnostic) | Locate 2026 native-market gap | ≥5pp disagreements account for 76.6% of gap | Descriptive concentration, not a cause |
| [D04](#d04-information-chain-diagnostic) | Batting events → lineup → winner trace | Mean event MSE gain +0.000070274 | Inconclusive; explicit stop |
| [V01](#v01-frozen-2025-evaluation) | Three original fits on 2025 | Actual-nine minus proxy +0.000184197 (adverse) | 2024 actual-nine gain did not generalize |
| [V02](#v02-annual-2025-refits) | Three unchanged specs refit through 2024 | Gains +0.000043537 / +0.000145990 / +0.000182718 | Modest, all uncertain |
| [V03](#v03-fixed-starter-2026-evaluation) | Annual starter reference vs proxy | Native minus market +0.002555361 (adverse) | Market wins both scores; intervals above zero |

## Source access and reproducibility

Original report names below are **local retained evidence references**, not public GitHub links. Their aggregate results are transcribed here; originals may contain licensed/provider details and are not copied into the public repository. Recent protocols, aggregate results and code are linked in-repository. The [source manifest](../research/pregame_2027/experiment_register/source_manifest.json) pins SHA-256 hashes of every indexed report and contextual review, with entry-to-source mappings. It records source-root aliases rather than publicizing host paths. Original root alias `retained_native_archive` identifies the retained Pops' Edge project archive on the Owner's machine; `independent_review_archive` identifies the October 9 task-3 review directory. Originals must be available locally for full source inspection; a public reader can inspect the summaries and public recent artifacts, not the licensed raw inputs.

The original October 9 independent review and pregame design addendum were read from their actual files. They contextualize the model and product, not additional experiments or an exhaustive substitute for these source reports. This documentation review checks inventory, transcription, interpretation and links; it does not rerun every historical fit or bootstrap. See the [independent register review](../research/pregame_2027/experiment_register/REVIEW.md).

## Winner-model comparisons

### M01 Team logistic and season interactions

**Inputs/comparison:** three lagged team-history differences, fixed logistic versus progress/interactions logistic, both against training home-win-rate constant. Train 2022–2023 (4,852); evaluate 2024 (2,426); 2021 team-history warm-up. Brier / log loss: constant 0.249551 / 0.692250; fixed 0.244649 / 0.682284; seasonal 0.244614 / 0.682235.

**Evidence/decision:** seasonal gain against constant +0.004937, interval [+0.002619,+0.007432]; fixed gain +0.004902, interval [+0.002459,+0.007332]. Seasonal beats fixed by only +0.000034953 Brier and +0.000048399 log loss. Nominal seasonal selection met the original rule, but the baseline intervals do not measure seasonal-versus-fixed superiority. This is positive native baseline evidence, not market or profit evidence. Source: `native_logistic_2026-09-28/RESULTS_REPORT.md`.

### M02 Team GAM

**Inputs/comparison:** the same three inputs as fixed logistic; additive cubic spline GAM with five training-quantile knots per input, 18 basis columns, C=1 and no interactions. Same 4,852 / 2,426 train/evaluation populations as M01. GAM Brier / log loss 0.244888 / 0.682765.

**Evidence/decision:** fixed-minus-GAM −0.000238326, interval [−0.001288,+0.000696]; seasonal-minus-GAM −0.000273279, interval [−0.001401,+0.000691]. The frozen selection rule failed; GAM still beat the constant baseline. This rejects this tested additive specification for promotion, not all nonlinear methods. Source: `native_gam_2026-09-28/RESULTS_REPORT.md`.

### M03 Starter features

**Inputs/comparison:** add lagged starter K−BB, HR rate and expected innings to seven team/progress terms (ten inputs total). Train 4,852; evaluate the same 2,426 2024 games. Starter Brier 0.243134308, log loss 0.679227637.

**Evidence/decision:** gain over seasonal +0.001480, interval [−0.000022,+0.002814]; seven-day also spans zero. Original promising rule passed; retained as the simpler working reference. On the separate original 2,291-game market-common cohort, starter 0.243999 versus book 0.242288: 40.9% closure of the prior point-estimate gap, with uncertainty spanning zero. No pitcher-driven target exclusions, causal attribution or market superiority follows. Source: `native_starter_2026-09-28/RESULTS_REPORT.md`.

### M04 Bullpen quality and workload

**Inputs/comparison:** four lagged relief quality/workload features added to starter; same 2022–2023 training 4,852 and 2024 evaluation 2,426. Extension Brier / log loss 0.243049 / 0.679055 versus starter 0.243134 / 0.679228.

**Evidence/decision:** gain +0.00008517, interval [−0.000648,+0.000773]. Directional promising rule technically passed; weak evidence did not justify replacing simpler starter. Common 2,291-game extension Brier 0.243858 versus book 0.242288. Imputed workload remained visible and all native targets were retained. This does not establish bullpen irrelevance. Source: `native_bullpen_2026-09-28/RESULTS_REPORT.md`.

### M05 Separate offense and prevention

**Inputs/comparison:** four separate runs-scored/runs-allowed dimensions/interactions added to starter (14 inputs), not a run-count likelihood. Same train 4,852 / 2024 evaluate 2,426. Extension Brier / log loss 0.243603 / 0.680199.

**Evidence/decision:** extension-minus-starter +0.000469 Brier, +0.000971 log loss (both adverse); 14-day Brier interval [+0.000053,+0.000930], seven-day [−0.000007,+0.000999]. Original rule failed; statistical sign classification depends on block length. Market comparison used the later 2,278-game subset. This is not a test of the later score-distribution proposal. Source: `native_offense_prevention_2026-09-29/RESULTS_REPORT.md`.

### M06 Opponent strength features

**Inputs/comparison:** four lagged prior-opposition/window-progress features added to starter; one-pass summaries, not recursive ratings. Same train 4,852 / evaluate 2,426 in 2024. Candidate Brier 0.242999652, log loss 0.678945007.

**Evidence/decision:** gain over starter +0.000135, interval [−0.000546,+0.000837]. Promising directional rule passed; future superiority unestablished. Later-season improvement with early deterioration is descriptive, not an identified mechanism. Common 2,278-game Brier 0.243974 versus book 0.241632. Distinct from M13's replacement rating. Source: `native_opponent_2026-09-29/RESULTS_REPORT.md`.

### M07 Projected batting unit

**Inputs/comparison:** add three recent-usage-weighted OBP/ISO/hand features to starter (13 inputs); last-30-day PA usage proxy, 365-day histories, 180-day half-life and 200-PA shrinkage. Same train 4,852 / 2024 evaluation 2,426. Candidate Brier 0.242880027, log loss 0.678705887.

**Evidence/decision:** gain +0.000254, interval [−0.000129,+0.000726]. Promising rule passed, but uncertain. This used neither confirmed actual nine nor measured platoon-quality effects. An incorrect hand encoding caused an invalid attempt; corrected rerun tested the same hypothesis, not a new independent experiment. `invalid_attempt_hand_encoding` remains in the local package. Market subset 2,278. Source: `native_batting_unit_2026-09-29/RESULTS_REPORT.md`.

### M08 Combined starter, opponent and batting

**Inputs/comparison:** jointly refit 17 inputs: ten starter reference + four M06 + three corrected M07; no bullpen extension. Same train 4,852 / evaluate 2,426 in 2024. Combined Brier 0.242812827, log loss 0.678565636.

**Evidence/decision:** gains versus starter +0.000321 [−0.000417,+0.001200], opponent +0.000187 [−0.000163,+0.000643], batting +0.000067 [−0.000572,+0.000743]. Promising point estimate, all intervals span zero; improvements are not additive. Market subset 2,278. Later tests are V01/V02, not concealed additional tuning here. Source: `native_combined_2026-09-29/RESULTS_REPORT.md`.

### M09 Actual-nine substitution

**Inputs/comparison:** replace M08's three proxy batting terms by equal-1/9 actual starting-nine aggregates; order retained for provenance, not order weights. Fourteen other predictors unchanged; all 17 coefficients refitted. Same train 4,852 / 2024 evaluate 2,426. Actual-nine Brier 0.242706211, log loss 0.678358979.

**Evidence/decision:** proxy-minus-actual +0.000106615, interval [−0.000333934,+0.000518352]. Original promising rule passed, uncertain; no live as-of lineup claim. No 2021 batter warm-up. Common 2,278-game actual Brier 0.243651422 versus proxy 0.243824606 and book 0.241631692. Later 2025 generalization failure is V01, retained separately. Source: `native_actual_lineup_2026-09-29/RESULTS_REPORT.md`.

### M10 Regularization and transferred calibration

**Inputs/comparison:** one bounded four-arm campaign on the same ten inputs. C∈{.001,.01,.1,1} selected using training-only chronological 2023/2024 validation (4,849 pooled games); .01 chosen, validation Brier 0.243441623 versus C=1 0.243531984. Calibration learned on 2025 out-of-time forecasts (2,426) then transferred after 2026 annual refit through 2025 (9,704 train). Evaluate the same 2,428 2026 games.

| Arm | 2026 Brier | Log loss |
| --- | ---: | ---: |
| C=1 raw | 0.246136090 | 0.685346418 |
| C=1 calibrated | 0.246231064 | 0.685552716 |
| C=.01 raw | 0.246007706 | 0.685081956 |
| C=.01 calibrated | 0.246177008 | 0.685441942 |
| Opening consensus | 0.243580729 | 0.680038040 |

**Evidence/decision:** raw regularization gain +0.000128384 [−0.000060541,+0.000253205], meeting the old point-estimate promising rule but unestablished and not adopted as replacement. Calibration worsened each corresponding raw arm. All still trailed market. Motivation included already-seen 2026 results; training-only selection does not make evaluation fresh. This does not disprove every calibration method. Source: `native_calibration_2026-09-30/RESULTS_REPORT.md`.

### M11 Starter GAM

**Inputs/comparison:** seven team terms stay linear; three starter terms use additive cubic splines. Three/four/five knots selected on chronological training-only pooled 4,849-game validation; three chosen, C=1 fixed. Final train through 2024 (7,278), evaluate 2025 (2,426). GAM Brier / log loss 0.244255825 / 0.681368061 versus linear 0.243885748 / 0.680590378.

**Evidence/decision:** linear-minus-GAM −0.000370078 [−0.000778549,+0.000031657]. No promotion; the interval narrowly spans zero. Market common 2,425 unchanged, market better point estimate. This is distinct from M02 and not a general rejection of nonlinearity. Source: `native_starter_gam_2026-09-30/RESULTS_REPORT.md`.

### M12 Native-market overlay

**Inputs/comparison:** market-control logistic uses intercept + logit market; combination adds native-minus-market logit. Native training forecasts are out-of-time: 2024 from 2022–2023 fit and 2025 from 2022–2024 fit. Overlay training 4,703 market-common games (2,278 filtered 2024 + 2,425 2025); evaluate 2026 (2,428). Native disagreement coefficient 0.105394.

**Evidence/decision:** control Brier / log loss 0.243578747 / 0.680041481; combination 0.243650369 / 0.680199920; raw market 0.243580729 / 0.680038040. Control-minus-combination −0.000071622 [−0.000223935,+0.000090921]. Rule failed: no demonstrated incremental benefit, not proof of redundancy of all native information. Retain post-inspection exclusion caveat; no operational combination admitted. Source: fitted-overlay portion of `native_market_diagnostic_2026-10-01/RESULTS_REPORT.md`; descriptive question indexed at D03.

### M13 Experiment 01: strength rating

**Inputs/comparison:** replace six rolling team/progress-interaction inputs by a fixed opponent-adjusted, recency-weighted ridge run rating; retain starter terms and progress, same logistic settings. Annual training through previous year; evaluate 2024/2025/2026 (2,426 / 2,426 / 2,428). Exact reference replay precedes comparison.

**Evidence/decision:** annual Brier gains −0.000115 / +0.000239 / +0.000879 (rounded); equal-year mean +0.000334224 [−0.000256781,+0.000790124]. Two positive years and no worse pooled log loss did not rescue average gain below the frozen 0.001 requirement. Gate failed; no promotion or automatic second challenger. This is a model comparison, not a Kalshi price/depth test. [Results](../research/pregame_2027/experiment_01/RESULTS.md), [protocol](../research/pregame_2027/experiment_01/PROTOCOL.md), [full metrics](../research/pregame_2027/experiment_01/results.json).

### M14 Experiment 02: modern learners

**Inputs/comparison:** one campaign, two candidate arms on the same ten native inputs: explicit pinned TabPFN-v2 (four intrinsic estimators) and a bounded eight-configuration, training-only CatBoost control. This did not test TabPFN-3.5. Annual 2024–2026 full native cohort 7,280 (2,426 / 2,426 / 2,428), original market-common 7,144 (2,291 / 2,425 / 2,428).

**Evidence/decision:** equal-year Brier gains: v2 +0.000057915 [−0.000224890,+0.000320501]; CatBoost −0.000479901 [−0.001122217,+0.000057721]. Both frozen continuation gates failed; opening consensus better on both proper scores in each year. No automatic tuning or different-version substitution. Wrapper version and underlying model version must remain distinct. [Results](../research/pregame_2027/experiment_02/RESULTS.md), [protocol](../research/pregame_2027/experiment_02/PROTOCOL.md), [full metrics](../research/pregame_2027/experiment_02/results.json).

### M15 Experiment 04: Steamer offense

**Inputs/comparison:** matched twelve-input logistic arms: native ten + own lagged offense and shared hand, versus replacing offense with fixed preseason Steamer. Same initial-nine identities, fixed training-only slot weights, fixed 2013 event-rate definition and same learner/settings. Own histories 365-day/180-day half-life/200 shrinkage. Train 2022–2023 (4,852) → evaluate 2024 (2,426); train through 2024 (7,278) → evaluate 2025 (2,426); no 2026 validation.

**Evidence/decision:** 2024 control Brier 0.242807313 versus Steamer 0.241801625 (gain +0.001005688); 2025 control 0.243867523 versus Steamer 0.243925061 (gain −0.000057538). Equal-year gain +0.000474075 [−0.000423151,+0.001021038]. Information gate failed (size, two positive years, positive interval); market gate failed. Common 4,716 (2,291 / 2,425) pooled Steamer Brier / log loss 0.243305559 / 0.679481939 versus book 0.241753881 / 0.676802837. Close this specification without retuning. Raw archive vintage/revisions are not independently verified as contemporaneous releases; byte-identical year-label reconciliation does not establish as-of availability. [Results](../research/pregame_2027/experiment_04/RESULTS.md), [protocol](../research/pregame_2027/experiment_04/PROTOCOL.md), [full metrics](../research/pregame_2027/experiment_04/results.json).

## Player component study

### C01 Experiment 03: pitcher-batter component

**Inputs/comparison:** conditional three-class PA prediction (K / unintentional BB / other) against initial starters. Strong lagged rate/hand baseline versus partial-pooled pitcher/batter residual effects, fixed 100 individual penalty; three gamma values selected training-only. Final train 365,207 / 547,147 all-role PA; evaluate 2024/2025 primary 106,845 / 106,429 starter PA (213,274 paired). Entire saved all-role population 729,517 differs from the primary cohort.

**Evidence/decision:** baseline/challenger log loss 0.759468030 / 0.758812781 (2024), 0.760425012 / 0.759635649 (2025). Equal-year relative log-loss reduction **0.095041%** [0.077841%,0.113720%] versus required **0.5%**. Multiclass Brier improved both years, but practical-size gate failed. This is real small conditional component improvement, not a winner-probability percentage-point gain. No game simulation, market comparison or return calculation occurred.

Two explicitly approved numerical amendments (whole-objective/gradient rescaling per PA, including penalties; normalized convergence acceptance) preserved the same hypothesis/minimizers. Earlier numerical stops are retained, not counted as additional failed statistical experiments. [Results](../research/pregame_2027/experiment_03/RESULTS.md), [protocol](../research/pregame_2027/experiment_03/PROTOCOL.md), [numerical history](../research/pregame_2027/experiment_03/NUMERICAL_HISTORY.md), [full metrics](../research/pregame_2027/experiment_03/results.json).

## Diagnostics

### D01 Original market comparison

**Question/cohort:** no new learner; compare M01/M02 forecasts with opening consensus on original 2,291 common 2024 games out of 2,426 native eligible. Missing opening records 115, no eligible quote 20; original comparison used no result-dependent exclusions. Approximate timestamp concern: many quotes have UTC-midnight records; this is not a validated same-time decision benchmark.

**Evidence/decision:** fixed / seasonal / GAM Brier 0.245233 / 0.245183 / 0.245498, market 0.242288. Seasonal-minus-market adverse +0.002895 [−0.000703,+0.006219]. Market has stronger point scores; conditional interval spans zero. Early-phase native advantage is descriptive, not a selective policy. Later 13-game quote-exclusion sensitivity belongs to subsequent campaign lineage, not a newly fitted winner model or silently corrected original denominator. Source: `native_market_comparison_2026-09-28/RESULTS_REPORT.md`.

### D02 Deletions and calibration

**Question/cohort:** three conditional group deletions from M09, all remaining coefficients refitted on 4,852 training games; same 2,426 2024 evaluation. Diagnostic refits are not three separately promoted challengers. Full actual-nine Brier 0.242706211.

**Evidence/decision:** deleting batting raises Brier +0.000293441 [−0.000368290,+0.000990954]; deleting opponent +0.000090528 [−0.000542776,+0.000765983]; deleting starter +0.001539213 [+0.000098263,+0.002863270]. Starter contribution supported conditionally; others uncertain. Joint calibration slope 0.97506, intercept −0.01809; ideal values inside intervals, no fitted adjustment adopted. This is not causal feature importance; hand terms still reference opposing starter after starter-quality deletion. Source: `native_diagnostics_2026-09-29/RESULTS_REPORT.md`.

### D03 Market-disagreement diagnostic

**Question/cohort:** unchanged C=1 annual starter model, 2,428 2026 games; locate native-minus-market Brier gap +0.002555361. No new forecast fit in this part of the package.

**Evidence/decision:** ≥5-percentage-point disagreements are 604 games (24.9%) and account for 76.6% of observed gap; 5–10pp band 529 games accounts for 60.2%. Late season accounts for 73.1%. Low effective starter history (<200 recency-weighted BF) is more common in the ≥10pp band (57.3%, 75 games) than overall (47.2%); this is not the percentage for all ≥5pp disagreements. These associations do not establish causal failure or a betting/filter rule. Separate fitted overlay is M12. Source: diagnostic portion of `native_market_diagnostic_2026-10-01/RESULTS_REPORT.md`.

### D04 Information-chain diagnostic

**Question/cohort:** frozen calculation using M15's saved rates, 2013 event values and eligible opportunity denominator AB+uBB+SF+HBP. Score completed PA by initial-nine identities only, not substitute PA; IBB/SH/interference explicitly unscored. No new learner, calibration or tuning. Primary eligible opportunities 174,413 / 174,612 in 2024/2025 (349,025); all 4,852 games retained in winner trace.

**Evidence/decision:** own/Steamer event-value MSE 0.270720527 / 0.270733015 (2024), 0.273597563 / 0.273444527 (2025). Annual gains −0.000012487 / +0.000153035; equal-year +0.000070274 [−0.000049266,+0.000172273]. Hitter-game mean gain +0.000026090 [−0.000097683,+0.000132734]. Complete-nine absolute side-weighted gains −0.000237554 / −0.000101009; interval [−0.000223975,−0.000127079]. This target differs from the winner model's home-minus-away difference, so it does not prove aggregation destroyed signal.

Saved winner probabilities changed by mean absolute 2.228 / 2.231 percentage points. Input reached the forecast; optimal translation or cause of winner-score differences is unestablished. No stable upstream advantage established; inconclusive diagnostic, explicit stop, no fifth model. M15 gates remain failed. [Decision/results](../research/pregame_2027/information_chain/DECISION.md), [protocol](../research/pregame_2027/information_chain/PROTOCOL.md), [full metrics](../research/pregame_2027/information_chain/results.json).

## Annual evaluations and refits

### V01 Frozen 2025 evaluation

**Question/cohort:** evaluate original 2022–2023 coefficients without refitting M03/M08/M09; same 2,426 eligible 2025 games. Original four resumed-target exclusions from 2,430 official games preserved; no extra lineup-driven exclusions. Common market cohort 2,425.

**Evidence/decision:** starter / proxy / actual-nine Brier 0.243929285 / 0.244095171 / 0.244279368; log loss 0.680669268 / 0.680994896 / 0.681379594. Actual-minus-proxy adverse +0.000184197, 14-day [+0.000000891,+0.000468290], seven-day [−0.000077741,+0.000502012]. Actual-minus-starter +0.000350083 [−0.000799068,+0.001555729]. Actual's 2024 point gain did not generalize; narrower significance against proxy is block-sensitive. On 2,425, actual 0.244267190 versus market 0.241248966; adverse gap +0.003018224 [+0.000281378,+0.005123102]. Source: `native_2025_comparison_2026-09-29/RESULTS_REPORT.md`.

### V02 Annual 2025 refits

**Question/cohort:** exactly three unchanged predeclared specifications, training expanded to 7,278 games through 2024; all coefficients/scalers refitted, same 2,426 2025 games. This changes training sample, scaler and coefficients together, not an isolated test of coefficient staleness.

**Evidence/decision:** starter Brier 0.243885748, old-minus-new gain +0.000043537 [−0.000129249,+0.000232815]; proxy 0.243949182, gain +0.000145990 [−0.000195156,+0.000458960]; actual-nine 0.244096650, gain +0.000182718 [−0.000123859,+0.000503920]. All modest improvements, all uncertain; simpler starter retained. On unchanged 2,425 market-common games, starter 0.243860017 versus book 0.241248966. These are annual updates to existing families, not three independent new information hypotheses. Source: `native_2025_retraining_2026-09-29/RESULTS_REPORT.md`.

### V03 Fixed starter 2026 evaluation

**Question/cohort:** annual refit of unchanged ten-input starter, train 2022–2025 (9,704); evaluate March 25–September 27, 2026. Of 2,429 canonical completed games, one resumed target excluded by existing policy; remaining 2,428 all have benchmark. Annual coefficients fixed; earlier completed season games can update lagged inputs.

**Evidence/decision:** native Brier / log loss 0.246136090 / 0.685346418 versus opening consensus 0.243580729 / 0.680038040. Native-minus-market adverse Brier +0.002555361 [+0.000466592,+0.004207373]; log loss +0.005308378 [+0.000931566,+0.008700189]. Seven-day intervals also above zero. Strongest retained historical proxy comparison favors market on both scores. This is not a Kalshi verdict, profitable-selection test or untouched holdout. Source: `native_2026_evaluation_2026-09-30/RESULTS_REPORT.md`.

## Supporting work and proposals outside the completed count

| ID | Record | Status / boundary |
| --- | --- | --- |
| S01 | [Finite lineup observation](MLB_2027_LINEUP_OBSERVATION_FINAL.md) | Completed two postseason games/four orders; first complete observations 3h25–3h54 before scheduled starts. Process-loss gap and first-game premature stop visible; actual first pitch and explicit pitcher confirmation unknown. Supports working assumption only; no duplicate observer. |
| S02 | [Component readiness](../research/pregame_2027/component_readiness/RESULTS.md) | Data/schema/identity readiness audit supporting C01, not another predictive comparison. |
| S03 | [Projection comparison record](MLB_2027_PROJECTION_COMPARISON_PROPOSAL.md) | Access/import/readiness and approvals feed M15. Not a separate executed winner experiment. |
| P01 | [Score-model proposal](MLB_2027_SCORE_MODEL_PROPOSAL.md) | Discussed, unexecuted run-distribution family. M05 did not execute it; no training authority follows. |
| P02 | [Matched paper-pilot proposal](MLB_2027_MATCHED_PAPER_PILOT_PROPOSAL.md) | Unexecuted forward paper workflow; T−90/60/30 remains proposed. Same-time forecasts and selected executable-price/depth/fee/delay entries require separate evaluation and agreement. |
| P03 | [Modern learner/version discussion](MLB_2027_MODERN_ML_PROPOSAL.md) | TabPFN-3.5 alternative unexecuted; actual tested v2 is M14. Historical proposal text is superseded by appended decisions where applicable. |

Replay checks, optimizer amendments and failed invalid acquisition/encoding attempts stay in their parent campaign histories. They neither inflate the campaign count nor disappear because a corrected run completed. Supporting licensed raw provider data, credentials and unrelated private information remain outside this public register.

## Questions for the next discussion

1. Given V03's sportsbook gap and the failed recent continuation gates, is our next objective stronger full-population forecasting or a separately frozen selective paper policy? The latter would need its own executable-price/depth/fee/delay evidence; neither choice is authorized here.
2. What distinct missing information or representation hypothesis is supported strongly enough to justify another bounded test? M03's starter contribution is supported; M15/D04 do not identify a stable upstream offense advantage or a causal translation failure. A new proposal should explain what it changes beyond the tested specifications.
3. What prospective evidence would justify continuing after reused development seasons? Agree any forward population, decision time, coverage accounting, practical-size criterion and stopping rule before observations; another historical gain alone cannot supply fresh confirmation.

These questions organize discussion, not an automatic research checklist or a request to approve an unspecified next experiment. The current pause remains in force.

## Maintaining the register

Use the stable ID when discussing an existing result. For any newly approved distinct hypothesis, add a proposed entry with linked frozen inputs, comparison, decision time, population, validation and gate **before execution**; transition it after execution with all results and failures. Do not infer authorization from a proposal or this maintenance instruction. Record annual evaluation extensions under the appropriate campaign with exact cohort/chronology, and separate new questions when appropriate. Current next gate is Owner discussion of the evidence; no next model is prescribed or authorized here.
