# Experiment 05 / M16: v3.5 core completed; continuation gate failed

October 16, 2026. **Retain the ten-input logistic reference; do not promote or retune this v3.5 configuration automatically.** Owner authorized the comparison; [protocol](PROTOCOL.md), configuration, code and running register entry were committed/pushed in `a0985289188856cca58f9c9600f099cd59d93d08` before v3.5 baseball execution. The independent preflight review passed. This is a new campaign, separate from experiment 02/M14: its original v2/CatBoost forecasts, configuration and results remain unchanged.

Built with PriorLabs-TabPFN. Personally completed Owner acceptance was verified on the official Licenses page. The pinned default core checkpoint was acquired using the documented manual route, with verified checksum and no credentials configured. This evaluates local **v3.5 core**, four intrinsic estimators and native temperature 1.0—not Plus, Thinking, Fast or unlimited tuning. V2 retains its original temperature 0.9; this compares declared configurations, not an isolated architecture effect.

## Same inputs and annual populations

Ten native team/starter/progress features only; no payroll/WAR/market/lineup inputs. Train through 2023/evaluate 2024, through 2024/evaluate 2025, through 2025/evaluate 2026. Full context sizes 4,852/7,278/9,704, complete evaluation 2,426/2,426/2,428. Prior-day chronology, actual-starter assumption and fallbacks remain unchanged. No target exclusions, tuning, post-fit calibration or new provider data. All seasons are reused development; chronology does not make them untouched holdouts.

Lower Brier and natural-log loss are better. Gain is reference-minus-v3.5 Brier; positive favors v3.5.

| Year | Games | Logistic Brier | Saved v2 Brier | v3.5 Brier | v3.5 gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 | 2426 | 0.243134308 | 0.243272348 | 0.243392473 | -0.000258165 |
| 2025 | 2426 | 0.243885748 | 0.243605265 | 0.243823125 | 0.000062623 |
| 2026 | 2428 | 0.246136090 | 0.246104789 | 0.246020562 | 0.000115527 |

Primary equal-weight annual gain is **−0.000026672**, versus required **+0.001**. Paired 14-day 95% interval **[−0.000269930,+0.000185215]**; seven-day sensitivity [−0.000297338,+0.000230407]. Both include zero. The small adverse point estimate does not establish significant inferiority; it does fail the practical continuation requirement.

| Frozen continuation condition | Result |
| --- | --- |
| Mean annual Brier gain≥0.001 | Fail: −0.000026672 |
| Positive annual Brier gain in≥2 years | Pass: 2025, 2026 |
| Pooled log loss no worse than logistic | Fail: 0.681792630 vs 0.681722474 |
| Identical target coverage | Pass: 7,280 paired games |
| No new hindsight dependence | Pass within inherited historical availability assumptions |

All were required. Pooled Brier is 0.244412495 versus logistic 0.244385863; pooled gain −0.000026633 is not the primary equal-year measure. Calibration slopes for v3.5 are 1.004/0.881/0.817; intercepts −0.024/0.084/0.018. These are descriptive, unapplied diagnostic fits—not per-game uncertainty or reasons to add calibration after failure.

## Saved learner and sportsbook contrasts

Equal-year saved-v2-minus-v3.5 Brier is **−0.000084586**, 14-day interval [−0.000291464,+0.000107322]; seven-day also spans zero. V3.5 does not establish improvement over v2, and v2's original +0.000057915 gain/failed gate remain intact. V3.5 improves on the weaker saved CatBoost point estimate by +0.000453230; its 14-day interval [+0.000015267,+0.000986275] excludes zero, while seven-day [−0.000038039,+0.000965904] spans zero. That secondary block-sensitive result does not rescue the primary gate.

Original common sportsbook population 7,144 (2,291/2,425/2,428), without the historical 13-game post-inspection exclusion. Different denominator from the full-native table above.

| Year | Common games | v3.5 Brier | Sportsbook Brier | v3.5 log loss | Sportsbook log loss |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 | 2291 | 0.244213957 | 0.242288328 | 0.681434587 | 0.678619896 |
| 2025 | 2425 | 0.243804481 | 0.241248966 | 0.680438180 | 0.675086184 |
| 2026 | 2428 | 0.246020562 | 0.243580729 | 0.685149036 | 0.680038040 |

Sportsbook opening consensus is better on **both scores in every year**. Pooled common Brier 0.244688965(v3.5) versus0.242374764(book); log loss 0.682358774 versus0.677902371. Equal-year v3.5-minus-book adverse Brier gap+0.002306992, 14-day interval [+0.000656665,+0.003580918]; seven-day [+0.000755594,+0.003548711]. Corresponding14-day adverse log-loss interval [+0.000708329,+0.007284264] is also above zero. These intervals describe this fixed reused-development comparison, not selection-adjusted discovery. The opening consensus is the agreed historical Kalshi proxy, not actual Kalshi or same-time executable prices/depth/fees/delay. No profit or selected-entry claim follows.

## Verification and practical feasibility

- All 38 source hashes, comparison/freeze pins and original v2 private hashes match. Saved reference probabilities replay exactly in all three years. Every retained v2/CatBoost/market column and original full/common cohort remains identical; prior public annual baseline metrics match exactly.
- All 7,280 v3.5 saved-context predictions replay exactly. Later test-feature mutation changes earlier predictions by zero in each year. Batch-isolation maximum difference3.58e−7, below fixed1e−6 tolerance. No fit receives outer labels; no post-result tuning/calibration occurred.
- Team-history inputs independently reconstructed for all 12,132 source feature rows; all 12,132 stored starter lineages pass prior-day/no-target checks. This does not rerun the original raw starter-rate builder or validate historical publication timestamps.
- Separate scalar Brier/log-loss arithmetic agrees within1.12e−16. All 5,000 paired bootstrap draws at both block lengths and both populations were reconstructed via per-game day-multiplicity weights; bound differences≤2.43e−17. Calibration score equations reconcile within6.75e−14.
- Separate delegated reviewer independently checked all 7,280 original-column joins, scalar annual/pooled scores and bootstrap endpoints (maximum difference1.12e−16), then reviewed conclusions. See [final review](REVIEW.md) for exact scope and limitations; same-assistant saved-context replay is distinguished from independent delegated arithmetic review.
- Local Metal fit/context seconds 10.06/16.14/27.87; prediction seconds 6.47/7.61/9.43. No wall-cap failures or numerical retries. Highest driver reading after prediction 4.44 GB is not measured peak memory. Network audit records no model-use network attempts. No paid compute, credential changes or uploads.

[Full aggregate results](results.json), [reference replay](reference_replay.json), [verification](verification.json), [measurement verification](measurement_verification.json), [timings](timings.json), [execution freeze receipt](execution_start.json), [provenance](provenance.json), [runner](run.py), [model configuration](local_model.py), [measurement](measurement.py), [replay/chronology verifier](verify.py), [separate measurement verifier](verify_measurement.py).

## Decision and limits

Close this tested v3.5 configuration without promotion, automatic tuning, alternate checkpoints, threshold relaxation or follow-on learner. Keep the simpler reference and all prior evidence. Local feasibility succeeded; predictive continuation failed. This does not show that every v3.5 setting, Thinking variant or model with additional information would fail, and does not itself justify trying them.

All seasons informed prior development, including the decision to try v3.5. Conditional intervals omit training/model-selection uncertainty. Historical actual-starter identities and publication/price timing assumptions persist. The reviewer did not independently retrain the learner, revalidate all provider raw records or audit pretraining. No fresh 2027 or executable-entry evaluation occurred. Raw licensed provider inputs, per-game predictions, weights and fitted contexts remain private. Only permitted code/aggregates/documentation go to draft PR #86 after review; no merge, deployment, collector/pin/schedule/T−6h change. Payroll/WAR remain unexecuted.
