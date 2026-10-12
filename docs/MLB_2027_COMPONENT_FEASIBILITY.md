# Player-component feasibility after experiment 02

October 12, 2026. **Read-only assessment complete; recommend one starter–batter
plate-appearance component, subject to a small data-readiness gate. No fit approved.**

Tom authorized this assessment and durable documentation. Current main verified
as `9564b12dcd80f0b3347b4860b95984763f2e3061`. Experiments 01/02 remain failed,
closed and unpromoted. TabPFN 3.5 permission is separate and pending.

## What is actually retained

Inventory inspected local source manifests, decoded player-event files, original
diagnostic/bullpen reports and the four detailed-game samples. These are retained
historical files, not a newly queried provider inventory. Repeated copies of the
same sample do not create independent observations.

| Evidence | Actual extent | Useful information / important gap |
| --- | --- | --- |
| Derived pitching appearances | 103,937 rows, 2022–2026; 20,877 / 20,634 / 20,695 / 20,878 / 20,853 annually | Batters faced, K, BB, HR, outs, starting role, IDs, chronology/issues; player-game totals, not PA or pitch observations |
| Starter rows in those files | 4,856 / 4,860 / 4,853 / 4,858 / 4,858 annually; 530,170 total batters faced | These starter rows have no recorded count issues; that does not establish complete source coverage or error-free identities |
| Derived batting appearances | 202,701 rows, 2022–2025; 50,267 / 50,751 / 50,749 / 50,934 annually | PA, AB, hits, BB, HBP, total bases and handedness metadata; existing derived table omits batter K and intentional walks |
| Retained 2026 raw stat pages | 72,412 mixed rows; 49,566 positive-PA batting rows, distinct player/game pairs | All these batting rows contain K and intentional-walk fields. This count is not a validated batting-quality/complete-season audit; no new feature table built |
| Detailed provider samples | Four distinct games, one each in 2022–2025: 71 / 77 / 84 / 75 PA; 249 / 314 / 326 / 323 nested pitches | 307 PA and 1,212 pitches total. Pitch speed/type/location exist; all sampled swing and whiff flags are null. PA result labels exist |
| Pitch-type game summaries | Same four games; 123 pitcher/type rows, 315 hitter/type rows | Aggregates rather than a full pitch corpus. Seventy-two copied manifests reduce to twelve distinct endpoint/game samples |

No season-scale PA/pitch archive was found in this inspected project archive.
This does not assert that none exists elsewhere. Provider-ID fragmentation and
invalid history remain documented; never merge namesakes automatically. Existing
final-lineup evidence does not establish historical announcement times.

Private supporting inventory: the named original event files, raw stat manifests,
and `historical_data_readiness/season_2024/prior_evidence/four_historical_samples`.
Raw licensed records remain outside Git; public counts are aggregate summaries.

## Why this component first

The retained 2024 deletion diagnostic found removing starter quality worsened
Brier by 0.001539 (exploratory 14-day interval +0.000098 to +0.002863). Removing
batting worsened it by 0.000293 with an interval crossing zero. These conditional,
single-season results do not rank the ultimate missing information or establish
causal importance. They do provide a firmer starting point for a bounded test.

Offense is materially compressed: nine-player OBP/ISO/hand averages ignore
individual opponent interactions and batting order; that substitution failed in
2025. Bullpen quality/availability is also incomplete, but individual pregame
rosters, injuries, availability and managerial selection require more unverified
state. The existing team-level bullpen K−BB/HR/workload extension added little.
Neither failure establishes that offense or bullpen information has little value.

Recommend **starter–batter matchup probabilities for strikeout, unintentional walk,
or other PA outcome**. This jointly models pitching and opponent offense, rather
than claiming pitching alone is the largest remaining opportunity. It tests
individual outcome attribution and partial pooling, not another K−BB/HR summary
added to the same winner logistic. Pitch mechanics and deep pitch-sequence models
are deferred: the retained sample cannot train them, and their benefit is unproven.

## Obtainable sources, rights and costs

- [Retrosheet parsed PA/event downloads](https://retrosheet.org/downloads/plays.html)
  list annual files through 2025 and document batter/pitcher IDs, handedness, PA,
  K, walk/intentional-walk and lineup fields. [Retrosheet's own use notice](https://www.retrosheet.org/game.htm#Notices)
  permits broad use without a data fee, with prominent prescribed attribution.
  It is an independent historical source, not MLB's official feed. Favor it for
  the first PA experiment; no need to pay for pitch telemetry. Actual archive
  size, completeness, suspended-game chronology, starter reconstruction and ID
  mapping have not been validated because no archive was downloaded here.
- [Official Baseball Savant CSV documentation](https://baseballsavant.mlb.com/csv-docs)
  exposes pitch telemetry, MLB player IDs and terminal PA events. MLB's
  [general terms](https://www.mlb.com/official-information/terms-of-use) restrict
  automated collection; public CSV access is not a blanket license. No new
  scripted season ingestion, permissions acceptance or vendor inquiry here.
- [BALLDONTLIE documentation](https://mlb.balldontlie.io/#account-tiers) lists
  pitcher/hitter pitch-type detail at GOAT, $39.99/month for MLB at this check;
  ALL-ACCESS is $299.99/month. An API key is required. This is advertised access,
  not verified current account entitlement, season completeness or redistribution
  rights. Terms page retrieval failed; do not infer rights from prior samples.
  Trial signup requires payment details and is outside scope. No purchase needed
  for the recommended Retrosheet route.

Readiness can use Retrosheet identities consistently without a provider bridge.
Later joining this component to the existing game model needs explicit, audited
game/player crosswalks. Free source cost does not remove parsing/validation effort.

## One proposed experiment, after readiness and approval

**Target:** conditional three-category PA probabilities against the initial
starting pitcher. Train on completed PA outcomes with intentional walks excluded
by a frozen rule; record their count in coverage. K includes strikeouts where the
batter reaches safely. Walk means unintentional walk; HBP/contact/interference
remain in other. Validate mutually exclusive/exhaustive labels before fitting.

**Information:** pitcher and batter identity, handedness and lagged completed
PA histories. Produce matchup probabilities once before each game's first pitch,
using strict prior-New-York-day history; no target-game pitch speed, count, score,
actual batters-faced exposure or same-day result is an input. Evaluate observed
starter matchups as a conditional component task. Actual substitute/matchup
identities and pitcher survival are not guaranteed known pregame; this experiment
does not forecast which matchups occur, starter duration or total strikeouts.
Missing/ambiguous identity and outcome coverage must remain visible for both fits.

**Strong baseline:** training-only regularized multinomial logistic on lagged,
shrunk pitcher K/BB rates, opponent batter K/BB rates and handedness pairing.
Include a league-only diagnostic, but do not use it as the continuation comparator.
Baseline windows/shrinkage and its small regularization grid must be frozen before
outer evaluation; use chronological inner validation, not the outer season.

**Single challenger:** multinomial partial-pooling pitcher and batter effects,
plus common handedness pairing and lagged form terms. Estimate categorical
probabilities jointly so they sum to one. Hierarchical shrinkage handles thin/new
players. Use the same histories and populations as the strong baseline; no
batter–pitcher pair memorization, pitch-data expansion or architecture search.
Detailed equations, penalties and optimizer controls still require a pre-fit protocol.

**Chronology:** train through 2023/evaluate 2024, then through 2024/evaluate 2025,
using 2022 onward for history. Tune only on rolling earlier seasons (2023 inner
validation for the first outer fit). Annual parameters stay fixed; previously
completed games update lagged histories. These are reused development seasons.
2026 is not promised: the currently listed Retrosheet annual PA files end in 2025.

**Proposed continuation gate:** at least 0.5% relative improvement in average
annual per-PA multiclass log loss against the strong baseline, improvement in
both years, no worse average multiclass Brier, and a paired 14-calendar-day
interval excluding zero (7-day sensitivity). Group PAs within games/days rather
than bootstrap pitches independently. Show both PA-weighted primary and
equal-game sensitivity, calibration and cold-start coverage. This is a proposed
engineering threshold, not economically derived or already agreed. Freeze it
with a five-focused-working-day fitting/verification effort cap after readiness;
failure closes this specification without a new family or retuning automatically.

## Connection to winner probabilities and the market goal

A passed component gate only shows improved conditional K/walk prediction.
It does not imply better final scores, winner probabilities or a market edge.
The other category still mixes singles, extra-base hits, outs and tactical events;
K reaching base and baserunning also prevent a direct three-state run simulator.

A later separately proposed integration would supply matchup K/walk probabilities
to a richer PA/run model, alongside contact outcomes, lineup order, starter
duration and reliever selection. That model would generate score/winner
distributions. Avoid simply inserting a new starter score into the failed winner
regression and claiming the component result validates the game prediction.
The unchanged reference and sportsbook proxy must remain comparators on identical
games; winner Brier/log loss and fresh validation decide game-level usefulness.
Any eventual opportunity policy separately needs executable Kalshi prices,
depth, fees, delay and uncertainty. Component accuracy cannot satisfy that gate.

## Decision and next gate

Assessment accepted as a feasible direction with a **data-readiness blocker**:
no sufficient validated PA archive is retained. The authorized assessment and
GitHub documentation are complete; no acquisition or training happened.

Recommend Tom authorize one small Retrosheet readiness pass: one 2023 annual
parsed archive plus required season metadata, up to 100 MB compressed / 1 GB
expanded and one focused working day; audit a deterministic 100-game sample,
schema, labels, starters, identifiers and suspended-game handling, without a fit.
Stop visibly if bounds or scientific checks fail. Then return the concrete frozen
experiment protocol for agreement before acquiring more seasons or training.
The [separate readiness handoff](MLB_2027_COMPONENT_READINESS_HANDOFF.md) is a
proposal, not execution authority. No need to wait for the unrelated 3.5 inquiry.
