# Pops' Edge Architecture

## Purpose and authority

This document defines how Pops' Edge realizes the capabilities in [`docs/PRODUCT.md`](docs/PRODUCT.md). Architecture realizes the Product; it does not redefine it.

[`EMPIRICAL_RESEARCH_METHODOLOGY.md`](EMPIRICAL_RESEARCH_METHODOLOGY.md) is the governing methodological authority. It defines how empirical knowledge is created and interpreted. The Product defines the required capabilities, this document defines their architectural boundaries, and implementation conforms to those boundaries:

```text
Empirical Research Methodology
            ↓
         Product
            ↓
      Architecture
            ↓
      Implementation
```

This architecture preserves methodological integrity without duplicating the Methodology or Product. It describes both the durable target architecture and the current implementation state. Where those differ, the difference is explicit.

## Architectural spine

The durable architecture follows the Product's flow from observation to governed action:

```text
Identity
        ↓
Evidence
        ↓
Measurement
        ↓
Forecast Intelligence
        ↓
Policy
        ↓
Operations
```

Each layer has a distinct responsibility:

- **Identity** establishes what is being observed.
- **Evidence** preserves what sources reported and what occurred.
- **Measurement** derives objective quantitative results from Evidence.
- **Forecast Intelligence** turns Measurement into reproducible operational knowledge.
- **Policy** records what behavior the Product Owner has authorized.
- **Operations** applies authorized Policy to current Evidence and records action.

Derived state never becomes Evidence. Research never creates production authority. Governance is the only bridge from empirical knowledge to authorized operational behavior.

## Current implementation state

Pops' Edge contains two implementation generations that intentionally coexist.

The World Cup production workflow remains a local, file-based pipeline. Python modules ingest forecast and market files, normalize workbooks, calculate value boards, import wager history, and render Excel and HTML outputs. Shell scripts coordinate local execution, archives, iCloud copies, notifications, and report opening. These workflows are not retrofitted merely to resemble the newer contracts.

The MLB implementation provides most of the reusable architectural foundation:

- canonical event and source-identity contracts;
- immutable forecast, market, outcome, and position observations;
- provider and model identity;
- Forecast Series and Market Series;
- deterministic Forecast Evaluation Measurement;
- provider-neutral Forecast Intelligence foundations;
- immutable Forecast Policy, Forecast Policy Execution, and Policy Forecast;
- event-sourced Product Owner Governance; and
- a deterministic Opportunity Board over the legacy direct-provider analysis path.

The following Product-aligned integration remains approved but not implemented:

- the Forecast Intelligence Workspace;
- first-class Research Protocol, Edge Claim, Market Edge, Research Review, and Drift Surveillance contracts at the full Methodology boundary;
- canonical Comparative Performance Report naming in implementation;
- migration of Opportunity Analysis from the direct DRatings forecast path to governance-authorized Policy Forecast consumption.

Historical Policy Forecast evaluation and automated Shadow measurement remain unimplemented analytical capabilities that may be required to support future policy evaluation; their implementation scope remains subject to separate architectural approval.

Current code names `ForecastIntelligenceReport` and `PolicyProposal` remain truthful implementation symbols. In this document, `ForecastIntelligenceReport` is treated as a legacy precursor to the canonical **Comparative Performance Report**, and `PolicyProposal` is treated as an advisory artifact subordinate to **Policy Recommendation**. No implementation rename or persisted-contract change is implied.

## Architectural principles

### Identity, Evidence, Analysis, and Policy remain separate

Identity defines durable objects. Evidence records immutable observations. Measurement and other Analysis are deterministic derivations. Policy governs selection, eligibility, thresholds, sizing, risk, and execution behavior.

> Identity is immutable. Evidence is immutable. Policy changes through explicit governance.

Policy may change without rewriting Identity, Evidence, Measurement, or prior Analysis.

### Evidence is append-only

Corrections, withdrawals, provider revisions, schedule changes, and outcome changes append new observations or relationships. They never mutate the historical information state.

### Derived results are reproducible

Forecast Evaluations, Comparative Performance, Policy Forecasts, Opportunity Analysis, and other derived artifacts identify their immutable inputs and versioned rules. Unstated repository state, incidental input order, filesystem timestamps, and wall-clock run time do not alter material identity.

### Ambiguity fails closed

Unresolved identity, incompatible propositions, invalid distributions, missing required providers, stale or incompatible Evidence, governance conflicts, unsupported fallback, and incomplete execution prevent authoritative output. Missing an opportunity is preferable to presenting a false edge.

### Shared abstractions are earned

Provider-specific and sport-specific meaning stays in adapters. World Cup and MLB justify common concepts, not speculative universal abstractions or a broad rewrite of working pipelines.

## Identity

### Canonical Event and source-native identity

A Canonical Event contains immutable contest identity: sport, competition, season, event identifier, participants, and authoritative sport-native identifiers. Scheduled time, status, pitchers, and other changing facts are observations rather than event identity.

For MLB, `gamePk` is the authoritative MLB-native identifier preserved by the MLB adapter. It is not a universal cross-sport identifier. `CanonicalEvent`, `SportNativeIdentifier`, and MLB-specific event contracts implement this boundary in `event_contracts.py` and `mlb_contracts.py`.

Provider-native event identifiers and mappings remain separate immutable records. Discovering a mapping never replaces canonical identity. Ambiguous source reconciliation selects no event.

### Participant and provider identity

Participant identity is canonical and independent of provider ordering or labels. Sport adapters assign roles such as home and away; provider position alone never establishes canonical semantics.

A Forecast Provider is a durable publishing source. A Forecast Model belongs to one provider, and a Forecast Version identifies a durable revision of one model. Unknown provider versions remain explicitly unknown; Pops' Edge never invents a version from collection time.

Provider, model, and version metadata is referenced by observations rather than copied into every record.

> **Reference durable objects; do not duplicate durable metadata.**

### Forecast Series

A Forecast Series identifies one provider/model/version forecast for one Canonical Event. It contains no probabilities, timestamps, assumptions, validation, or disposition. Those belong to Forecast Observations.

The identity chain is:

```text
Forecast Provider
        ↓
Forecast Model
        ↓
Forecast Version
        ↓
Forecast Series + Canonical Event
```

### Market Series

A Market Series is introduced only where a concrete market implementation requires durable contract identity. The implemented Kalshi Market Series maps one provider contract to one typed Winner Proposition for one Canonical Event. Provider YES/NO labels and settlement semantics remain adapter responsibilities.

Market status is Evidence, not Series identity. Ambiguous event, proposition, or side mapping creates no authoritative Series or valuation.

## Evidence

Evidence consists of immutable source observations with explicit provenance. The architecture currently supports:

- Schedule, Pitcher, and Status Observations;
- Forecast Observations;
- Market Observations;
- authoritative Outcome Observations; and
- Position and provider-activity observations where the operational workflow uses them.

Each observation preserves its source and source-native identity, Pops' Edge collection time, provider timestamp when actually known, canonical mapping, source representation or digest where applicable, validation, and structured limitations or rejection reasons.

Collection time and provider publication time are distinct. An unknown provider timestamp remains unknown. Source-native values, ordering, precision, assumptions, and disposition are preserved rather than silently repaired.

### Forecast Observations

A Forecast Observation is immutable external Evidence linking a Forecast Series to the complete probability distribution published for a Canonical Event. Every probability references a structured outcome identifier; participant order has no semantic meaning.

Published numeric values and precision are preserved. Materially inconsistent distributions remain Evidence but are invalid for downstream use. Probabilities are never silently normalized. Any permitted normalization is a separate, versioned, traceable Policy transformation.

Every provider revision appends a new observation. Corrections and withdrawals preserve the earlier record and add lineage. Validation (`valid`, `incomplete`, or `invalid`) remains distinct from provider disposition (`active`, `corrected`, or `withdrawn`).

### Market Observations

A Market Observation preserves a bounded market capture, quotes, visible depth, statistics, lifecycle status, component timestamps, and provenance. Direct provider bids remain distinct from complement-derived offers. A derived offer records its source side, source price, quantity, transformation, and acquisition side; it is never represented as a provider-supplied ask.

Closed, suspended, settled, cancelled, unknown, or depthless observations remain Evidence even when factually non-executable. That factual constraint remains distinct from operational Policy.

### Outcome Evidence

An Outcome Observation is authoritative immutable Evidence for one Canonical Event. For MLB, the MLB Stats API is the authoritative facts source. Kalshi settlement, provider result tables, and sportsbook results may corroborate an outcome but do not replace the authoritative observation.

Outcome corrections append a new observation. The earlier outcome and any Measurements derived from it remain immutable. A derived latest-authoritative-final view selects the current outcome without rewriting history.

### Current state is a derived view

Time-varying Evidence follows the durable pattern:

```text
Durable Identity
        ↓
Immutable Observations
        ↓
Derived Views
```

Concrete examples include:

```text
Forecast Series → Forecast Observations → Current Forecast / Latest Pregame Forecast

Market Series → Market Observations → Current Market / Latest Valid Pregame Market

Canonical Event → Schedule and Status Observations → Current Game State
```

“Current” and “latest” are queries over append-only history. The architecture does not introduce additional Series concepts merely for symmetry.

## Measurement

Measurement provides objective quantitative inputs to Forecast Intelligence.

**Consumes:** immutable Forecast Observations, authoritative Outcome Observations, Outcome History where chronology is material, and versioned Evaluation Eligibility Policy.

**Produces:** immutable Forecast Evaluations and reproducible aggregate inputs.

**Owns:** deterministic scoring and explicit linkage between the forecast distribution and realized outcome.

**Does not own:** Evidence, Market Edge conclusions, Forecast Policy, Expected Value, or operational authority.

### Forecast Evaluation

A Forecast Evaluation is immutable derived Measurement for exactly one Forecast Observation and one authoritative Outcome Observation for the same Canonical Event. It evaluates the complete published probability distribution, not merely whether the provider's favored side won.

Implemented MLB winner Measurement preserves:

- conventional binary Brier Score;
- Log Loss using exact Decimal calculation, including tagged positive infinity when the realized outcome received probability zero;
- unique-favorite directional accuracy;
- inputs required for Calibration;
- algorithm and eligibility versions;
- exact Forecast and Outcome identities; and
- warnings and limitations.

Evaluation Eligibility is Policy, not Evidence. It determines whether immutable forecast and outcome records may be compared under a versioned rule. For MLB, strict pregame eligibility uses Pops' Edge collection time when provider publication time is unavailable, without relabeling that collection time as provider provenance. Postponement, rescheduling, suspension, disposition, reconciliation, and authoritative-final rules fail closed when chronology is insufficient.

Forecast Evaluation History is append-only. When an authoritative final changes, a new evaluation references the new outcome. A derived current-evaluation selection marks earlier evaluations superseded so current summaries do not count one event twice.

Expected Value is not Forecast Evaluation Measurement. It belongs to Opportunity Analysis, where an authorized Policy Forecast is compared with current Market Evidence.

## Forecast Intelligence

Forecast Intelligence is the umbrella architectural capability that transforms immutable Evidence and Measurement into reproducible operational knowledge about Probability Sources relative to the Market Benchmark.

**Consumes:** Research Protocols, immutable Evidence, Forecast Evaluations and other Measurement, explicit research populations and analysis boundaries, and versioned analytical rules.

**Produces:** Comparative Performance, Comparative Performance Reports, Edge Claims and their assessments, Research Reviews, Drift findings, Market Edges, Policy Recommendations, and inputs to Policy Hypotheses.

**Owns:** provider-neutral empirical analysis, reproducibility, research provenance, and the scientific status of Market Edges.

**Does not own:** Evidence, Product Owner decisions, Forecast Policy lifecycle, production authority, Opportunity Analysis, or Execution.

### Research Protocols

A Research Protocol is an immutable, versioned specification for a reproducible investigation. It fixes the research question, population, benchmark and alternative Probability Sources, synchronization and eligibility conditions, measurements, analytical rules, burden of proof, surveillance, and review boundaries before outcomes are interpreted.

The Methodology governs protocol meaning. Architecture must preserve protocol identity, version, material inputs, and provenance without embedding protocol rules into provider adapters.

Full first-class Research Protocol contracts are approved but not yet implemented. Existing evaluation windows, eligibility policies, segmentation versions, and adequacy rules are narrower precursors and must not be presented as a complete protocol implementation.

### Comparative Performance

Comparative Performance evaluates a Probability Source relative to the Market Benchmark over a common qualifying evidence population. Absolute Brier Score, Log Loss, Calibration, or directional accuracy may describe a source, but absolute forecast quality alone does not establish a Market Edge.

Comparative Performance is pair-specific and reproducible from immutable Measurement under an explicit Research Protocol. Missing, excluded, unsynchronized, invalid, and superseded inputs remain visible. Different challengers may have different valid paired populations.

### Comparative Performance Reports

A Comparative Performance Report is the canonical immutable research artifact for one Research Protocol and analysis boundary. It communicates comparative findings, uncertainty, coverage, surveillance, and limitations while preserving sufficient input identities and rule versions for deterministic reproduction.

The implemented `ForecastIntelligenceReport` in `forecast_intelligence.py` is a provider-neutral precursor. It currently measures one Forecast Provider within an explicit domain and evaluation window and includes coverage, forecast quality, Calibration, segmentation, adequacy, excluded evaluations, deterministic identity, and provenance. Its symbol has not been renamed, and its provider-level absolute analysis does not yet implement the full Market-Benchmark-relative Comparative Performance Report required by the finalized Product and Methodology.

Architecture uses **Comparative Performance Report** as the canonical concept. Compatibility with the legacy symbol must be handled by a separately approved implementation change.

### Edge Claims and Market Edges

An Edge Claim is a durable or reproducibly derived research assertion under evaluation. It references its Research Protocol, Probability Source, Market Benchmark, research domain, and supporting empirical material sufficiently to reproduce its assessment.

```text
Research Question
        ↓
Edge Claim
        ↓
Empirical Support
        ↓
Market Edge
```

An Edge Claim is not Evidence, Policy, or production authority. Persistence is not prescribed until concrete implementation requirements justify it.

A Market Edge is the Forecast Intelligence conclusion that a Probability Source has demonstrated comparative advantage relative to the Market Benchmark under defined conditions. A probability disagreement is not automatically a Market Edge. Opportunity Analysis neither discovers nor establishes Market Edges; it consumes their operational expression through approved Forecast Policy.

First-class Edge Claim and Market Edge contracts are approved but not yet implemented. Existing adequacy and proposal artifacts must not be mistaken for those scientific conclusions.

### Research Reviews and Drift Surveillance

A Research Review evaluates Comparative Performance Reports and Edge Claims against the governing Research Protocol and burden of proof. The durable `ResearchReview` artifact represents one completed, immutable review and records only its completed scientific conclusion. It changes scientific conclusions discretely while leaving Evidence, Measurement, prior Research Reviews, Edge Claims, and historical Market Edges unchanged.

Drift Surveillance is deterministic, rerunnable analysis over cumulative and time-bounded Evidence. A valid material Drift finding creates a review obligation, but it does not mutate an Edge Claim, prior Research Review, Market Edge, Forecast Policy, or Governance History. Valid insufficient evidence remains distinct from a structurally invalid artifact or incompatible input; invalid material cannot produce a scientific finding.

**Under Review** is a derived procedural condition, not a completed Research Review conclusion. At an explicit timezone-aware `as_of` boundary, deterministic replay considers all protocol-defined scheduled review boundaries due by `as_of` and all valid protocol-defined material-event artifacts effective by `as_of`. An obligation remains unresolved unless a qualifying completed Research Review explicitly covers it; a newer Research Review does not resolve an obligation merely because it occurred later. A scheduled boundary may include only a grace period prospectively defined by the Research Protocol. An implementation must not invent another grace period.

While any qualifying obligation remains unresolved, Current Scientific Applicability is suspended and operational reliance must fail closed, while the latest completed scientific conclusion and historical Market Edge remain intact. Scientific inapplicability neither creates nor revokes Governance authority and does not modify Governance History.

Current Scientific Applicability may be exposed as a deterministic replayable projection; it is not stored as mutable authoritative state. Workspace or UI state cannot originate, resolve, or override Under Review. PR13 introduces no generic `ReviewTrigger` contract, mutable review lifecycle, workflow manager, always-on surveillance service, or additional durable contract whose purpose is to store current applicability.

This personal hobby platform does not require speculative always-on services. Scheduled local analysis and explicit reruns are sufficient until operational evidence justifies more infrastructure.

### Policy Recommendations and the legacy `PolicyProposal`

A Policy Recommendation is an advisory Forecast Intelligence output. It may recommend further research, creation or revision of a Policy Hypothesis, or reconsideration, suspension, or retirement of operational reliance. It never creates lifecycle state or production authority.

The implemented `PolicyProposal` artifact is a deterministic advisory precursor. It links the legacy report artifact to an implemented Policy Hypothesis, preserves supporting and adverse analysis, limitations, benchmark references, a versioned suggestion rule, and deterministic provenance. It remains subordinate to Forecast Intelligence and the canonical Policy Recommendation concept; it is not a primary architectural stage.

The implementation symbol remains until separately approved code and serialization migration work occurs.

### Research and production separation

```text
Research Protocol + Evidence + Measurement
                    ↓
          Forecast Intelligence
                    ↓
          Policy Recommendation
                    ↓
            Policy Hypothesis
                    ↓
       Explicit Product Owner action

Production-authorized Forecast Policy + current Evidence
                    ↓
        Forecast Policy Execution
                    ↓
             Policy Forecast
                    ↓
          Opportunity Analysis
                    ↓
              Execution
```

> **Research never changes production. Governance changes production.**

## Policy and Governance

### Policy Hypothesis

A Policy Hypothesis is a proposed operational strategy for exploiting one or more empirically supported Market Edges. It belongs between Forecast Intelligence and Product Owner Governance.

It may describe proposed source selection, conditions of use, transformations, weighting, eligibility, thresholds, fallback, sizing, or risk constraints. Multiple Policy Hypotheses may share the same empirical foundation.

A Policy Hypothesis is not Evidence, not a Market Edge, not production-authorized, and not a Forecast Policy.

The implemented `PolicyHypothesis` in `forecast_intelligence.py` predates the finalized semantics and primarily represents an immutable analytical forecasting candidate with provider/model constraints, weights, transformations, fallback, and domain scope. It is a useful precursor, but it is not yet explicitly anchored to one or more empirically supported Market Edges. This is a Product-versus-current-implementation gap; this documentation does not alter the symbol or its deterministic identity.

### Product Owner Governance

Product Owner Governance is the only architectural boundary that grants production authority.

**Consumes:** an already-defined immutable Forecast Policy, explicit Product Owner decision, Governance Scope, effective time, and references to supporting research artifacts.

**Produces:** immutable Governance Records and replay-derived lifecycle, Production authority, Shadow authorization, and diagnostics.

**Owns:** authorization and lifecycle decisions.

**Does not own:** Evidence, Forecast Intelligence findings, Forecast Policy contents, execution rules, or Opportunity Analysis.

#### Governance Record

A `GovernanceRecord` is one immutable, append-only Product Owner decision governing exactly one immutable Forecast Policy. It never governs a provider, policy family, or Policy Hypothesis.

Each record preserves the Forecast Policy identity, immutable Governance Scope, bounded decision, material `decision_effective_at`, stable Product Owner identity, schema and algorithm versions, rationale, limitations, and canonically ordered supporting research references. Supporting artifacts are referenced, not copied. A record stores no mutable previous, next, or current lifecycle state.

The decision vocabulary remains:

- `Research`: research-only use without production authority;
- `Shadow`: parallel production measurement without Opportunity Analysis or wagering authority;
- `Production`: production authority for the governed Forecast Policy;
- `Retire`: withdrawal of production authority while preserving history; and
- `Reject`: terminal rejection of that immutable Forecast Policy.

#### Governance History and replay

`GovernanceHistory` is an immutable append-only collection of Governance Records. Deterministic replay at an explicit `as_of` boundary derives policy lifecycle and scope authority from `decision_effective_at`.

Replay preserves these contracts:

- record ID, filename, input order, serialization order, and filesystem time never establish chronology;
- materially conflicting same-time decisions fail closed;
- Reject is terminal for an immutable Forecast Policy;
- at most one Production authority exists per Governance Scope;
- a later Production decision displaces earlier authority;
- removing current authority does not implicitly restore an earlier policy;
- Shadow authorization is resolved separately and may include multiple policies; and
- conflicts preserve all participating record identities and diagnostics.

Thus `A Production → B Production → B Retire` resolves to no production authority, while `A Production → B Shadow` retains A as Production authority. Governance state is always derived; no authoritative mutable lifecycle cache exists.

### Forecast Policy

A Forecast Policy is the governed bridge between Forecast Intelligence and operational decision making. It is an immutable executable Policy specification, separate from its lifecycle and governance state.

**Consumes:** no mutable state; its specification references provider/model/version constraints and versioned rule components.

**Produces:** deterministic behavior when applied by Forecast Policy Execution.

**Owns:** eligibility, selection, transformation, weighting, normalization, fallback, validation, and applicable sizing or risk rules.

**Does not own:** Evidence, research conclusions, Product Owner approval, lifecycle state, or market opportunity.

Forecast Policy identity depends on material executable specification inputs: domain scope, providers, model/version constraints, eligibility and selection, transformations, weights, normalization, fallback, validation, rule-component identities and parameters, implementation version, and limitations. It excludes governance state, Product Owner identity, wall-clock time, filesystem metadata, and repository location.

The implemented contract supports one or multiple providers without embedding DRatings semantics. A Policy Hypothesis or advisory `PolicyProposal` never automatically becomes a Forecast Policy.

## Operations

### Forecast Policy Execution

```text
Forecast Policy
        ↓
Forecast Policy Execution
        ↓
Policy Forecast
```

A Forecast Policy Execution is an immutable batch context for one deterministic application of one Forecast Policy to an explicit supplied observation scope. It never discovers events or collects provider data autonomously.

Execution identity is based on the policy, canonical immutable input set, explicit scope and analysis boundary, algorithm and rule-component versions, material event context, and output-affecting parameters. Runtime, repository state, filesystem order, and governance lifecycle are non-identifying.

The versioned rule pipeline is:

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

Required providers, fallback, transformations, weighting, and normalization are explicit. Execution never silently renormalizes, substitutes providers, uses stale observations, infers weights, falls back to market probability, or emits an incomplete distribution.

### Policy Forecast

A Policy Forecast is the immutable event-level result of one Forecast Policy Execution. It preserves the event and proposition, policy and execution identities, included and excluded Forecast Observations, provider/model/version identities, material rule decisions, event context, output algorithm version, complete probability distribution, exact arithmetic, validation, limitations, and analysis boundary.

It is derived Analysis, never Evidence. Multiple Policy Forecasts may coexist for one event. A Policy Forecast contains no market price, Expected Value, position, wager recommendation, order, lifecycle state, or Product Owner approval. Governance determines which Forecast Policy, and therefore which compatible Policy Forecast, may carry production authority.

Policy Forecast production and governance are implemented. The current Opportunity Analysis consumer has not yet migrated from direct DRatings Forecast Evidence to governance-authorized Policy Forecasts.

### Opportunity Analysis

**Consumes:** a governance-authorized Policy Forecast and compatible current Market Evidence.

**Produces:** deterministic Market Valuation, Expected Value, Opportunity eligibility, and the analytical basis for Evidence-Supported Positive Expected Value.

**Owns:** current economic comparison, explicit costs, executable-price semantics, and compatibility validation.

**Does not own:** Probability Source trust, Edge Claims, Market Edges, Forecast Policy, governance, Position Sizing Policy, or Execution.

Opportunity Analysis compares the approved operational probability with current executable market state. A positive arithmetic difference is not sufficient: the Policy Forecast must express a currently applicable, governed empirical basis and the current opportunity must satisfy applicable constraints before the Product can identify Evidence-Supported Positive Expected Value.

The implemented MLB precursor directly compares DRatings Forecast Evidence with Kalshi Market Evidence. It preserves side- and quantity-aware visible depth, explicit derived offers, gross-before-fees labeling where fee Policy is not approved, pregame comparison timing, and separate in-play liquidation analysis. This path is truthful legacy behavior, not the final Policy Forecast consumer architecture.

### Opportunity, Position Sizing, and Execution

An Opportunity is transient derived state rebuilt from authoritative inputs. The current `Opportunity` references a Forecast Observation, Market Observation, Market Valuation, and Position; the Product-aligned form will instead reference the governance-compatible Policy Forecast after consumer migration. Partial, ambiguous, rejected, or non-executable cases remain visible as diagnostics rather than fabricated Opportunities.

Position Sizing is governed downstream behavior. Expected Value does not determine exposure by itself. Fixed sizing, fractional Kelly, exposure caps, bankroll constraints, liquidity, and other rules must be explicit Policy and fail closed when required inputs are absent.

**Execution consumes** an eligible Opportunity and approved operational Policy. **It produces** immutable or append-only records of actions and outcomes. **It does not own** scientific conclusions or Forecast Policy.

One wager outcome does not establish forecasting quality. Operational outcomes may later become Evidence under an appropriate Research Protocol; research evaluates populations, not anecdotes.

## Product surfaces

### Forecast Intelligence Workspace

The Forecast Intelligence Workspace is the Product Owner's primary interactive surface for Forecast Intelligence. It is a surface over the capability, not the capability itself.

The approved architecture is a deterministic, read-only, locally generated projection over immutable inputs and existing domain services. It introduces no authoritative business state, browser persistence, database, governance engine, wagering interface, or execution workflow. Identical material inputs and context produce substantively identical output.

The Workspace may surface:

- Research context and protocol scope;
- Comparative Performance and Comparative Performance Reports;
- Edge Claims and Market Edges;
- Research Reviews and Drift Surveillance;
- Policy Recommendations and subordinate legacy `PolicyProposal` artifacts;
- Policy Hypotheses;
- Product Owner Governance context and non-authoritative decision drafts; and
- diagnostics, exclusions, immutable identities, and provenance.

All sections share one explicit immutable context containing domain, research and governance boundaries, provider scope, Policy Hypothesis scope, and Forecast Policy scope. No section silently widens or replaces that context. Incompatible artifacts are excluded with diagnostics.

The Workspace may orchestrate existing selection, Forecast Intelligence, advisory, and governance-replay services. It must not fork their rules. A governance decision draft has no authority and cannot create a Governance Record.

The Workspace is approved but not currently implemented. Existing documentation and planned context names elsewhere in the repository predate the Product terminology; this document defines the canonical Product-facing surface name without claiming those artifacts have been migrated.

### Opportunity Board

The Opportunity Board is the operational surface for current opportunities and diagnostics. It presents market state, operational probability, valuation, position state, eligibility, and provenance without performing research or granting trust.

The current MLB board is deterministic and uses explicit ordering for adverse exposure, unresolved diagnostics, other positions, positive-EV unheld analyses, and remaining complete rows. Presentation order is neither Evidence nor a wagering recommendation. The board remains on the legacy direct-provider consumer path until Policy Forecast integration is implemented.

### Reports

Reports communicate product state and analysis. They preserve provenance and never become hidden sources of Policy. Comparative Performance Reports are Forecast Intelligence artifacts; operational reports remain downstream views.

## Cross-cutting patterns

### Provenance and deterministic identity

Material derived artifacts identify their immutable inputs, scope, analysis boundary, algorithm and rule versions, transformations, exclusions, limitations, and deterministic digest where implemented. Canonical ordering removes irrelevant input-order effects.

Wall-clock generation time may be presentation provenance but is not material identity unless explicitly declared as an analysis boundary. Tagged JSON preserves non-standard analytical values such as positive-infinite Log Loss without emitting invalid JSON numbers.

### Reconciliation

Offline source reconciliation returns `matched`, `ambiguous`, or `rejected`. A match identifies one Canonical Event and supporting evidence. An ambiguous result retains all eligible candidates and selects none. A rejection selects none while preserving structured reasons and candidate-evaluation audit material where available.

Valid source Evidence and valid canonical reconciliation are separate concerns. A source record remains Evidence even when reconciliation prevents Analysis.

### Fail-closed behavior

Hard failures include unresolved event or participant identity, doubleheader ambiguity, incompatible propositions, conflicting chronology, invalid distributions, stale forecasts or markets, missing executable prices, unclear side or settlement mapping, absent required providers, unsupported fallback, governance conflict, and incomplete Policy execution.

Failures remain explicit and local. One invalid comparison does not invalidate unrelated valid comparisons.

### Provider and sport adapters

Adapters retain provider-native schemas, authentication, identifiers, timestamps, parsing, licensing constraints, and validation. Sport adapters retain schedules, participant roles, doubleheaders, postponements, suspensions, extra time, penalty shootouts, and settlement meaning.

Reusable contracts address only responsibilities demonstrated across implementations: canonical identity, immutable observations, provenance, reconciliation, deterministic Analysis, governance, and stable presentation boundaries.

### World Cup component boundary

World Cup-specific components remain:

- `process_silver.py` and `process_silver_futures.py` for Silver schemas and normalization;
- `build_value_board.py`, `build_futures_value_board.py`, and `build_ladder_board.py` for World Cup valuation and position views;
- World Cup HTML builders, filenames, sheet semantics, ticker families, archives, and workflow commands; and
- mixed reusable and World Cup behavior in `import_wagers.py`, `build_web_betlog.py`, and shell orchestration.

Potentially reusable components include configuration patterns, Kalshi acquisition, wager-ingestion foundations, reporting utilities, quality checks, archival patterns, and fixture-based tests. They are candidates, not declarations of sport-neutral architecture.

## Current data flows

### World Cup production flow

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

### MLB architectural flow

```text
Provider and sport adapters
        ↓
Canonical Identity + immutable Evidence
        ↓
Forecast Evaluation Measurement
        ↓
Forecast Intelligence
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
Opportunity Board / Execution
```

The Evidence-through-Policy Forecast path is substantially implemented. The Policy Forecast-to-Opportunity Analysis connection remains an approved integration gap.

## Boundaries and dependencies

- Local World Cup state is workbook/CSV based; generated artifacts are not canonical Evidence.
- `config.py` currently sets `PROJECT_DIR` to `~/pops-edge`.
- Manual inputs are discovered in the project directory or `~/Downloads`.
- Current market ingestion uses public Kalshi APIs.
- World Cup forecast ingestion uses manually downloaded Silver exports.
- DRatings MLB ingestion parses manually captured local HTML and performs no provider network access.
- The MLB Stats API adapter is read-only, has injectable transport, bounded retries, explicit request parameters, raw-response and semantic digests, and no import-time network activity.
- macOS workflows use local tooling such as `open`, optional `osascript`, and an iCloud Drive directory.
- A local Python environment and third-party packages are assumed.
- Detailed schemas and operator behavior belong in `DEVELOPER.md`; release history and sequencing belong in `CHANGELOG.md`, `ROADMAP.md`, and `docs/RELEASE_PLAN_v1.1.0.md`.

## Current implementation gaps

The following gaps are architectural state, not roadmap commitments:

| Capability | State |
|---|---|
| Canonical Identity and immutable observation contracts | Implemented for MLB; World Cup remains legacy file-based |
| Forecast Evaluation Measurement | Implemented for MLB winner forecasts |
| Provider-neutral Forecast Intelligence precursor | Implemented with legacy report and proposal symbols |
| Full Research Protocol and Comparative Performance Report boundary | Approved, not implemented |
| Edge Claim, Market Edge, Research Review, and Drift Surveillance contracts | Approved, not implemented |
| Policy Hypothesis aligned explicitly to supported Market Edges | Product-approved; existing symbol has older analytical-candidate semantics |
| Forecast Policy, deterministic execution, and Policy Forecast | Implemented |
| Event-sourced Product Owner Governance | Implemented |
| Forecast Intelligence Workspace | Approved, not implemented |
| Opportunity Analysis consuming governance-authorized Policy Forecast | Approved, not integrated; legacy direct-provider path remains active |
| Historical Policy Forecast evaluation and automated Shadow measurement | Not implemented |

These gaps must be resolved through separately approved implementation work. Architecture does not invent compatibility shims or silently redefine existing contracts.
