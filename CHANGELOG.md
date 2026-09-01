# Changelog

## PR17B2 — Kalshi MLB acquisition and durable Evidence operations

- Added an inactive, fixture-driven Kalshi operational boundary with separate
  dry-run namespaces, bounded retry ownership, and exactly one transport request
  per PR17B1-derived prospective slot.
- Added atomic create-only raw/normalized storage, individually immutable
  manifests, bounded OS advisory locking and recovery diagnostics, rebuildable
  SQLite discovery, and create-only digest-verified secondary synchronization.
- Added one explicit operations CLI, typed JSON/human diagnostics, offline
  status/preflight/inspection, and three thin `launchd` template groups.
- Added offline concurrency, recovery, pagination, identity, retry, index,
  secondary-copy, namespace-isolation, and compatibility validation. Neither
  Protocol is activated and no real Evidence or empirical report is created.
- Independent-review amendments replace caller-selected prospective chronology
  with trusted-clock discovery from archived PR17B1 authority, reconstruct exact
  version-dispatched contracts for real graph replay, and reconcile interrupted
  raw/normalized orphans as visible non-authority excluded from indexes and
  secondary synchronization.
- Preserve every prospective provider call across slot/window boundaries by
  fixing slot authority at trusted request start and recording completion as
  attempt effectiveness and completed manifest chronology.
- Classify out-of-request-interval provider observations as persisted typed
  captured-invalid attempts so no executed call disappears from Coverage.
- Translate expected provider-controlled PR17 deserialization and contract
  validation failures into replayable malformed/incomplete/mapping attempts
  without disguising unexpected internal failures.
- Recursively validate every shared tagged-serialization marker before provider
  contract deserialization, including malformed enum/Decimal shapes that could
  otherwise escape without an immutable attempt.
- Add annotation-derived structural validation for the complete provider
  `MarketObservation` tree so incompatible ordinary field shapes also become
  failure-inclusive captured-invalid attempts.

## PR17B1 — standalone scientific contracts and deterministic replay

- Added the offline-only `forecast_standalone_research.py` successor family for
  closed tagged retrospective/prospective Protocols sharing one immutable
  activation-boundary identity without pooling study authority.
- Added historical query-manifest/correction replay, immutable candle Evidence
  and derivation, typed five-slot prospective attempts and terminal Snapshots,
  standalone market derivation, V3 analytics/reporting, serialization, and
  upstream-first graph validation.
- Added one synthetic two-study fixture and deterministic non-authoritative
  inspector. Acquisition, persistence, scheduling, backup, CLI, and dry-run
  operations remain PR17B2; PR17C/PR17D and downstream numbering are unchanged.
- Independent-review amendments add the governed bootstrap, exact
  Measurement-to-opportunity replay, upstream-first graph reconstruction,
  separate cumulative and `(start, end]` bounded Coverage, composable graph
  roots, and typed cursor-linked archive-page pagination.
- Latest review amendments derive the complete schedule universe, eligibility,
  and Coverage categories upstream-first; enforce exact analytical and report-
  window rules; reconcile each candle to one archived retrieval page; and add
  explicit successor-registry delegation for approved legacy graph authority.
- Latest amendments preserve cross-activation reschedule opportunities, add
  immutable boundary-aware event-classification Evidence, correct prospective
  valid-capture and no-call precedence, and make derivation/Outcome/Measurement
  selection boundary-aware and order-independent.

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

The bounded PR17 feasibility spike established qualitative public-API
feasibility for deterministic Kalshi MLB event discovery and historical
one-minute candle reconstruction, subject to explicit candle-timing,
non-simultaneity, historical-schedule, and operational limitations. Its
temporary API material and observed values are not Evidence or repository
authority. PR17A records documentation authority only; it activates neither
Protocol and adds no collected data or empirical result.

Independent review amendments separate comparative and standalone Protocol
families and add canonical standalone report authority; define immutable
historical-candle Evidence, typed candle derivation, and version-dispatched
standalone Measurement successors without changing PR16B identities; and fix
prospective acquisition to five non-backdating slots, with slots 0–3 half-open,
slot 4 including exact `target_at + 5 minutes`, and later acquisition prohibited.
The Methodology now distinguishes contemporaneously captured prospective
Evidence from later-acquired retrospective archive Evidence, preserves both
historical effective and acquisition times, and shows separate comparative,
prospective-standalone, and retrospective-standalone research paths.

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
event-level derived Analysis that is canonical only to its specific policy
execution, not globally or for production.
Execution uses versioned compatibility, production eligibility, observation and
provider selection, transformation, weighting, normalization, fallback, and
validation stages; invalid or unresolved inputs fail closed. Policies contain
no approval or lifecycle state, and PR12 retains all governance authority. The
initial planned demonstration is a supplied single-provider DRatings MLB winner
policy with latest eligible pregame selection, identity transform, weight
`1.0`, complete-distribution validation, and no fallback. Opportunity Board
consumer migration is deliberately separated into PR14; release hardening moves
to PR15. This documentation adds no PR11 implementation or production behavior.

PR11 implements the provider-neutral Forecast Policy execution foundation.
Immutable executable policy specifications preserve versioned bounded rule
components without governance state. Distinct structured production eligibility
and unique-latest selection process supplied Forecast Observations in immutable
multi-event batch executions; ambiguous, missing, invalid, incompatible, or
chronologically unresolved inputs fail closed. Event-level Policy Forecasts
preserve exact Decimal source distributions, identity transformation, fixed
weight `1.0`, no-fallback decisions, complete rule-stage provenance, validation,
and deterministic identity. A compact synthetic fixture and offline inspection
exercise two successful events alongside unresolved cases. No provider access,
Opportunity Board migration, governance, market valuation, or wagering behavior
is introduced.

The PR11 boundary audit makes execution identity explicitly acyclic, identifies
and preserves every material event context, removes wall-clock time from
canonical analytical contracts, reconciles completed output references, and
labels reason-code totals as overlapping occurrences. Multiple Policy Forecasts
may coexist for an event; PR12 alone will govern production authority and PR14
will migrate the downstream consumer.

The approved PR12 architecture defines immutable append-only Governance Records
as Product Owner decisions governing exactly one Forecast Policy, plus immutable
Governance History and deterministic replay-derived lifecycle. The bounded
decisions are Research, Shadow, Production, Retire, and terminal Reject;
lifecycle is never stored or mutated. Production resolution yields at most one
authorized policy per immutable sport/competition/proposition scope. Material
`decision_effective_at` orders current and historical replay; incidental order
never breaks simultaneous conflicts, which fail closed. Policy-level lifecycle
and scope-level authority remain separate derived views, while Shadow resolution
is measurement-only. Supporting Forecast Intelligence, Policy Hypotheses, and
Policy Proposals remain referenced non-executable Analysis.

PR12 implements that bounded governance layer with deterministic Governance
Scope and Governance Record identities, explicit Product Owner and effective
decision time, immutable Governance History, historical lifecycle views,
scope-level production resolution, structured conflicts, fixture-only
inspection, and regression coverage. It does not change Forecast Policy
execution, Opportunity Analysis, wagering, or begin PR13/PR14 work.
The final governance-semantics audit makes stable Product Owner ID material but
keeps optional display name descriptive, distinguishes equivalent same-time
decisions from conflicting decisions, retains complete supporting and conflict
record provenance, and fails scope authority closed only for conflicts material
to current or candidate Production authority. Unrelated research-only conflict
diagnostics remain visible without mutating valid production resolution.

PR13 implements the first-class `ResearchProtocol`, `EdgeClaim`,
`ResearchReview`, `MarketEdge`, and `DriftSurveillance` contracts. Bounded
supporting values express typed scientific rules, Probability Sources, Research
Populations, approved dimensions and domains, scheduled review boundaries,
future Comparative Performance Report references, explicit scheduled and
material-Drift obligation coverage, and nonmaterial audit provenance.

Scientific identities use versioned canonical SHA-256 material, exact Decimal,
UTC-equivalent datetime normalization, tagged serialization, and fail-closed
reconstruction. Pure graph validation enforces claim/report/protocol
compatibility, scheduled and Drift chronology, protocol-derived material-event
qualification, and one historical Market Edge established by the first
qualifying Review without arbitrary tie-breaking. The compact MLB fixture and
offline inspector exercise all five contracts without provider or network
access.

PR13 does not implement the canonical Comparative Performance Report,
authoritative Current Scientific Applicability, Policy, Governance, Workspace,
Opportunity Analysis, or production behavior. Those responsibilities remain
deferred to their approved later boundaries.

PR14 implements the protocol-governed path from Schedule Evidence to immutable
Research Capture Opportunities and Research Snapshots, including missing and
failed captures, append-only corrections, and deterministic historical replay.
Provider-neutral event-stage Evidence, complete authoritative Outcome History,
and boundary-specific Population Eligibility Results derive the Coverage
denominator and exclusions without caller authority.
Pair-specific Comparative Measurements reuse authoritative Forecast Evaluation
Brier and Log Loss values and preserve canonical proposition orientation.
Cumulative claim/domain Comparative Performance adds exact failure-inclusive
Coverage, deterministic paired-bootstrap uncertainty, Practical Significance
threshold reporting, Log Loss, and version-2 fixed-bin Calibration with absent
WACE for an empty paired population. Log Loss preserves deterministic signed
infinity and absent indeterminate comparisons without shrinking the Brier or
Calibration population. The synthetic fixture and offline
inspector add no provider collection or operational behavior. Canonical
Comparative Performance Reports remain PR15; Current Scientific Applicability
and Policy Recommendation remain PR20. PR16A defines standalone Probability
Source performance architecture. PR16B now implements its explicit v2 Protocol,
typed capture, market derivation, source Measurement, failure-inclusive Coverage,
cumulative and time-bounded performance, uncertainty, report-reference,
replay-validation, fixture, test, and offline inspection path. PR17A defines
separate retrospective candle and prospective order-book Kalshi MLB standalone
Protocols, home-team YES authority, contiguous activation, failure-inclusive
Coverage, append-only local Evidence storage, scheduling and backup seams,
correction-aware Outcome replay, and non-pooled reporting. PR17B–PR17D retain
implementation, activation, collection, and separate-report ownership.
The PR16B replay path derives capture eligibility from prospective authority,
selects corrected Outcome/Measurement lineage at explicit boundaries, enforces
causal effective chronology and complete schedule windows, and validates typed
paired cumulative, bounded, and Drift references during report composition.
Due-state replay is independent of the prospectively frozen population decision;
forecast-backed Measurements now replay their eligibility and evaluation
authority; paired populations are claim-specific for multi-challenger reports;
and equal-price market depth preserves every contributing Evidence level.
Snapshot schedule and target timing now replay from immutable Schedule Evidence,
standalone Coverage rejects cross-Protocol analytical authority, and pairwise
synchronization is reproduced from exact capture timestamps and Protocol rules.

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
## Unreleased — PR17C1

- Prepared exact typed prospective activation authority for September 5, 2026 midnight `America/New_York` (`04:00:00Z`), contingent on explicit Product Owner authorization and reviewed merge by September 3.
- Added injected, bounded, TLS-only read paths; macOS Keychain credential boundary; deterministic Kalshi home-team YES discovery; refresh deduplication; activated/dry-run isolation; health reporting; offline rehearsal; and inert local-Mac `launchd` templates.
- Documented PR17C1/PR17C2/PR17C3 with downstream PR17D unchanged. No Protocol was activated, no scheduler installed, no provider contacted, and no real Evidence created.
- Replaced successful placeholder commands with fail-closed typed composition, corrected fresh-clock request chronology, implemented documented Kalshi RSA-PSS signing seams, append-only operational heartbeat health inputs, absolute-path launchd rendering, and an artifact-derived offline rehearsal.
- Added canonical activated-authority initialization, provider-native MLB/catalog composition, strict raw-preserving `orderbook_fp` adaptation, independently aged health cadences, fail-closed inspect/index maintenance, and an activated all-rendered-job fixture rehearsal.
- Corrected proposed PR17C1 prospective scope to include the complete 2026 MLB regular-season scheduled-state universe; decoupled MLB opportunities from Kalshi mapping; added correction-aware supporting replay, bounded cursor-complete catalogs, New York obligation-driven MLB dates, and correct two-sided `orderbook_fp` bid complements. Missing, ambiguous, doubleheader, reschedule, cancellation, and invalid states remain visible. No live activation or Evidence collection occurred.
- Bound PR17C1 supporting and Outcome contracts to replay-verified acquisition manifests over exact raw pages and explicitly derived unions; retained unresolved non-terminal Outcome dates without an age cutoff; unified loaders on one trusted command start; and safely encoded opaque Kalshi cursors.
- Added real monotonic per-request chronology and acquisition-group crash reconciliation: incomplete or competing page groups are blocking partial authority excluded from replay, health, maintenance, indexes, and secondary synchronization until deterministic create-only recovery.
- Replaced trust in envelope contract serialization with independent, correction-aware reconstruction from verified provider pages and exact canonical comparison during ordinary replay.
- Added durable fresh-process recovery: `reconcile-acquisitions` immutably abandons exact unambiguous page-only groups without deleting Evidence, allowing later independently acquired replacements with truthful chronology while retaining the audit trail.
