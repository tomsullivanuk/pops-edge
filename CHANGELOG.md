# Changelog

All notable Pops' Edge releases are recorded here. Dates and release status
must not imply that an untagged release has shipped.

## [Unreleased]

### v1.1.0 — MLB Research and Multi-Sport Foundation

Planned:

- MLB source research, contracts, ingestion, valuation, and reports.
- Initial multi-sport boundaries proven by World Cup and MLB.
- Durable product, architecture, workflow, roadmap, backlog, release, and
  migration documentation.

PR1 establishes documentation and planning only; it does not change production
behavior.

PR2 research selects MLB `gamePk` as canonical identity and a licensed
official-data feed for production schedule/pitcher facts; identifies DRatings
and FanGraphs as conditional forecast candidates; documents Kalshi
`KXMLBGAME`, provenance, backfill, reconciliation, and fail-closed gates; and
defers sportsbook ingestion without changing production behavior.

PR2A documents Pops' Edge as an external-forecast evaluation platform,
establishes commercial-data cost and rights review, separates reusable concepts
from adapter semantics, makes immutable provenance and fail-closed validation
core principles, and formalizes the product-manager/architect and Codex
implementation-engineer workflow.

PR3 adds deterministic offline Canonical Event and MLB identity contracts,
immutable schedule/pitcher/status observations, explicit provenance and
schedule lineage, structured matched/ambiguous/rejected reconciliation, and
fixture-backed semantic validation. It adds no provider client, persistence,
market comparison, report, wagering behavior, or World Cup integration.
Canonical identity is restricted to authoritative sport-native identifiers;
later provider mappings remain separate, and rejected reconciliation preserves
candidate-evaluation evidence without exposing an eligible candidate.

PR3A documents the external-forecast architecture without implementing it. It
establishes Provider → Model → Version → Observation as distinct domain
concepts; requires complete structured outcome distributions, preserved
published precision, precision-aware validation, distinct timestamps,
immutable revision and correction history, provider-reported assumptions, and
fail-closed event reconciliation; and separates immutable identity and evidence
from mutable weighting, eligibility, and wagering policy. No provider is
approved or privileged.

PR4 implements deterministic offline Forecast Provider, Model, Version,
Outcome, Published Probability, Distribution, provider-assumption, Observation,
validation, disposition, relationship, and timing contracts. Exact decimal
values and published precision drive aggregate rounding-tolerance validation;
outcomes serialize in canonical non-semantic order; inconsistent distributions
remain preserved without normalization; and PR3 provenance and reconciliation
semantics are reused. It adds fixtures and semantic tests but no provider
adapter, persistence, weighting, market, valuation, report, or wagering work.

PR5 adds a bounded read-only MLB Stats API facts adapter for the personal,
noncommercial project. It separately preserves exact-response and canonical-
JSON digests, uses authoritative `gamePk` and MLB team IDs, constructs canonical
games and schedule/status/pitcher observations, returns explicit deterministic
complete/partial/rejected results, and fails closed on unsafe identity without
inventing source timestamps or lineage. Fixture-backed tests remain offline;
an explicit concise smoke path is not run automatically. Persistence,
scheduled collection, forecasts, markets, valuation, reports, and wagering
remain deferred.

PR5A documents Durable Identity → Immutable Observations → Derived Views as the
shared architecture for time-varying evidence. It defines Forecast Series as
the durable identity for one Provider, Model, Version, and Canonical Event;
keeps probabilities, timestamps, assumptions, provenance, validation,
disposition, and relationships on immutable Forecast Observations; and makes
latest, pregame, history, evolution, and movement computed views. It strengthens
the Identity / Evidence / Policy boundary and scopes PR6 to implement Forecast
Series plus the first external provider adapter without changing contracts or
runtime behavior in PR5A.

PR6 implements immutable Forecast Series, append-only Forecast History, and a
provider-neutral offline adapter-result boundary with explicit complete,
partial, ambiguous, and rejected states. Its first provider implementation
parses a faithful manually captured DRatings Upcoming table, preserving exact
published probabilities and precision, pitcher assumptions, scheduled UTC
times, page-level update evidence, source URLs, row locators, and raw/canonical
digests. Separately captured MLB schedule evidence supplies `gamePk`, team
identity, home/away roles, and exact-time reconciliation; the controlled
`Oakland Athletics` → `Athletics` alias is explicit. No provider row timestamp,
stable record ID, or disclosed model version is invented. The local inspection
command performs no provider network access, and automation, persistence,
freshness, weighting, markets, valuation, reports, and wagering remain deferred.

The documentation checkpoint in `docs/V1.1.0_CHECKPOINT_THROUGH_PR6.md`
records the implemented platform baseline before PR7. It changes no runtime
behavior, does not release v1.1.0, and preserves the sequence approved at that
checkpoint; later architecture review expanded the release sequence.

PR7 implements provider-neutral Winner Propositions, provider-specific Market
Series, immutable capture-session Market Observations, and the first bounded
read-only Kalshi MLB market adapter. Explicit participant/date and YES/NO
evidence is required; ambiguous doubleheaders and unsafe mappings expose no
series or valuation. Exact-Decimal executable-depth analysis and explicit fee
models produce reproducible expected value without recommendation, sizing,
bankroll, freshness, liquidity, portfolio, or wagering policy. A separate
non-persisting smoke command is provided but was not run.

PR8 adds the position-aware Opportunity Board as the primary MLB product
surface. Derived Opportunities reference forecast evidence, market evidence,
valuation, and one aggregated position; unresolved Board Entries retain
partial, ambiguous, rejected, and non-executable diagnostics without inventing
missing evidence. A local manual runner builds one sortable HTML board and
prints factual workflow counts. Attention ordering remains deterministic
presentation, while recommendations, Kelly sizing, bankroll, portfolio
optimization, provider automation, persistence, and wagering remain deferred.
Position inputs are authoritative provider-market/proposition/event/side open
summaries rather than transaction history; offsetting sides remain separate.
Liquidation proceeds and unrealized P/L use visible held-side bid depth, expose
unpriced quantity, and never extrapolate a top bid across the full position.
Downloaded Kalshi activity can now be normalized into reconciled current
positions without treating orders as exposure or folding fees into entry cost.
Bounded public order-book captures preserve per-response timestamps and
digests; the Board reports their capture range and uses explicit one-contract
analysis quantities. DRatings winner outcomes now carry canonical participant
IDs so compatible real MLB forecast and market evidence values end to end.
The final PR8 correction separates latest strictly pregame comparison evidence
from latest liquidation evidence. In-play-only rows retain current position
monitoring but suppress forecast comparison, and capture exactly at start is
treated as in-play. Opportunity output is labeled Gross Edge before Kalshi
fees, lifecycle status precedes missing depth, and paired display fields use
canonical away-first/home-second order without mutating provider evidence.
August 2 real evidence now validates 15 fully reconciled pregame games and an
authoritative activity-derived zero-position state through the existing MLB
schedule client. August 1 remains a separate regression artifact, including
in-play liquidation, settlement precedence, and a rejected proposition that
keeps its game incomplete and both canonical participant lines visible.

PR9 adds authoritative MLB Outcome Evidence and deterministic forecast-quality
Measurement. Immutable MLB Stats API Outcome Observations retain lifecycle,
scores, participants, timestamps, source digests, validation, and append-only
history through Canonical Event `gamePk` identity. A versioned eligibility
Policy emits an explicit decision for every candidate pair and requires Pops'
Edge forecast collection strictly before scheduled start. Eligibility is
state-independent; immutable Outcome History makes pre-postponement forecasts
ineligible, permits later pregame forecasts after a documented reschedule, and
fails indeterminate when chronology is incomplete. Duplicate pairs are rejected
by Forecast Evaluation History rather than by eligibility Policy. Immutable Forecast
Evaluations preserve the complete distribution and compute versioned binary
Brier score, Decimal log loss, directional correctness, and calibration bucket.
Exact-zero realized probability remains unclipped positive-infinite log loss,
uses portable tagged JSON, and is counted separately from finite log loss in
the validation summary.
The offline inspection and minimal replay summary introduce no Forecast
Intelligence, market-relative evaluation, wagering evaluation, Policy Forecast,
or Opportunity Board change. Forecast Intelligence remains PR10 scope.

The approved PR10 documentation direction defines provider-neutral Forecast
Intelligence Reports over explicit current Forecast Evaluations and immutable
Policy Hypotheses plus analytical Policy Proposals demonstrated with DRatings
alone. A Policy Hypothesis is a non-executable PR10 Research specification, not
the PR11 Forecast Policy contract. The direction separates Research Mode from
Production Mode, requires explicit evaluation windows, coverage, calibration,
sample adequacy, included/excluded identities, and limitations, and prevents
reports, hypotheses, or proposals from changing production. Explicit
analysis-as-of boundaries affect deterministic identity; wall-clock generation
timestamps remain non-identifying provenance.
Product Owner governance records and lifecycle transitions remain PR12;
Forecast Policy execution remains PR11. Those decisions define the boundary
implemented by PR10 without changing production behavior.

PR10 implements the provider-neutral Forecast Intelligence foundation over PR9
current Forecast Evaluations. Immutable reports preserve explicit window,
scope, included/excluded/superseded identities, coverage, Brier and log-loss,
calibration, deterministic segments, trends, and versioned adequacy limitations.
Immutable Policy Hypotheses describe non-executable Research candidates, and
immutable Policy Proposals retain report linkage, metrics, benchmarks,
uncertainty, limitations, and advisory governance suggestions. A fixture-only
inspection demonstrates DRatings MLB winner evaluations. Generation time does
not affect deterministic identity. No production Policy, governance transition,
Shadow mode, provider access, Opportunity Board, market-relative, wagering, or
Execution behavior is added.

The PR10 statistical-semantics audit fixes primary MLB calibration to one
home-win observation per included game, makes bucket boundaries and contributing
identities explicit, and replaces ambiguous participant segments with
reconciled actual-result, strict-favorite-result, and home-win-probability
families. Directional accuracy excludes tied forecasts from its denominator.
Policy Proposal suggestions now use a versioned deterministic rule preserving
adequacy, benchmark absence, metrics, reason codes, and evaluation identities;
no synthetic benchmark is introduced.

The approved PR11 architecture defines Forecast Policy as a provider-neutral
immutable executable specification, Forecast Policy Execution as an immutable
explicit batch context, and Policy Forecast as independently replayable
event-level derived Analysis and Pops' Edge's canonical internal forecast.
Execution uses versioned compatibility, production eligibility, observation and
provider selection, transformation, weighting, normalization, fallback, and
validation stages; invalid or unresolved inputs fail closed. Policies contain
no approval or lifecycle state, and PR12 retains all governance authority. The
initial planned demonstration is a supplied single-provider DRatings MLB winner
policy with latest eligible pregame selection, identity transform, weight
`1.0`, complete-distribution validation, and no fallback. Opportunity Board
consumer migration is deliberately separated into PR14; release hardening moves
to PR15. This documentation adds no PR11 implementation or production behavior.

## [v1.0.0] — World Cup baseline

The existing production World Cup implementation is designated Pops' Edge
v1.0.0. It includes Silver forecast ingestion, supported Kalshi World Cup
markets, match and futures value boards, portfolio and ladder reporting, wager
import, CLV and position monitoring, archives, and local Excel/HTML workflows.

This designation records the baseline; PR1 does not create or backfill a tag.

### Maintenance

- Add an active-position Ladder Board workbook and sortable web view.
- Track exited and remaining contracts so closed positions are excluded and
  partially closed positions use their remaining exposure.
- Integrate Ladder Board generation, archiving, iCloud copying, and opening
  into the existing World Cup workflows.
- Add bounded retry handling for transient Kalshi API failures without
  advancing the pagination cursor.
