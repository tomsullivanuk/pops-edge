# Approved one-session information-chain diagnostic

Tom approved comparing saved pregame batting estimates with actual 2024/2025
initial-nine batting events, then tracing the existing winner models. Freeze
this calculation before inspecting comparative losses. No fit, calibration,
tuning, market-residual analysis, new data or operational action.

Use experiment 04's saved player-slot rates, shared slot weights, hand/native
features, fitted coefficients/scalers and winner probabilities. Preserve its
confirmed source-year association, 2013 event weights and exact missing-projection
control fallback. Both prior failed gates remain failed.

## Definition and comparability gate

One actual batting opportunity contributes denominator
`d = AB + (BB-IBB) + SF + HBP`; its event value numerator is
`.690*uBB + .722*HBP + .888*1B + 1.271*2B + 1.616*3B + 2.101*HR`.
For completed PA records require d=0 or 1, finite nonnegative values and a
mutually exclusive source outcome. Only d=1 observations are scored, with
the numerator as observed V. IBB, sacrifice bunts and interference with d=0
are explicitly counted, not invented zero-value opportunities. No runners-only
or incomplete events. K with safe reach remains an AB-valued zero hit outcome.

Select only PA made by each game's initial-nine players. Map by the frozen
one-to-one game/team/initial-slot and MLBAM–RetroID bridge; substitute hitters
are excluded and counted even if they occupy the same slot. No name matching.
Every native game remains in winner tracing. Zero-opportunity initial hitters
have no batting score, remain counted and are not assigned an actual mean.

Validate source hashes, unique file/row event keys, two sides/unique nine,
slot IDs, observed denominators and archived saved-rate equality. Stop with a
comparability report if identity, denominator or definition consistency fails.
Source-year/archive revision and assumed pregame lineup limitations remain.

## Frozen scores and uncertainty

Primary: paired **per eligible opportunity** squared error
`(own_rate - V)^2` versus `(Steamer_rate - V)^2`. Lower is better; gain is own
minus Steamer. This scores a conditional mean event value, not a categorical
probability, win Brier or batting total forecast. Report each year and equal
average annual losses/gain; also event-weighted pooled values without swapping
the primary weighting. No outcome-selected slicing or new threshold.

Two predeclared aggregation diagnostics:
1. Each observed hitter-game's actual mean N/D (D>0), with equal hitter-game
   weighting. This changes noise/exposure weighting; it is not the primary score.
2. Side-level saved-slot-weighted mean prediction versus weighted actual
   hitter-game means, only where all nine have D>0. Record the incomplete-side
   denominator, no imputed actual means. This conditional subset cannot rescue
   a failed primary result or establish a cause of game-level loss.

For all three scores report paired 14-calendar-day moving-block 95% intervals,
5,000 draws, seed 20261012, with seven-day sensitivity. All events/hitters/sides
from a game/day stay together, include empty days, resample within each year
and average annual scores equally. Original New York game date assigns the block.
Do not use independent-PA standard errors.

## Exact saved winner-model trace

Rebuild each offense feature from all eighteen `slot_weight * saved_player_rate`
terms: weighted home minus weighted away. Rebuild shared handedness/native
columns. Express saved standardized models in raw units:
`raw_beta = coefficient/scale`, `raw_intercept = intercept - raw_beta*mean`.
Require the sum of twelve feature contributions and intercept to replay every
saved probability, within 1e-12.

Allocate the actual Steamer-minus-control logit change using the frozen control
anchor:
`data_term = raw_beta_control_offense * (offense_S - offense_C)`;
`coefficient_term = intercept_S - intercept_C + (beta_S-beta_C)*x_S`.
Their sum must equal the actual logit difference. Record exact private game/slot
traces and public aggregate mean/absolute terms, changed-probability magnitude,
offense coefficients and player-rate/lineup spreads. This is accounting, not
causal attribution. Do not score or promote an intermediate counterfactual model.

## Deliverable and stop

One concise decision memo, aggregate table, reproducible code and independent
verification in draft PR86; licensed raw data and event/player/game traces private.
No new model or decision rule. Report whether batting mean signal is present,
aggregation diagnostics retain it, and the saved winner model actually responds.
Do not claim any branch proves causation. If yearly signs/uncertainty are
inconclusive, explicitly stop rather than choose a fifth fit. Otherwise recommend
one next hypothesis for discussion only; historical batting scores are not market
edge or profitability. Cap one focused session; no deployment/merge.
