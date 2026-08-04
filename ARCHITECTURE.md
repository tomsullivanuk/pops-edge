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

### Identity, Evidence, Analysis, and Policy

The durable boundary is `Identity -> Evidence -> Analysis -> Policy`.
Identity defines canonical events, typed propositions, and durable provider
series. Forecast and market Evidence remain separate immutable observations.
Analysis is deterministic, reproducible mathematics: expected value and
explicit transaction costs belong here, never mutate inputs, and never
recommend action. Mutable Policy owns minimum edge, Kelly sizing, bankroll and
position limits, liquidity/freshness thresholds, and bet/no-bet decisions.

The approved long-term capability hierarchy refines that implemented boundary
without making derived results into Evidence:

```text
Mission
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
Forecast Intelligence Report
    ↓
Policy Proposal
    ↓
Policy Hypothesis
    ↓
Product Owner Governance
    ↓
Forecast Policy
    ↓
Forecast Policy Execution
    ↓
Policy Forecast
    ↓
Opportunity Analysis
    ↓
Execution
```

Evidence remains immutable. Forecast Evaluation, Forecast Intelligence Report,
Policy Hypothesis, Policy Proposal, Forecast Policy Execution, Policy Forecast,
and Opportunity Analysis are reproducible objects or derived Analysis; they
never become Evidence.
Execution consumes derived results but does not define the Mission. PR9
Forecast Evaluation and the PR10 Forecast Intelligence Report, Policy
Hypothesis, and Policy Proposal foundation are implemented. Governance,
Forecast Policy, and Policy Forecast remain planned capabilities.

Research supports this flow but is not its endpoint. Measurement exists to
improve future decisions, and Forecast Policies remain valid only while
reproducible empirical results continue to support them.

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

### Outcome Evidence and Evaluation Eligibility

Outcome Evidence establishes what actually happened. An Outcome Observation is
immutable provider Evidence for exactly one Canonical Event. For MLB, the MLB
Stats API is the authoritative Outcome Evidence provider. Kalshi settlement,
DRatings completed tables, sportsbook results, and other sources may
corroborate an Outcome Observation, but they do not replace the authoritative
MLB facts.

Outcome Evidence records provider facts only. It does not decide whether a
Forecast Observation should be evaluated. Evaluation Eligibility is mutable
Policy and may consider timing, reconciliation, disposition, completeness, or
other approved rules without altering either the Forecast Observation or the
Outcome Observation.

> Outcome Evidence establishes reality. Evaluation Eligibility decides which
> comparisons Policy permits.

### Forecast Evaluation

A Forecast Evaluation is immutable derived Analysis that measures how
accurately one Forecast Observation predicted the Outcome Observation for
exactly one Canonical Event. It is deterministic and reproducible from its
referenced immutable inputs and the versioned evaluation method.

Forecast Evaluation evaluates the complete published probability distribution,
not merely whether the provider selected the winning side. Distribution-aware
metrics can therefore preserve information about calibration and confidence.
Market-relative evaluation and wagering evaluation are separate future
analytical families and are not part of Forecast Evaluation.

Although a Forecast Evaluation is immutable once identified by its inputs and
method, it remains derived Analysis. Derived objects never become Evidence.

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

PR7 applies the pattern to markets. A provider-neutral Winner Proposition is
one participant's win claim for one Canonical Event. A Kalshi Market Series is
a distinct provider contract mapped to exactly one proposition. Its immutable
Market Observations preserve bounded capture sessions, quotes, depth,
statistics, status, component timestamps, and provenance. YES/NO labels remain
adapter semantics. Series are created only with a first valid observation;
ambiguous event or side mapping exposes neither series nor valuation.

Kalshi order books preserve the provider's direct fixed-point YES and NO bids.
Executable offers derived as `1 - opposite-side bid` retain the source side,
source price, quantity, exact transformation, and derived acquisition side;
they are never represented as provider-supplied asks. Operational status is
evidence, not Series identity. Closed, suspended, settled, cancelled, unknown,
or depthless observations remain evidence but are factually non-executable;
that constraint is distinct from mutable wagering policy.

### Opportunity presentation

PR8 adds a presentation layer after deterministic Analysis. An `Opportunity`
references exactly one Forecast Observation, Market Observation, Market
Valuation, and Position and stores only derived display fields. It is rebuilt
for each board run and is not persisted. A separate `BoardEntry` displays
partial, ambiguous, rejected, or non-executable cases where PR7 correctly
withholds one of those authoritative inputs; presentation never fabricates the
missing evidence.

The Opportunity Board is the primary MLB product surface. Its explicit
presentation policy orders: (1) existing exposure with unpriced quantity or
negative executable-quantity P/L, with constrained exits first, most adverse
P/L next, and larger cost basis as a tie-breaker; (2) unresolved diagnostic
states in ambiguous, rejected, partial, non-executable order; (3) other
existing exposure by descending cost basis; (4) positive-EV unheld analyses by
descending EV then visible liquidity; and (5) remaining complete rows. Stable
entry identity breaks all remaining ties. This ordering is neither evidence,
valuation, nor a recommendation threshold. Inline diagnostics expose forecast,
market, valuation, reconciliation, and provenance without parallel reports.
Downloaded Kalshi activity is immutable source evidence; a deterministic
adapter reconstructs only current open quantity and weighted entry cost after
exact Market Series reconciliation. Entry and exit fees remain separate from
cost basis. Order-book captures use bounded public market endpoints, preserve
per-response timestamps and digests, and feed neutral one-contract analysis;
they never imply a wager size.
Forecast comparison selects the latest Market Observation whose capture is
strictly before event start; capture at or after start is not pregame. A
separate derived selection uses the latest observation for position
liquidation, so in-play evidence can monitor exposure without contaminating a
pregame comparison. Presentation labels zero-fee analysis as gross before
fees, applies lifecycle status before missing-depth status, and orders paired
teams away then home while immutable provider evidence retains source order.
The August 2 operational validation demonstrates the normal pregame,
authoritative-zero-position path using one application-owned MLB schedule
capture. Retained August 1 evidence remains the regression path for in-play
liquidation, settlement, rejected-side completeness, and positions.

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

Forecast Providers publish original probabilistic forecasts and create
Forecast Observations. DRatings is the first implemented MLB Forecast Provider;
future providers and internal models may use the same boundary. A Forecast
Provider never evaluates itself, combines itself with another provider,
assigns weights, or determines whether it should be trusted. Measurement,
Forecast Intelligence, and Forecast Policy own those responsibilities.

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

### Forecast Intelligence, Forecast Policy, and Opportunity Analysis

Forecast Intelligence learns from many immutable Forecast Evaluations. It is
provider-neutral and always derived from immutable Forecast Evaluations. It is
never mutable accumulated state and is never promoted to Evidence. Provider
comparisons, calibration, Brier score, log loss, historical performance,
longitudinal analysis, and other empirical learning are reproducible derived
views over referenced evaluations.

Forecast Intelligence does not create forecasts. It produces knowledge about
forecast performance. Any cached or presented result must remain reproducible
from immutable Forecast Evaluations rather than becoming an independently
mutable total. It supports Forecast Policy comparison, selection,
configuration, replacement, and empirical justification; it does not provide
the probabilities for today's Canonical Event.

Forecast Intelligence is an analysis engine over Forecast Evaluations, not a
feature of a Forecast Provider. Its contracts must work with one provider,
multiple providers, internal models, and future Policy Forecast evaluations.
PR10 demonstrates that provider-neutral boundary with DRatings because
DRatings is the sole currently implemented MLB Forecast Provider; the
architecture neither requires nor claims a second provider.

#### Research Mode and Production Mode

- **Research Mode** consumes immutable Forecast Evaluations, authoritative
  Outcome History when needed to select current evaluations, an explicit
  evaluation-window definition, and versioned intelligence rules. It may rerun
  analyses and compare hypotheses. Its outputs are immutable Forecast
  Intelligence Reports and analytical Policy Proposals.
- **Production Mode** consumes an approved active Forecast Policy, eligible
  current Forecast Observations, and current Market Evidence. It deterministically
  produces Policy Forecast, Opportunity Analysis, Opportunity Board, and later
  governed Execution. It does not autonomously learn, promote, replace, or
  reconfigure its policy.

> **Research never changes production. Governance changes production.**

#### Forecast Intelligence Report

The primary PR10 artifact is one immutable, deterministic, provider-neutral
Forecast Intelligence Report measuring one Forecast Provider within one
forecasting domain and one explicit evaluation window. Its identity and
provenance include report and intelligence-algorithm IDs and versions;
provider, model, and version scope; sport; competition; proposition type;
requested window; Evaluation Eligibility Policy and Forecast Evaluation
algorithm versions; included current evaluation IDs; excluded or superseded
evaluation IDs; generation timestamp; deterministic input digest; and
limitations. Situational segments are report sections, not separate
first-class intelligence identities.

The deterministic report ID includes every material, output-affecting input:
provider/model scope; sport, competition, and proposition; evaluation-window
definition and any explicit analysis-as-of boundary; canonically ordered
included evaluation IDs; materially consumed excluded or superseded IDs;
eligibility, evaluation, intelligence, segmentation, and adequacy algorithm
versions; and other explicit parameters. It excludes wall-clock run time,
filesystem timestamps, semantically irrelevant input ordering, and unstated
mutable repository state. `generated_at` or `derived_at` is provenance metadata
only unless that value is explicitly declared as the material analysis-as-of
boundary.

A report derives only from an explicit set of current Forecast Evaluations
selected against each latest authoritative final Outcome Observation. It never
queries unstated mutable repository state and never counts superseded
evaluations as additional games. Explicitly scoped historical replay may select
an earlier evaluation state, but must label that scope and preserve every
included and excluded evaluation identity.

Every report uses an immutable evaluation-window definition—initially the
simplest explicit historical date range or fixture-defined window sufficient
to prove PR10. It discloses the requested window, actual covered period, event
count, gaps, and complete or partial coverage; “all available data” is not an
implicit window. Future season, rolling-count, competition-period, or other
window rules must be versioned and deterministic.

Report sections preserve:

- coverage: candidate, current, superseded, included, and excluded counts;
  exclusion reasons; observed period; provider/model coverage; and gaps;
- forecast quality: sample size, mean Brier, mean finite log loss, infinite
  log-loss count, and directional accuracy whose denominator is games with a
  unique strict forecast favorite; tied forecasts remain explicit and excluded;
- primary calibration: exactly one observation per included MLB game, targeting
  `home participant wins`, with published home-win probability compared with a
  realized zero-or-one home-win indicator;
- versioned calibration buckets with explicit boundaries, inclusion rules,
  contributing evaluation IDs, forecast count, predicted sum/mean, home-win
  count, observed frequency, calibration difference, and warning;
- deterministic evaluation-level segment families for actual home/away result,
  strict-favorite result including `no-unique-favorite`, and published home-win
  probability band. Each states grouping, numerator, denominator, contributing
  evaluation IDs, sample size, and limitations; and
- versioned non-overlapping or rolling historical trends without persisted
  mutable cumulative totals.

Sample adequacy is a structured analytical assessment, not Evidence or a
universal truth. It discloses total and per-section sample sizes, coverage
duration, model continuity, missing periods, and whether findings are merely
descriptive or plausibly sufficient for policy consideration. Any adequacy
threshold is explicit, versioned, reproducible, and retained as an analytical
rule. One bucket or one observation never establishes calibration quality.

#### Policy Hypothesis

A Policy Hypothesis is PR10's immutable, versioned, measurable analytical
candidate specification. It describes a forecasting approach that Forecast
Intelligence has evaluated or proposes for further Research. It may be derived
Analysis or explicitly supplied Research input and preserves hypothesis ID and
version; provider and model/version constraints; evaluation eligibility and
provider-selection rules; weights; normalization or transformation rules;
missing-provider and fallback behavior; algorithm or implementation
assumptions; and intended sport, competition, and proposition scope.

A Policy Hypothesis is non-executable, has no lifecycle authority, is never
Evidence, and is not a Forecast Policy or Policy Forecast. It may be replayed
historically and may later be evaluated prospectively in Shadow. It does not
automatically become production configuration. PR11 owns the separate
executable Forecast Policy definition.

#### Policy Proposal and Product Owner governance

PR10 Forecast Intelligence may produce an immutable, deterministic,
evidence-backed Policy Proposal. The proposal is advisory derived Analysis: it
is never Evidence, an active Forecast Policy, a Policy Forecast, a wagering
recommendation, or an executable lifecycle transition. It links one Forecast
Intelligence Report to one versioned Policy Hypothesis and,
where applicable, an incumbent or benchmark.

The proposal preserves its own and derivation identity; report identity;
Policy Hypothesis and benchmark identities; sport and proposition scope;
provider/model constraints; selection or fixed-weight rules; normalization,
missing-provider, and fallback behavior; implementation version; evaluation
window and design classification; included sample; benchmark and later Shadow
results; Brier, log loss, calibration, directional, segment, and sample-size
evidence; and all adverse evidence and limitations. Limitations include
inadequate sample, coverage gaps, model changes, in-sample optimization,
selection bias, missing prospective Shadow history, and underperforming
segments.

Its versioned suggestion rule deterministically preserves the adequacy result,
factual benchmark availability, material metric inputs, triggered reason codes,
and contributing evaluation IDs. An absent benchmark remains absent and yields
an explicit reason rather than a synthetic comparison.

The deterministic proposal ID includes the Forecast Intelligence Report ID,
Policy Hypothesis ID/version, benchmark identities, proposal and
suggested-action rule versions, material limitations, and every other
output-affecting analytical input. Its generation timestamp is non-identifying
provenance metadata. It never depends on wall-clock run time, filesystem state,
irrelevant input order, or unstated mutable repository contents.

A proposal may suggest rejection, continued Research, advancement to Shadow,
continued Shadow evaluation, incumbent retention, consideration of activation,
or consideration of retirement or replacement. A recommendation is not a
lifecycle transition and cannot create a Forecast Policy. Only the Product
Owner may approve creation or lifecycle advancement of a distinct Forecast
Policy based on a Policy Hypothesis, move it to Shadow, activate, replace,
retire, or reject it; those governance records and transitions remain PR12
work. Forecast Intelligence analyzes hypotheses and proposes, Product Owner
governance decides, the Forecast Policy engine executes a separately approved
policy, and Opportunity Analysis consumes its Policy Forecast with Market
Evidence.

Reports and proposals distinguish measured fact, derived interpretation,
limitation, and suggested governance action. Neither artifact declares a model
“correct” or claims production authority.

Identical immutable material inputs and identical algorithm versions produce
identical Forecast Intelligence Report, Policy Hypothesis, and Policy Proposal
identities and analytical contents, regardless of when the derivation is rerun.

#### Forecast Policy

A Forecast Policy is an immutable executable specification that
deterministically transforms eligible current Forecast Observations into Policy
Forecasts. It is a production-side Policy object, not Evidence, Forecast
Intelligence, a Policy Hypothesis, Policy Proposal, governance or activation
record, lifecycle state, Policy Forecast, Opportunity Analysis, or wagering
recommendation. It does not know whether it is approved, active, Shadow,
retired, or rejected; PR12 governance owns those states and production
authority.

The complete executable specification preserves policy ID and version; sport,
competition, and proposition scope; required providers and provider
model/version constraints; observation eligibility and selection; weighting,
transformation, normalization, missing-provider, fallback, and output-validation
rules; each material rule-component ID, version, and parameters; implementation
version; limitations; and deterministic identity. Identity depends only on
material specification inputs, never governance state, Product Owner identity,
wall-clock time, repository location, filesystem metadata, or unpreserved
mutable configuration. The contract supports one or multiple providers without
embedding DRatings semantics.

A PR10 Policy Hypothesis is measurable, replayable Research and has no
production execution authority. A Forecast Policy is a distinct complete PR11
executable contract. A hypothesis or proposal never automatically becomes a
Forecast Policy; future PR12 Product Owner governance may authorize creation of
a separate policy based on them.

#### Forecast Policy Execution

A Forecast Policy Execution is an immutable batch execution context recording
one deterministic application of one Forecast Policy to one explicit supplied
input scope, such as an MLB slate, competition/date scope, or observation set.
It groups independently identified Policy Forecasts produced together and owns
batch context rather than event probabilities. It never discovers events or
collects provider data autonomously; collection remains upstream.

The execution preserves execution ID; policy ID/version; execution algorithm
version; scope and any analysis-as-of boundary; candidate, included, and
excluded Forecast Observation IDs with structured reasons; Canonical Event IDs;
produced Policy Forecast IDs; rule-component identities; deterministic input
digest; statistics, warnings, and limitations; and a non-identifying
`generated_at`. Its identity depends on the policy, canonical immutable input
set, explicit scope/as-of boundary, algorithm version, and material parameters,
not runtime, filesystem or input order without semantics, repository state, or
governance lifecycle. One execution may cover multiple events, but no mutable
Policy Forecast Set is introduced.

#### Policy Forecast

A Policy Forecast is the immutable canonical internal forecast produced by one
Forecast Policy Execution for one Canonical Event and proposition. It is
derived Analysis, never Evidence, and answers which complete probability
distribution Pops' Edge deterministically produced from which inputs and rules.

It preserves its ID and deterministic digest; execution and policy IDs/versions;
event and domain scope; output algorithm version; candidate, included, and
excluded Forecast Observation IDs; provider/model/version identities; input
probabilities and compatibility limitations; every material eligibility,
selection, provider-selection, transformation, weighting, normalization,
fallback, and validation decision with rule-component identity; complete output
distribution with outcome semantics and arithmetic precision; validation
status, issues, limitations, analysis-as-of boundary, and non-identifying
generation timestamp. It contains no market price, expected value, Kelly or
bankroll policy, position, wager recommendation, order, activation state, or
Product Owner approval state.

Opportunity Analysis is intended to apply a Policy Forecast to compatible
current Market Evidence. The current PR7/PR8 MLB workflow directly compares
DRatings Evidence with Kalshi Evidence and remains the implemented precursor.
PR11 will create Policy Forecasts but will not redesign that consumer. A later
bounded PR14 will migrate Opportunity Analysis and the Opportunity Board to
consume Policy Forecast identities; until then no documentation claims the
consumer integration is implemented. Market-relative analysis, wagering Policy,
Kelly sizing, bankroll management, and Execution remain separate.

#### Deterministic rule pipeline and fail-closed execution

Policy execution composes explicit versioned stages:

```text
Input Compatibility
        ↓
Observation Eligibility
        ↓
Observation Selection
        ↓
Provider Selection
        ↓
Transformation
        ↓
Weighting
        ↓
Normalization
        ↓
Output Validation
        ↓
Policy Forecast
```

Every material stage has an ID, version, parameters, deterministic decision,
and limitations. PR11 needs no dynamic plug-in system, dependency-injection
framework, runtime registry, or external rule configuration: preserving stage
identities permits later replacement without speculative infrastructure.
Transformation, weighting, and normalization remain distinct and replayable.
Provider weights are policy inputs, not optimized by PR11, and specify sums,
unavailable-provider treatment, redistribution, fallback effects, precision,
and validation. Normalization never conceals invalid inputs unless an explicit
versioned rule requires a deterministic correction.

Production observation eligibility is distinct from PR9 historical Evaluation
Eligibility. It may consider provider/model/version, validation, Canonical Event
and proposition compatibility, pregame timing, disposition, explicitly defined
recency, assumptions, and duplicate/superseded observations. Multiple eligible
observations from one provider are never selected by input order; the initial
policy selects the unique latest eligible validated pregame observation before
an explicit analysis-as-of boundary and fails closed if multiple observations
share that latest material timestamp.

Execution fails closed and preserves unresolved/excluded cases when required
providers are absent without explicit fallback; identities or semantics
conflict; distributions are invalid or incomplete; constraints, components,
weights, chronology, normalization, validation, or reproducibility fail. It
never silently renormalizes, substitutes providers, uses stale observations,
infers weights, falls back to market probability, or emits a partial
distribution as authoritative. Fallback behavior and invocation are explicit,
versioned, output-affecting provenance.

PR11's bounded demonstration is a supplied, offline DRatings MLB winner policy:
latest eligible validated pregame observation before the explicit analysis-as-of
boundary; identity transformation; weight `1.0`; complete two-outcome
distribution validation without silent correction; fail closed when DRatings is
missing; and no fallback. This demonstrates a deterministic production contract,
not empirical approval, active status, provider access, or governance authority.
PR11 will add immutable policy, rule-component, batch-execution, and event-level
forecast contracts plus deterministic serialization, fixtures, inspection, and
tests only. PR12 retains all approval and lifecycle behavior.

Research Mode follows this flow:

```text
Forecast Observations + Outcome Observations
                    ↓
          Forecast Evaluations
                    ↓
      Current Evaluation Selection
                    ↓
    Forecast Intelligence Report
                    ↓
           Policy Proposal
                    ↓
          Policy Hypothesis
                    ↓
         Product Owner Review
```

Current-event execution follows a separate flow:

```text
        Supplied Forecast Policy
                    +
Eligible current Forecast Observations
                    ↓
      Forecast Policy Execution
                    ↓
             Policy Forecast
                    +
        Current Market Evidence
                    ↓
          Opportunity Analysis
                    ↓
          Opportunity Board
                    ↓
         Governed Execution
```

Forecast Intelligence does not replace current Forecast Observations. Forecast
Policy execution does not convert its derived output into Evidence.

PR10 implements this Research boundary in `forecast_intelligence.py`. An
explicit immutable current-evaluation selection accounts for every stored PR9
Forecast Evaluation as current or superseded using authoritative Outcome
History. A report then applies explicit provider/model/domain scope, evaluation
window, participant-role context, calibration/segmentation versions, and a
versioned adequacy rule. It preserves every included, excluded, superseded, and
selected Outcome identity. `inspect_forecast_intelligence.py` demonstrates the
pipeline from fixture evaluations through report, hypothesis, and advisory
proposal without provider access or production mutation. No Forecast Policy,
Policy Forecast, governance transition, Shadow mode, market-relative or
wagering evaluation, or Opportunity Board behavior is implemented.

PR9 implements only the Evidence-to-Measurement foundation in
`outcome_contracts.py`, `mlb_outcome_adapter.py`, and
`forecast_evaluation.py`. MLB Stats API Outcome Observations are authoritative,
immutable, and retained in append-only Outcome History. The derived latest and
latest-authoritative-final views never mutate prior observations. Evaluation
Eligibility uses versioned Policy
`mlb-winner-evaluation-eligibility-v1`; a forecast is pregame only when its
Pops' Edge collection timestamp is strictly before the scheduled start.
Provider publication time is not invented, and collection time remains labeled
as provenance. Eligibility is a pure function of the immutable Forecast
Observation, evaluated Outcome Observation, supplied immutable Outcome History,
and versioned Policy. Existing evaluations never affect the decision. Replaying
the same pair therefore produces the same decision and evaluation identities;
Forecast Evaluation History, rather than eligibility Policy, rejects duplicate
pairs. A chronology-sensitive decision serializes the exact material Outcome
Observation IDs it consumed. Its deterministic identity includes that canonical
material set, while unrelated history observations have no effect.

Outcome History supplies postponement and material-reschedule chronology. A
forecast collected before authoritative postponement evidence is ineligible; a
new forecast collected after that evidence and strictly before the revised
start can be eligible. Missing earlier schedule chronology is indeterminate.
Suspension remains distinct: an unresolved suspension is ineligible, while an
official later-completed suspended game can be evaluated without invoking the
postponement rule.

Eligible evaluations use the complete two-participant distribution. PR9 stores
the conventional binary Brier score `(p_realized - 1)^2`, 50-digit Decimal log
loss `-ln(p_realized)`, positive infinity for a realized outcome assigned exact
zero probability, unique-favorite directional correctness, and fixed-width
realized-probability buckets `[0.0,0.1)`, ..., `[0.8,0.9)`, `[0.9,1.0]`.
Positive infinity uses an explicit tagged JSON representation rather than a
non-standard bare JSON number. Summaries disclose finite and infinite log-loss
counts separately and calculate a mean only over finite log losses.
Forecast Evaluation History is append-only; its minimal replayable summary is
validation tooling, not Forecast Intelligence or mutable provider state.
When an authoritative final is corrected, the earlier evaluation remains
immutable and a new evaluation references the later Outcome Observation. A
derived view selects the evaluation tied to Outcome History's latest
authoritative final and classifies the others as superseded. Current summaries
use only that derived selection, so corrected games are not double-counted;
stored-history summaries remain available for replay.
Market-relative evaluation, wagering evaluation, Forecast Intelligence,
Forecast Policy, Policy Forecast, and changes to Opportunity Analysis remain
deferred.

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

PR6 implements that durable identity in `forecast_adapter.py`. A Series is
created only with its first valid observation after exact event reconciliation;
`ForecastHistory` appends immutable observations and derives the latest view.
`dratings_adapter.py` is the first provider implementation. It parses only a
manually captured local HTML Upcoming table, performs no provider network
access, and reconciles ordered teams plus exact UTC time against separately
captured MLB schedule evidence. Source positions retain their paired team,
probability, and pitcher evidence; only MLB participant identity assigns those
positions away/home semantics, so a provider-order reversal cannot invert the
forecast silently. DRatings page-update evidence stays page-level;
row timestamps, model version, authoritative identifiers, and stable record
identity remain unknown. Complete, partial, ambiguous, and rejected results
fail closed without introducing policy.

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

MLB is implemented behind explicit sport-specific contracts and isolated
artifacts. PR9 adds the first Outcome Evidence and Forecast Evaluation
Measurement boundary without changing current World Cup calculations or
reports merely to make the repository appear multi-sport.

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
