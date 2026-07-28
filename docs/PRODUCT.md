# Pops' Edge Product

## Vision

Pops' Edge is a durable, reproducible prediction-market analytics platform. It
helps an operator compare independent estimates with market prices, evaluate
potential edges, size research-informed positions, and monitor decisions
without hiding the evidence or assumptions behind them.

The product is not defined by one exchange, source, tournament, or report.
Kalshi is the current market provider and the World Cup system is the first
production implementation, but both sit within a broader product identity.

## Product philosophy

- **Evidence before action.** Preserve the forecast, market observation,
  transformation, and decision rule behind every conclusion.
- **Reproducibility over manual editing.** Canonical inputs and code produce
  reports; generated workbooks and HTML are outputs.
- **Research before abstraction.** Understand a sport and its sources before
  creating shared interfaces.
- **Explicit uncertainty.** Surface freshness, missing data, matching failures,
  assumptions, and model limitations.
- **Human judgment remains central.** Pops' Edge supports research and
  decisions; it does not silently place trades.
- **Compatibility matters.** New sports must not destabilize a working sport.
- **Small, reviewable releases.** Each PR has bounded scope, validation, and a
  review-before-commit handoff.

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
- source provenance and freshness;
- canonical forecast and market contracts;
- validation and quality reporting;
- deterministic fixture testing;
- output isolation and archives; and
- common presentation utilities where schemas actually align.

Sport-specific adapters should retain:

- source acquisition and schema mappings;
- team, event, game, and market identifiers;
- calendars, stages, doubleheaders, postponements, and cancellations;
- market matching and settlement assumptions;
- sport-specific probability and valuation policy; and
- sport-specific reports when operator needs differ.

The boundary is empirical. v1.1.0 may extract a shared component only after the
World Cup and MLB implementations demonstrate the same responsibility.

## Long-term direction

Pops' Edge should evolve into a portfolio of independently operable sport
adapters on a small, well-tested analytics foundation. Future releases may add
sports, providers, source comparisons, calibration, portfolio analytics, and
operational tooling. Automated trading, generalized hosting, and broad
architecture rewrites require separate product decisions and are not implicit
in this direction.
