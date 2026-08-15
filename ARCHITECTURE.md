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

The durable comparative-research path crosses those layers explicitly:

```text
Protocol-governed Schedule Evidence
        ↓
ResearchCaptureOpportunity          (Evidence identity/supporting value)
        ↓
ResearchSnapshot                    (Evidence)
        ↓
Outcome Evidence
        ↓
ComparativeMeasurement              (Measurement)
        ↓
ComparativePerformance              (Forecast Intelligence)
        ↓
ComparativePerformanceReport        (PR15 Forecast Intelligence)
        ↓
ResearchReview / Drift Surveillance
```

PR14 implements this path only through cumulative `ComparativePerformance`.

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
- protocol-governed Research Capture Opportunities and Research Snapshots;
- immutable Comparative Measurement and cumulative claim-level Comparative Performance;
- canonical Comparative Performance Report naming in implementation;
- migration of Opportunity Analysis from the direct DRatings forecast path to governance-authorized Policy Forecast consumption.

The first-class Research Protocol, Edge Claim, Market Edge, Research Review,
and Drift Surveillance contracts are implemented in
`forecast_research_contracts.py`. They provide immutable scientific rules,
typed report and review-obligation references, deterministic identity,
provenance, serialization, and fail-closed graph validation. They do not
calculate Current Scientific Applicability or create production authority.

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

### Research Capture Opportunity

`ResearchCaptureOpportunity` has one purpose:

> Identify one protocol-defined pregame scientific capture opportunity independently of later canonical-event interpretation or runtime execution details.

It is a bounded Evidence identity and planning value, not an additional scientific stage, scheduler, workflow, mutable attempt, service, or queue.

Its deterministic identity is based only on the Research Protocol ID, upstream Schedule Observation ID, proposition type, and schema/identity version. Canonical-event mapping, parsed scheduled start, target or actual capture timestamps, runtime job or process IDs, retries, filesystem metadata, and capture success do not define it.

A genuine new upstream Schedule Observation, including an actual reschedule, creates a new Research Capture Opportunity. A corrected mapping or parsing of the same Schedule Observation remains within the original opportunity, and retries do not automatically create a new scientific opportunity. The Research Protocol's postponement and rescheduling rules determine whether either opportunity is scientifically eligible.

```text
Schedule Observation A (7:00 PM) → Research Capture Opportunity A
Schedule Observation B (9:00 PM) → Research Capture Opportunity B
```

Opportunity B does not correct Opportunity A.

#### Research event eligibility context

`ResearchEventEligibilityContext` is a bounded, immutable, deterministic,
replayable, provider-neutral supporting Evidence value. It assembles and
validates the authoritative facts required to evaluate one Research Capture
Opportunity against its Research Population at an explicit timezone-aware
`analysis_boundary`. It is not a new top-level scientific stage, source-of-truth
replacement, mutable current-state object, scheduler or workflow state,
provider-adapter authority, or production authority.

Authority remains separated:

- `CanonicalEvent` owns canonical event identity, sport, competition, season,
  and participants.
- Immutable sport-provider event-classification Evidence owns event phase,
  postseason or regular-season status, or the equivalent competition-stage
  classification prospectively available for that sport.
- `OutcomeHistory` owns scheduled-start and authoritative status chronology,
  including postponement, cancellation, rescheduling, and status transitions.
- `ResearchEventEligibilityContext` only assembles and validates those facts as
  available through the analysis boundary.

An MLB adapter may derive competition-stage Evidence from authoritative MLB
event Evidence such as `MLBGame.game_type`; neither `MLBGame` nor its native
codes become a provider-neutral dependency of Comparative Performance. Other
sports may supply equivalent phase/stage Evidence without redesigning PR14.

One latest Outcome Observation is insufficient for history-sensitive rules.
Eligibility consumes the authoritative Outcome History, or equivalently
complete immutable schedule/status history, through the analysis boundary.
Later Evidence cannot rewrite earlier replay, and a future Schedule Observation
cannot enter an earlier Coverage denominator.

A bounded immutable Population Eligibility Result deterministically applies the
Research Population's temporal-scope, event-status, postseason, postponement,
cancellation, rescheduling, inclusion, and exclusion rules. It preserves the
Research Capture Opportunity, eligibility-context, Protocol and population
identities; analysis boundary; eligibility disposition; governing rule IDs and
versions; deterministic reason codes; validation; and provenance. It is not a
generic rule engine, mutable lifecycle, or caller-owned exclusion state. A rule
requiring facts not represented by the context fails closed.

```text
Authoritative event/classification/schedule Evidence
        -> ResearchEventEligibilityContext
        -> deterministic Protocol Population evaluation
        -> eligible Research Capture Opportunity population
        -> Research Snapshot and capture outcomes
        -> Comparative Coverage
```

An opportunity is not eligible merely because it exists, references a Protocol,
has a supplied Snapshot, or appears in caller input. Conversely, once proven
prospectively eligible, total or partial capture failure does not remove it from
Coverage. Protocol exclusions are rule-derived and preserve excluded identities
and reasons; arbitrary caller-supplied lists have no scientific authority.

Opportunity identity and correction semantics do not change. A genuine new
Schedule Observation creates a new opportunity; corrected interpretation of
the same observation remains within the same opportunity and Snapshot lineage.
Postponement, cancellation, and rescheduling evaluation preserves original and
later opportunities and the current schedule state at each analysis boundary,
rather than collapsing history into the latest eventual state. Cancellation
remains immutable Evidence and is excluded or retained in a reasoned Coverage
category only as directed by the prospective cancellation rule.

### Research Snapshot

A `ResearchSnapshot` is one first-class immutable Evidence record of what was actually available at one protocol-defined pregame information state. It preserves its Research Capture Opportunity and Research Protocol references; event and proposition interpretation; scheduled-event information; target and capture chronology; source-capture results; pairwise synchronization; prospectively approved Research Dimension classifications; validation status and reasons; limitations; provenance; correction lineage; and timezone-aware `effective_at`.

Source-capture state distinguishes scientifically meaningful outcomes such as captured and valid, missing, captured but invalid, and outside capture tolerance. Individual source validity and pairwise synchronization are distinct. Synchronization is evaluated independently between the Market Benchmark and each Alternative Probability Source, and the Snapshot preserves pair-specific diagnostics. Failure of one challenger pair does not invalidate another valid pair from the same Snapshot. No standalone generic comparative-pair reference or trigger is introduced.

Research Dimension classifications use only information available at the Snapshot and prospectively approved Research Protocol rules. They are preserved immutably for later Comparative Performance selection. Reports never reconstruct or retrospectively reclassify them using later information.

A known protocol-eligible capture opportunity may produce a Snapshot even when every provider observation is missing. Missing capture is scientific Evidence and remains visible in later Coverage. A Snapshot contains no Outcome, Brier Score, Log Loss, Research Review conclusion, Market Edge status, Current Scientific Applicability, Policy, Governance, Opportunity Analysis, or production authority.

#### Snapshot correction, uniqueness, and replay

Snapshot correction is append-only. A correction creates a new immutable Snapshot that explicitly supersedes the earlier Snapshot; there is no mutable `is_current`, `is_superseded`, or current-Snapshot pointer.

> A correction repairs the preserved representation or deterministic interpretation of prospectively captured Evidence. A materially different information state is a new observation or capture opportunity.

Legitimate corrections include event or proposition mapping errors, timezone parsing errors, probability parsing errors reproducible from preserved raw Evidence, incorrect dimension classification under unchanged rules and inputs, incorrect synchronization under unchanged timestamps and rules, or a prospectively captured observation incorrectly recorded as missing. Corrections cannot introduce retrospectively discovered probabilities, later provider updates, actual provider/model-version changes, actual reschedules or postponements, new propositions or Research Protocols, later Outcome Evidence, retrospective partition changes, or changed capture tolerances. They never reconstruct prospectively missing Evidence.

Within each Research Capture Opportunity, identical deterministic Snapshot copies represent the same artifact. Materially different Snapshots require explicit supersession lineage within that opportunity. Lineage is acyclic; unknown references and branching fail closed. Deterministic replay at an analysis boundary must yield exactly one authoritative terminal Snapshot. Ambiguity is never resolved by ID, generation time, input order, filesystem order, serialization order, or another arbitrary tie breaker.

`target_capture_at`, `capture_started_at`, and `capture_completed_at` preserve capture chronology. They are distinct from `effective_at`: the instant an immutable Snapshot version entered the accepted scientific record and became available to downstream scientific computation. A correction may preserve original capture chronology while becoming effective later. Historical analysis includes only versions satisfying `snapshot.effective_at <= analysis_boundary`, so a later correction cannot silently alter an earlier analysis or report.

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

### Comparative Measurement

`ComparativeMeasurement` is one immutable Measurement-layer artifact for one valid synchronized Market Benchmark/Alternative Probability Source pair from one Research Snapshot and one authoritative Outcome. The Outcome remains separate from the pregame Snapshot:

```text
ResearchSnapshot + Outcome Evidence → ComparativeMeasurement
```

Snapshot identity and content never depend on the realized Outcome. A valid Comparative Measurement requires the same immutable Research Protocol, Research Snapshot, event, proposition, and authoritative Outcome; the Protocol's Market Benchmark; one authorized Alternative Probability Source; valid benchmark and challenger observations; valid pair synchronization and Outcome; and complete Protocol compatibility. One failed challenger pair does not invalidate another valid pair.

The Measurement references authoritative upstream artifacts and preserves benchmark and challenger probabilities, Outcome, each Brier Score, Brier improvement, each Log Loss, Log Loss improvement, preserved Research Dimension classifications, methodology and algorithm versions, validation, limitations, and provenance. These deterministic Measurement outputs do not compete with upstream Evidence authority and must reproduce from the referenced inputs.

```text
Brier improvement    = benchmark Brier Score - challenger Brier Score
Log Loss improvement = benchmark Log Loss - challenger Log Loss
```

Positive values favor the challenger. Calibration remains a population-level supporting measure rather than an event-level comparative conclusion.

Source Log Loss is narrowly defined over the extended nonnegative real range
`[0, +Infinity]`. Zero probability for the realized Outcome legitimately yields
`+Infinity`; `NaN` and source-level `-Infinity` are invalid. Paired improvement
uses these exact semantics:

```text
finite    - finite    -> finite
+Infinity - finite    -> +Infinity
finite    - +Infinity -> -Infinity
+Infinity - +Infinity -> absent / not applicable
```

The last case is mathematically indeterminate and supplies no pairwise Log Loss
ranking. Both source values remain `+Infinity`, but the Comparative Measurement
remains valid and retains its Brier values and improvement, Outcome and source
lineage, Snapshot lineage, Coverage contribution, and Research Dimension
classifications. It remains in the exact Brier and Calibration paired
population.

## Forecast Intelligence

Forecast Intelligence is the umbrella architectural capability that transforms immutable Evidence and Measurement into reproducible operational knowledge about Probability Sources relative to the Market Benchmark.

**Consumes:** Research Protocols, immutable Evidence, Forecast Evaluations and other Measurement, explicit research populations and analysis boundaries, and versioned analytical rules.

**Produces:** Comparative Performance, Comparative Performance Reports, Edge Claims and their assessments, Research Reviews, Drift findings, Market Edges, Policy Recommendations, and inputs to Policy Hypotheses.

**Owns:** provider-neutral empirical analysis, reproducibility, research provenance, and the scientific status of Market Edges.

**Does not own:** Evidence, Product Owner decisions, Forecast Policy lifecycle, production authority, Opportunity Analysis, or Execution.

### Research Protocols

A Research Protocol is an immutable, versioned specification for a reproducible investigation. It fixes the research question, population, benchmark and alternative Probability Sources, synchronization and eligibility conditions, measurements, analytical rules, burden of proof, surveillance, and review boundaries before outcomes are interpreted.

One Research Protocol may investigate multiple Alternative Probability Sources. Each distinct Alternative Probability Source-versus-Market Benchmark hypothesis within a Research Domain has its own Edge Claim.

The Methodology governs protocol meaning. Architecture must preserve protocol identity, version, material inputs, and provenance without embedding protocol rules into provider adapters.

First-class Research Protocol contracts are implemented. Existing evaluation windows, eligibility policies, segmentation versions, and adequacy rules remain narrower precursors and must not be presented as protocol-governed Evidence collection or the canonical Comparative Performance implementation.

### Comparative Performance

One immutable `ComparativePerformance` is cumulative claim-level Forecast Intelligence for exactly one Research Protocol, one Edge Claim, one Research Domain, one Market Benchmark, one challenger, one analysis boundary, and one cumulative paired Comparative Measurement population. `ComparativeMeasurement` is not Edge-Claim-specific; the same Measurement may contribute to multiple prospectively authorized Research Domains through classifications preserved on its Snapshot.

Its population contains all and only Measurements satisfying Protocol, benchmark, challenger, validity, eligibility, and Research Domain compatibility; whose authoritative Snapshot is effective by the analysis boundary; and whose Measurement is available/effective by that boundary. The broad Research Domain is independently aggregated from all qualifying broad-population Measurements. Segmented-domain results never reconstruct the broad result.

Brier improvement relative to the Market Benchmark is the single Methodology v1 primary endpoint. Comparative Performance reports at minimum paired sample size, benchmark and challenger mean Brier Scores, and mean paired Brier improvement. It introduces no weighted composite score.

Uncertainty follows the immutable Research Protocol statistical-method rule. For the approved paired bootstrap, the resampling unit is the complete Comparative Measurement, benchmark and challenger values are never independently resampled, and the resampled statistic is mean paired Brier improvement. Output includes the point estimate, paired sample size, interval bounds, confidence level, statistical-rule identity/version, resample count, and analysis algorithm version.

Bootstrap is reproducible: its pseudorandom seed derives from immutable scientific material such as Protocol ID, Edge Claim ID, analysis boundary, canonically ordered Comparative Measurement IDs, statistical-rule identity, and Comparative Performance algorithm version. Wall-clock randomness is forbidden, and a material mechanics change requires a new analysis algorithm version.

Comparative Performance reports findings, not scientific conclusions. It stores none of `statistically_significant`, `practically_significant`, `burden_of_proof_met`, `edge_supported`, or `market_edge_exists`; it neither creates nor modifies an Edge Claim or Market Edge. It reports observed mean Brier improvement beside the Protocol Practical Significance threshold, leaving interpretation to Research Review.

Over the exact same paired population it reports benchmark and challenger mean Log Loss and mean Log Loss improvement. Log Loss is a safeguard, not a second primary endpoint, and receives no independent inferential test unless prospectively required by the Protocol.

Each source mean uses extended nonnegative-real semantics over that complete
population: all-finite values produce the finite arithmetic mean, while any
`+Infinity` produces a `+Infinity` source mean. Infinite observations are never
discarded or diluted by a finite-only convention.

Mean paired Log Loss improvement uses every event-level paired improvement from
the same population. If any event has an absent improvement because both source
losses are `+Infinity`, the aggregate improvement is absent/not applicable; the
event is not dropped and absence is not zero. Otherwise finite and
signed-infinite improvements use deterministic extended-real arithmetic. If
both `+Infinity` and `-Infinity` occur in that aggregate, the mean is
mathematically indeterminate and therefore absent/not applicable rather than
ordered or coerced. Positive infinity favors the challenger; negative infinity
favors the benchmark.

Scientific serialization represents finite Decimal, `+Infinity`, `-Infinity`,
and absent/not-applicable paired improvement with explicit, type-safe,
deterministic, round-trip-reproducible tagged forms. These states are distinct
from arbitrary strings and from one another; `NaN` remains invalid. This is a
bounded Log Loss extension and does not authorize infinity for unrelated
Decimal fields.

Calibration is calculated separately for benchmark and challenger over that exact same paired Comparative Measurement population. Each uses the probability assigned to the canonical binary proposition and the realized Outcome in that same upstream-governed orientation; downstream analysis never silently flips orientation or substitutes unmatched or post hoc filtered observations.

The prospective `calibration-safeguard` rule version 2 fixes exact-decimal bins `[0.00, 0.10)`, `[0.10, 0.20)`, `[0.20, 0.30)`, `[0.30, 0.40)`, `[0.40, 0.50)`, `[0.50, 0.60)`, `[0.60, 0.70)`, `[0.70, 0.80)`, `[0.80, 0.90)`, and `[0.90, 1.00]`. Lower bounds are inclusive; upper bounds are exclusive except that the final bin includes `1.00`. Every valid probability belongs to exactly one bin, and both sources use identical boundaries. Adaptive or data-dependent bins are not version-2 semantics.

Each bin reports count, mean forecast probability, observed Outcome frequency, and calibration gap (`observed frequency - mean probability`). Empty bins remain present with count zero and absent/not-applicable statistics rather than fabricated zeros. Small nonempty bins remain visible without minimum-size exclusion, smoothing, shrinkage, or pseudocounts.

For a nonempty paired population (`N > 0`), each source also reports weighted absolute calibration error, `Σ_b (n_b / N) × |gap_b|`, over nonempty bins, where `N` is the total paired Calibration sample size. Exact Decimal arithmetic and canonical ordering make bin assignment, per-bin results, and the scalar summary deterministic and input-order independent.

When the complete paired population is empty (`N = 0`), all ten canonical bins remain represented with count zero; their mean forecast probabilities, observed Outcome frequencies, and gaps are absent/not applicable. Weighted absolute calibration error is likewise absent/not applicable, never numerical zero, because zero would falsely encode perfect observed Calibration rather than absence of Evidence.

Calibration is a descriptive safeguard only. Comparative Performance stores no Calibration pass/fail, independent hypothesis test or interval, or Burden-of-Proof conclusion. Research Review interprets it with the primary Brier result, paired uncertainty, Practical Significance, and Log Loss. Legacy PR10 Calibration remains implementation precedent, not scientific authority for PR14.

The under-specified rule version 1 remains immutable historical Protocol material and is not reinterpreted. Future Protocols requiring canonical PR14 Calibration use version 2 and identify the fixed exact-decimal boundaries and weighted absolute calibration error method prospectively. The bounded rule-parameter representation may be extended during PR14 implementation to carry an exact immutable Decimal collection while preserving existing PR13 serialization and contracts; Architecture does not encode the boundaries as textual scientific values merely to fit the current narrower parameter type.

Coverage is first-class scientific information within Comparative Performance, not another top-level scientific stage. It preserves exact opportunity, Snapshot, and Measurement identities sufficient to reproduce all counts. Snapshot/population coverage distinguishes eligible Research Capture Opportunities, authoritative Research Snapshots, benchmark and challenger capture successes and failures, and timing failures. Pair-specific analytical coverage distinguishes the eligible Snapshot population, benchmark and challenger availability, synchronized and unsynchronized pairs, resolved Outcomes, Protocol exclusions, and the Comparative Measurement population.

The denominator is the Research Capture Opportunity population proven eligible
from authoritative immutable eligibility contexts, deterministic Protocol rule
evaluation, and the analysis boundary, together with its authoritative Snapshot
population through that boundary—never merely caller-supplied opportunities or
successful Comparative Measurements. Future Evidence cannot enter an earlier
denominator. Missing benchmark or challenger captures, invalid or
out-of-tolerance captures, synchronization failures, cancellations, unresolved
Outcomes, and rule-derived Protocol exclusions remain visible with identities
and deterministic reasons. This prevents survivorship bias, including when an
eligible opportunity has zero successful provider observations.

PR14 implements Research Capture Opportunity, Research Snapshot, Comparative Measurement, and cumulative Comparative Performance only. It does not implement the canonical Comparative Performance Report, time-bounded surveillance analytics beyond existing PR13 contract support, Research Review conclusions, Current Scientific Applicability, Policy Recommendation, Policy Hypothesis, Forecast Policy, Governance, Workspace, Opportunity Analysis, Position Sizing, Execution, wagering, mutable scientific state, generic triggers, workflow management, scheduling, services, queues, databases, provider-network collection, or always-on surveillance infrastructure.

### Comparative Performance Reports

A Comparative Performance Report is the canonical immutable research artifact for one Research Protocol and analysis boundary. It communicates comparative findings, uncertainty, coverage, surveillance, and limitations while preserving sufficient input identities and rule versions for deterministic reproduction. PR15 owns this canonical report and alignment with Forecast Intelligence.

One Comparative Performance Report may support multiple claim-specific Research Reviews. PR13 represents that dependency through an immutable typed report reference; it does not implement the canonical report or bind new Reviews directly to the legacy `ForecastIntelligenceReport` symbol.

The implemented `ForecastIntelligenceReport` in `forecast_intelligence.py` is a provider-neutral precursor. It currently measures one Forecast Provider within an explicit domain and evaluation window and includes coverage, forecast quality, Calibration, segmentation, adequacy, excluded evaluations, deterministic identity, and provenance. Its symbol has not been renamed, and its provider-level absolute analysis does not yet implement the full Market-Benchmark-relative Comparative Performance Report required by the finalized Product and Methodology.

Architecture uses **Comparative Performance Report** as the canonical concept. Compatibility with the legacy symbol must be handled by a separately approved implementation change.

### Edge Claims and Market Edges

An Edge Claim is a durable or reproducibly derived research assertion under evaluation. It represents one Alternative Probability Source-versus-Market Benchmark hypothesis under one Research Protocol and Research Domain, and references its supporting empirical material sufficiently to reproduce its assessment.

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

The first completed Research Review for an Edge Claim with a Supported or Strongly Supported conclusion establishes its Market Edge. At most one historical Market Edge exists per Edge Claim, and it identifies that first qualifying Review. Later Reviews may change applicability to the same Market Edge but never mutate, replace, erase, or recreate it.

First-class Edge Claim and historical Market Edge contracts are implemented. Existing adequacy and proposal artifacts remain distinct and must not be mistaken for those scientific conclusions.

### Research Reviews and Drift Surveillance

A Research Review evaluates Comparative Performance Reports and Edge Claims against the governing Research Protocol and burden of proof. The durable `ResearchReview` artifact represents one completed, immutable review, assesses exactly one Edge Claim, and records exactly one completed scientific conclusion. It may explicitly cover multiple scheduled or valid material-event obligations relevant to that claim. It changes scientific conclusions discretely while leaving Evidence, Measurement, prior Research Reviews, Edge Claims, and historical Market Edges unchanged.

Drift Surveillance is deterministic, rerunnable analysis over cumulative and time-bounded Evidence. Each immutable artifact concerns exactly one Edge Claim under its governing Research Protocol and records one valid protocol-defined disposition: no material Drift, material Drift, or insufficient evidence to determine Drift. Only a disposition that the protocol defines as a qualifying material event creates a review obligation. It does not mutate an Edge Claim, prior Research Review, Market Edge, Forecast Policy, or Governance History, and it cannot restore Current Scientific Applicability by itself. Structurally invalid or incompatible input fails validation and cannot become a scientific disposition.

**Under Review** is a derived procedural condition, not a completed Research Review conclusion. At an explicit timezone-aware `as_of` boundary, deterministic replay considers all protocol-defined scheduled review boundaries due by `as_of` and all valid protocol-defined material-event artifacts effective by `as_of`. An obligation remains unresolved unless a qualifying completed Research Review explicitly covers it; a newer Research Review does not resolve an obligation merely because it occurred later. A scheduled boundary may include only a grace period prospectively defined by the Research Protocol. An implementation must not invent another grace period.

While any qualifying obligation remains unresolved, Current Scientific Applicability is suspended and operational reliance must fail closed, while the latest completed scientific conclusion and historical Market Edge remain intact. Scientific inapplicability neither creates nor revokes Governance authority and does not modify Governance History.

Current Scientific Applicability is a deterministic replayable Forecast Intelligence projection owned by PR16; it is not stored as mutable authoritative state. At an explicit timezone-aware `as_of` boundary, the projection identifies the latest completed conclusion for the Edge Claim, all scheduled obligations due by `as_of`, all valid material-event artifacts effective by `as_of`, and the obligations explicitly covered by completed Reviews. Unresolved obligations suspend applicability. Otherwise only Supported or Strongly Supported may support applicability, subject to every other protocol, Research Domain, Research Population, Evidence, analytical, and compatibility requirement. Resolving an obligation does not by itself restore applicability.

PR13 provides the immutable structures needed for this replay: claim and Market Edge relationships, scheduled review-boundary identities, authorized material-event references, effective and completion times, completed conclusions, explicit obligation coverage, deterministic identities, provenance, serialization, and fail-closed validation. Bounded typed supporting value objects may express these relationships; they are not additional top-level research contracts and must not become mutable workflow or current-state objects.

PR13 does not calculate or store authoritative Current Scientific Applicability, implement the canonical Comparative Performance Report, or introduce a generic `ReviewTrigger`, mutable review lifecycle, workflow manager, always-on surveillance service, Workspace/UI state, or additional durable current-applicability contract. Workspace or UI state cannot originate, resolve, or override Under Review. PR16 owns Current Scientific Applicability and Policy Recommendation without granting Governance or operational authority.

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
| Full Research Protocol contracts | Implemented with typed scientific rules and deterministic validation |
| Research Snapshot, Comparative Measurement, and cumulative Comparative Performance | Approved for PR14; not implemented |
| Canonical Comparative Performance Report | Approved for PR15; PR13 provides a typed forward reference only |
| Current Scientific Applicability and Policy Recommendation | Approved for PR16; not implemented |
| Edge Claim, Market Edge, Research Review, and Drift Surveillance contracts | Implemented |
| Policy Hypothesis aligned explicitly to supported Market Edges | Product-approved; existing symbol has older analytical-candidate semantics |
| Forecast Policy, deterministic execution, and Policy Forecast | Implemented |
| Event-sourced Product Owner Governance | Implemented |
| Forecast Intelligence Workspace | Approved, not implemented |
| Opportunity Analysis consuming governance-authorized Policy Forecast | Approved, not integrated; legacy direct-provider path remains active |
| Historical Policy Forecast evaluation and automated Shadow measurement | Not implemented |

These gaps must be resolved through separately approved implementation work. Architecture does not invent compatibility shims or silently redefine existing contracts.
