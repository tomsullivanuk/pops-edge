# Pops' Edge Architecture

## Current state

The v1.0.0 architecture is a file-based World Cup pipeline. Python modules
ingest forecasts and markets, normalize them into workbooks, calculate value
boards, import wager history, and render Excel/HTML outputs. Shell scripts
coordinate local execution, archives, iCloud copies, notifications, and report
opening.

This document describes the present system; it does not introduce a refactor.

## Component inventory

### Existing reusable or potentially reusable components

- `config.py`: filenames, archive paths, sheet names, and shared column names.
- `kalshi_pull.py`: paginated/retried market API acquisition, currently filtered
  to World Cup event families.
- Wager ingestion foundations in `import_wagers.py`: activity discovery,
  preservation of manual fields, status and P/L handling.
- Workbook/report utilities and patterns in the board and web builders.
- Quality checks, run metadata, archival patterns, and fixture-based tests.
- Shell orchestration patterns: virtual-environment activation, failure
  handling, summaries, and child-workflow coordination.

These are candidates, not declarations of already sport-neutral architecture.

### World Cup-specific components

- `process_silver.py` and `process_silver_futures.py`: Silver World Cup schemas,
  team/stage normalization, and archives.
- `build_value_board.py`: World Cup match matching and valuation report.
- `build_futures_value_board.py`: World Cup advancement/champion valuation,
  Champion Proxy logic, and sell ladders.
- `build_ladder_board.py`: active World Cup position ladder report.
- `build_web_betsheet.py`, `build_web_futures_betsheet.py`, and
  `build_web_ladder_board.py`: World Cup board views.
- World Cup event ticker families, filenames, sheet semantics, iCloud
  destination, wager enrichment, fixtures, and workflow commands.

`build_web_betlog.py`, `import_wagers.py`, and the update scripts mix reusable
patterns with World Cup-specific filenames and operating assumptions.

## Architecture boundaries

### Reusable platform concepts

World Cup and MLB demonstrate common responsibilities that may be represented
by minimal reusable contracts:

- forecast providers and independently retained forecast observations;
- market providers and executable market observations;
- immutable observations, source provenance, and validation;
- canonical events with explicit source-identity mappings;
- derived edge analysis and recommendations;
- positions, portfolio tracking, outcomes, and performance evaluation;
- configuration, reporting, output isolation, and deterministic testing.

These are shared concepts, not proof that current World Cup modules must be
rewritten into a universal framework.

### Adapter-level responsibilities

Provider and sport adapters retain the semantics that give source data meaning:

- provider-native schemas, identifiers, authentication, timestamps, and
  parsing;
- league or competition schedules and participant identity;
- MLB starting pitchers, doubleheaders, postponements, suspensions, and
  resumptions;
- World Cup groups, knockout rounds, extra time, and penalty shootouts;
- provider contract discovery, market-side mapping, and settlement
  interpretation; and
- source- or sport-specific validation and rejection rules.

A shared abstraction must not erase important sport or provider semantics.
Shared abstractions must be earned through multiple working implementations.
World Cup and MLB provide enough evidence to recognize common concepts, but
future PRs should introduce only the minimum reusable contracts required by
their approved scope. They do not justify a broad World Cup rewrite.

### Canonical events and source identity

The platform uses a reusable canonical-event concept containing only immutable
contest identity: sport, league or competition, season, event identifier,
participants, and authoritative sport-native identifiers. Scheduled time and
status are observations rather than identity. For MLB, `gamePk` is the
authoritative MLB-native game identifier preserved by the MLB adapter; it is
not a universal cross-sport identifier. Forecast-provider, market-provider,
and other non-sport-native mappings remain separate immutable records so
discovering a mapping never replaces canonical identity.

PR3 implements this boundary in `event_contracts.py` and `mlb_contracts.py`.
`CanonicalEvent` contains only immutable contest identity. Its participant and
event identifier mappings accept only `SportNativeIdentifier` values.
`MLBGame` carries MLB-specific home/away roles, game type, and doubleheader
designation. Construction validates its duplicated convenience fields against
the canonical participants, season, and `gamePk`, making disagreement invalid.
Schedules, pitchers, statuses, and lineage evidence are separate immutable
observations or relationships. The contracts are an offline boundary, not a
persistence schema or a retrofit of the World Cup pipeline.

### Immutable observations and derived state

Event facts, forecast observations, market observations, derived comparisons,
recommendations, positions, and outcomes are separate. An observation preserves
the source, source-native identifier, source publication or representation
time, Pops' Edge collection time, canonical-event mapping, transformations,
validation result, and rejection reasons.

Later observations do not overwrite earlier observations when doing so would
lose auditability or the historical information state. “Current” or “latest”
values are derived views over immutable observations.

### Series and observations

Time-varying evidence follows one durable pattern:

```text
Durable Identity
        │
        ▼
Immutable Observations
        │
        ▼
Derived Views
```

The durable identity changes rarely and answers which thing is being observed.
Its observations are append-only evidence of what was known or published at a
point in time. Operational answers such as “current” and “latest” are computed
views; they are not stored evidence. Observations are never updated in place.

The existing game-facts architecture already follows this pattern:

```text
Canonical Event
        │
        ▼
Schedule Observations
Pitcher Observations
Status Observations
        │
        ▼
Current Game State
```

The Canonical Event remains durable while schedule, pitcher, and status
evidence accumulates. Current Game State is derived from those observations
without rewriting their history.

The approved forecast architecture applies the same language:

```text
Forecast Series
        │
        ▼
Forecast Observations
        │
        ▼
Current Forecast
Latest Pregame Forecast
Forecast History
Forecast Movement
```

A Forecast Series is the durable identity for one provider/model/version and
Canonical Event combination. It answers, “Which forecast are we discussing?”
Conceptually it owns references to the Forecast Provider, Forecast Model,
Forecast Version, and Canonical Event. It contains no probabilities,
timestamps, assumptions, validation, or disposition; those belong to its
observations.

A Forecast Observation answers, “What did this forecast look like at this
point in time?” Each provider update appends a new immutable snapshot containing
the outcome distribution, timestamps, assumptions, provenance, validation,
disposition, and relationships. Observations never replace one another. This
preserves the intuitive concept of one forecast changing over time without
sacrificing its complete historical evidence.

Latest forecast, latest pregame forecast, forecast before a pitcher change,
forecast evolution, and forecast movement are derived views. They may be
recomputed for an operational question and are not themselves immutable source
evidence.

The pattern is reusable where evidence naturally varies over time. Canonical
Event and Forecast Series are current examples; future Market Series, Weather
Series, or Injury Series may use it if concrete requirements justify them.
The presence of a durable object alone does not require a Series.

> Series identify the thing being observed. Observations preserve what was
> known at a point in time. Derived views answer operational questions without
> rewriting history.

> Reference durable objects; do not duplicate durable metadata.

### External forecast domain

The implemented PR4 contracts separate four first-class concepts. The approved
next boundary adds Forecast Series between durable forecast identity and its
observations:

```text
Forecast Provider
    └── Forecast Model
            └── Forecast Version
                    └── Forecast Series + Canonical Event
                            └── Forecast Observations
```

A provider is the durable publishing organization or source. Its referenced
metadata may include a stable identifier, name, organization, website,
documentation, supported sports or competitions, collection method, permitted
use or licensing status, typical update cadence, and active/inactive lifecycle
state. Provider approval, weights, freshness thresholds, trust decisions, and
wagering eligibility are policy and do not belong to the provider object.

A model is a durable forecast method owned by one provider. Its referenced
metadata may include a stable identifier, provider reference, name,
description, supported sports or competitions, documentation, methodology
classification, and market-independence classification. Approved methodology
classes are `statistical`, `market-derived`, `hybrid`, `expert judgment`,
`composite external forecasts`, and `unknown`. Approved market-independence
classes are `independent`, `partially market-informed`, `market-derived`, and
`unknown`. These classifications remain distinct: methodology describes how a
forecast is produced, while market independence describes how much market
information it uses. Neither model weights nor recommendation eligibility
belongs to the model.

A version is a durable revision of one model. Its referenced metadata may
include a stable identifier, model reference, provider-published version name,
effective and retirement dates, methodology and release notes, calibration
notes, and documentation. This boundary permits performance analysis across
methodology, calibration, or weighting changes. Every observation references
the exact known version that produced it. When a provider publishes no version,
the model has an explicit unknown version; Pops' Edge never invents one from a
collection date.

Provider, model, and version are separate because one provider may publish
multiple models, a model may have multiple versions, and methodology,
calibration, or weighting may change over time. A forecast observation is lean
and does not copy their durable metadata:

> Reference durable objects; do not duplicate durable metadata in observations.

#### Forecast observations and outcome distributions

A Forecast Observation is immutable external evidence linking a Canonical
Event and Forecast Version to the complete outcome distribution published by
the provider. It also references provider-reported assumptions, provenance,
timestamps, validation state, provider disposition, correction or withdrawal
relationships, and the event-reconciliation result. Observations from
different providers remain independently preserved and evaluable; none is the
single official Pops' Edge forecast.

The reusable distribution supports any set of mutually exclusive structured
outcomes tied to the Canonical Event, such as home/away win in MLB or
home/draw/away win in soccer. Every probability references a structured
outcome identifier. Participant identity alone does not define an outcome, and
outcome order has no semantic meaning. Pops' Edge preserves a complete
provider-published distribution rather than silently deriving replacement
values.

Each probability preserves the exact published numeric value, its published
precision, and, where practical, its source representation. Validation retains
the observed distribution total and applies a tolerance appropriate to that
precision: whole percentages may reasonably sum to 99–101%, tenths require a
correspondingly tighter tolerance, and greater precision requires tighter
validation. A materially inconsistent distribution is preserved and flagged,
not repaired. Probabilities are never silently normalized; normalization, if
later authorized, is a separate derived transformation with provenance.

#### Forecast time, assumptions, and revision history

Collection time is required and records when Pops' Edge obtained the forecast.
Provider publication, effective, and update times are separate and retained
when available. Unknown provider times remain unknown and are never inferred
from collection time. Scheduled event start remains Schedule Observation
evidence rather than copied forecast truth; a forecast may reference the
schedule evidence used for timing evaluation. Timestamp-based wagering
eligibility is later policy.

Provider-reported assumptions are preserved exactly as published, including
their absence. They may describe starting pitchers, expected lineups,
home-field assumptions, provider-specific event definitions, or other model
inputs. They remain separate from authoritative event observations. Conflicts
preserve both pieces of evidence, and missing assumptions do not alone
invalidate a forecast. If an assumption later changes, the old observation
remains historically valid evidence even if later policy considers it stale.

Every provider revision creates a new immutable observation; earlier evidence
is never overwritten. Corrections and withdrawals append records and preserve
the corrected or withdrawn history. Observation validation (`valid`,
`incomplete`, or `invalid`) is separate from provider disposition (`active`,
`corrected`, or `withdrawn`). Relationships and derived state—`superseded by`,
`corrected by`, `withdrawn by`, and `latest known observation`—are not
intrinsic mutations of an observation.

#### Forecast reconciliation and timing safety

A valid source forecast and a valid Canonical Event mapping are independent
concerns. A forecast must reconcile to one Canonical Event before edge
analysis. For an ambiguous record, including an unidentified doubleheader
game, Pops' Edge preserves the source evidence and candidate evaluations,
records an ambiguous reconciliation, selects no event, and fails closed for
edge or wagering analysis.

Post-start collection remains audit evidence but is not represented as
contemporaneously actionable, even if the provider reports a pregame
publication time. Retrospective evaluation may use it only when that provider
timestamp is independently trustworthy.

### Identity, evidence, and policy

Pops' Edge separates three layers:

- **Identity** defines what exists, including Canonical Events, Forecast
  Series, teams, providers, models, and versions.
- **Evidence** records what an external source reported at a point in time,
  including schedule, pitcher, forecast, and later market and outcome
  observations. Evidence is immutable and timestamped.
- **Policy** defines how Pops' Edge behaves, including approved providers,
  model weights, freshness and market-quality thresholds, pitcher-confirmation
  rules, edge requirements, Kelly configuration, portfolio limits, and wager
  eligibility.

Policy may change without rewriting identity or evidence. Future forecast
weighting may consider provider, model, version, methodology, market
independence, sport or competition, horizon, completeness, historical
calibration, and cross-source correlation, but no weight is part of an
immutable model or observation.

Series identify the thing being observed, while observations preserve its
time-varying evidence. Derived views select or compare observations without
becoming evidence and without mutating identity. Policy—including provider
approval, weighting, freshness, wager eligibility, Kelly sizing, and edge
thresholds—may select among derived views but must never mutate a Series or an
Observation.

> Identity is immutable. Evidence is immutable. Policy is mutable.

> Forecast Observations report what a provider published; they do not decide
> whether Pops' Edge should wager.

PR4 implements this boundary in `forecast_contracts.py`. The offline contracts
use one stable identifier chain: Model references Provider, Version references
Model, and Observation references only Version. They also provide exact
`Decimal` probabilities; canonical outcome ordering;
explicit assumptions, validation, disposition, and lineage; and composition
with PR3 reconciliation and provenance. Precision tolerance is the sum of each
published value's half-rounding interval after conversion to probability
scale. Materially inconsistent totals remain serialized evidence and are
classified invalid without normalization. Revision relationships are separate
immutable evidence, so later discovery does not rewrite an observation and
latest/disposition state is derived. A neutral timing helper compares
collection time with supplied schedule evidence but expresses no eligibility
policy. Provider adapters, persistence, weighting, markets, valuation, reports,
and wagering remain outside this boundary.

PR4 predates the approved Forecast Series contract. PR5A documents that durable
identity layer; PR6 will implement it and connect existing immutable Forecast
Observations to Series while preserving PR4 evidence semantics.

### Fail-closed quality behavior

Pops' Edge must not produce an edge or recommendation while material ambiguity
remains. Hard failures include unresolved event or participant identity,
doubleheader ambiguity, conflicting times, missing or post-start forecast
timestamps, stale or changed pitchers, unresolved YES-side mapping, unclear
settlement rules, stale market observations, missing executable prices,
conflicting source identifiers, and unsupported status.

Missing an opportunity is preferable to presenting a false edge caused by
uncertain data.

### Reconciliation and serialization

Offline source reconciliation returns exactly one structured outcome:
`matched`, `ambiguous`, or `rejected`. A matched result identifies one
canonical event and its evidence. An ambiguous result retains every eligible
candidate and selects none. A rejected result selects and retains no eligible
candidate, while candidate-evaluation audit records may preserve the event
identifiers, mappings, evidence, and structured reasons considered during
rejection. Contract construction errors, valid-but-incomplete observations,
ambiguous reconciliation, and rejected reconciliation remain distinguishable.

Contracts serialize to deterministic tagged JSON with timezone-aware ISO 8601
timestamps, enum values, source mappings, provenance, validation reasons, and
schedule lineage. This format supports fixtures and future adapter boundaries;
PR3 does not select a database or persistence framework.

## Data flow

```text
Silver match CSV ──> process_silver.py ──────────────> Silver_Current.xlsx
Silver futures CSV -> process_silver_futures.py ────> Silver_Futures_Current.xlsx
Kalshi API ─────────> kalshi_pull.py ────────────────> Kalshi_Current.xlsx
Activity CSV ───────> import_wagers.py ──────────────> World_Cup_Bet_Log.xlsx

Normalized inputs + wager log
        ├──> match value board ──> Excel + HTML
        ├──> futures value board -> Excel + HTML
        └──> ladder board ───────> Excel + HTML
```

Detailed schemas and operating behavior are documented in `DEVELOPER.md`.

## Boundaries and dependencies

- Local state is workbook/CSV based; generated artifacts are not canonical.
- `config.py` currently sets `PROJECT_DIR` to `~/pops-edge`.
- Manual inputs are discovered in the project directory or `~/Downloads`.
- Current market ingestion depends on the public Kalshi trade API.
- Forecast ingestion depends on manually downloaded Silver exports.
- macOS workflows depend on `open`, optional `osascript`, and a World Cup
  iCloud Drive directory.
- A local Python virtual environment and its third-party packages are assumed.
- External aliases, schedulers, IDE/Codex paths, GitHub integrations, and other
  clones may depend on the repository name and location and must be audited
  when either changes.

The complete rename dependency inventory is in
`docs/REPOSITORY_RENAME.md`.

## v1.1.0 direction

MLB will first be implemented behind explicit sport-specific contracts and
isolated artifacts. PR9 may extract platform interfaces demonstrated by both
sports. No current World Cup calculation or report is changed merely to make
the repository appear multi-sport.

PR2 establishes MLB `gamePk` as canonical identity while requiring a licensed
official-data adapter for production. Source event, forecast, market, and
sportsbook observations stay immutable and separate through normalization;
forecasts are not averaged, and unresolved identity, schedule, pitcher,
timestamp, or side mappings fail closed. See
`docs/MLB_SOURCE_RESEARCH_v1.1.0.md`.

### MLB Stats API facts adapter

PR5 implements the first MLB facts adapter in `mlb_stats_api.py` for the
personal, noncommercial project. The MLB Stats API is a replaceable source
behind the existing Canonical Event and MLB observation contracts, not a
permanent downstream dependency:

```text
MLB Stats API -> raw source evidence -> MLB facts adapter
              -> Canonical Event + schedule/pitcher/status observations
```

The read-only client has an injectable transport, bounded transient retries,
explicit request parameters and timeout, and no import-time network activity.
The client hashes the exact response bytes captured before JSON parsing, while
the adapter separately hashes canonicalized JSON for deterministic semantic
comparison. It retains request and response metadata, uses `gamePk` and MLB
team IDs for identity, and exposes explicit `complete`, `partial`, or
`rejected` event outcomes. Missing venue, pitcher, source timestamp, or complete
doubleheader evidence is reported without best-guess repair; unsafe identity
or required timestamp evidence fails closed while retaining raw evidence.
Collection time records when Pops' Edge received evidence and is never copied
into an unknown provider timestamp. Same-`gamePk` changes create later
observations of one event. Distinct games can be linked only when a direct
source relation field identifies the related `gamePk`; similarity never
creates lineage.

`smoke_mlb_stats_api.py` is an explicit small, read-only schedule check. It
requires a date, prints only concise identifiers, outcomes, and issues, writes
nothing, and exits nonzero for transport failure or rejected evidence. It is
not part of automated tests or workflows. PR5 adds no durable raw-payload
retention, persistence, scheduled collection, forecast adapter, market
adapter, valuation, reports, or wagering behavior.
