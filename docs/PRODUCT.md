# Pops' Edge Product

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

- A **forecast provider** publishes independent probability estimates; a
  **forecast observation** is one provider's timestamped report for an event.
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
