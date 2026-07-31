# Pops' Edge v1.1.0 — MLB Research and Multi-Sport Foundation

## Release intent

Pops' Edge v1.1.0 introduces MLB research and begins the transition from the
v1.0.0 World Cup implementation to a multi-sport product. The transition is
incremental: v1.0.0 World Cup behavior remains the compatibility baseline
unless a later PR explicitly documents, tests, and obtains review for a change.

This plan defines the intended sequence. Each PR must remain independently
reviewable, preserve prior acceptance criteria, and use the workflow in
`docs/CODEX_WORKFLOW.md`.

## Version boundaries

### v1.0.0

v1.0.0 is the existing World Cup system: Silver forecast ingestion, Kalshi
World Cup market ingestion, match and futures value boards, portfolio and
ladder views, wager import, CLV and position tracking, web reports, archives,
and update scripts. Its existing calculations, report schemas, filenames, and
workflows are the regression baseline for v1.1.0.

### v1.1.0

v1.1.0 is complete when the approved MLB workflow is documented, implemented,
tested, and operable alongside the World Cup workflow through initial
multi-sport boundaries. It is not a promise to make every component
sport-agnostic. Broad refactoring is deferred until concrete MLB requirements
show which abstractions are durable.

## Release scope

- Research and select reproducible MLB data and market sources.
- Define canonical MLB contracts and sport-specific edge cases.
- Add deterministic MLB ingestion, valuation, reports, and operating workflow.
- Introduce only multi-sport boundaries proven by both World Cup and MLB.
- Preserve the World Cup v1.0.0 behavioral baseline.
- Complete documentation, migration notes, and release validation.

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

### PR5 — Implement MLB source ingestion

- Implement fixture-backed adapters for the selected MLB forecast, schedule,
  result, and market inputs.
- Add caching/provenance metadata and actionable validation failures.
- Keep network-dependent checks separate from the deterministic test suite.

**Gate:** canonical MLB inputs are reproducible from fixtures and source
failures are explicit.

### PR6 — Implement MLB valuation

- Match canonical MLB forecasts to markets.
- Implement and document MLB edge, action, ROI, sizing, and quality gates.
- Add deterministic calculation and matching tests, including no-vig or
  normalization behavior if approved by the research decision.

**Gate:** calculations are independently testable and World Cup regression
tests remain unchanged and passing.

### PR7 — Build MLB reports and operating workflow

- Produce the approved MLB research board(s), metadata, and web view.
- Add an MLB update workflow with archive/output behavior.
- Document operator inputs, commands, recovery steps, and generated artifacts.

**Gate:** an end-to-end fixture run produces validated MLB artifacts without
overwriting World Cup artifacts.

### PR8 — Introduce proven multi-sport boundaries

- Extract only interfaces and shared utilities demonstrated by both World Cup
  and MLB implementations.
- Centralize sport registration, shared configuration, and output isolation
  where evidence supports it.
- Preserve sport-specific logic where forced reuse would obscure behavior.

**Gate:** both sports run independently, shared boundaries have contract tests,
and World Cup outputs remain regression-compatible.

### PR9 — Release hardening and v1.1.0 handoff

- Run complete regression, compilation, shell, fixture, and documentation
  validation.
- Finalize operator/developer documentation, migration notes, known
  limitations, and rollback guidance.
- Confirm rename readiness and prepare release notes.
- Create tags, rename repositories/directories, commit, or push only when
  separately authorized.

**Gate:** all v1.1.0 acceptance criteria are traceable to passing validation or
an explicitly accepted limitation.

## Sequencing rules

PRs merge in numerical order. A later PR may refine a future PR's scope through
a documented decision, but it must not silently absorb unfinished earlier
work. Source research precedes contracts; contracts precede ingestion;
ingestion precedes valuation and reports; shared architecture follows two
working sport implementations.

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
- MLB reports operate without overwriting World Cup inputs or outputs.
- Proven shared boundaries support both sports without changing World Cup
  calculations or report behavior.
- The complete automated, compilation, shell, documentation, and release
  validation suite passes.
- Known limitations, operator guidance, rollback, and release notes are
  complete.
- Any commit, tag, push, hosted release, or rename occurs only after explicit
  authorization.

## Deferred capabilities

- Additional sports beyond World Cup and MLB.
- A universal sport schema or broad rewrite of the v1.0.0 pipeline.
- Automated trading or order placement.
- Changes to bankroll policy, Kelly policy, or existing wagering behavior.
- Hosted services, multi-user accounts, and generalized deployment.
- Repository and local-directory rename unless separately authorized.
- Data-source additions not approved by the PR2 research decision.
