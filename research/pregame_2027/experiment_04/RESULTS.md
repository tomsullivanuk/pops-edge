# Experiment 04: Steamer helps 2024; neither agreed gate passes

October 12, 2026. **Complete within the approved effort cap. Close this tested
specification without retuning, integration or promotion.** Tom explicitly
approved the proposal at `1d64e15`; implementation/input pins were published
at `43d8161` before any new fit or evaluation. Four annual arm fits converged.

The information used here was obtained free of charge from and is copyrighted
by Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd.,
Newark, DE 19711. FanGraphs/Steamer exports were supplied through the Owner's
permitted export workflow; raw files and player records remain private.

## What was compared

Both winner models keep the original ten team/starter inputs, the same initial
nine, the same training-only slot weights, shared handedness feature and C=1
logistic. They differ only in the offense index: our lagged/shrunk event rate
versus the fixed preseason Steamer projected event rate. Both use the same
historically published 2013 run weights, not supplied current-year WAR/wOBA/wRC+.
The unchanged native reference is separately retained. No feature/model sweep,
new source purchase, calibration of forecast outputs or post-result filtering.

Training: 4,852 games through 2023 for 2024; 7,278 through 2024 for 2025.
Evaluate 2,426 games each year. All are **reused development seasons**.

## Information comparison: full paired populations

| Year | Games | Own-rate control Brier | Steamer Brier | Control minus Steamer |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 2,426 | 0.242807313 | 0.241801625 | +0.001005688 |
| 2025 | 2,426 | 0.243867523 | 0.243925061 | −0.000057538 |

| Year | Own-rate control log loss | Steamer log loss |
| --- | ---: | ---: |
| 2024 | 0.678584666 | 0.676476103 |
| 2025 | 0.680544391 | 0.680672911 |

Average annual Brier gain: **0.000474075**, below the required **0.001**.
Paired 14-calendar-day 95% interval: **[−0.000423151, +0.001021038]**;
7-day sensitivity: **[−0.000388476, +0.001162100]**. Both include zero.
2024 improves; 2025 is slightly worse. Pooled log loss improves and coverage
is unchanged, but the size, both-year and positive-interval rules fail.
**Information gate: failed.** This is not a percentage-point winner advantage.

Over all 4,852 games, pooled native/control/Steamer Brier is
0.243510028 / 0.243337418 / 0.242863343. That pooled improvement is not a reason
to replace the agreed equal-year gate or ignore the unsuccessful 2025 result.

## Sportsbook proxy: original matched populations

| Year | Matched games | Native Brier | Control Brier | Steamer Brier | Sportsbook Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 | 2,291 | 0.243998626 | 0.243652250 | 0.242664479 | 0.242288328 |
| 2025 | 2,425 | 0.243860017 | 0.243851160 | 0.243911214 | 0.241248966 |

| Model | Pooled matched Brier | Pooled matched log loss |
| --- | ---: | ---: |
| Native | 0.243927353 | 0.680759393 |
| Control | 0.243754531 | 0.680420942 |
| Steamer | 0.243305559 | 0.679481939 |
| Sportsbook | 0.241753881 | 0.676802837 |

Steamer remains worse than the proxy on pooled Brier/log loss and annual Brier.
Its 2024 matched log loss is slightly lower than the proxy (0.678250785 versus
0.678619896), but that isolated score does not satisfy the market gate.
**Market-competitiveness gate: failed.** No Kalshi depth, fees, delay, entries
or returns were tested. Sportsbook opening consensus remains the historical proxy.

## Coverage and diagnostics

No native target was dropped. Missing-projection fallback was the exact control
player rate: 110 slots/games in 2022 training, 43 in 2023, zero in 2024 and
116 in 2025. Cold control slots were 571 / 108 / 109 / 114. All raw unidentified
projection rows stay visible in coverage receipts, outside player matching.

2025 remains slightly worse among the 2,310 fully projected games (Steamer Brier
0.243727226 versus control 0.243644049). This descriptive, predeclared coverage
diagnostic does not establish a cause or authorize selecting a more favorable
subset. Calibration slopes for control/Steamer are 0.9518/0.9853 in 2024 and
0.8514/0.8427 in 2025; no calibrated forecasts were produced.

## Validation evidence and material limits

- Direct recency calculations rebuilt 216 player slots, agreeing within 3.17e-15;
  same/future source mutation leaves admitted histories unchanged.
- All original ten inputs and shared handedness columns remain identical between
  arms. Missing-projection slots use exactly the control value.
- Saved model coefficients/scalers replay all 4,852 annual predictions exactly.
  Fits converged in 19–28 iterations without warnings or numerical amendments.
- Separate scalar Brier/log-loss calculations agree within 1.12e-16. All 5,000
  primary and market Brier bootstrap draws were rebuilt with block-multiplicity
  weights; interval differences are below 7.2e-18.
- Original 2,291/2,425 market coverage is retained; no old 13-game exclusion list.

These are same-assistant validation checks, not external review or an independent
full raw-history/fit rerun. Historical initial lineups remain assumed available.
The Owner-labelled exports and 2024 URL establish supplied archive/year provenance,
but original release timestamps, archive revisions and contemporaneous byte
immutability remain unverified. No daily historical projection vintages are claimed.
Those limitations do not turn the failed gates into a passing result.

## Decision and next action

Retain the reference and close this exact comparison. Steamer showed useful
2024 improvement but did not establish stable two-year improvement under the
agreed rule, or sportsbook competitiveness. This does not prove player projections
never help; it rejects promotion/continuation of this tested specification.
Review the outcome before choosing any distinct new hypothesis. Do not retune
the rate, use only the best year, lower gates or add WAR/defense automatically.
No new experiment or operational action is authorized by these results.

Supporting material: [protocol](PROTOCOL.md), [input pins](input_manifest.json),
[slot weights](slot_weights.json), [coverage](feature_coverage.json),
[feature checks](feature_verification.json), [measurement/gates](results.json),
[replay/arithmetic checks](result_verification.json), [runner](run.py),
[measurements](measure.py) and [verification](verify_results.py).
Licensed raw exports, per-game features/predictions and fitted contexts remain
outside public Git. Draft PR #86 stays unmerged; production collectors, pins,
schedules and T−6h studies remain intact. No paid compute or further purchase.
