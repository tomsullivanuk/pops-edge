# One proposed comparison: preseason Steamer versus our lagged batting rates

Status: **data/identity/year association readiness passes;
approved by Tom for bounded offline execution.** October 12, 2026.
Prior experiments remain closed and unpromoted. Read the
[information assessment](MLB_2027_PLAYER_INFORMATION_GAPS.md) and
[export/coverage receipts](../research/pregame_2027/projection_feasibility/).

## Question and contrast

Do preseason Steamer hitter forecasts improve game-win probabilities compared
with our own lagged hitter rates when lineup identities, exposure, feature count
and learner are held fixed? This tests information quality, not another model swap.

Use two 12-input L2 winner logistics: the retained ten team/starter inputs, one
home-minus-away lineup offense index, and one shared opposite-handed matchup
share. The control's offense index uses our prior-day PA histories; the challenger
uses the corresponding preseason Steamer event-count forecast, fixed all season.
Keep the same initial nine and batting-order weights in both. Do not add WAR,
fielding/baserunning, new pitcher features, platoon forecasts or percentiles.
Report the unchanged native model and sportsbook proxy as separate references.

## Input readiness

All four supplied CSVs are readable on this executor, outside Git. The 2024
file is linked to Tom's exact `steamer_2024` batting URL. Tom supplied replacement exports labelled 2022, 2023, 2024 and 2025 immediately
after selecting each historical year. All match the corresponding earlier files
byte-for-byte and by normalized content: -2=2022, -3=2023, -4=2025. No correction
to the provisional mapping was needed. This is Owner-supplied year provenance,
not independently observed browser actions.
Original release timestamps and archive revisions are unverified limitations;
do not call these contemporaneously retained preseason bytes or daily snapshots.

| Candidate year | Identified projection rows | Required batters matched | Slots matched | Both nines fully projected |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 3,303 | 676 / 678 | 43,612 / 43,722 | 2,319 / 2,429 games |
| 2023 | 3,590 | 641 / 643 | 43,571 / 43,614 | 2,380 / 2,423 games |
| 2024 | 3,710 | 645 / 645 | 43,668 / 43,668 | 2,426 / 2,426 games |
| 2025 | 4,138 | 660 / 661 | 43,552 / 43,668 | 2,310 / 2,426 games |

Identified rows have unique FanGraphs/MLBAM IDs and finite nonnegative required
rates/counts. Every file has one unnamed row without IDs; 2025 also has a named
row without MLBAMID. Neither joins to a target. These remain visible, not silently
counted as matched players. Event denominators are positive, H<=AB and IBB<=BB.
Published fractional hit totals differ from component sums by at most 0.000112
expected hits; preserve the values and allow 0.0002 absolute consistency tolerance,
without modifying them. This is a pre-fit arithmetic tolerance, not result tuning.

All 9,704 native games join to retained Retrosheet initial lineups. Joining official
MLBAM IDs to RetroIDs by the same game/team/initial slot yields 1,022 one-to-one
player pairs across 174,672 slots, with zero two-way identity conflicts. No name
matching is required. Readable-byte hashes, scope and private lineage provenance
are retained. No more paid data, registration or pitch archive is needed.

## Fixed offense construction and missing-player rule

To isolate the forecast information rather than different provider scale constants,
calculate the same fixed **2013-weight run-value index** in both arms:

`(.690*uBB + .722*HBP + .888*1B + 1.271*2B + 1.616*3B + 2.101*HR)
 / (AB + uBB + SF + HBP)`, with `uBB=BB-IBB`.

The [historically published weights](https://library.fangraphs.com/offense/woba/)
predate all target seasons. Label this common index explicitly; it is not the
provider's current-year wOBA or park-adjusted wRC+. Supplied wOBA/WAR fields are
metadata/checks only. No target-year league constants are learned from evaluation.

Control: trailing 365 calendar days, half-life 180 days, completed-game availability
strictly before original New York target day. Shrink numerator/denominator with
200 pseudo-denominator opportunities toward the equally lagged league index;
initial no-history league index .320. Available-day release uses the latest
documented original/resumption/play date. Same/future-day performance never enters.
Player history pools teams, using the verified MLBAM/RetroID bridge.

Challenger: derive the index from that year's preseason projected event counts,
fixed throughout the season. If a target has no valid matching projection, use
**the control player's index**, making that player's data contrast zero. Retain
every game and show IDs, slots and games using this fallback. No missing-projection
game deletion, retrospective roster filter or substitution of another system.

For each annual fit, learn common slot weights from completed training-season
PA counts by initial batting-order slot, counting slot opportunities including
substitutes; normalize all nine weights to sum one. Freeze them through its outer
year, then apply them to each initial nine. Their exact derivation and exceptional
substitution handling must be pinned/validated before outcome inspection. Shared
handedness is the existing opposite-hand indicator, not new measured split quality;
use prior observed batter hand and the retained starter-hand policy, with .5 unknown.

## Chronology and fitting

Train 2022–2023 (4,852 native games), evaluate 2024 (2,426); then train through
2024 (7,278), evaluate 2025 (2,426). These are reused development seasons.
2021 team warm-up remains unchanged; no extra projection year is required.
Use the same logistic C=1, deterministic fitting settings and training-only
standardization in both arms. Annual coefficients/scalers/slot weights stay fixed;
only previously completed games update the control's history. No parameter sweep,
calibration, model-family change, outcome-inspected exclusions or split selection.
Historic final-lineup availability remains an offline assumption, not an asserted
announcement time; prospective lineup timing is not a modeling blocker.

## Evaluation and continuation rule to agree

Primary: paired winner Brier and log loss for challenger versus matched control
on all 2,426 games in each year. Show original market intersections (2,291 in
2024; 2,425 in 2025), both new arms, saved native forecasts and sportsbook opening
consensus. No prior 13-game exclusion list or inferred Kalshi quotes.

Propose an **information-improvement gate**: equal-average annual Brier gain
against control >=0.001, positive in both years, no worse pooled log loss,
14-calendar-day paired 95% Brier-gain interval above zero, and unchanged coverage.
Use 5,000 paired calendar-block replicates, seed 20261012, 7-day sensitivity.
Calibration and missing-projection/cold-history strata are diagnostics only.

Separately, **market competitiveness** requires lower pooled common-population
Brier and log loss than sportsbook consensus, with no worse annual Brier in either
year. Passing the information gate alone justifies further research discussion;
it does not pass this market gate or establish an actionable edge. Even favorable
reused-season results need fresh validation before product promotion.

Propose five focused working days after agreement for feature construction,
implementation freeze, fits and verification. Confirm source/label/identity
reconciliation, direct feature reconstruction, same/future-game mutation,
missing-projection fallback, saved probability replay and independent score/block
arithmetic. Record failed gates/numerical failures and stop without automatic
retuning. Neither paid access nor training happens under this proposal alone.

## Decision

Repository, field and identity readiness: **go**. Source-year association: **reconciled by the labelled replacement exports**;
no further year-confirmation request is needed.
Historical publication/revision limitations remain visible in the protocol.
Training: **approved by Tom**, including the stated fallback and two distinct gates. No purchases, credentials, collector/pin/schedule
changes, T−6h changes, trading, merge or deployment follow from agreement to research.


## Execution approval

Tom explicitly answered yes to running this proposal at `1d64e15`. Authority covers the bounded offline comparison and draft results only. Implementation uses identical C=1 lbfgs logistics, tol=1e-8, max_iter=10000, one BLAS thread, four annual arm fits and saved native references. Slot opportunities count every valid regular-season PA in native training games, including substitutions/IW; source lineup position assigns the slot. Raw exports remain private.


## Completed execution

[Experiment 04](../research/pregame_2027/experiment_04/RESULTS.md) is complete and verified. Both agreed gates fail; the specification is closed without automatic tuning or further evaluation. The approval covered this completed bounded run, not a new experiment or production promotion.
