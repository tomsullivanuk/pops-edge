# Next step: unchanged-reference matched pregame measurement

October 12, 2026. **Background feasibility notes only; deprioritized after Tom’s benchmark-proxy clarification. No implementation or live capture authorized.**

Tom clarified that sportsbook consensus is intentionally the historical Kalshi proxy and that better probabilities, not changing benchmark venue, are the immediate problem. This supersedes the recommended next-step priority below; retain the useful capture specifications as background. The current [next model discussion](MLB_2027_SCORE_MODEL_PROPOSAL.md) is separate and unapproved.
Experiment 01 [failed its continuation gate](../research/pregame_2027/experiment_01/RESULTS.md).
Keep that decision intact: no challenger promotion, retuning, threshold search or
new model variant. This proposal addresses the missing operational comparison,
not a claim that the reference is useful for wagering.

## Recommend the next bounded work

First approve an **offline rehearsal, capped at two focused working days**, using
existing history and genuinely saved pregame payloads. Prove that the unchanged
reference can emit a reproducible forecast from what was actually known, correctly
match the team contract, and calculate both midpoint and executable-cost measures.
If a field, identity or matched timestamp is absent, show the missing case rather
than reconstructing it. Rehearsal fixtures are synthetic/retrospective diagnostics,
never forecasts claimed to have been issued live.

Only after that works should Tom separately authorize a tiny finite matched
capture pilot: at most four preselected games across two future playoff game-days,
at most 100 total provider requests, no automatic extension. Select the slate from
the official schedule before seeing model-price differences or results. If no
playoff slate remains, stop and prepare the regular-season pilot instead.
Playoffs test mapping, input availability, chronology, fee/depth calculation and
replay. They are out of the reference's regular-season domain and cannot provide
regular-season performance/return acceptance. The separate 2027 regular-season
comparison needs its own frozen population, duration and analysis plan.

## What is feasible with current material

| Component | Verified support | Remaining work before live pairing |
|---|---|---|
| Fixed reference inference | Retained annual 2026 reference model/scaler reproduced exactly in experiment 01; ten-input logistic is inexpensive | Pin that existing model/scaler hash; no refit, replacement or calibration |
| Team-history inputs | Retained canonical regular-season scores through September 27; original 60/10-game prior-day rules and resumed handling exist | Turn file-bound builder into an isolated replayable function; maintain an honest completed-history receipt |
| Starter quality/workload | Retained player events through September 27; 365-day window, 180-day decay, 200-BF shrinkage and last-five-start workload rules exist | Reference events use BDL player IDs; live MLB probable starters use MLB IDs. A complete verified bridge for pilot starters has not been demonstrated |
| Pregame identity/orders | Existing finite observer saves official live feeds, full-order status, probable pitchers and response chronology | Provider-published complete order is not explicit confirmation; preserve that distinction |
| Game-to-contract identity | Existing MLB/Kalshi adapters and PR85 date-only postseason matching | Reconcile the exact selected live slate, sides, settlement rules and revisions; fail ambiguous games closed |
| Kalshi price/depth | Existing read-only orderbook/metadata collectors and opposite-bid ask conversion | Add joint forecast/input receipts and complete depth-cost calculations in a separate namespace |
| Fees and delayed paper costs | Official series metadata exposes fee type/multiplier and an effective fee schedule exists | Existing MLB Bet Sheet is before fees; no finished fee-aware matched-native ledger was found. Implement/replay calculation before live use |

This is a code/data feasibility assessment, not a fresh account-access test.
No model/provider requests, credentials or production configuration changed in
this assessment. The observer's BDL trial credential is unavailable; do not assume
paid access or renewal. MLB live feeds were verified by the existing observer,
not recaptured here. Public Kalshi GET capabilities exist in code/documentation;
successful live access for the proposed future slate remains a bounded preflight.

## Can reference features be computed as of live time?

**Yes in principle, conditional on verified identity and complete lagged history;
not yet a demonstrated end-to-end live workflow.** Preserve all ten input formulas
and the current annual model. A daily history snapshot admits only games completed
before the target's New York calendar date and actually retrieved before the
forecast. Never use target-game pitching, final target lineups, future season totals
or later corrections that were not yet observed. Same-day/doubleheader results
remain excluded because the reference excludes them.

At the check, take currently published pitcher identities from the saved live feed,
join them to retained histories through a verified ID bridge, and compute the
original shrunk features. Do not join on a name alone. The original unknown-starter
or no-history league-prior fallback is allowed only with its exact reason/count
recorded; an ambiguous bridge suppresses any paper candidate rather than silently
turning it into a known starter. A fallback forecast may be retained as explicitly
flagged diagnostic data, not treated as a complete-input forecast.

The present feed exposes probable pitchers, not certified starters. Forecasts
using them are honestly prospective **probable-starter forecasts** with unchanged
coefficients, not the retrospective assumed-actual-starter experiment. Require
both published complete unique-nine orders for the proposed lineup-ready record;
those orders are readiness/context, not new batting features. Preserve unknown
confirmation status. A later pitcher/order change invalidates the paper candidate;
retain the originally issued forecast and log the change rather than rewriting it.

For a playoff plumbing run, use the frozen regular-season history through
September 27 and label it explicitly as regular-season-history-only, out-of-domain.
Do not add postseason performances into the reference history by accident.
For 2027, extend the prior-day history from genuine completed regular-season
boxscores, with source availability receipts and tested field/count semantics.
Current official pitch-count fields must be checked against retained BDL counts
(K, BB, HR, BF, outs, start indicator) before claiming compatible live updates.
No new source parser or ID bridge has been implemented/validated here.

## Proposed observation and measurement rules

Keep T−90, T−60 and T−30 minutes relative to latest admitted official scheduled
start as the only checks. A check missed by more than two minutes is recorded
missing; no catch-up forecast or later substitute. Use the first qualifying check
with complete orders, usable starter identities, valid history and unique mapping
as the game's primary paired record. Save failures and later scheduled checks as
diagnostics; do not choose the most favorable time after seeing prices/results.
The two-minute tolerance and next bounds are proposed operational choices,
not empirically established optima.

Use a narrow bounded capture interval: first input request start through last
market response completion at most 30 seconds, with individual request timeouts
bounded so the batch can fit. Compute the forecast using only that input snapshot
and an already-admitted history snapshot. Save actual component times and the
forecast emission time. This is bounded contemporaneous pairing, not an atomic
simultaneous observation. Long/failed batches remain visible unpaired data.

Canonical probability scoring: model home-win probability versus midpoint of the
verified home-team YES bid/ask from the same orderbook snapshot. Do not call an
ask or last trade a market probability. Away-win model probability is 1−p_home.
Preserve both teams' contract observations; score one home-oriented binary outcome
per game to avoid double-counting complementary outcomes. No sample of four
playoff games can demonstrate comparative superiority.

Executable measurement: derive YES ask from opposite NO bids, preserving quantity
and transformation. Record a fixed **one-contract paper probe** for each outcome
as a liquidity/cost diagnostic, not a staking choice. Acquisition cost C comes from
actual ask depth; compute fees F using the captured series metadata and applicable
effective schedule/rounding. Unknown fee rules or insufficient depth means missing
net EV, not zero costs. Net model-implied EV is p−C−F for the one-contract probe;
ROI is EV/(C+F). Probability-minus-ask is a percentage-point difference and remains
separate. See the official [orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook),
[series metadata](https://docs.kalshi.com/api-reference/market/get-series) and
[fee schedule](https://kalshi.com/docs/kalshi-fee-schedule.pdf), checked October 12.
No permanent universal fee multiplier is assumed.

One additional capture 60 seconds after the primary pair revalidates game status,
pitcher/order identity and both books. Report initial and delayed executable costs
for both outcomes without selecting a profitable-looking subset. An initial
one-contract ask is the diagnostic limit cap: delayed ask above it, unavailable
depth, changed input/status, or absent delayed capture means an unfilled probe.
Do not simulate fills at stale initial prices. This pilot does not estimate actual
manual execution or queue fills; its fixed delay is a future-policy design input.

There is **no wager recommendation or alert policy in this pilot**. Negative or
zero net model-implied EV explicitly says “No paper opportunity”; positive EV says
“Unvalidated positive model-price difference; paper only.” Neither authorizes
action. Keep both sides, no threshold tuning, no model-error allowance falsely
labelled a per-game confidence interval. A later selected-entry trial must first
freeze an uncertainty allowance, price cap, quantity and practical return/risk
criteria; this proposal does not quietly choose them.

## What must be saved

- Independent official selected-slate inventory, schedule/status revisions and
  game/phase identity; every planned check, attempted request, missed check and
  no-pair/no-paper reason, including zero-market games.
- Raw private source bytes, endpoint/parameters, request start/completion, hashes,
  publication/effective times where actually supplied, and missing timing fields.
- Full-order and probable-pitcher snapshot, verified provider-ID crosswalk version,
  input/fallback flags, daily history cutoff/source IDs, feature vector, model and
  scaler hashes, emitted probability and actual emission timestamp.
- Contract tickers, YES team/outcome, matching basis, rules/settlement/status,
  two-sided books and depth, home midpoint derivation, fee type/multiplier/schedule
  version, one-contract cost/EV/ROI and signed probability-point difference.
- Delayed snapshot/time, price-cap result, input-change invalidations/unfilled
  probes; later official outcome and Kalshi settlement separately, with retrieval
  chronology and compatible final disposition. No results in pregame inputs.

Raw licensed material and credentials stay out of GitHub. Publish only scrubbed
spec/code, aggregate coverage/latency/measurement findings and decisions. Use a
new private research namespace, not either accepted T−6h study archive.

## Cost, runtime and gates

Offline rehearsal: estimate one to two focused working days; no new subscriptions
or provider calls. Inference itself is tiny local CPU work; ID/count compatibility,
receipts and replay are the substantive work. Existing experiment modeling
environment can be reused read-only. No cloud service or always-on monitor needed.

Future finite pilot: zero proposed provider purchases, no new credentials; Mac
must be awake across the declared checks. Four games would ordinarily require
roughly 60 initial game/feed/metadata/book requests, 12 delayed feed/book requests,
plus bounded schedule/catalog/series/outcome reads, with a hard 100-request ceiling
including errors/retries. Stop at the cap rather than increase it; document gaps.
Actual runtime spans the selected game-days and is driven by schedule and response
latency, not training. Do not promise API access, full coverage or date availability.

Offline acceptance: exact reference inference, verified pilot-starter IDs/count
semantics, chronology mutation checks, team/outcome/complement/depth/fee replay,
negative-edge no-action wording, stale/changed-input and missingness behavior.
This is a readiness gate, not acceptance of model accuracy or paper returns.
If the player bridge/history route cannot be validated with retained material,
deliver quote/input-only rehearsal and report the model-dependent blocker; do not
manufacture a native forecast or buy access.

Pilot acceptance later: trustworthy paired records and honest missed denominators,
no post-cutoff inputs, deterministic cost calculations and replay, no production
mutation. Its aggregate findings decide whether a separately approved 2027
regular-season collection is ready; they cannot promote the model or prove returns.

The existing finite lineup observer continues under its parent's authority; this
proposal launches no second observer or automation. If a future matched pilot uses
an overlapping game, share its existing sufficiently fresh feed observation or
exclude that pair—do not create duplicate polling silently. Existing T−6h
collectors, pins, schedules, phase separation and evidence stay untouched.

## Read-only assessment evidence

Inspected current repository `kalshi_mlb_adapter.py`,
`collect_kalshi_mlb_orderbooks.py`, `mlb_odds_store.py`, `mlb_stats_api.py`,
and fee-metadata-only handling in `retrieve_kalshi_nfl.py`; retained native starter
protocol/builders, 2026 model/events/identities and trial collector contracts.
Official fee/orderbook/series documentation was read. No complete live native
feature/fee-aware comparison sidecar was found. Individual components are
reusable; claiming the complete workflow already works would overstate evidence.

Next Owner decision: approve this **offline rehearsal only**, or revise its scope.
The finite live pilot, regular-season collection and policy remain later decisions.
