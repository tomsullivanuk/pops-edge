# Pops' Edge v1.1.0 — Empirical Decision Foundation

## Release intent

Pops' Edge v1.1.0 completes the first end-to-end empirical decision lifecycle while continuing the incremental transition from the v1.0.0 World Cup implementation to a multi-sport product:

```text
Evidence
        ↓
Measurement
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

The release preserves the World Cup compatibility baseline, deterministic behavior, provenance, fail-closed validation, and the scope appropriate to a personal hobby project. Shared architecture continues to evolve only where concrete World Cup and MLB implementations justify it.

This plan defines the implementation sequence. Each PR must remain independently reviewable, preserve prior acceptance criteria, and follow `docs/CODEX_WORKFLOW.md`.

## Version boundaries

### v1.0.0

v1.0.0 is the existing World Cup system: Silver forecast ingestion, Kalshi
World Cup market ingestion, match and futures value boards, portfolio and
ladder views, wager import, CLV and position tracking, web reports, archives,
and update scripts. Its existing calculations, report schemas, filenames, and
workflows are the regression baseline for v1.1.0.

### v1.1.0

v1.1.0 is complete when Pops' Edge demonstrates the first end-to-end empirical
decision lifecycle for MLB—from immutable Evidence and Measurement through
Forecast Intelligence, governed Forecast Policy, Policy Forecast consumption,
Opportunity Analysis, and operational presentation—while preserving the World
Cup v1.0.0 compatibility baseline.

The release does not promise universal sport abstraction or require a broad
World Cup rewrite. It introduces shared boundaries only where concrete World
Cup and MLB implementations justify them.

## Release scope

- Establish reproducible MLB data and market sources, canonical identity, and
  immutable Evidence.
- Deliver deterministic ingestion, valuation, operational reporting,
  authoritative Outcome Evidence, and Forecast Evaluation Measurement.
- Add first-class Forecast Intelligence research contracts for Research
  Protocols, Edge Claims, Market Edges, Research Reviews, and Drift
  Surveillance.
- Implement Market-Benchmark-relative Comparative Performance and canonical
  Comparative Performance Reports.
- Align Policy Hypotheses to empirically supported Market Edges.
- Deliver the deterministic, read-only Forecast Intelligence Workspace.
- Migrate Opportunity Analysis to governance-authorized Policy Forecast
  consumption.
- Introduce shared multi-sport boundaries only where World Cup and MLB justify
  them, while preserving the World Cup v1.0.0 behavioral baseline.
- Complete documentation, operator workflow, regression, and release
  validation.

## Architectural principles

- Reusable platform code owns cross-sport concerns such as provenance,
  validation, configuration patterns, market/forecast contracts, output
  isolation, and deterministic testing.
- Sport adapters own source schemas, identifiers, schedules, settlement
  assumptions, matching rules, and sport-specific valuation policy.
- Facts, market observations, valuation decisions, and reports remain distinct.
- Source inputs and generated artifacts are reproducible and traceable.
- Shared abstractions must be earned by two real implementations.
- Network access is excluded from the deterministic test suite.

## PR sequence

### PR1 — Establish product foundation

- Establish Pops' Edge as the durable product name.
- Record v1.0.0 as the World Cup baseline and define v1.1.0.
- Add the release plan and Codex PR workflow.
- Inventory rename dependencies and document, but do not execute, the
  repository rename.
- Make no production calculation or report changes.

**Gate:** documentation is internally consistent; the full v1.0.0 test and
syntax suite passes.

### PR2 — Research MLB data and market sources

- Evaluate candidate MLB projection, schedule, result, roster, and market
  sources.
- Record licensing, authentication, freshness, coverage, identifiers, rate
  limits, failure modes, and reproducibility constraints.
- Select primary and fallback candidates without implementing production
  ingestion. Technical accessibility does not constitute approval until
  automated access and evidence-retention rights are documented.

**Gate:** a source decision record and representative, non-production samples
support the intended MLB use cases. The decision is recorded in
`docs/MLB_SOURCE_RESEARCH_v1.1.0.md`; production adapters remain blocked on
source-specific licensing gates.

### PR2A — Document product and architecture decisions

- Define Pops' Edge as an external-forecast evaluation platform rather than a
  proprietary prediction engine.
- Record the commercial-data cost and rights philosophy without approving a
  provider.
- Clarify reusable platform concepts, adapter responsibilities, canonical
  event identity, immutable observations, and fail-closed behavior.
- Formalize the product-manager/architect and Codex implementation-engineer
  workflow.

**Gate:** durable product, architecture, workflow, and release documentation
is internally consistent before PR3 begins; no production behavior changes.

### PR3 — Define the MLB domain and contracts

- Specify canonical MLB game, team, market, price, forecast, and result models.
- Define source-to-canonical mappings, time zones, game identity, doubleheader
  handling, postponements, cancellations, and market settlement assumptions.
- Add contract/schema tests using approved fixtures.
- Use MLB `gamePk` as canonical while preserving licensed-vendor identifiers
  and mapping evidence. Do not add network collection in PR3.

**Gate:** contracts cover documented edge cases without changing World Cup
contracts.

**Implemented boundary:** reusable Canonical Event identity, MLB `gamePk` and
team/game references, immutable schedule/pitcher/status observations,
source provenance, explicit lineage between distinct events, deterministic
serialization, and matched/ambiguous/rejected reconciliation. Provider
adapters, persistence, forecast and market contracts, and World Cup integration
remain deferred to their approved PRs.

### PR3A — Document external forecast architecture

- Establish Forecast Provider, Forecast Model, Forecast Version, and Forecast
  Observation as separate domain concepts.
- Document complete structured outcome distributions, precision-aware
  validation, timestamps, assumptions, revisions, corrections, withdrawals,
  and fail-closed event reconciliation.
- Separate immutable identity and evidence from mutable weighting and wagering
  policy without approving a provider or implementing contracts.

**Gate:** durable product and architecture documentation fully bounds the
provider-neutral PR4 contract work; no implementation or provider decision is
included.

### PR4 — Forecast Observation Contracts

- Implement offline, provider-neutral contracts for Forecast Provider,
  Forecast Model, Forecast Version, structured Forecast Outcomes, published
  probability values and precision, Forecast Observation, and
  provider-reported assumptions.
- Represent revisions, corrections, withdrawals, validation states, provider
  dispositions, and reconciliation references without mutating prior evidence.
- Add deterministic serialization, fixtures, and semantic tests.
- Defer provider adapters, DRatings or FanGraphs access, commercial-provider
  approval, network collection, persistence, weighting, eligibility and
  freshness policy, market observations, edge calculations, reports, and
  wagers.

**Gate:** provider-neutral contracts preserve the documented semantics in
offline fixtures and tests without changing World Cup behavior or beginning
provider integration.

**Implemented boundary:** immutable Provider, Model, Version, structured
Outcome, Published Probability, Distribution, provider-assumption, Forecast
Observation, validation, disposition, relationship, and timing contracts;
exact decimal and date serialization; precision-aware total validation;
deterministic canonical ordering; and composition with PR3 provenance and
event reconciliation. Provider access, adapters, persistence, weighting,
eligibility, freshness, markets, valuation, reports, wagers, and World Cup
integration remain deferred.

### PR5 — MLB Stats API Facts Adapter

- Implement one read-only, fixture-backed MLB Stats API adapter for Canonical
  Event, schedule, status, pitcher, and explicit lineage evidence.
- Preserve raw-source traceability and return deterministic partial success
  while failing closed on unsafe identity.
- Provide a separately invoked smoke path; keep all automated tests offline.
- Defer persistence, scheduled collection, forecast-provider and market
  adapters, valuation, reports, and wagering.

**Gate:** MLB facts are reproducible from fixtures, missing optional evidence
and source failures are explicit, and World Cup behavior remains unchanged.

**Implemented boundary:** `mlb_stats_api.py` provides the injectable client,
separate raw-byte and canonical-JSON evidence digests, structured issues,
explicit complete/partial/rejected results, honest source chronology,
deterministic serialization, and translation into PR3 contracts. Lineage
requires a direct source relation to another `gamePk`. `smoke_mlb_stats_api.py`
is explicit, concise, read-only, non-persisting, and fail-closed. Durable
retention and remaining forecast/market source work require later approved
scope before valuation.

### PR5A — Document Series / Observation architecture

- Establish Durable Identity → Immutable Observations → Derived Views as the
  shared language for time-varying evidence.
- Document Canonical Event as the owner of schedule, pitcher, and status
  observations and Forecast Series as the durable owner of Forecast
  Observations.
- Separate Series identity from observation evidence and derived current-state
  views while strengthening the Identity / Evidence / Policy boundary.
- Make no contract, adapter, persistence, market, valuation, report, wagering,
  or World Cup behavior changes.

**Gate:** durable product and architecture guidance fully bounds Forecast
Series implementation before PR6 begins.

### PR6 — Implement Forecast Series and first provider adapter

- Implemented provider-neutral Forecast Series contracts that reference Forecast
  Provider, Forecast Model, Forecast Version, and Canonical Event.
- Connected immutable Forecast Observations and their relationships to a Series
  without mutating prior evidence.
- Implemented the first external forecast adapter as an offline parser of a
  faithful, manually captured DRatings HTML snapshot. No automated DRatings
  access is approved.
- Reconcile against a separate MLB schedule fixture using controlled aliases,
  ordered participants, and exact UTC times; ambiguity fails closed.
- Keep current/latest/pregame/history/movement state derived, and defer
  persistence, weighting, freshness policy, markets, valuation, reports, and
  wagering.

**Gate:** Series identity, observation history, derived-view semantics, and the
first provider translation are deterministic and fixture-tested without
redesigning PR5A architecture or changing World Cup behavior.

**Checkpoint:** the implemented baseline through PR6 is summarized in
`docs/V1.1.0_CHECKPOINT_THROUGH_PR6.md`. PR7 remains the next planned product
and architecture review; this checkpoint is not a release or tag.

### PR7 — Kalshi MLB market evidence and deterministic valuation

- Implement provider-neutral Winner Propositions, Provider Market Series, and
  immutable Market Observations.
- Add bounded, injectable, read-only Kalshi MLB acquisition with explicit
  event and side reconciliation and partial-success results.
- Calculate side-aware executable acquisition and exact-Decimal expected value
  using an explicit fee model.
- Preserve component timing and provenance while deferring recommendation,
  sizing, bankroll, liquidity, freshness, and wagering policy.

**Implemented boundary:** market identity remains distinct from provider
identity; YES/NO semantics require explicit evidence; series creation is lazy;
ambiguous mappings fail closed; valuation is deterministic derived analysis.
The live smoke path is explicit and was not run during implementation.

**Gate:** fixture-backed calculations and matching are independently testable,
and World Cup regression tests remain unchanged and passing.

### PR8 — Opportunity Board and manual operating workflow

- Build the Opportunity Board as the primary MLB product surface over forecast
  evidence, market evidence, valuation, and current positions.
- Rank attention deterministically while displaying complete, partial,
  ambiguous, rejected, and non-executable cases with inline diagnostics.
- Add an explicitly invoked local workflow that validates prepared evidence,
  rebuilds the HTML board, and prints concise factual notifications.
- Use versioned temporary integration bundles and authoritative current
  open-position summaries; value held exposure only through visible
  quantity-aware liquidation depth.
- Normalize downloaded Kalshi trade activity deterministically with separate
  fees and source digest, and preserve bounded public order-book response
  timestamps/digests for executable-depth validation.
- Select strictly pregame observations for gross forecast comparison and the
  latest observation independently for liquidation; suppress comparison for
  in-play-only evidence, prioritize lifecycle states, and render canonical
  away/home ordering without changing provider evidence order.
- Validate both the August 2 pregame, no-position operating path and the
  retained August 1 in-play, settlement, position, and rejected-proposition
  regression path using the existing MLB schedule client.
- Defer recommendation policy, sizing, portfolio optimization, provider
  automation, durable persistence, and wagering.

**Implemented boundary:** Opportunity is derived presentation, never evidence
or policy. The workflow creates one primary HTML output without overwriting or
integrating with World Cup production artifacts.

**Gate:** an end-to-end fixture run produces a deterministic position-aware
Opportunity Board, and all World Cup regression tests remain passing.

### PR9 — Outcome Evidence and Forecast Evaluation

- Introduce immutable Outcome Evidence and authoritative MLB Outcome
  Observations sourced from the MLB Stats API; treat settlement and other
  provider results only as corroboration.
- Keep Evaluation Eligibility in Policy rather than embedding it in Outcome
  Evidence.
- Introduce immutable, reproducible Forecast Evaluations that compare one
  Forecast Observation's complete probability distribution with one Outcome
  Observation for exactly one Canonical Event.
- Score the complete two-participant distribution with versioned binary Brier,
  log-loss, directional, and calibration-bucket definitions.
- Preserve append-only Outcome and Forecast Evaluation histories with only a
  minimal replayable validation summary.
- Provide a bounded offline inspection command and compact, explicitly labeled
  fixture cases for lifecycle, exceptional-result, and chronology behavior.
- Defer Forecast Intelligence, Forecast Policy, Policy Forecast,
  market-relative evaluation, wagering evaluation, and automated Execution.

**Implemented boundary:** Outcome Evidence remains immutable and authoritative
through MLB `gamePk` and Canonical Event identity. Evaluation Eligibility is
versioned Policy. Eligibility Decisions and Forecast Evaluations are immutable
derived Analysis and never Evidence. Strict pregame eligibility uses Pops'
Edge collection provenance when row-specific provider publication time is
unknown. Eligibility is state-independent: duplicate evaluation pairs are
rejected by Forecast Evaluation History, not Policy. Immutable Outcome History
makes pre-postponement forecasts ineligible, permits later pregame forecasts
after documented rescheduling, keeps suspension distinct, and returns
indeterminate when chronology is incomplete. Positive-infinite log loss is
unclipped, portably tagged in JSON, and counted separately from finite log loss
in summaries. No provider-performance accumulation or Forecast Intelligence is
implemented.

**Gate:** Outcome and Forecast Evaluation contracts preserve authoritative
Evidence and reproduce distribution-aware Measurement; histories replay
deterministically; current MLB Opportunity Board and World Cup outputs remain
regression-compatible.

### PR10 — Forecast Intelligence Reports, Policy Hypotheses, and Proposals

- Add provider-neutral Forecast Intelligence contracts demonstrated with the
  sole currently implemented MLB Forecast Provider, DRatings, without requiring
  or claiming a second provider.
- Consume an explicit set of current Forecast Evaluations selected against
  authoritative Outcome History; preserve included, excluded, and superseded
  evaluation identities without double-counting corrected games.
- Define immutable evaluation windows and deterministic coverage, aggregate
  Brier/log-loss, calibration, bounded segment, trend, limitation, and
  sample-adequacy analysis.
- Produce an immutable Forecast Intelligence Report for one provider, domain,
  and evaluation window, with complete algorithm and input provenance.
- Define immutable, versioned, non-executable Policy Hypotheses as PR10
  analytical candidate specifications without depending on the PR11 Forecast
  Policy contract.
- Produce an immutable analytical Policy Proposal that connects measured
  findings and adverse evidence about one Policy Hypothesis to a suggested
  Product Owner governance action.
- Keep deterministic identities independent of wall-clock generation time;
  explicit evaluation windows or analysis-as-of boundaries are material, while
  `generated_at` or `derived_at` is provenance unless explicitly used as that
  boundary.
- Provide bounded offline fixtures, inspection tooling, focused tests, and
  documentation; do not persist mutable cumulative totals.
- Keep Research Mode non-executing: no second provider, weight optimization,
  broad hyperparameter search, active Policy execution, Policy Forecast,
  governance transition, Shadow production, Opportunity Board change,
  market-relative or wagering evaluation, sizing, bankroll, automatic
  production authority, or production configuration mutation.

**Gate:** Reports, hypotheses, and proposals replay deterministically from
immutable PR9 evaluations and explicit windows; identical material inputs and
algorithm versions produce identical identities regardless of rerun time;
limitations and sample sizes remain visible; no analytical artifact can create
a Forecast Policy or grant it production authority. Research never changes
production; Governance changes production.

**Implemented boundary:** provider-neutral immutable current-evaluation
selection, explicit date-range/as-of windows, coverage, aggregate Brier and
finite/infinite log-loss analysis, one-home-win-observation-per-game decile
calibration, reconciled actual-result, strict-favorite-result (including ties),
and home-win-probability-band segments, historical trend,
versioned sample adequacy, immutable Policy Hypothesis, advisory Policy
Proposal with deterministic rule provenance and factual benchmark absence,
fixture-only inspection, and focused tests. DRatings MLB winner
evaluations demonstrate the contracts without embedding DRatings semantics.
PR10 adds no Forecast Policy, Policy Forecast, governance record or transition,
Shadow mode, additional provider, Opportunity Board change, market-relative or
wagering evaluation, sizing, bankroll, or Execution behavior.

### PR11 — Forecast Policy, Batch Execution, and Policy Forecast

- Implement provider-neutral immutable Forecast Policy specifications with
  explicit domain/provider constraints and versioned compatibility,
  production-eligibility, observation/provider selection, transformation,
  weighting, normalization, missing-provider, fallback, and validation stages.
- Implement immutable Forecast Policy Execution as an explicit deterministic
  batch context with candidate/included/excluded observation provenance,
  reasons, identified material event contexts and conflicts, scope/as-of
  boundary, statistics, warnings, and output identities. Derive its identity
  before output creation; completed output IDs are reconciliation references.
- Produce independently identified immutable Policy Forecast derived Analysis
  for each Canonical Event with complete input, stage-decision, distribution,
  validation, precision, limitation, and derivation provenance.
  Each is canonical to its specific execution, not globally or for production.
- Demonstrate a supplied DRatings MLB winner policy: unique latest eligible
  validated pregame observation before explicit analysis-as-of, failing closed
  on a latest-timestamp tie; identity transform;
  weight `1.0`; complete two-outcome validation without silent correction;
  missing provider fails closed; no fallback.
- Add bounded offline fixtures, inspection tooling, deterministic serialization,
  focused tests, and documentation. Do not add dynamic rule plug-ins, provider
  access, weight optimization, governance, or Opportunity Board integration.

**Gate:** identical policy specifications and immutable input batches reproduce
identical execution and Policy Forecast identities; unresolved cases fail
closed; Evidence is never mutated or impersonated. Historical Evaluation
Eligibility remains distinct from production observation eligibility. A PR10
Policy Hypothesis does not automatically become this separate executable
production definition, and offline execution does not imply active status.
Wall-clock run time is absent from canonical analytical serialization. PR12
governance will select which Policy Forecast, if any, has production authority;
PR19 will consume that authorized output.

**Implemented boundary:** immutable provider-neutral Forecast Policy and
versioned rule components; distinct structured production eligibility;
deterministic unique-latest selection; exact Decimal identity transformation,
weight `1.0`, and complete-distribution validation; immutable multi-event batch
execution; independently replayable Policy Forecasts; structured unresolved
events and overlapping reason-code occurrence counts; acyclic execution/output
identity; identified event-context provenance; deterministic serialization;
compact synthetic fixtures; offline inspection; and focused tests. No governance state, provider
access, automatic policy selection, Opportunity Board migration, or wagering
behavior is added.

### PR12 — Product Owner Governance and Policy Lifecycle

- Implement immutable append-only `GovernanceRecord` decisions governing
  exactly one immutable Forecast Policy. Preserve governance schema/algorithm
  version, immutable production-scope identity, material
  `decision_effective_at`, Product Owner identity, rationale, notes, limitations,
  and references—not copies—of supporting Policy Proposal,
  Forecast Intelligence Report, and Policy Hypothesis objects.
- Support the bounded decision vocabulary `Research`, `Shadow`, `Production`,
  `Retire`, and terminal `Reject`. Decisions are events, never mutable policy or
  record fields; lifecycle values `Research`, `Shadow`, `Production`, `Retired`,
  and `Rejected` are replay-derived.
- Implement immutable `GovernanceHistory`, duplicate rejection, chronological
  deterministic replay at an explicit `as_of` boundary, policy-level historical
  lifecycle views, scope-level fail-closed production-policy resolution, and
  separate Shadow-policy resolution.
- Resolve at most one production-authorized Forecast Policy per immutable
  sport/competition/proposition scope. A later Production decision replaces the
  selection in that scope; a later non-Production decision for the selected
  policy removes authority; no earlier policy resumes implicitly. A
  non-Production decision for another policy does not disturb current authority.
  Policies in different scopes resolve independently.
- Fail closed on decisions after terminal Reject, different same-time policy
  decisions, simultaneous same-scope Production decisions, scope/policy mismatch, unknown
  policy, or missing effective time or Product Owner. Never order material ties
  by input, serialization, filename, record ID, operational timestamp, or
  filesystem metadata.
- Add bounded inspection tooling, deterministic fixtures, focused tests, and
  documentation. Do not change Forecast Policy execution, add providers,
  implement Opportunity Analysis or Opportunity Board migration, value markets,
  wager, or begin PR13/PR14.

**Gate:** identical material Product Owner decisions reproduce identical
Governance Record identities; append-only replay reproduces current and
historical lifecycle and authority without mutable state; Reject is terminal;
missing or conflicting production authority fails closed; Research artifacts
remain non-executable; changing effective time or scope changes record identity;
PR19 consumer migration remains deferred.

**Implemented boundary:** PR12 now provides immutable deterministic Governance
Scope and Governance Record contracts, append-only Governance History,
historical lifecycle derivation, structured fail-closed conflict diagnostics,
and exclusive production-policy resolution from a caller-supplied immutable
policy registry. Fixture-only inspection is available; no operational workflow
selects or executes a governed policy, and PR19 remains deferred.
Stable Product Owner ID is identifying while display name is optional metadata;
equivalent same-time decisions retain all supporting record IDs, materially
different decisions fail closed, and only conflicts involving current or
candidate Production authority invalidate an otherwise resolved scope.

### PR13 — Forecast Intelligence Research Contracts

**Purpose:** implement the first-class research-domain contracts required by the finalized Methodology and Architecture.

**Scope:**

- Research Protocol;
- Edge Claim;
- Market Edge;
- Research Review;
- Drift Surveillance;
- one claim-specific completed conclusion per Research Review;
- at most one immutable historical Market Edge per Edge Claim, established by
  its first Supported or Strongly Supported completed Review;
- protocol-defined scheduled review-boundary identities, authorized
  material-event references, explicit effective and completion times, and
  explicit review-obligation coverage;
- an immutable typed reference to the future canonical Comparative Performance
  Report;
- deterministic identities;
- provenance;
- serialization; and
- validation.

**Dependencies:** completed Evidence, Forecast Evaluation Measurement, Forecast Intelligence precursor, Forecast Policy, and Governance foundations from PR1–PR12.

**Exclusions:** do not calculate or store authoritative Current Scientific Applicability; implement a mutable applicability lifecycle, generic review-trigger contract, canonical Comparative Performance Report, always-on surveillance service, or Workspace/UI state; migrate Opportunity Analysis; modify Forecast Policy; or create Governance or operational authority.

**Gate:** the five research contracts preserve the Methodology's boundaries, cardinalities, immutable history, explicit obligation coverage, deterministic identities, provenance, serialization, and fail-closed validation. Drift Surveillance is claim-specific and distinguishes valid no-Drift, material-Drift, and insufficient-evidence findings from invalid input. PR13 creates neither authoritative current applicability nor production authority.

**Implemented boundary:** `forecast_research_contracts.py` supplies exactly the
five top-level contracts with bounded typed scientific rules, Probability
Source, population, dimension, domain, schedule, report-reference, obligation,
and provenance values. A compact offline MLB fixture, inspector, focused tests,
and pure `validate_research_contracts(...)` graph validation exercise scheduled
and Drift obligation chronology and first-qualifying Market Edge recognition.
The canonical Comparative Performance Report and deterministic Current
Scientific Applicability projection remain PR15 and PR16 responsibilities,
respectively.

### PR14 — Research Snapshot, Comparative Measurement, and Comparative Performance

**Purpose:** implement the protocol-governed path from pregame Evidence through cumulative claim-level Forecast Intelligence.

**Scope:** Research Capture Opportunity identity; immutable Research Snapshot Evidence, correction lineage, and historical replay; immutable pair-specific Comparative Measurement; cumulative claim/domain Comparative Performance; Protocol-governed paired uncertainty and deterministic Calibration safeguards; and exact Coverage populations.

**Dependencies:** PR13 research contracts and the completed identity, Evidence, Outcome, and Forecast Evaluation foundations.

**Exclusions:** canonical Comparative Performance Report, time-bounded surveillance analytics beyond PR13 contract support, scientific conclusions, Current Scientific Applicability, Policy Recommendation, Policy Hypothesis, Governance, Workspace, Opportunity Analysis, production authority, mutable state, and collection or workflow infrastructure.

**Gate:** deterministic protocol-compatible inputs reproduce one authoritative Snapshot lineage, pair-specific Measurements, cumulative Comparative Performance, paired uncertainty, versioned fixed-bin Calibration over the same paired population, and failure-inclusive Coverage without retrospective reconstruction or survivorship bias.

### PR15 — Comparative Performance Report and Forecast Intelligence Alignment

**Purpose:** implement the canonical Comparative Performance Report and align Forecast Intelligence terminology with the finalized Product and Architecture.

**Scope:** canonical reporting over PR14 cumulative Comparative Performance; alignment of the legacy `ForecastIntelligenceReport` implementation while preserving truthful compatibility; report provenance, findings, limitations, Coverage, and Research Review references.

**Dependencies:** PR13 research contracts and PR14 Evidence, Measurement, and cumulative Comparative Performance.

**Exclusions:** Research Review conclusions, Current Scientific Applicability, Policy Recommendation, Policy Hypothesis redesign, Governance, Workspace, or operational authority.

**Gate:** canonical reports reproducibly communicate Market-Benchmark-relative findings without reclassifying Snapshot Evidence, replacing Research Review, or misrepresenting the legacy provider-level report.

### PR16 — Current Scientific Applicability and Policy Recommendation

**Purpose:** derive current scientific applicability and advisory Policy Recommendations from immutable research history.

**Scope:** deterministic Current Scientific Applicability projection at an explicit timezone-aware `as_of` boundary; complete scheduled and material-event obligation replay; and non-authoritative Policy Recommendation aligned with the legacy `PolicyProposal` precursor.

**Dependencies:** PR13 contracts and PR15 canonical Comparative Performance Reports and Forecast Intelligence alignment.

**Exclusions:** mutable applicability state, Policy Hypothesis alignment, Product Owner Governance decisions, Forecast Policy, Workspace, or operational authority.

**Gate:** replay preserves historical Reviews and Market Edges, fails closed on unresolved obligations or incompatibility, and creates neither Governance nor production authority.

### PR17 — Policy Hypothesis Alignment

**Purpose:** align the implemented `PolicyHypothesis` with the finalized Product definition: a proposed operational strategy for exploiting one or more empirically supported Market Edges.

**Scope:** explicit linkage to supporting Market Edges and Forecast Intelligence; deterministic identity and provenance; multiple competing hypotheses over the same empirical foundation; and alignment of existing candidate-strategy semantics.

**Dependencies:** PR13 Edge Claim and Market Edge contracts and PR16 applicability and recommendation outputs.

**Exclusions:** a Policy Hypothesis remains non-authoritative, is not Evidence or a Forecast Policy, and does not redesign Product Owner Governance.

**Gate:** aligned Policy Hypotheses remain reproducible and non-executable, and no hypothesis grants itself production authority or mutates Governance.

### PR18 — Forecast Intelligence Workspace

**Purpose:** implement the first deterministic, read-only Forecast Intelligence Workspace as a surface over existing Forecast Intelligence and Governance context.

**Scope:** one locally generated workspace; shared explicit research and governance context; Comparative Performance and Reports; Edge Claims, Market Edges, Research Reviews, and Drift Surveillance; Policy Recommendations and Policy Hypotheses; Product Owner Governance context; diagnostics; and provenance.

**Dependencies:** PR13–PR17 canonical research, Forecast Intelligence, applicability, recommendation, and Policy Hypothesis contracts, plus completed Governance replay.

**Exclusions:** database, browser persistence, execution, governance authority, mutable business state, or independent analytical rules.

**Gate:** identical immutable inputs and context produce substantively identical projections; the Workspace cannot create Governance Records or production behavior.

### PR19 — Policy Forecast Opportunity Integration

**Purpose:** complete the migration from direct-provider Opportunity Analysis to governance-authorized Policy Forecast consumption.

```text
Forecast Policy
        ↓
Forecast Policy Execution
        ↓
Policy Forecast
        ↓
Opportunity Analysis
```

**Scope:**

- select the production-authorized Forecast Policy through existing Governance;
- execute that policy against compatible current Forecast Evidence;
- supply the resulting Policy Forecast to Opportunity Analysis;
- retain deterministic Expected Value and current Market Evidence;
- preserve existing position semantics and Opportunity Board behavior; and
- preserve complete provenance and fail-closed validation.

**Dependencies:** completed PR11 Forecast Policy and Policy Forecast, completed PR12 Governance, and aligned PR13–PR17 research-to-policy contracts. The Workspace is not an operational dependency, but PR18 precedes this work in the release sequence.

**Exclusions:** do not introduce historical Policy Forecast evaluation, automated Shadow measurement, new sizing Policy, or automated Execution.

**Gate:** Opportunity Analysis consumes only a compatible Policy Forecast produced by the Governance-authorized Forecast Policy; the legacy direct-provider path is removed or explicitly isolated without changing World Cup behavior.

### PR20 — v1.1.0 Integration and Release Readiness

**Purpose:** complete integration and release validation without introducing new analytical capabilities.

**Scope:**

- full regression validation;
- World Cup compatibility;
- MLB lifecycle validation from Evidence through operational outputs;
- documentation review;
- operator workflow validation;
- known-limitations and rollback review; and
- release readiness.

**Dependencies:** PR13–PR19 complete and their acceptance gates satisfied.

**Exclusions:** no new research, analytical, governance, policy, or operational capability.

**Gate:** the complete v1.1.0 lifecycle is traceable to passing validation or an explicitly accepted limitation, and release preparation does not create a tag, hosted release, repository rename, commit, or push without separate authorization.

## Sequencing rules

PRs merge in numerical order. A later PR may refine a future PR's scope through
a documented decision, but it must not silently absorb unfinished earlier
work. The completed foundation followed research before contracts, contracts
before ingestion, and ingestion before valuation and reporting; shared
architecture remains justified by concrete implementations.

The remaining work follows this sequence:

```text
Research contracts
        ↓
Evidence → Measurement → cumulative Comparative Performance
        ↓
Canonical reporting and Forecast Intelligence alignment
        ↓
Current applicability and Policy Recommendation
        ↓
Policy alignment
        ↓
Product surface
        ↓
Operational integration
        ↓
Release validation
```

PR18 precedes PR19 as a release-sequencing choice. The Forecast Intelligence
Workspace is not an architectural runtime dependency of Policy Forecast
Opportunity Integration.

Every PR must:

- state what changed and what deliberately did not;
- keep generated/local artifacts out of version control;
- add or update tests in proportion to behavioral change;
- run the validation required by `docs/CODEX_WORKFLOW.md`;
- identify external/manual validation that could not be automated; and
- stop before commit, push, tag, or repository rename unless explicitly
  authorized.

## Release-level risks

- MLB source terms, stability, identifiers, and rate limits may constrain the
  design.
- Schedule changes and doubleheaders make game identity and time handling
  materially different from tournament matches.
- Market availability and settlement rules may not map directly to World Cup
  assumptions.
- Premature abstraction could couple sports instead of isolating them.
- The repository and local-directory rename can break hard-coded paths,
  aliases, scheduled jobs, iCloud copies, IDE/task configuration, and external
  links.

These risks are addressed through research-first sequencing, fixture-backed
contracts, isolated outputs, and the deferred rename checklist.

## Release acceptance criteria

- Pops' Edge documentation consistently describes v1.0.0 and v1.1.0.
- Approved MLB sources and their operational constraints are documented.
- MLB contracts cover identifiers, time zones, doubleheaders, schedule changes,
  and settlement-relevant states.
- Fixture-backed MLB ingestion and valuation are deterministic and tested.
- First-class Research Protocol, Edge Claim, Market Edge, Research Review, and
  Drift Surveillance boundaries are implemented with deterministic provenance
  and fail-closed validation.
- Forecast Intelligence measures Comparative Performance relative to the
  Market Benchmark and produces canonical Comparative Performance Reports.
- Policy Hypotheses represent operational strategies grounded in empirically
  supported Market Edges without acquiring production authority.
- The Forecast Intelligence Workspace is operational as a deterministic,
  read-only Product surface over Forecast Intelligence.
- Opportunity Analysis consumes a governance-authorized Policy Forecast rather
  than the legacy direct-provider path.
- MLB operational reporting does not overwrite World Cup inputs or outputs.
- Proven shared boundaries support both sports while preserving World Cup
  v1.0.0 calculations, reports, and operator behavior.
- Historical Policy Forecast evaluation and automated Shadow measurement
  remain explicitly deferred pending separate architectural approval.
- The complete automated, compilation, shell, documentation, and release
  validation suite passes.
- Known limitations, operator guidance, rollback, and release notes are
  complete.
- Any commit, tag, push, hosted release, or rename occurs only after explicit
  authorization.

## Deferred capabilities

The following analytical capabilities remain intentionally deferred pending separate architectural approval:

- Historical Policy Forecast evaluation.
- Automated Shadow measurement.

Other deferred capabilities:

- Additional sports beyond World Cup and MLB.
- A universal sport schema or broad rewrite of the v1.0.0 pipeline.
- Automated trading or order placement.
- Changes to bankroll policy, Kelly policy, or existing wagering behavior.
- Hosted services, multi-user accounts, and generalized deployment.
- Repository and local-directory rename unless separately authorized.
- Data-source additions not approved by the PR2 research decision.
