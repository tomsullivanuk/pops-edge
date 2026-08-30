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
ComparativePerformance              (cumulative Forecast Intelligence)
        +
TimeBoundedComparativePerformance
        ↓
ComparativeDriftAnalysis
        ↓
ComparativePerformanceReport        (PR15 Forecast Intelligence)
        ↓
ResearchReview / Drift Surveillance
```

PR14 implements this path only through cumulative `ComparativePerformance`;
PR15 owns the three downstream artifacts shown here.

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
- time-bounded Comparative Performance, Comparative Drift Analysis, and the
  canonical Comparative Performance Report;
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

### Standalone Probability Source analytical path (implemented in PR16B)

PR16A defines the governing architecture; PR16B implements its provider-neutral,
offline-replayable contract path:

```text
Protocol-governed Schedule Evidence
        ↓
ResearchCaptureOpportunity
        ↓
ResearchSnapshot
        +
MarketObservation
        ↓
MarketProbabilityDerivation
        +
Outcome Evidence
        ↓
ProbabilitySourceMeasurement
        ↓
ProbabilitySourcePerformance
        +
TimeBoundedProbabilitySourcePerformance
        ↓
ComparativePerformanceReport references
```

`MarketProbabilityDerivation` is narrow immutable supporting derived Analysis. It identifies the Market Observation; Market Series and proposition; Probability Source Reference and Protocol role; canonical event, outcome mapping, and fixed canonical outcome; valid contemporaneous bid and offer; direct or exact complement-derived origin, source side, and source price of each bound; positive displayed quantities; component chronology; exact midpoint and complement; representation and transformation rules; algorithm identity/version; limitations; deterministic identity; and provenance. It may exist before an outcome. It contains no outcome, score, population, aggregate performance, execution valuation, conclusion, Policy, or production authority. Market Evidence remains Market Evidence and never becomes Forecast Evidence.

`ProbabilitySourceMeasurement` is one immutable event-level Measurement for one Protocol, Research Snapshot, Probability Source Reference and Protocol role, compatible probability distribution, authoritative outcome, scoring algorithm, and effective/available time. It owns realized outcome, probability distribution, Brier Score, extended-real Log Loss, Calibration input, a derivation or direct-source reference, arithmetic inputs, limitations, deterministic identity, and provenance. A Market Benchmark Measurement consumes `MarketProbabilityDerivation`.

Compatible standalone and paired paths reuse the same `MarketProbabilityDerivation`. On overlapping events they agree exactly on source identity, probability distribution, realized outcome, Brier Score, and Log Loss. Aggregate equality is neither required nor expected because populations differ. This reconciliation does not rewrite historical PR9 Forecast Evaluations or persisted PR14/PR15 artifacts.

`ProbabilitySourceCoverage` owns complete failure-inclusive accounting without creating another scientific stage. It distinguishes the schedule-derived Coverage universe from its eligible standalone denominator. The former contains every relevant schedule-derived opportunity known and effective at the boundary and reconciles exactly into capture not yet due, protocol-ineligible, and the eligible standalone denominator. The latter contains only due, prospectively eligible opportunities and reconciles exactly into source capture missing, source capture invalid, outside capture tolerance, probability derivation unavailable or invalid, outcome unresolved or ineligible, and successfully measured. Categories are deterministic, disjoint, exhaustive for their parent population, correction-aware, and capable of valid empty populations. Coverage rates use the eligible standalone denominator; capture-not-yet-due and protocol-ineligible opportunities provide obligation accounting but never enter that rate denominator. Challenger state is nonmaterial to every standalone population level, and missing or invalid states remain visible rather than being retrospectively reconstructed or filtered away.

`ProbabilitySourcePerformance` is cumulative immutable Forecast Intelligence for exactly one Research Protocol, Research Domain, Probability Source Reference, Protocol source role, analysis boundary, measured performance population, and Coverage authority. Its performance metrics use only valid `ProbabilitySourceMeasurement` members of the measured performance population; failures remain in the eligible standalone Coverage denominator without contaminating metric calculation. Its identity commits materially to the relevant schemas and algorithms, Protocol, domain, source, role, boundary, canonically ordered Measurements, Coverage, Calibration rule, uncertainty rule, and material limitations.

`TimeBoundedProbabilitySourcePerformance` is an immutable sibling over the Protocol's approved rolling window using the same metrics, Coverage, and open-left/closed-right chronology. It does not mutate cumulative performance, become an optional field on it, or create standalone Drift or a review obligation.

Both performance authorities carry `SourcePerformanceUncertainty`, a deterministic one-sample bootstrap result for mean Brier Score. Seed material includes Protocol, domain, source, source role, cumulative or time-bounded scope, analysis boundary, applicable window, canonical Measurement IDs, statistical rule/version, confidence level, resample count, and algorithm version. Wall-clock randomness, input ordering, filesystem state, and ambient Decimal context are nonmaterial. Empty populations have absent point estimate and interval; singletons have a deterministic degenerate interval and explicit limitation; identical scores have a zero-width interval and explicit no-observed-variation limitation; otherwise the ordinary deterministic bootstrap applies. No universal minimum sample threshold or automatic evidence classification is introduced.

Corrections preserve append-only Evidence and correction lineage. Deterministic replay selects authoritative Snapshot and outcome versions at explicit boundaries and produces new immutable Measurements after corrections while preserving earlier performance artifacts. Ambiguous, branched, incomplete, or conflicting lineage fails closed; incidental ordering is never a substantive tie-breaker.

### PR17 Kalshi MLB study architecture (documentation authority)

PR17A defines two Kalshi-only standalone Protocols in the 2026 MLB regular-
season game-winner domain. The retrospective candle Protocol and prospective
order-book Protocol share no Protocol, Coverage, Measurement, performance,
uncertainty, or report identity. Each event contributes at most one
authoritative home-team YES observation. Away-team contracts remain diagnostic
Evidence and cannot affect derivation or membership. MLB Stats API owns schedule,
state, and Outcome authority; Kalshi timing and settlement only corroborate it.

Both are instances of the new sibling
`StandaloneProbabilitySourceProtocol`, not the implemented comparative
`ResearchProtocol` or `ResearchProtocolV2`. Existing comparative schemas,
serialization, identity, registries, graph validation, and artifacts remain
unchanged. A standalone Protocol materially owns one source and role, question,
domain, proposition/outcome mapping, population and Coverage rules, capture and
failure rules, typed probability representation, schedule/Outcome authority,
correction replay, scoring, Calibration, uncertainty, cumulative/time-bounded
analysis and report boundaries, limitations, identity, and provenance. It owns
no challenger, pair, Claim Set, Edge Claim, comparative significance, Burden of
Proof, Drift, or Research Review obligation. PR17B1 implements the offline
sibling contract and deterministic replay; PR17B2 implements later operations.

The dependency remains one-way:

```text
existing foundational contracts
        ↓
forecast_standalone_performance.py
        ↓
forecast_standalone_research.py
        ↓
forecast_standalone_operations.py
        ↓
operate_forecast_standalone_research.py + thin launchd wrappers
```

The PR17B2 layer is implemented but inactive. Each operating namespace owns
separate content-addressed raw and normalized stores, immutable per-entry
manifests, an OS advisory mutation lock, a rebuildable SQLite discovery index,
and a create-only digest-verified secondary copy. Primary manifest publication
is authoritative; index and secondary failures remain visible Operations state
without rewriting primary authority. Status, preflight, and inspection share one
typed deterministic diagnostic representation and make no scientific claim.

Provider calls occur only after acquiring the namespace lock. Prospective slots
invoke the PR17B1 timing function and allow one request with redirects and hidden
retries disabled. A fresh trusted request-start timestamp fixes the authorized
slot and becomes the typed attempt's invocation time. The trusted completion
timestamp becomes its effective time and the manifest's completed acquisition
time; crossing slot boundaries never relabels the call or authorizes another
request. Every actual call receives one immutable typed disposition in its
request-start slot. An observation collected outside the inclusive request-start
to request-completion interval is captured-invalid: its permitted raw response
and call remain visible, but it cannot enter valid Market Evidence. Supporting acquisition may use only configured bounded
deterministic retries. Operational configuration controls paths, endpoints,
timeouts, locks, logging, and scheduling—not Protocol rules or scientific identity.

Malformed, incomplete, unknown, or contract-invalid provider-supplied PR17
payloads cross a narrow provider-data exception boundary into captured-invalid
attempts with sanitized deterministic diagnostics. Expected provider-data
failures cannot create Market Evidence or erase the executed call; unexpected
internal, archive-integrity, and system failures are not relabeled as provider
invalidity.
Before scientific deserialization, the adapter recursively validates every
shared tagged-serialization marker (`__type__`, `__enum__`, `__date__`,
`__datetime__`, `__decimal__`, and `__non_finite_decimal__`), including exact
scalar-marker shape, value type, nesting depth, and conflicting/duplicate keys.
The parsed envelope is then checked structurally against the actual annotated
`MarketObservation` dataclass tree: complete canonical fields, no unknown
fields, exact nested contract and enum tags, exact primitive types, encoded
tuples, optionals, aware datetimes, dates, and Decimals. Canonical constructors
and PR17B1 replay remain the sole owners of scientific semantics.

The persistence adapter stores exact version-dispatched PR17B1 serializations in
an operational envelope. Replay reconstructs those existing contract types and
invokes their resolvers and graph validator; an operational string never stands
in for typed authority. Prospective discovery is a locked archive query driven
by a trusted execution clock. The scheduled command accepts configuration only,
and its wrapper contains no scientific identity or timestamp.

Archive reconciliation treats immutable manifests as the sole reference set.
Missing or corrupt referenced objects fail closed. Unreferenced raw/normalized
objects left by interrupted manifest-last publication are visible non-authority:
they are excluded from replay, indexes, and secondary synchronization and are
never automatically moved or deleted. Deterministic failpoints cover every
publication boundary and identical retry completion.

The V3 module owns closed tagged designs, the shared activation-boundary
identity, complete historical manifest correction replay, typed prospective
attempts and terminal Snapshots, standalone-specific legacy derivation reuse,
V3 analytics and reports, explicit registry dispatch, and upstream-first graph
validation. Its canonical bundle and inspector are synthetic/offline only.

Every V3 Measurement resolves one exact `ResearchCaptureOpportunity` and its
Schedule Observation, eligibility, derivation, and Outcome authority. Coverage
derives the one-to-one measured mapping. Cumulative and `(start, end]` bounded
performance use separate matching Coverage. Uncertainty uses the governed
deterministic one-sample bootstrap and commits scope, window, population, rule,
and algorithm material to its seed.

Historical pagination is an ordered chain of typed page entries binding cursor,
position, completion, archive reference/digest, retrieval time, candle IDs,
validation, and limitations. Generic upstream-first graph replay accepts either
study independently, prospective pre-report state, or both studies. Exactly two
report roots is a canonical-fixture assertion, not a universal requirement.

The immutable activation boundary partitions authoritative scheduled starts:

```text
2026 regular-season start
        ↓ retrospective happy-path Protocol
scheduled_start_at < activation_at
        │
        ├── activation_at = midnight at a pre-approved America/New_York date
        │
scheduled_start_at >= activation_at
        ↓ prospective all-opportunity Protocol
final 2026 regular-season games
```

PR17A does not set `activation_at`. After PR17B2 dry-run validation, the Product
Owner approves a future Eastern calendar date before it begins. The boundary is
timezone-aware, contiguous, non-overlapping, has no mid-date split, and cannot
be changed according to prices, outcomes, Coverage, or performance. No
retrospective performance is calculated before approval, and dry-run material
cannot become Evidence.

The retrospective path uses a new immutable
`HistoricalMarketCandleObservation`, which preserves provider and API tier/
endpoint; series and native contract; event and home-team proposition mapping;
interval and end-period semantics; complete returned YES bid, YES ask, and
transaction-price OHLC; volume/open interest when present; raw digest/archive
reference; distinct retrieval and candle timestamps; schema/identity versions;
validation, limitations, identity, and provenance. Retrieval after Outcome is
expected and never represented as contemporaneous capture; a historical
provider timestamp does not change that acquisition classification. The
standalone Protocol's population, selection, representation, scoring, Coverage,
and report rules are fixed before the archive query and any calculation or
interpretation. That precommitment prevents result-directed choice but does not
make acquisition prospective. It is not a
`MarketObservation` and cannot satisfy positive-depth
`MarketProbabilityDerivation`.

`HistoricalCandleProbabilityDerivation` derives an exact-decimal midpoint from the latest real
one-minute candle satisfying `T-6h-5m < end_period_ts <= T-6h` and containing
both closing home-team YES bid and ask. Historical and live candle schemas may
be normalized without changing decimal meaning, but candle closes are
same-candle aggregates, not documented simultaneous quotes. Synthetic candles,
late observations, fallbacks, null repair, away-side substitution, and claims of
positive depth or executability from volume/open interest fail closed.
Retrospective Coverage separately reconciles schedule universe, rule-derived
happy-path exclusion, Kalshi offering, and home-team measurement, with offered-
over-eligible and measurable-over-offered rates and valid empty populations.

The derivation references its standalone Protocol, candle Evidence,
authoritative Schedule Evidence, source/series/contract/event/proposition,
target and versioned window rule, complete candidate authority, selected end and
distance, exact bounds, midpoint/complement, transformations, algorithms,
limitations, identity, and provenance. It validates exact home-team mapping,
MLB/Kalshi minute corroboration, real one-minute semantics, latest-candidate
selection, and exact arithmetic and fails closed on ambiguity or fallback. Raw
content remains Evidence; selection is supporting Analysis.

This retrospective Evidence cannot repair or enter prospective Evidence, feed
paired Comparative Performance under the current Methodology, or establish an
Edge Claim, Market Edge, applicability, Policy, Governance, wagering,
Opportunity Analysis, or production authority. Reports disclose archive
availability, survivorship, provider revision, timestamp, schedule-history,
aggregation, and non-simultaneity limitations where applicable.

The prospective path reuses PR16's positive-depth, two-sided home-team YES
order-book midpoint. Exactly five slots cover `target_at` through the inclusive
`target_at + 5 minutes` endpoint: slots 0–3 are the half-open one-minute
intervals beginning at minutes 0–3, and slot 4 is
`[target_at + 4m, target_at + 5m]`. The first current-slot invocation may execute
at most one provider acquisition only if no earlier slot succeeded. Equality at
the upper endpoint belongs to slot 4; later timestamps are prohibited. An
invocation uses actual acquisition time and exact target distance, never
backdates a current quote, executes a missed earlier slot, or performs catch-up
acquisitions. Duplicate same-slot invocation is idempotent. Elapsed unresolved
earlier slots receive deterministic non-acquisition `missed` dispositions,
never fabricated attempts; the earliest successful slot is selected and later
slots are skipped visibly. Every slot disposition is persisted. After the
inclusive endpoint, unresolved slots become missed, no quote is acquired, and
one idempotent terminal missed-window disposition is appended if none succeeded.
No late or historical observation repairs it. Price and Outcome never influence
slot selection. The schedule-derived population
keeps ordinary games, explicitly numbered doubleheaders, postponements,
reschedules as new opportunities, suspensions pending Outcome, cancellations,
ambiguous mappings, and acquisition or persistence failures visible without
later-fact deletion.

#### Evidence archive and acquisition boundary

Raw Evidence remains outside Git in a local content-addressed, append-only
filesystem archive. Paths use stable content identity or another deterministic
non-semantic layout. Scientific identity excludes absolute path, hostname, user,
filesystem timestamp, scheduler identity, and incidental ordering. A versioned
append-only manifest records capture opportunity and attempt; sanitized request
and endpoint; retrieval and effective timestamps; HTTP disposition and content
type; schema version; raw digest and archive reference; validation result;
software and Protocol versions; and correction or supersession lineage.

Persistence is atomic. Duplicate invocation is idempotent; conflicting content
under one semantic identity fails closed; interrupted writes never appear as
valid Evidence. A rebuildable derived query index is non-authoritative. One
configured secondary copy preserves completed immutable objects and manifest
material and is digest-verified. Primary persistence determines capture success;
backup health and lag are Operations diagnostics and never change Evidence
identity or validity. Evidence, reports, archives, indexes, and secrets stay
outside version control.

One idempotent application CLI owns opportunity discovery, due-attempt
calculation, retry rules, provider acquisition, atomic persistence, validation,
failure dispositions, daily Outcome reconciliation, backup invocation/status,
and diagnostics. It uses an injected clock and explicit `as_of` boundaries. A
thin macOS `launchd` wrapper invokes it periodically and owns no scientific or
analytical semantics. Sleeping, offline, or late machines produce visible
missed opportunities; PR17 does not automate wake or power management. A future
status/preflight surface may report upcoming windows, clock/timezone state,
scheduler health, archive writability, backup freshness, and recent failures,
but remains Operations rather than Evidence.

An idempotent daily process appends MLB schedule and Outcome observations on
state change. Corrections preserve prior observations and deterministic lineage;
every report replays authoritative Outcome state at its explicit boundary.

The filesystem and `launchd` are replaceable implementation seams, not Product
boundaries. A future cloud scheduler or object store may replace them without
changing Protocol, Evidence, identity, replay, Measurement, or reporting
semantics. PR17A selects no cloud provider, service, database, deployment model,
or migration plan and introduces no speculative distributed-system abstraction.

Retrospective and prospective reports remain separate through cumulative and
time-bounded performance and uncertainty. Neither repairs or reinterprets the
other. A non-authoritative side-by-side Product summary cannot pool observations,
create a combined metric, or become Measurement authority, and observed
differences cannot be attributed solely to capture method.

#### Versioned Measurement and standalone report paths

Existing PR16B `ProbabilitySourceMeasurement` v1/v2 and all associated
serialization, identities, registries, and graph behavior remain unchanged.
PR17B1 implements explicit `ProbabilitySourceMeasurementV3` dispatch from exactly
one typed derivation authorized by its standalone Protocol: retrospective uses
`HistoricalCandleProbabilityDerivation`; prospective uses existing
`MarketProbabilityDerivation`. Missing, multiple, unknown, foreign, wrong-kind,
or mixed-within-Protocol derivations fail closed. V3 preserves the existing
probability distribution, Outcome, Brier, extended-real Log Loss, and
Calibration-input meanings plus complete typed lineage.

Where existing Coverage, cumulative/time-bounded performance, uncertainty,
reference, registry, replay, or graph contracts cannot consume V3 without
reinterpretation, PR17B1 provides explicit versioned successors. Dispatch is by
version and type, never optional fields. Historical identities remain stable.

Coverage replay starts from complete Schedule histories, derives every expected
opportunity and eligibility result, and independently assigns each failure or
success category; stored reconciliation is an output rather than constructor
authority. Protocol identity validates exact scoring, fixed-bin Calibration and
WACE, bootstrap, and bounded-report-window specifications. Each historical
candle resolves to exactly one retrieval page's position, raw-response archive
reference/digest, and chronology. The V3 entry point handles successor records
locally and explicitly delegates approved legacy graph records to their
canonical deserializers without changing legacy registries.

Schedule-universe projection operates per genuine scheduled-state Observation,
so a reschedule across activation preserves one opportunity on each applicable
Protocol side while status-only changes add none. A V3 immutable provider-neutral
event-classification Evidence value supplies season, phase, game type,
ordinary/doubleheader identity, participant mapping, validation, chronology, and
correction lineage to eligibility replay. Prospective opportunity classification
first honors the authoritative earliest valid capture; only when none exists does
the explicit acquired-invalid, provider-call-failure, pure-no-call precedence
apply. Derivation, Outcome, and Measurement selection filters by effective
boundary, rejects ambiguity, and never uses registry order as authority.

```text
Retrospective:
StandaloneProbabilitySourceProtocol
        +
HistoricalMarketCandleObservation
        ↓
HistoricalCandleProbabilityDerivation
        +
Authoritative Outcome Evidence
        ↓
ProbabilitySourceMeasurementV3
        ↓
ProbabilitySourcePerformance successor/reuse
        ↓
ProbabilitySourcePerformanceReport

Prospective:
StandaloneProbabilitySourceProtocol
        +
MarketObservation
        ↓
MarketProbabilityDerivation
        +
Authoritative Outcome Evidence
        ↓
ProbabilitySourceMeasurementV3
        ↓
ProbabilitySourcePerformance successor/reuse
        ↓
ProbabilitySourcePerformanceReport
```

`ProbabilitySourcePerformanceReport` is immutable, deterministic,
content-addressed, and governed by exactly one standalone Protocol, source,
role, domain, and boundary. It references rather than recomputes exactly one
compatible cumulative performance, one applicable compatible time-bounded
performance, their authoritative Coverage, full three-level/failure
reconciliation, uncertainty, limitations, and provenance. Protocol,
representation, rules, boundary, and window compatibility are exact. Empty
populations remain reportable; unknown, duplicate, foreign, conflicting, or
multiple compatible-looking authorities fail closed. Corrections produce new
report identities.

It has no Claim Set, Edge Claim, challenger, pair, Comparative Performance or
Drift, Burden-of-Proof disposition, Review conclusion, Market Edge,
applicability, Policy, Governance, or production authority. Existing
`ComparativePerformanceReport` and its PR15/PR16B standalone benchmark
references are unchanged and are not reinterpreted. PR17C and PR17D each own a
separate `ProbabilitySourcePerformanceReport`.

## Forecast Intelligence

Forecast Intelligence is the umbrella architectural capability that transforms immutable Evidence and Measurement into reproducible knowledge about the standalone and comparative performance of Probability Sources.

**Consumes:** Research Protocols, immutable Evidence, Forecast Evaluations and other Measurement, explicit research populations and analysis boundaries, and versioned analytical rules.

**Produces:** standalone Probability Source Performance, Comparative Performance, Comparative Performance Reports, Edge Claims and their assessments, Research Reviews, Drift findings, Market Edges, Policy Recommendations, and inputs to Policy Hypotheses.

**Owns:** provider-neutral empirical analysis, reproducibility, research provenance, and the scientific status of Market Edges.

**Does not own:** Evidence, Product Owner decisions, Forecast Policy lifecycle, production authority, Opportunity Analysis, or Execution.

### Research Protocol families

`ComparativeResearchProtocol` and `StandaloneProbabilitySourceProtocol` are
explicit sibling authorities. The implemented `ResearchProtocol` and
`ResearchProtocolV2` remain the comparative contracts: they fix benchmark and
challengers, synchronization, comparative rules, Burden of Proof, surveillance,
Review, Claim Set, and Edge Claim authority. One comparative Protocol may
investigate multiple Alternative Probability Sources, and each distinct
benchmark-versus-challenger hypothesis has its own Edge Claim.

The standalone sibling fixes exactly one source investigation and the
descriptive standalone authority listed above. It is never constructed by
emptying or wrapping a comparative contract and gains no comparative semantics
merely because its source serves as a benchmark elsewhere.

The Methodology governs protocol meaning. Architecture must preserve protocol identity, version, material inputs, and provenance without embedding protocol rules into provider adapters.

First-class comparative Research Protocol contracts are implemented. The
standalone sibling is PR17B1 implementation scope. Existing evaluation
windows, eligibility policies, segmentation versions, and adequacy rules remain
narrower precursors and must not be presented as either family or as canonical
Comparative Performance implementation.

### Protocol Claim Sets

`ProtocolClaimSet` is an immutable, deterministic, content-addressed,
versioned, tagged-serializable supporting Identity and research-contract
artifact. It establishes the complete authoritative Edge Claim membership of
one immutable `ResearchProtocol` as of one scientific effective time. It is not
a new scientific stage: `ResearchProtocol` remains prospective scientific
protocol authority, `EdgeClaim` remains immutable scientific claim identity,
and `ResearchReview` remains scientific conclusion authority.

The bounded contract contains material equivalent to `schema_version`,
`identity_algorithm_version`, `protocol_claim_set_id`, `protocol_id`, a
timezone-aware `effective_at`, canonically Edge-Claim-ID-ordered
`edge_claim_ids`, and an optional `predecessor_protocol_claim_set_id`, plus
bounded provenance under the research-contract convention. Its semantic ID
prefix is `protocol-claim-set:`. Protocol, scientific time, membership, and
predecessor lineage are identity-material; generation time, runtime metadata,
and audit provenance are nonmaterial. `effective_at` is specifically the
timezone-aware instant the immutable Claim Set entered the accepted scientific
record and became available to downstream scientific replay. It is
identity-material and replay-authoritative; generation or creation time,
serialization, filesystem, process, job, scheduler, approval-workflow runtime,
and audit-record timestamps do not determine it unless that instant
independently is the scientific effective time. Membership is nonempty and
unique; duplicates fail before normalization. Referenced claims must exist,
retain valid immutable identity and Protocol compatibility, and share the Claim
Set's Protocol. Unknown, foreign-Protocol, and same-ID/different-content claims
fail closed at graph validation.

Claim membership is explicit scientific history, not the Cartesian product of
the Protocol's Alternative Probability Sources and Research Domains and not a
projection from report-selected analytical children. A Protocol may exist
before claim admission, but its first Claim Set becomes effective only when at
least one existing valid Edge Claim is admitted. `ProtocolClaimSet` never
creates a claim or introduces a mutable catalog, current pointer, database,
workflow, scheduler, or approval service.

Lineage is immutable, append-only, and monotonic for v1.1.0. The first Claim Set
has no predecessor. Every distinct successor references the same Protocol's
immediately preceding Claim Set, has a strictly later `effective_at`, retains
all predecessor claim IDs, and adds at least one claim. Identical deterministic
copies have one identity rather than forming a successor. A Research Review
conclusion—including weakening, no-longer-supported, or rejected—does not remove
or mutate membership. Claim retirement, removal, inactive/current state, and
`is_active` or `is_current` semantics require a later architecture decision.

At analysis boundary `T`, deterministic replay uses only Claim Sets with
`effective_at <= T` and must resolve exactly one authoritative terminal set for
the Protocol in one connected linear lineage. Unknown or cross-Protocol
predecessors, multiple initial sets, disconnected lineage, cycles, branches,
and competing or ambiguous terminal sets fail closed. Generation timestamp,
lexical ID, caller, filesystem, and serialization ordering are not tie-breakers.
A later Claim Set cannot rewrite the membership of an earlier report.

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

PR14 implements Research Capture Opportunity, Research Snapshot, Comparative Measurement, and cumulative Comparative Performance only. PR15 begins downstream of that one canonical cumulative authority and must not recalculate its population, add optional surveillance windows to it, reinterpret Coverage, Brier, Log Loss, Calibration, or paired uncertainty, or create another cumulative authority.

### Time-Bounded Comparative Performance

`TimeBoundedComparativePerformance` is an immutable, deterministic,
content-addressed supporting Forecast Intelligence artifact representing one
Edge Claim's comparative empirical performance over one Protocol-defined
surveillance window at one analysis boundary. It is a sibling of cumulative
`ComparativePerformance`, not its subtype, mode, or replacement. Its exact
cardinality is one Protocol, Edge Claim, Research Domain, Market Benchmark,
challenger, surveillance-window rule, resolved surveillance window, analysis
boundary, and bounded scientific population.

For rolling-days version 2, `window_end_at == analysis_boundary`,
`window_start_at == analysis_boundary - timedelta(days=N)`, and membership is
the timezone-aware interval `(window_start_at, window_end_at]`. Membership uses
the authoritative scheduled event time of the Protocol-eligible Research
Capture Opportunity after schedule/rescheduling rules, never Measurement
effective time. Evidence must still be effective by the analysis boundary, so
delayed Evidence neither moves an old event into the current window nor leaks
into the historical baseline.

Bounded Coverage starts from eligible opportunities scheduled within the
interval and preserves missing, invalid, outside-tolerance, synchronization-
failed, unresolved-Outcome, Protocol-excluded, and valid Measurement states. A
valid empty population produces an artifact with truthful Coverage; invalid or
unreproducible structure does not. The artifact reuses PR14 Brier, paired
uncertainty, Practical Significance reporting, extended-real Log Loss,
Calibration, and Coverage semantics and owns no Drift disposition, conclusion,
Market Edge, applicability, Policy, Governance, or production authority.

For v1.1.0, `surveillance_window_rules` remains a tuple but must contain exactly
one active rule; zero or multiple rules fail closed. Historical rolling-days
version 1 identities remain under-specified and unchanged. Prospective version
2 uses bounded typed parameters and static registration for positive duration,
scheduled-event membership, open-start/closed-end bounds, and cumulative replay
through the window start. No dynamic rule/plugin mechanism is introduced.

### Comparative Drift Analysis

`ComparativeDriftAnalysis` is immutable, deterministic, content-addressed
supporting Forecast Intelligence comparing one claim's historical cumulative
`ComparativePerformance` with current `TimeBoundedComparativePerformance`. It
has exactly one Protocol, claim, domain, benchmark, challenger, surveillance
rule, Drift-classification rule, historical result, current result, and
analysis boundary. The inputs agree on their shared scientific identities and:

```text
historical.analysis_boundary == current.window_start_at
current.window_end_at == current.analysis_boundary
                      == drift_analysis.analysis_boundary
```

Historical performance is replayed at `window_start_at` from only artifacts
scientifically effective by then. It is never today's cumulative population
filtered by event date, a previous report, or the Market-Edge-establishing
report; a report need not have existed at that boundary.

Measured deterioration is historical minus current mean Brier improvement, so
positive is deterioration. Uncertainty uses independent deterministic
with-replacement resampling of complete Measurements from the two populations,
not subtraction of their intervals. The Protocol statistical rule supplies
confidence level and resamples; a distinct Drift algorithm version governs the
mechanics. Seed material includes all immutable artifact/rule identities,
boundary, canonical Measurement IDs, algorithm version, replicate/draw index,
and distinguishable historical/current population role. Wall-clock randomness
and component-wise resampling are forbidden.

With threshold `T` and interval `[L,U]`, unestimable deterioration is
`insufficient-evidence-to-determine-drift`; `L >= T` is `material-drift`; `U <
T` is `no-material-drift`; all other cases are insufficient Evidence. Thus
`L == T` is material while `U == T` with `L < T` is insufficient. Valid empty
or otherwise unestimable populations may produce a valid insufficient-Evidence
analysis with absent statistic and interval. Invalid/incompatible structure
produces none. There is no hidden minimum sample size. Log Loss, Calibration,
and Coverage remain non-classifying safeguards.

Historical brier-deterioration version 1 identities remain under-specified and
unchanged. Prospective version 2 statically governs the threshold, sign,
two-population bootstrap, interval comparison, and exact three-way mapping with
bounded typed parameters and no composite score, veto, hidden test/settings, or
arbitrary executable behavior.

### Comparative Performance Reports

`ComparativePerformanceReport` is the canonical immutable, deterministic,
content-addressed scientific communication artifact for one Research Protocol
at one analysis boundary. It assembles authoritative Forecast Intelligence
artifacts and does not recompute or authoritatively copy their populations,
Brier values, uncertainty, Log Loss, Calibration, WACE, Coverage, or Drift
deterioration.

The report references exactly one `ProtocolClaimSet`: the uniquely authoritative
terminal Claim Set for its Protocol at its analysis boundary. Its
`protocol_claim_set_id` is material report identity. The Claim Set must share
the report Protocol, must be effective no later than the report boundary, and
its Edge Claim IDs must exactly equal the report's claim-finding IDs: no older
nonterminal set, selected subset, duplicate, unknown, additional, or foreign
claim. The report therefore cannot establish its own completeness from its
selected analytical package.

Every canonical report boundary also requires exactly one compatible broad-domain cumulative `ProbabilitySourcePerformance` and one `TimeBoundedProbabilitySourcePerformance` for the Probability Source in the Protocol's Market Benchmark role. The report references their identities and does not copy authoritative standalone metrics. Its presentation identifies which counts describe the schedule-derived Coverage universe, eligible standalone denominator, and measured performance population; Coverage rates use the eligible denominator, while performance metrics use the measured population. This Protocol-level standalone completeness is independent of `ProtocolClaimSet`, which continues to govern Edge Claim membership. Challenger state cannot change any standalone population level.

Every claim requires exactly one compatible cumulative
`ComparativePerformance`, one `TimeBoundedComparativePerformance`, and one
`ComparativeDriftAnalysis` at the report boundary using the Protocol's single
active surveillance rule. All agree on Protocol, claim, domain, benchmark,
challenger, and boundary. Broad and segmented claims and multiple challengers
may coexist, but broad results are never reconstructed from segments.

The bounded report composition is Protocol ID, analysis boundary, claim
findings, report-level limitations, and provenance. Each finding is Edge Claim
ID, cumulative Comparative Performance ID, and a surveillance finding made of
surveillance-rule ID, bounded-performance ID, and Drift-analysis ID. Supporting
display values are projections, not additional scientific stages or authority.

The report keeps four version concepts distinct:

- `schema_version` versions its structure and serialization;
- `identity_algorithm_version` versions canonical scientific identity;
- `contract_version` versions the scientific semantics of the report contract;
  and
- `report_algorithm_version` versions deterministic assembly and validation.

An initial implementation may use `"1"` for each, but changing one has only its
stated meaning. Material report identity comprises those four versions,
`protocol_id`, `protocol_claim_set_id`, `analysis_boundary`, canonically ordered claim findings,
material report-level limitations, and the canonical material/input digest.
Each claim finding recursively commits the report to its Edge Claim,
cumulative Comparative Performance, surveillance-window rule,
Time-Bounded Comparative Performance, and Comparative Drift Analysis IDs.
Measurement and Coverage IDs and analytical values such as Brier, Log Loss,
Calibration, WACE, and Drift deterioration are not redundantly copied into
top-level identity because the child artifact IDs already commit to that
scientific lineage.

Claim findings are ordered canonically by Edge Claim ID. Caller order is
nonmaterial, duplicate findings fail closed, and the single active v1.1.0
surveillance rule leaves no multiple-window ordering ambiguity. For one
Protocol, analysis boundary, report contract/algorithm version, and complete
compatible authoritative analytical graph, exactly one deterministic report
identity exists. Repeated generation from identical scientific inputs yields
the same report ID. A material change to boundary, claim scope, a child
artifact, contract or report algorithm version, or material limitation produces
a different identity. Evidence effective after an earlier boundary never
rewrites that earlier report.

Producer identity/version, generation timestamp, audit notes, invocation
context, and similar provenance are nonmaterial where retained. In particular,
wall-clock `generated_at`, scheduled or material-Drift trigger, manual
invocation, job/process/scheduler ID, workflow state, and generation reason do
not alter scientific identity. PR15 introduces no scientific `ReportTrigger`,
`ReportPurpose`, or `ReportReason` contract.

The canonical report deterministically projects the unchanged PR13
`ComparativePerformanceReportReference`; the reference never invents an
independent report identity. The projection satisfies exactly:

```text
reference.report_id            == report.comparative_performance_report_id
reference.contract_version     == report.contract_version
reference.protocol_id          == report.protocol_id
reference.analysis_boundary    == report.analysis_boundary
reference.edge_claim_ids       == canonical report claim Edge Claim IDs
```

Reference `schema_version` and `identity_algorithm_version` remain compatible
with the report under the existing PR13 reference contract. Reference claim IDs
are the report's complete canonical coverage with none omitted, added, or
alternatively ordered. The reference shape does not add
`protocol_claim_set_id`: `reference.report_id` identifies the canonical report
whose material identity commits to that Claim Set, while the reference claim
IDs equal both report coverage and Claim Set membership. The PR13 reference has
no independent authority to select a Claim Set or claim subset.

A canonical report may exist at any valid explicit analysis boundary when its
immutable scientific inputs exist. Scheduled, material-Drift, regeneration, and
intermediate-inspection contexts do not change the artifact. For a scheduled
boundary with `required_analysis_boundary_at == T`, the normal scheduled report
uses `analysis_boundary == T`; Review grace affects timeliness only and never
moves that scientific cutoff. Existing PR13 coverage remains broader: a later
compatible report may cover an overdue scheduled obligation when
`T <= report.analysis_boundary <= review.completed_at`.

A report may reveal material Drift, after which the corresponding PR13 Drift
artifact becomes effective and a compatible unscheduled Research Review may use
the same report; no second report is required. The Review may instead use a
later compatible report under existing PR13 chronology. One claim-specific
Review may explicitly cover both a scheduled-boundary reference and a Drift-
surveillance reference when both are compatible, chronology is valid, the
report covers the claim, and `ReviewObligationCoverage` contains both. Mere
chronology resolves neither obligation.

Downstream use never mutates a report. It stores no `reviewed`,
`used_for_scheduled_review`, `used_for_drift_review`, `review_ids`, `drift_ids`,
or `is_current` state; Reviews and Drift artifacts reference the report. These
artifact semantics introduce no scheduler, daemon, queue, service, workflow
engine, or always-on surveillance infrastructure.

The report creates no Research Review conclusion, Drift Surveillance contract,
Market Edge status, Current Scientific Applicability, Policy Recommendation,
Policy Hypothesis, Governance, Workspace authority, Opportunity Analysis, or
production authority. Research Review remains the scientific conclusion
boundary. PR13 `DriftSurveillance` remains the immutable claim-specific Drift
artifact that records the compatible report reference and disposition; the
PR15 analytical result supplies its scientific basis without absorbing that
contract layer.

One Comparative Performance Report may support multiple claim-specific Research Reviews. PR13 represents that dependency through an immutable typed report reference; it does not implement the canonical report or bind new Reviews directly to the legacy `ForecastIntelligenceReport` symbol.

The implemented `ForecastIntelligenceReport` in `forecast_intelligence.py` remains a provider-neutral legacy precursor. It measures one Forecast Provider within an explicit domain and evaluation window and includes coverage, forecast quality, Calibration, segmentation, adequacy, excluded evaluations, deterministic identity, and provenance. Its symbol has not been renamed, and its provider-level absolute analysis remains distinct from the PR15 Market-Benchmark-relative `ComparativePerformanceReport`.

Architecture uses **Comparative Performance Report** as the canonical concept. PR15 implements it as an independent Forecast Intelligence contract with no structural dependency on the legacy symbol.

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

Drift Surveillance is the immutable claim-specific Drift artifact in the PR13
research-contract layer. It references compatible PR15 scientific reporting and
records one valid protocol-defined disposition: no material Drift, material
Drift, or insufficient evidence to determine Drift. Only a disposition that the
protocol defines as a qualifying material event creates a review obligation. It
does not mutate an Edge Claim, prior Research Review, Market Edge, Forecast
Policy, or Governance History, and it cannot restore Current Scientific
Applicability by itself. Structurally invalid or incompatible input fails
validation and cannot become a scientific disposition.

A PR13 `DriftSurveillance` backed by a canonical report validates against
exactly one corresponding report `ComparativeDriftAnalysis`. Its report
reference equals the report's deterministic PR13 projection; Protocol IDs agree
across all three artifacts; the Drift Edge Claim equals the analysis claim and
is covered by the report; Drift rule ID and version equal the corresponding
analysis rule ID and version; and the recorded disposition equals the analysis
disposition. No competing Drift assertion is permitted.

`DriftSurveillance.effective_at` remains distinct from report and Drift-analysis
`analysis_boundary` and is not part of PR15 analytical identity. Existing PR13
chronology is preserved: their shared scientific boundary must not be later
than `effective_at`, but equality is not required. PR15 does not change the PR13
contract shape. The one-window invariant makes this mapping unambiguous for
v1.1.0; any future multi-window identity extension requires a later contract
version.

**Under Review** is a derived procedural condition, not a completed Research Review conclusion. At an explicit timezone-aware `as_of` boundary, claim-specific deterministic replay considers only Protocol-defined scheduled review boundaries due by `as_of` at which the Edge Claim was already a member of the authoritative `ProtocolClaimSet`, plus all valid Protocol-defined material-event artifacts effective by `as_of`. Claim Set replay at a scheduled boundary includes only sets with `effective_at <=` that boundary. A scheduled boundary earlier than claim admission creates no obligation for that claim and never becomes retrospectively overdue; before the first Claim Set it creates no claim-specific obligation or empty Protocol-level Review/report. The first scheduled boundary that may apply is the first otherwise-valid boundary at which the claim is already a member, and admission between boundaries creates no special immediate Review.

An applicable obligation remains unresolved unless a qualifying completed Research Review explicitly covers it; a newer Research Review does not resolve an obligation merely because it occurred later. A scheduled boundary may include only a grace period prospectively defined by the Research Protocol. Grace governs timeliness after applicability; it cannot move admission backward, change Claim Set `effective_at`, make an earlier boundary applicable, move the Evidence cutoff, or create a retrospective obligation. `ReviewObligationCoverage` remains authoritative for explicit coverage, and chronology alone resolves none. These scheduled-boundary membership rules do not change material-Drift or other valid material-event obligations.

While any qualifying obligation remains unresolved, Current Scientific Applicability is suspended and operational reliance must fail closed, while the latest completed scientific conclusion and historical Market Edge remain intact. Scientific inapplicability neither creates nor revokes Governance authority and does not modify Governance History.

Current Scientific Applicability is a deterministic replayable Forecast Intelligence projection owned by PR19; it is not stored as mutable authoritative state. At an explicit timezone-aware `as_of` boundary, the projection identifies the latest completed conclusion for the Edge Claim, all scheduled obligations due by `as_of`, all valid material-event artifacts effective by `as_of`, and the obligations explicitly covered by completed Reviews. Unresolved obligations suspend applicability. Otherwise only Supported or Strongly Supported may support applicability, subject to every other protocol, Research Domain, Research Population, Evidence, analytical, and compatibility requirement. Resolving an obligation does not by itself restore applicability.

PR13 provides the immutable structures needed for this replay: claim and Market Edge relationships, scheduled review-boundary identities, authorized material-event references, effective and completion times, completed conclusions, explicit obligation coverage, deterministic identities, provenance, serialization, and fail-closed validation. Bounded typed supporting value objects may express these relationships; they are not additional top-level research contracts and must not become mutable workflow or current-state objects.

PR13 does not calculate or store authoritative Current Scientific Applicability, implement the canonical Comparative Performance Report, or introduce a generic `ReviewTrigger`, mutable review lifecycle, workflow manager, always-on surveillance service, Workspace/UI state, or additional durable current-applicability contract. Workspace or UI state cannot originate, resolve, or override Under Review. PR19 owns Current Scientific Applicability and Policy Recommendation without granting Governance or operational authority.

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
| Research Snapshot, Comparative Measurement, and cumulative Comparative Performance | Implemented by PR14 with deterministic replay, paired analysis, Calibration, and failure-inclusive Coverage |
| Protocol Claim Set, time-bounded Comparative Performance, comparative Drift analysis, and canonical Comparative Performance Report | Implemented by PR15 with deterministic replay, authoritative claim completeness, and PR13 reference compatibility |
| Standalone Probability Source methodology and target architecture | Governed by merged PR16A; its synthetic/offline contract path is implemented by PR16B |
| Market probability derivation, standalone Measurement, Coverage, cumulative/time-bounded performance, and report integration | Implemented in PR16B for the broad Research Domain with synthetic offline Evidence |
| Separate retrospective/prospective Kalshi MLB authority | Defined by PR17A; contracts/replay implemented in PR17B1; operations and activation remain PR17B2–PR17D |
| Current Scientific Applicability and Policy Recommendation | Approved for PR19; not implemented |
| Edge Claim, Market Edge, Research Review, and Drift Surveillance contracts | Implemented |
| Policy Hypothesis aligned explicitly to supported Market Edges | Product-approved; existing symbol has older analytical-candidate semantics |
| Forecast Policy, deterministic execution, and Policy Forecast | Implemented |
| Event-sourced Product Owner Governance | Implemented |
| Forecast Intelligence Workspace | Approved, not implemented |
| Opportunity Analysis consuming governance-authorized Policy Forecast | Approved, not integrated; legacy direct-provider path remains active |
| Historical Policy Forecast evaluation and automated Shadow measurement | Not implemented |

These gaps must be resolved through separately approved implementation work. Architecture does not invent compatibility shims or silently redefine existing contracts.
## PR17C1 activation operations

PR17C1 adds typed activation and replaceable read-only provider/credential seams without altering PR17B1 scientific contracts or PR17B2 archive contracts. Its exact proposed boundary is `2026-09-05T00:00:00-04:00` (`America/New_York`, `2026-09-05T04:00:00Z`), immutable only following explicit Product Owner authorization and reviewed merge by September 3. An activated local-Mac configuration may be pre-staged, but the trusted boundary enforces zero early calls and zero early attempts. Secrets are retrieved only at the live Kalshi boundary through a replaceable macOS Keychain provider; they never enter configuration, archives, reports, or diagnostics.

Thin `launchd` wrappers invoke typed operations every 30 seconds, hourly, or daily. Exact-one market discovery, immutable external Evidence, create-only publication, dry-run/activated physical isolation, daily same-drive secondary synchronization (not physical backup), and non-authoritative health reporting preserve separation among scientific, operational, reporting, Policy, Governance, and production authority. PR17C2, PR17C3, and PR17D remain unimplemented.

Kalshi authentication follows its documented read-only RSA-PSS/SHA-256 boundary: public key ID plus Keychain-provided private key, millisecond timestamp, and signature over timestamp, `GET`, and the query-free path. Headers exist only at transport invocation. Append-only sanitized heartbeats supply actual command chronology and counts to deterministic health inspection. The deployment renderer emits absolute-path plists but performs no installation.

Current Kalshi catalog and order-book routes are public read-only market-data GETs, so the signing/Keychain seam is retained but not invoked for them. The order-book successor seam archives exact provider bytes separately from canonical `MarketObservation` material and strictly accepts `orderbook_fp` fixed-point bids. The `maintain` command verifies authoritative integrity, rebuilds only the derived SQLite index, then verifies index health. The activated rehearsal uses these same initialization, adapter, CLI, heartbeat, rendering, and archive paths with fixtures.
PR17C1 keeps schedule authority upstream of market discovery. Complete MLB responses produce correction-aware histories, classifications, eligibility, and scheduled-state opportunities before independent per-event Kalshi reconciliation; a missing or ambiguous market cannot discard another event or the MLB universe. Catalog acquisition follows a bounded validated cursor chain and preserves page raw material, while MLB requests use the versioned New York obligation/lookback date rule and expose incomplete multi-date acquisition. Kalshi `orderbook_fp` resting YES bids complement to canonical NO offers and resting NO bids complement to canonical YES offers. Refreshes append genuine corrections, suppress semantic no-change, and preserve earlier-boundary replay.

The multi-date union rule `provider-pages-canonical-union-2` binds
`mlb-explicit-reschedule-lineage-1`. Raw response pages remain immutable; the
derived union groups stable same-`gamePk` identity and admits materially
different records only when canonical reschedule fields establish one unique
forward lineage. The derived record order, outcome history, terminal
classification, acquisition digest, completion, replay, inspection, and index
reconstruction all consume that same order-independent rule.

`provider-pages-canonical-union-3` binds
`mlb-explicit-schedule-evolution-lineage-2`. Its typed derived descriptor keeps
reciprocal resume lineage separate from reschedule lineage and never rewrites
provider records. Resume classification preserves the original official date,
sets `ordinary_game` false, retains both ordered Outcome observations, and
suppresses a second scheduled-state/candle opportunity. Version-to-union
pairings are exact; versions 2/1 and 3/2 remain replayable without
reinterpretation.

PR17C2 retrospective supporting acquisition may retry one unchanged logical
MLB schedule, Kalshi historical-cutoff, historical-catalog, or live-catalog
request under supporting-page schema 2. The finite policy is three attempts,
five seconds per request, one- then two-second backoff, a twenty-second page
envelope, and at most two honored `Retry-After` seconds. Only timeout,
connection failure, rate limiting, and provider/server error may continue.
Every attempt, safe response body, timestamp, status, and call remains bound to
the single logical page; validation and integrity failures remain fail-closed.
Schema-1 pages retain their original single-call replay semantics.

Retrospective MLB winner-market reconciliation requires an explicitly binary
market and a narrow provider settlement-rule template that identifies the YES
participant, opponent, two-participant matchup, and original New York local
schedule instant. The rule-derived aware instant and participants must exactly
equal MLB authority. A repeated NO proposition label becomes the complement
only after that independent proof; expiration and close metadata grant no event
identity. It has no participant-only fallback. Regular-season
eligibility consumes canonical phase and ordinary-game classification; the
provider-native game-type code is retained but is not a second population gate.
Versioned supporting-session corrections reuse immutable pages, name one exact
predecessor, and publish new bundles plus one manifest-last authority. Replay
selects the sole verified leaf without manifest-order tie-breaking.

PR17C1 acquisition authority is one replay-verified envelope, not a synthetic raw response: exact create-only pages carry provider/query identity and chronology, the typed manifest commits to their order and digests, and the canonical union is labeled derived under a versioned rule. Outcomes use the same page lineage. `eastern-unresolved-obligations-lookback-2` retains all unresolved non-terminal dates and bounds only resolved corrections. Loaders receive the command's single trusted start time, and standard query encoding preserves opaque cursors without allowing parameter injection.

Page chronology records real trusted request intervals and is monotonic from the fixed command start through acquisition completion. Archive reconciliation treats every acquisition group as atomic authority: page-only, conflicting, shared, or multiply enveloped groups are partial/blocking; replay and operational consumers admit only a group closed by exactly one complete envelope. Retry reuses verified create-only pages and never deletes or rewrites abandoned material.

Ordinary replay independently rebuilds each versioned union and correction-aware scientific contract set from verified pages, trusted chronology, canonical Protocol authority, and the exact predecessor state. It requires exact canonical stored-set equality; envelope serialization is never Evidence or an independent trust boundary.

The narrow `reconcile-acquisitions` operation closes only the operational integrity state of an unambiguous page-only group. Its create-only abandonment artifact names the exact immutable pages, provider, command family, rule, reason, and trusted reconciliation time; it cannot confer scientific authority. A restarted acquisition retains new chronology and identity, while inspection and secondary storage preserve both the abandoned audit trail and independent replacement.
