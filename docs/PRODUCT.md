# Pops' Edge Product

Pops' Edge separates durable Identity, immutable Evidence, deterministic
Analysis, and mutable Policy. Expected value explains reproducible economics
from compatible forecast and executable market evidence; it is not a
recommendation. Thresholds, liquidity/freshness requirements, bankroll,
sizing, and bet/no-bet decisions remain Policy.

Executable market analysis is side- and quantity-aware and uses visible depth.
Provider bids and complement-derived offers remain distinguishable, fees are
explicit Analysis inputs, and valuation is derived rather than source
evidence. Closed or illiquid markets may still be preserved as evidence but
are operationally non-executable independent of recommendation policy.

## Vision

Pops' Edge is a durable, reproducible external-forecast evaluation platform.
It imports probability forecasts from independent forecast providers and
prices from prediction-market providers, preserves each source independently,
and compares forecast observations with executable market observations. It
helps an operator identify potential edges, form recommendations, manage
positions and a portfolio, and evaluate performance without hiding the
evidence or assumptions behind a decision.

Pops' Edge does not presently aim to create its own underlying probability
forecasts. Its product responsibility begins with evaluating forecasts supplied
by external providers. Forecast providers must remain interchangeable and
independently evaluable; no provider is permanently privileged as “the model.”

The product is not defined by one exchange, source, tournament, or report.
Kalshi is the current market provider and the World Cup system is the first
production implementation, but both sit within a broader product identity.

## Product philosophy

1. **Evidence before implementation.** Research sources and semantics before
   building adapters or shared contracts.
2. **Preserve provenance.** Retain what each source reported, when it reported
   it, when it was collected, and how it was transformed.
3. **Fail closed on ambiguity.** Missing an opportunity is preferable to
   presenting a false edge caused by uncertain identity, timing, mapping,
   freshness, or settlement meaning.
4. **Prefer interchangeable providers.** Provider-specific behavior must not
   become product logic.
5. **Keep sport-specific rules in adapters.** Shared concepts must not erase
   schedules, identifiers, participants, or settlement semantics.
6. **Earn shared architecture.** Reuse should emerge from multiple working
   implementations rather than speculative generalization.
7. **Compare external forecasts.** Building a proprietary prediction model is
   outside the current product vision.
8. **Evaluate commercial data deliberately.** Judge value, cost, rights,
   reliability, coverage, and maintainability together.
9. **Decide consequential questions explicitly.** Product and architecture
   decisions precede substantial coding.
10. **Optimize for long-term coherence.** Implementation speed does not justify
    hidden policy, lost provenance, or unstable boundaries.

Generated workbooks and HTML remain derived outputs, human judgment remains
central, new sports must not destabilize a working sport, and each PR remains
bounded and reviewable.

## Product language

- A **forecast provider** is the durable source that owns one or more
  **forecast models**; each model may have separately identified **forecast
  versions**. A **forecast series** identifies one provider/model/version
  forecast for one Canonical Event. A **forecast observation** is immutable
  evidence of what that Series published at one point in time, including its
  complete structured outcome distribution.
- A **market provider** lists tradable contracts; a **market observation** is a
  timestamped price, depth, volume, rules, and side mapping from that provider.
- A **canonical event** is Pops' Edge's normalized immutable event identity,
  including authoritative sport-native identifiers. Provider-native mappings
  are separate immutable records linked to that identity so later discovery
  does not mutate the event.
- An **edge** is a derived comparison between an eligible forecast observation
  and an executable market price.
- A **recommendation** is a policy-governed proposed action based on an edge;
  it is not the forecast itself.
- A **position** is exposure to a contract; the **portfolio** is the collection
  of positions and their risk and performance.
- An **outcome** is the settlement-relevant event result.
- **Performance evaluation** measures forecasts, recommendations, prices, and
  positions against outcomes while retaining their original information state.

Event facts, observations, comparisons, recommendations, positions, and
outcomes are distinct records. A later value must not silently overwrite an
earlier observation needed for audit or historical evaluation.

Pops' Edge uses a consistent Series / Observation pattern where evidence
naturally changes over time: durable identity owns append-only observations,
and current state is derived rather than stored. A Forecast Series represents
the conceptual “one forecast”; every provider update is a new immutable
Forecast Observation. Latest forecast, latest pregame forecast, forecast
history, and forecast movement are computed views, not source evidence.

Provider, model, and version metadata is referenced rather than duplicated in
each observation. Provider assumptions are preserved as reported and remain
separate from authoritative event facts. Published values and precision are
preserved; inconsistent distributions are flagged, never silently normalized.
Unknown provider timestamps and versions remain explicitly unknown rather
than being inferred from collection time.

Pops' Edge distinguishes identity, evidence, and policy. Identity—including
Canonical Event, Forecast Series, Provider, Model, and Version—defines what
exists; evidence records what a source reported at a point in time; policy
decides how Pops' Edge evaluates and acts on that evidence. Approval, weights,
freshness, eligibility, edge requirements, Kelly settings, and portfolio
limits are policy. They may change without rewriting immutable identity or
historical evidence.

Series identify the thing being observed. Observations preserve what was known
at a point in time. Derived views answer operational questions without
rewriting history. Durable objects are referenced rather than duplicated, and
observations are never updated in place.

> Identity is immutable. Evidence is immutable. Policy is mutable.

> Forecast Observations report what a provider published; they do not decide
> whether Pops' Edge should wager.

## Commercial data philosophy

Pops' Edge may use commercial data when it materially improves long-term
quality, reliability, permitted automated use, legal clarity, stable
identifiers, historical coverage, or operational maintainability. A source
decision must consider monthly and annual cost, pricing structure, minimum
contract term, API limits, retention rights, attribution, historical access,
source quality, and realistic value to this personal-use product.

As a present preference, approximately USD 100 annually may be reasonable;
approximately USD 100 monthly generally would not be. Higher cost requires
explicit product approval supported by demonstrated value. This is guidance,
not a universal architecture budget.

Naming a provider does not approve it. Sportradar, SportsDataIO, DRatings,
FanGraphs, The Odds API, and all other providers remain candidates until their
access method, permitted use, retention rights, reliability, and actual cost
are understood and explicitly approved.

For v1.1.0, the MLB Stats API is approved as the first read-only MLB facts
source for this personal, noncommercial project. This approves a bounded facts
adapter, not a permanent architecture dependency and not any forecast, market,
or commercial provider. Canonical Event and downstream observation contracts
remain provider-neutral so a licensed facts source can replace it later.
Adapter evidence distinguishes exact response-byte identity from canonical
JSON equivalence, and every game reports an explicit complete, partial, or
rejected outcome. Provider timestamps are never invented from collection time.

PR6 approves DRatings only as a manually captured local forecast-evidence
source; it does not approve automated access. The adapter preserves the
Upcoming table's ordered matchup names, exact UTC time, displayed pitcher
assumptions, and two published win probabilities. A page-level update time is
not a row timestamp. DRatings supplies neither MLB `gamePk` nor authoritative
team/pitcher identity, a disclosed model version, or a proven stable forecast
record ID. Separately captured MLB evidence establishes event identity and
home/away roles. Complete, partial, ambiguous, and rejected outcomes keep
uncertainty visible and create a Forecast Series only with a valid first
observation.

## Supported sports

| Sport | Status | Product version |
|---|---|---|
| FIFA World Cup | Production baseline | v1.0.0 |
| MLB | Planned research and implementation | v1.1.0 |
| Other sports | Deferred | Future |

“Supported” means the sport has documented sources, contracts, valuation rules,
reports, tests, and an operator workflow. Product documentation must not imply
support before those conditions are met.

## Platform and adapter relationship

Reusable platform components should address concerns that genuinely recur:

- configuration and sport registration;
- forecast and market provider boundaries;
- immutable observations, provenance, and freshness;
- canonical events and source mappings;
- edge analysis, recommendations, positions, portfolios, and performance
  evaluation;
- validation and quality reporting;
- deterministic fixture testing;
- output isolation and archives; and
- common presentation utilities where schemas actually align.

Sport-specific adapters should retain:

- provider acquisition, authentication, native schemas, parsing, identifiers,
  and timestamps;
- team, event, game, and market identifiers;
- calendars, stages, doubleheaders, postponements, and cancellations;
- starting pitchers, knockout rounds, and penalty shootouts;
- market matching and settlement assumptions;
- sport-specific probability and valuation policy; and
- sport-specific reports when operator needs differ.

The boundary is empirical. Shared abstractions must be earned through multiple
working implementations. World Cup and MLB justify common product concepts,
but not a broad rewrite of the production World Cup system.

## Long-term direction

Pops' Edge should evolve into a portfolio of independently operable sport
adapters on a small, well-tested analytics foundation. Future releases may add
sports, providers, source comparisons, calibration, portfolio analytics, and
operational tooling. Automated trading, generalized hosting, and broad
architecture rewrites require separate product decisions and are not implicit
in this direction.
