# Pops' Edge Product

## Mission

Pops' Edge is a quantitative decision platform whose purpose is to identify
opportunities with demonstrable statistical advantage. It accomplishes this
by collecting high-quality Evidence, objectively measuring forecasting
performance, developing and validating Forecast Policies, and applying those
policies to identify positive expected-value opportunities. The platform
continuously measures its own performance so that every Forecast Policy is
supported by empirical Evidence rather than intuition.

Sports wagering is the current proving ground for this decision framework. It
is an application of the platform, not the platform's defining purpose. The
same capability boundaries are intended eventually to support other domains
where reproducible forecasts, observable outcomes, and actionable market or
decision Evidence can be reconciled. No additional domain is currently
implemented or implied by that direction.

## Product capability hierarchy

Every durable product capability exists to support the Mission:

```text
Mission: identify opportunities with demonstrable statistical advantage
    ↓
Identity
    ↓
Evidence
    ├── Forecast Observation
    ├── Outcome Observation
    ├── Market Observation
    └── Position Observation
    ↓
Measurement
    ↓
Forecast Evaluation
    ↓
Forecast Intelligence
    ↓
Forecast Policy
    ↓
Policy Forecast
    ↓
Opportunity Analysis
    ↓
Execution
```

- **Identity** defines the canonical events, participants, propositions,
  providers, models, versions, and Series to which observations refer.
- **Evidence** preserves what authoritative and external sources reported,
  when they reported it, when it was collected, and how it was transformed.
- **Measurement** evaluates forecasts, Forecast Policies, opportunities,
  decisions, and outcomes using reproducible historical information states.
- **Forecast Evaluation** reproducibly compares one Forecast Observation with
  one Outcome Observation for the same Canonical Event.
- **Forecast Intelligence** transforms Evidence into objective knowledge about
  forecast quality and the comparative performance of forecasting providers
  and models.
- **Forecast Policy** defines a versioned, testable method for converting
  eligible current Forecast Observations into a derived Policy Forecast. Its
  selection and configuration are justified by Forecast Intelligence.
- **Policy Forecast** is the immutable derived probability distribution
  produced by executing one Forecast Policy for one Canonical Event.
- **Opportunity Analysis** applies a Policy Forecast to compatible current
  Market Evidence to identify statistically advantageous opportunities.
- **Execution** consumes the preceding capabilities when an approved action is
  warranted. It is one consumer of the platform, not its purpose.

The current implementation uses the narrower durable boundary documented in
`ARCHITECTURE.md`: Identity, Evidence, deterministic Analysis, and mutable
Policy. The hierarchy above states the intended product capabilities without
claiming that each has already been fully implemented. In particular,
Opportunity Analysis remains deterministic analysis rather than a
recommendation, and current Execution remains manual.

## Outcome Evidence

Outcome Evidence establishes what actually happened. It consists of immutable
provider facts represented as Outcome Observations. For MLB, the MLB Stats API
is authoritative. Kalshi settlement, DRatings completed tables, sportsbook
results, and other sources may corroborate those facts but are not
authoritative Outcome Evidence.

Outcome Evidence does not decide whether a forecast should be evaluated.
Evaluation Eligibility is Policy. It can select eligible Forecast Observations
and Outcome Observations without changing either source record.

## Forecast Evaluation

A Forecast Evaluation is immutable, reproducible derived Analysis for exactly
one Canonical Event. It compares one Forecast Observation with one Outcome
Observation and measures the complete probability distribution that the
provider published, not merely whether its highest-probability side won.

Forecast Evaluation is distinct from future market-relative evaluation and
wagering evaluation. It never becomes Evidence, even though a particular
evaluation remains immutable once its inputs and method are fixed.

## Guiding principle

> **Every Forecast Policy must earn the right to exist through empirical
> Measurement.**

A Forecast Policy is a hypothesis, not received truth. Reproducible historical
Measurement determines whether it enters or remains part of the platform.
Intuition may motivate a candidate Forecast Policy, but intuition alone never
justifies using it. Competing Forecast Policies must be evaluated against
preserved Evidence and outcomes using explicit, repeatable methods.

## Current analytical boundary

Expected value explains reproducible economics from compatible forecast and
executable market Evidence; it is not a recommendation. Thresholds,
liquidity/freshness requirements, bankroll, sizing, and bet/no-bet decisions
remain mutable Policy in the current architecture.

Executable market analysis is side- and quantity-aware and uses visible depth.
Provider bids and complement-derived offers remain distinguishable, fees are
explicit Analysis inputs, and valuation is derived rather than source
Evidence. Closed or illiquid markets may still be preserved as Evidence but
are operationally non-executable independent of recommendation Policy.

The Opportunity Board is the primary MLB product interface. It combines
forecast and market Evidence, deterministic valuation, and current position
awareness to answer what has value, what is already owned, and what needs
attention.
Attention ordering is deterministic presentation. Constrained or adverse
existing exposure comes first, followed by unresolved diagnostics, other
existing exposure, positive-EV unheld analyses, and remaining complete rows.
Cost basis, executable-quantity P/L, EV, liquidity, and stable Identity provide
documented tie-breakers. “Positive” means only mathematically positive expected
value; it neither recommends nor sizes a wager.

Expandable diagnostics keep Evidence, reconciliation, valuation, and
provenance available within the same board. The manual workflow rebuilds this
derived surface from local inputs and emits a concise factual summary; no
Opportunity is persisted.

Positions are authoritative open-position summaries identified by provider
market, proposition, event, and semantic side. Offsetting YES and NO exposure
remains separate. Position value consumes visible executable exit depth, and
P/L is shown only for the executable quantity; any remainder is explicitly
unpriced.
Downloaded activity may be normalized into that summary only after exact
market/event/side reconciliation. Trades establish or reduce exposure;
unfilled orders do not. Fees remain visible Evidence separate from average
entry cost. The board labels its bounded public order-book capture range and
uses a one-contract comparison quantity solely for analysis, not sizing.
Pregame forecast comparison requires market capture strictly before first
pitch. In-play books may still value current liquidation exposure, but they do
not produce forecast-comparison edge. Until production Kalshi fees are
approved, displayed comparison values are Gross Edge before fees, never net
EV. Lifecycle states such as Settled and Suspended take precedence over absent
depth. Paired team lines always display away first and home second while the
underlying Evidence preserves provider order.
Operational validation deliberately retains two information states: August 2
shows the normal pregame board with an activity-derived zero-position state,
while August 1 proves that position monitoring and fail-closed game status
remain correct after games begin or propositions reject.

## Vision

Pops' Edge should become a durable, reproducible quantitative decision
platform. Today it imports probability forecasts from an external forecast
provider and prices from a prediction-market provider, preserves each source
independently, and compares forecast observations with executable market
observations. Over time, Measurement, Forecast Intelligence, and competing
Forecast Policies should make the empirical basis of each opportunity and
decision inspectable without hiding Evidence or assumptions.

Pops' Edge does not presently aim to create its own underlying probability
forecasts. Its product responsibility begins with evaluating forecasts supplied
by external providers. Forecast providers must remain interchangeable and
independently evaluable; no provider is permanently privileged as “the model.”

The product is not defined by one exchange, source, sport, tournament, or
report. MLB, DRatings, and Kalshi are the current proving-ground combination;
the World Cup workflow remains the production baseline. Multiple forecast
providers, additional sports, and non-wagering domains are planned evolution,
not present capabilities.

## Forecast Providers

Forecast Providers publish original probabilistic forecasts and create
Forecast Observations. DRatings is the current MLB Forecast Provider; future
providers and internal models may participate through the same architectural
boundary.

A Forecast Provider does not evaluate itself, combine itself with another
provider, assign its own weight, or determine whether it should be trusted.
Those responsibilities belong to Measurement, Forecast Intelligence, and
Forecast Policy. No additional MLB Forecast Provider is currently implemented.

## Forecast Intelligence

Forecast Intelligence is the provider-neutral capability that transforms
Evidence into actionable knowledge. It evaluates forecasting providers,
measures forecast quality, compares competing models, evaluates calibration,
computes objective performance metrics, supports the development of Forecast
Policies, and preserves reproducible historical evaluation.

Forecast Intelligence does not merely average models, and it does not
permanently privilege a provider or create forecasts. It is always derived
from immutable Forecast Evaluations, never stored as mutable accumulated state,
and never becomes Evidence. Its conclusions must be reproducible from their
referenced evaluations. It supports Forecast Policy comparison, selection,
configuration, replacement, and empirical justification, but does not provide
today's event probabilities. The current platform has one MLB Forecast
Provider, DRatings; Forecast Intelligence, comparative provider analysis, and
calibration tooling remain approved direction rather than implemented
capabilities.

## Forecast Policy

A Forecast Policy is a versioned, measurable, and replaceable rule set. Its
adoption and configuration must be justified by Forecast Intelligence. When
executed for a current Canonical Event, it consumes eligible current Forecast
Observations according to explicit rules. It preserves all input Forecast
Observation identities and never mutates or replaces provider Evidence.

Candidate Forecast Policies may include a single-provider Forecast Policy,
equal-weight combination, fixed weighted combination, exclusion of stale or
incomplete observations, and future adaptive Forecast Policies. These are
competing rule sets, not declarations of “the correct model.” Each must
demonstrate value through reproducible Measurement before adoption and remain
subject to replacement when later Measurement no longer supports it.

## Policy Forecast

A Policy Forecast is the immutable derived Analysis produced by executing one
Forecast Policy against eligible current Forecast Observations for exactly one
Canonical Event. It preserves the Forecast Policy identifier and version;
input Forecast Observation identifiers; provider, model, and version identity;
eligibility and exclusion decisions; weights or transformation parameters; the
resulting probability distribution; deterministic derivation identity;
limitations; and an appropriate derivation or Analysis timestamp.

A Policy Forecast is not provider Evidence, never becomes Evidence, and never
claims that a provider published the derived distribution.

## Opportunity Analysis

Opportunity Analysis consumes a Policy Forecast together with compatible
current Market Evidence. Once the Forecast Policy capability is implemented,
it does not consume provider Forecast Observations directly. It remains
separate from wagering Policy, Kelly sizing, bankroll management,
recommendation thresholds, and Execution.

The current MLB workflow compares DRatings Forecast Observations directly with
Kalshi market Evidence under deterministic PR7 valuation. That is the present
single-provider precursor to the fuller Forecast Policy capability, not a
claim that Forecast Intelligence, Forecast Policy execution, or Policy
Forecast has already been implemented.

Historical learning and Policy governance follow this conceptual flow:

```text
Forecast Observations + Outcome Observations
                    ↓
          Forecast Evaluations
                    ↓
         Forecast Intelligence
                    ↓
Forecast Policy selection and configuration
```

Current-event execution follows a separate flow:

```text
Eligible current Forecast Observations
                    ↓
       Forecast Policy execution
                    ↓
             Policy Forecast
                    ↓
          Opportunity Analysis
                    ↓
                Execution
```

Forecast Intelligence does not replace current Forecast Observations, and
Forecast Policy execution does not turn its derived output into Evidence.

## Product philosophy

Research is not an end in itself. Measurement exists to improve future
decisions, and every adopted Forecast Policy remains subject to continuous
validation against empirical Evidence.

1. **Every Forecast Policy must earn the right to exist.** Require empirical,
   reproducible Measurement rather than intuition alone.
2. **Evidence before implementation.** Research sources and semantics before
   building adapters or shared contracts.
3. **Preserve provenance.** Retain what each source reported, when it reported
   it, when it was collected, and how it was transformed.
4. **Fail closed on ambiguity.** Missing an opportunity is preferable to
   presenting a false edge caused by uncertain Identity, timing, mapping,
   freshness, or settlement meaning.
5. **Prefer interchangeable providers.** Provider-specific behavior must not
   become product logic.
6. **Keep sport-specific rules in adapters.** Shared concepts must not erase
   schedules, identifiers, participants, or settlement semantics.
7. **Earn shared architecture.** Reuse should emerge from multiple working
   implementations rather than speculative generalization.
8. **Compare external forecasts.** Building a proprietary prediction model is
   outside the current product vision.
9. **Evaluate commercial data deliberately.** Judge value, cost, rights,
   reliability, coverage, and maintainability together.
10. **Decide consequential questions explicitly.** Product and architecture
   decisions precede substantial coding.
11. **Optimize for long-term coherence.** Implementation speed does not justify
    hidden Policy, lost provenance, or unstable boundaries.

Generated workbooks and HTML remain derived outputs, human judgment remains
central, new sports must not destabilize a working sport, and each PR remains
bounded and reviewable.

## Product language

- A **forecast provider** is the durable source that owns one or more
  **forecast models**; each model may have separately identified **forecast
  versions**. A **forecast series** identifies one provider/model/version
  forecast for one Canonical Event. A **forecast observation** is immutable
  Evidence of what that Series published at one point in time, including its
  complete structured outcome distribution.
- A **market provider** lists tradable contracts; a **market observation** is a
  timestamped price, depth, volume, rules, and side mapping from that provider.
- An **outcome observation** is immutable Outcome Evidence from the
  authoritative facts provider for one Canonical Event. Corroborating provider
  results remain separate Evidence.
- A **Forecast Evaluation** is immutable derived Analysis comparing one
  Forecast Observation's complete distribution with one Outcome Observation;
  Evaluation Eligibility remains Policy.
- A **canonical event** is Pops' Edge's normalized immutable event Identity,
  including authoritative sport-native identifiers. Provider-native mappings
  are separate immutable records linked to that Identity so later discovery
  does not mutate the event.
- An **edge** is a derived comparison between an eligible forecast observation
  and an executable market price.
- A **recommendation** is a Policy-governed proposed action based on an edge;
  it is not the forecast itself.
- A **position** is exposure to a contract; the **portfolio** is the collection
  of positions and their risk and performance.
- An **outcome** is the settlement-relevant event result.
- **Measurement** evaluates forecasts, Forecast Policies, opportunities,
  decisions, prices, positions, and outcomes while retaining their original
  information state.

Event facts, observations, comparisons, recommendations, positions, and
outcomes are distinct records. A later value must not silently overwrite an
earlier observation needed for audit or historical evaluation.

Pops' Edge uses a consistent Series / Observation pattern where Evidence
naturally changes over time: durable Identity owns append-only observations,
and current state is derived rather than stored. A Forecast Series represents
the conceptual “one forecast”; every provider update is a new immutable
Forecast Observation. Latest forecast, latest pregame forecast, forecast
history, and forecast movement are computed views, not source Evidence.

Provider, model, and version metadata is referenced rather than duplicated in
each observation. Provider assumptions are preserved as reported and remain
separate from authoritative event facts. Published values and precision are
preserved; inconsistent distributions are flagged, never silently normalized.
Unknown provider timestamps and versions remain explicitly unknown rather
than being inferred from collection time.

Pops' Edge distinguishes Identity, Evidence, and Policy. Identity—including
Canonical Event, Forecast Series, Provider, Model, and Version—defines what
exists; Evidence records what a source reported at a point in time; Policy
decides how Pops' Edge evaluates and acts on that Evidence. Approval, weights,
freshness, eligibility, edge requirements, Kelly settings, and portfolio
limits are Policy. They may change without rewriting immutable Identity or
historical Evidence.

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
Adapter Evidence distinguishes exact response-byte Identity from canonical
JSON equivalence, and every game reports an explicit complete, partial, or
rejected outcome. Provider timestamps are never invented from collection time.

PR6 approves DRatings only as a manually captured local source of forecast
Evidence; it does not approve automated access. The adapter preserves the
Upcoming table's ordered matchup names, exact UTC time, displayed pitcher
assumptions, and two published win probabilities. A page-level update time is
not a row timestamp. DRatings supplies neither MLB `gamePk` nor authoritative
team/pitcher Identity, a disclosed model version, or a proven stable forecast
record ID. Separately captured MLB Evidence establishes event Identity and
home/away roles. Complete, partial, ambiguous, and rejected outcomes keep
uncertainty visible and create a Forecast Series only with a valid first
observation.

## Supported sports

| Sport | Status | Product version |
|---|---|---|
| FIFA World Cup | Production baseline | v1.0.0 |
| MLB | Implemented manual Opportunity Board workflow | v1.1.0 |
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
- sport-specific probability and valuation Policy; and
- sport-specific reports when operator needs differ.

The boundary is empirical. Shared abstractions must be earned through multiple
working implementations. World Cup and MLB justify common product concepts,
but not a broad rewrite of the production World Cup system.

## Long-term direction

Pops' Edge should evolve into a set of independently operable domain adapters
on a small, well-tested quantitative decision foundation. Sports remain the
current proving ground. Future releases may add sports, forecast providers,
source comparisons, calibration, Forecast Policies, portfolio analytics, and
operational tooling; still later product decisions may validate applications
outside sports. Automated trading, generalized hosting, additional domains,
and broad architecture rewrites require separate approval and are not implicit
in this direction.
