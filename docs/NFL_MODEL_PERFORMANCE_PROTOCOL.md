# NFL Model Performance — weekly contract-value protocol

Status: owner-approved design, documentation implementation only. Baseline:
`ffd53eff29fb7d372a0f8758ad9dd8e187a6d912`. No collector or scoring activation
follows from this document. Protocol identifier: `nfl-weekly-contract-value-v1`;
a future activation record must pin its exact content digest and effective time.
Target release is unassigned; MLB remains allocated to v1.2.

## Question and measurement

How accurately did the imported weekly ELWAY forecast and contemporaneously
captured Kalshi market estimate the same NFL contracts' final payout values?
This is descriptive Measurement, not a full probability-distribution evaluation,
profit calculation, Market Edge finding or wagering policy. Include all official
regular-season games in the target week, independent of wagers, workbook rows,
market availability and positive Bet Sheet differences.

Use one home-team-equivalent observation per game, including neutral-site games.
With published home/away win probabilities h and a, ELWAY central value is
`e = (1 + h - a) / 2`. Preserve the source's decimal precision and existing feasible
rounding bounds; do not claim an exact residual tie probability. Invalid or
infeasible probabilities do not become a scored observation.

Use the uniquely matched home-team YES contract with supported full-game rules.
Kalshi best YES bid b comes from positive-quantity YES levels; YES ask is
`1 - best NO bid`. Require both sides in the same valid response, finite prices
in [0,1], and bid <= ask. Midpoint k is `(bid + ask)/2`. Missing, ambiguous,
non-open or unsupported markets remain unavailable. Never substitute the
cheapest route, pool books or borrow ELWAY's tie estimate. Include **no fees**.

For an eligible official result, payout y is 1 for home win, 0 for away win and
0.5 for tie. Source error is `(value-y)^2`; lower is better. Average the errors
on the identical paired game set. Mean `Kalshi error - ELWAY error` is positive
when ELWAY has lower observed error. Count each game once, not each contract
route. Preserve full calculation precision. Empty samples are unavailable,
not zero. Call this squared contract-value error, not binary Brier score or
log loss. These scores do not establish statistical or practical superiority.

## Weekly identity and acquisition

A baseline is keyed by protocol, season and explicit official target week.
A full-season workbook does not enroll every future week. The refresh flow must
show its target week; when ambiguous, require week selection. A new valid ELWAY
import triggers that week's Kalshi capture in the same refresh workflow.
Publication time, actual import time, validation time, each request start/end,
and complete/partial/failed attempt state remain distinct. No Tuesday assumption
or retrospective capture at Silver's publication time is permitted.

Define semantic forecast identity using source, season, published update time
and canonical validated target-week rows, preserving precision and markers.
Retain raw-file digests separately. Renaming or metadata-only Excel re-saving
cannot reset prices. Conflicting rows with the same publication time make that
version ambiguous; neither arrival order nor file naming resolves it.

Order candidates by published update time, not filesystem time or observed
performance. A new validated, unambiguous version imported before the weekly
cutoff becomes the selected candidate even if its capture is partial or failed;
show gaps rather than silently retaining an older version for those games.
A newer invalid input is a visible rejected attempt, not a qualifying forecast.
For an ambiguous newest version, expose unresolved selection rather than silently
falling back. Keep supersession and attempt histories.

For each game, keep the first successful qualifying observation in the selected
version's import attempt. Ordinary odds refreshes and identical imports do not
replace it. A separately recorded manual retry may fill only missing/failed
observations before cutoff; preserve its later request times and identify it as
a retry. No automatic retry subsystem or post-cutoff repair is required/allowed.
The initial capture range and retry delays must be inspectable; requests are
not assumed simultaneous.

## Cutoff, chronology and population

Freeze at the first official game kickoff of the target week, not individually
before Sunday's or Monday's games. Publication, import and selected request
completion must be strictly before cutoff and consistent in order. A request
spanning cutoff cannot qualify. No new prospective baseline is admitted for a
week already started when the protocol is activated.

Derive the cutoff from preserved official schedule history available at the
relevant boundary. If a potentially earlier game is TBD or the week/cutoff is
ambiguous, do not assert eligibility. Corrections append and trigger explicit
re-evaluation: an earlier established start can invalidate affected observations;
a later correction cannot reopen a window already closed. Retain original
reports and the correction lineage. Freezing is deterministic on replay; the
local app need not be awake at kickoff. Never infer missing historical schedule
states from a later schedule.

The frozen baseline covers the whole week's official population, with missing
ELWAY rows/markets represented. Do not mix old forecast versions per game.
Later imports can update the Bet Sheet but not this baseline. Record model age
and publication-to-import delay; no independent eight-day research guard or
24-hour-to-60-minute per-game capture rule is introduced. No silent cross-week
rollover. This compares available ELWAY with the market at import, not equal
underlying information freshness or closing prices.

## Outcomes and correction authority

Official NFL game-summary evidence supplies outcome identity, final phase and
scores. Validate `summary.gameId` against game ID and summary team IDs against
home/away team IDs. Scores must be nonnegative integers. The observed
`summary.phase=FINAL` and `summary.quarter=END_OF_GAME` establish finality with
consistent totals; outer `status=SCHEDULED` is schedule metadata and must not
veto this specific validated summary. Retain both fields and disclose the
mismatch. Other contradictory final evidence remains unresolved, not resolved
by field order. Additional provider final markers require explicit support.

Capture raw response/hash and observation time. Require a supported final
sporting outcome and compatible contract rules. Cancelled, suspended, forfeited,
postponed/fair-price or otherwise unsupported resolution remains excluded with
reason; do not treat it as zero or tie. Settlement/cash-out in an owner's CSV,
clock passage or market closure is not an official research outcome. Corrected
scores create new observations and measurement revisions without overwriting
prior evidence or historical reports.

## States, presentation and scope

Import → validated candidate → complete/partial/failed capture → selected weekly
candidate → frozen baseline → awaiting outcome → scored/excluded/unresolved.
Superseded candidates, rejected inputs and missed opportunities remain visible.
Coverage counts reconcile the official denominator to scored, awaiting and
missing/excluded cases; preserve multiple diagnostics while assigning a single
display disposition per game. Reports pin an analysis boundary and source IDs.
Only evidence available by that boundary can participate.

The eventual tab places season/week filters before paired summaries and a
cumulative chart. Show per-game source values/times, official result, errors and
selection/coverage details. All displays use the same filtered population.
Wager History is independent. Existing archives may support separately governed
historical exploration, never newly claimed prospective enrollment.

Accepted limits: local manual imports, missed captures, partial failures,
rounded ELWAY input, delayed outcomes and descriptive early samples. Defer
hosting, scheduler, closing-line capture, probability calibration/log loss,
formal uncertainty claims, Market Edge automation, postseason, spreads/totals,
profit/loss and model blending. MLB contracts and deployed workflows are unchanged.

## Acceptance examples

- New weekly workbook before Thursday opener captures prices once; reimport,
  renaming and metadata-only re-save do not reset them.
- A genuinely newer publication before cutoff supersedes the whole baseline;
  partial new capture retains gaps, not older per-game substitutions.
- A midweek import or a response at/after first kickoff cannot enter the baseline,
  even for unplayed games. Missing observations can only receive honest pre-cutoff
  retries. An unknown cutoff is unresolved.
- Duplicate market mappings, one-sided/crossed books, same-time conflicting
  forecasts, source tampering and impossible chronology cannot silently score.
- For e=.605 and k=.56: home win errors .156025/.1936; home loss .366025/.3136;
  tie .011025/.0036. No transaction fees or wager counts enter these values.
- Unwagered games and missing inputs remain in coverage; each paired game counts
  once. No observations means no score. Filtered summaries agree with rows.
- Official summary FINAL with validated IDs and scores can resolve despite the
  observed outer SCHEDULED marker; owner cash-out cannot. Corrections preserve
  earlier report replay. Repeated imports/replay never duplicate measurements.

See [source feasibility](NFL_MODEL_PERFORMANCE_SOURCE_FEASIBILITY.md).
