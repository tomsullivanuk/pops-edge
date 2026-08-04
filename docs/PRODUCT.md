# Pops' Edge Product

## Mission

Pops' Edge is a quantitative decision platform whose purpose is to identify
opportunities with demonstrable statistical advantage. It accomplishes this
by collecting high-quality Evidence, objectively measuring forecasting
performance, developing and validating Forecast Policies, and applying those
policies to identify positive expected-value opportunities. The platform
continuously measures its own performance so that every Forecast Policy is
supported by empirical Evidence rather than intuition.

Sports wagering is the current proving ground for this decision framework. It
is an application of the platform, not the platform's defining purpose. The
same capability boundaries are intended eventually to support other domains
where reproducible forecasts, observable outcomes, and actionable market or
decision Evidence can be reconciled. No additional domain is currently
implemented or implied by that direction.

## Product capability hierarchy

Every durable product capability exists to support the Mission:

```text
Mission: identify opportunities with demonstrable statistical advantage
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

- **Identity** defines the canonical events, participants, propositions,
  providers, models, versions, and Series to which observations refer.
- **Evidence** preserves what authoritative and external sources reported,
  when they reported it, when it was collected, and how it was transformed.
- **Measurement** evaluates forecasts, Forecast Policies, opportunities,
  decisions, and outcomes using reproducible historical information states.
- **Forecast Evaluation** reproducibly compares one Forecast Observation with
  one Outcome Observation for the same Canonical Event.
- **Forecast Intelligence Report** transforms Forecast Evaluations into
  objective, scoped knowledge about demonstrated forecast quality.
- **Policy Proposal** connects that analysis to a non-executable governance
  suggestion while preserving adverse evidence and limitations.
- **Policy Hypothesis** is the immutable, versioned, non-executable forecasting
  approach evaluated or proposed for further Research.
- **Product Owner Governance** alone may change policy lifecycle or production
  authority.
- **Forecast Policy** defines a versioned, testable method for converting
  eligible current Forecast Observations into a derived Policy Forecast. Its
  selection and configuration are justified by Forecast Intelligence.
- **Forecast Policy Execution** records one deterministic application of one
  Forecast Policy to an explicit batch of supplied Forecast Observations.
- **Policy Forecast** is the immutable derived probability distribution
  produced by executing one Forecast Policy for one Canonical Event.
- **Opportunity Analysis** applies a Policy Forecast to compatible current
  Market Evidence to identify statistically advantageous opportunities.
- **Execution** consumes the preceding capabilities when an approved action is
  warranted. It is one consumer of the platform, not its purpose.

The current implementation uses the narrower durable boundary documented in
`ARCHITECTURE.md`: Identity, Evidence, deterministic Analysis, and mutable
Policy. The hierarchy above states the intended product capabilities without
claiming that each has already been fully implemented. In particular,
Opportunity Analysis remains deterministic analysis rather than a
recommendation, and current Execution remains manual.

## Outcome Evidence

Outcome Evidence establishes what actually happened. It consists of immutable
provider facts represented as Outcome Observations. For MLB, the MLB Stats API
is authoritative. Kalshi settlement, DRatings completed tables, sportsbook
results, and other sources may corroborate those facts but are not
authoritative Outcome Evidence.

Outcome Evidence does not decide whether a forecast should be evaluated.
Evaluation Eligibility is Policy. It can select eligible Forecast Observations
and Outcome Observations without changing either source record.

## Forecast Evaluation

A Forecast Evaluation is immutable, reproducible derived Analysis for exactly
one Canonical Event. It compares one Forecast Observation with one Outcome
Observation and measures the complete probability distribution that the
provider published, not merely whether its highest-probability side won.

Forecast Evaluation is distinct from future market-relative evaluation and
wagering evaluation. It never becomes Evidence, even though a particular
evaluation remains immutable once its inputs and method are fixed.

## Guiding principle

> **Every Forecast Policy must earn the right to exist through empirical
> Measurement.**

A proposed forecasting approach begins as a Policy Hypothesis, not received
truth. Reproducible historical Measurement informs whether Product Owner
governance should consider creating or advancing a separate Forecast Policy.
Intuition may motivate a Policy Hypothesis, but intuition alone never justifies
production use. Competing hypotheses and policies must be evaluated against
preserved Evidence and outcomes using explicit, repeatable methods.

## Current analytical boundary

Expected value explains reproducible economics from compatible forecast and
executable market Evidence; it is not a recommendation. Thresholds,
liquidity/freshness requirements, bankroll, sizing, and bet/no-bet decisions
remain mutable Policy in the current architecture.

Executable market analysis is side- and quantity-aware and uses visible depth.
Provider bids and complement-derived offers remain distinguishable, fees are
explicit Analysis inputs, and valuation is derived rather than source
Evidence. Closed or illiquid markets may still be preserved as Evidence but
are operationally non-executable independent of recommendation Policy.

The Opportunity Board is the primary MLB product interface. It combines
forecast and market Evidence, deterministic valuation, and current position
awareness to answer what has value, what is already owned, and what needs
attention.
Attention ordering is deterministic presentation. Constrained or adverse
existing exposure comes first, followed by unresolved diagnostics, other
existing exposure, positive-EV unheld analyses, and remaining complete rows.
Cost basis, executable-quantity P/L, EV, liquidity, and stable Identity provide
documented tie-breakers. “Positive” means only mathematically positive expected
value; it neither recommends nor sizes a wager.

Expandable diagnostics keep Evidence, reconciliation, valuation, and
provenance available within the same board. The manual workflow rebuilds this
derived surface from local inputs and emits a concise factual summary; no
Opportunity is persisted.

Positions are authoritative open-position summaries identified by provider
market, proposition, event, and semantic side. Offsetting YES and NO exposure
remains separate. Position value consumes visible executable exit depth, and
P/L is shown only for the executable quantity; any remainder is explicitly
unpriced.
Downloaded activity may be normalized into that summary only after exact
market/event/side reconciliation. Trades establish or reduce exposure;
unfilled orders do not. Fees remain visible Evidence separate from average
entry cost. The board labels its bounded public order-book capture range and
uses a one-contract comparison quantity solely for analysis, not sizing.
Pregame forecast comparison requires market capture strictly before first
pitch. In-play books may still value current liquidation exposure, but they do
not produce forecast-comparison edge. Until production Kalshi fees are
approved, displayed comparison values are Gross Edge before fees, never net
EV. Lifecycle states such as Settled and Suspended take precedence over absent
depth. Paired team lines always display away first and home second while the
underlying Evidence preserves provider order.
Operational validation deliberately retains two information states: August 2
shows the normal pregame board with an activity-derived zero-position state,
while August 1 proves that position monitoring and fail-closed game status
remain correct after games begin or propositions reject.

## Vision

Pops' Edge should become a durable, reproducible quantitative decision
platform. Today it imports probability forecasts from an external forecast
provider and prices from a prediction-market provider, preserves each source
independently, and compares forecast observations with executable market
observations. Over time, Measurement, Forecast Intelligence, and competing
Forecast Policies should make the empirical basis of each opportunity and
decision inspectable without hiding Evidence or assumptions.

Pops' Edge does not presently aim to create its own underlying probability
forecasts. Its product responsibility begins with evaluating forecasts supplied
by external providers. Forecast providers must remain interchangeable and
independently evaluable; no provider is permanently privileged as “the model.”

The product is not defined by one exchange, source, sport, tournament, or
report. MLB, DRatings, and Kalshi are the current proving-ground combination;
the World Cup workflow remains the production baseline. Multiple forecast
providers, additional sports, and non-wagering domains are planned evolution,
not present capabilities.

## Forecast Providers

Forecast Providers publish original probabilistic forecasts and create
Forecast Observations. DRatings is the current MLB Forecast Provider; future
providers and internal models may participate through the same architectural
boundary.

A Forecast Provider does not evaluate itself, combine itself with another
provider, assign its own weight, or determine whether it should be trusted.
Those responsibilities belong to Measurement, Forecast Intelligence, and
Forecast Policy. No additional MLB Forecast Provider is currently implemented.

## Forecast Intelligence

Forecast Intelligence is the provider-neutral capability that transforms
Forecast Evaluations into objective knowledge. It evaluates forecasting
providers, measures forecast quality, compares competing models, evaluates
calibration, computes objective performance metrics, supports the development
of Forecast Policies, and preserves reproducible historical evaluation.

Forecast Intelligence does not merely average models, and it does not
permanently privilege a provider or create forecasts. It is always derived
from immutable Forecast Evaluations, never stored as mutable accumulated state,
and never becomes Evidence. Its conclusions must be reproducible from their
referenced evaluations. It supports Forecast Policy comparison, selection,
configuration, replacement, and empirical justification, but does not provide
today's event probabilities. The current platform has one MLB Forecast
Provider, DRatings. PR10 implements the provider-neutral single-provider
Forecast Intelligence foundation; comparative provider analysis and direct
cross-provider comparison remain future capabilities.

Forecast Intelligence is an analysis engine over Forecast Evaluations, not a
provider feature. Its provider-neutral contract must work with one provider,
multiple providers, internal models, and future Policy Forecast evaluations.
PR10 proves it with DRatings—the sole currently implemented MLB Forecast
Provider—for MLB winner forecasts. Additional providers and direct
cross-provider comparison remain future work.

### Research Mode and Production Mode

Research Mode learns from historical Evidence through immutable current
Forecast Evaluations, explicit evaluation windows, and versioned intelligence
rules. It may rerun analyses, compare hypotheses, identify strengths and
weaknesses, and emit Forecast Intelligence Reports and analytical Policy
Proposals. It cannot change production behavior.

Production Mode applies a production-authorized Forecast Policy to eligible current
Forecast Observations, produces a Policy Forecast, and combines it with current
Market Evidence through Opportunity Analysis. It does not autonomously learn,
replace, or promote its own policy.

> **Research never changes production. Governance changes production.**

## Forecast Research Workspace

PR13 is planned to add the Product Owner's primary quantitative research
environment as one deterministic, read-only projection over immutable PR9–PR12
inputs. The workspace owns orchestration, decision-oriented organization, and
presentation. It owns no Evidence, Measurement, Forecast Intelligence,
Forecast Policy, Governance, Opportunity Analysis, persistence, or mutable
business state.

It helps the Product Owner understand provider performance, Forecast
Intelligence conclusions, support for Policy Hypotheses and Policy Proposals,
their corresponding executable Forecast Policies, governance state, available
Shadow or policy-performance evidence, and any governance decision worth
considering. It cannot always answer which Forecast Policy historically
performed best; that requires compatible immutable policy-evaluation artifacts.

An immutable, explicitly supplied `ResearchWorkspaceContext` holds sport,
competition, proposition, evaluation window, `analysis_as_of`,
`governance_as_of`, provider scope, Forecast Policy scope, and Policy
Hypothesis scope. Every section derives from that same context without silently
widening or replacing it. Identical immutable inputs and identical context must
produce a substantively identical workspace projection. Any projection identity
uses context, supplied immutable identities, projection algorithm/version,
output-affecting renderer version, and section selection. Wall-clock generation
time is non-identifying provenance and may change presentation bytes without
changing projection substance.

The v1.1 product is one locally generated, self-contained, static HTML document:
read-only, printable, archiveable, and visually consistent with the Opportunity
Board's navy/white product language. It requires no server, database, browser
persistence, or write action. Sortable tables, concise summaries, collapsible
details, and expandable provenance support investigation without turning the
workspace into a separate application. Multiple views, tabs, and richer
interaction are deferred until actual usage supports them.

The workspace follows the Product Owner's research and governance decision
journey:

```text
Research Context
        ↓
Executive Overview
        ↓
Provider Performance
        ↓
Policy Candidate Comparison
        ↓
Policy Proposal Review
        ↓
Governance Review
        ↓
Governance Decision Draft
        ↓
Diagnostics
```

Research Context discloses scope and boundaries. Executive Overview presents
major conclusions, the best-supported policy candidate, adequacy, governance
state, and limitations while keeping descriptive facts, proposal
interpretations, governance state, and Product Owner decisions distinct.
“Best-supported” means strongest support from supplied Forecast Intelligence,
Policy Proposal, benchmark evidence, and governance context; it does not imply
measured historical predictive superiority. Provider Performance presents
Brier score, log loss, calibration, directional accuracy, coverage, and trends.
Policy Candidate Comparison presents Hypotheses, Proposals, Reports,
constraints, rules, benchmarks, adequacy, evidence, limitations, corresponding
policies, governance lifecycle, and history gaps. Provider evaluation metrics
are never relabeled as policy metrics; unavailable historical policy metrics
are identified explicitly with reasons. Policy Proposal Review presents
recommendation, favorable and adverse evidence,
uncertainty, and limitations. Governance Review derives Research, Shadow,
Production, Retired, and Rejected views at `governance_as_of`. Diagnostics
preserves provenance, identities, exclusions, superseded evaluations,
conflicts, and relevant serialized objects.

The Governance Decision Draft is explicitly non-authoritative and derives only
from an immutable Policy Proposal's suggested action or an explicit Product
Owner-selected decision supplied in context. It preserves Forecast Policy
ID/version, Governance Scope, source Proposal ID when applicable, source Report
IDs, source Hypothesis ID, the suggested or selected decision, rationale, and
limitations. It leaves `decision_effective_at` blank, states that it has no
authority, and cannot create a Governance Record or change any policy lifecycle.
Without a supporting proposal or Product Owner selection it states `No
governance decision drafted.` The workspace adds no recommendation algorithm:

```text
Workspace → Governance Decision Draft → Explicit Product Owner action
          → Governance Record
```

The workspace observes, compares, presents existing proposal interpretations,
and drafts. It never performs governance or production execution. PR13 does not modify Opportunity Analysis,
Opportunity Board, or wagering. PR14 remains responsible for consuming a
governance-compatible Policy Forecast in Opportunity Analysis.

PR9 evaluates provider Forecast Observations, and PR10 Forecast Intelligence
and Policy Proposals analyze and interpret that provider-level evidence. PR11
produces current Policy Forecasts; it does not evaluate their historical
predictive performance. PR12 governs policies without measuring them. The
workspace visibly distinguishes no Policy Forecast history, current-only
outputs, prospective Shadow outputs, compatible supplied policy-evaluation
artifacts, and insufficient evidence for policy-performance claims. It neither
implements Shadow execution nor creates policy backtesting. Historical policy
evaluation remains a possible future capability, not an implicit PR13–PR15
deliverable.

All supplied analytical and governance objects are checked fail-closed against
the full `ResearchWorkspaceContext`, including domain, time boundaries,
provider/model, Hypothesis, Policy, and Governance Scope. Incompatible objects
are excluded with diagnostics; no section silently widens context.

### Forecast Intelligence Report

One Forecast Intelligence Report measures one Forecast Provider within one
domain and one explicit immutable evaluation window. Its scope includes
provider and model/version scope, sport, competition, proposition type,
Evaluation Eligibility Policy version, Forecast Evaluation algorithm version,
and Forecast Intelligence algorithm version. Calibration buckets, probability
bands, home/away and favorite/underdog splits, historical periods, and other
supported segments remain sections within that report rather than fragmented
first-class intelligence identities.

The report is immutable, deterministic, reproducible derived Analysis—never
Evidence or mutable accumulated state. It preserves included current Forecast
Evaluation IDs, excluded and superseded IDs, window definition, actual coverage,
derivation identity, generation timestamp, deterministic input digest, and
limitations.
It normally uses evaluations selected against the latest authoritative final,
so superseded corrected-result evaluations are not double-counted. Earlier
evaluation states may be replayed only under an explicit historical scope.

Coverage, quality, calibration, segmentation, and trend sections disclose their
sample sizes and gaps. At minimum the report supports Brier score, finite and
infinite log-loss treatment, directional accuracy, probability distribution,
bucket-level predicted and observed rates, and calibration difference. Small
or unsupported samples remain visible as limited or unavailable. Any adequacy
label or threshold is versioned analytical Policy, not universal truth or
Evidence. The requested window, covered period, event count, completeness, and
missing periods are explicit; PR10 does not silently analyze “all available
data.”

For the initial MLB winner domain, primary calibration has one stable target:
`home participant wins`. Each included game contributes its published home-win
probability once and a realized zero-or-one home-win indicator. Actual-result,
strict-favorite-result (including no unique favorite), and home-win-probability
segments are separate evaluation-level views with explicit grouping, numerator,
denominator, contributing identities, sample size, and limitations. Directional
accuracy excludes tied forecasts and uses unique-favorite games as its
denominator.

The report's deterministic identity includes its provider/domain scope,
evaluation window and explicit analysis-as-of boundary, canonically ordered
material evaluation identities, algorithm and rule versions, and every other
output-affecting parameter. Wall-clock `generated_at` or `derived_at` remains
non-identifying provenance unless explicitly declared as the analysis-as-of
boundary. Filesystem timestamps, irrelevant input ordering, and unstated
mutable repository state never affect identity.

### Policy Hypothesis

A Policy Hypothesis is PR10's immutable, versioned, measurable analytical
candidate specification. It describes a forecasting approach evaluated or
proposed for further Research and may preserve provider and model/version
constraints, evaluation eligibility, selection and weighting, normalization or
transformation, missing-provider and fallback behavior, implementation
assumptions, and sport, competition, and proposition scope.

It may be explicitly supplied Research input or derived Analysis. It is
non-executable, has no lifecycle authority, never becomes Evidence, and is not
a Forecast Policy or Policy Forecast. Historical replay or later prospective
Shadow evaluation does not automatically convert it into production
configuration.

### Policy Proposal

A Policy Proposal is the immutable advisory bridge from a Forecast Intelligence
Report to Product Owner governance. It preserves report, proposal algorithm,
Policy Hypothesis, benchmark, domain, and derivation identities; the
hypothesis's provider/model constraints, eligibility, selection or weighting,
normalization, missing-provider, fallback, and implementation rules; evaluation
window and design; quantitative evidence; benchmarks; sample sizes; adverse
segments; and limitations such as missing coverage, model change, in-sample
optimization, selection bias, or absent prospective Shadow history.

It may suggest rejection, continued Research, Shadow consideration or
continuation, incumbent retention, or consideration of Production, Retire, or
replacement. It cannot perform any transition. It is not
Evidence, a production-authorized Forecast Policy, a Policy Forecast, a wagering
recommendation, or executable production configuration, and it cannot create a
Forecast Policy. Only the Product Owner may define a distinct Forecast Policy
based on a Policy Hypothesis and record Research, Shadow, Production, Retire,
or Reject governance decisions for it.
Reports and proposals distinguish measured fact, derived interpretation,
limitation, and suggested governance action. Neither declares a model
“correct” or claims production authority.

The proposal ID depends on report, Policy Hypothesis, benchmark, proposal
algorithm, suggested-action rule, material limitation, and other
output-affecting analytical identities. Its generation timestamp is metadata,
not identity. Identical immutable material inputs and algorithm versions
produce identical report, hypothesis, and proposal identities and analytical
contents regardless of rerun time.

The suggestion rule is explicit and versioned. It preserves the adequacy result,
factual benchmark availability, material metrics, deterministic reason codes,
and contributing evaluation identities. An absent benchmark remains absent and
cannot be replaced with a synthetic comparison. The resulting action remains
advisory Analysis and cannot alter lifecycle or production configuration.

## Forecast Policy

A Forecast Policy is an immutable executable specification that deterministically
transforms eligible current Forecast Observations into Policy Forecasts. It is a
production-side Policy object with complete domain, provider/model, eligibility,
selection, weighting, transformation, normalization, missing-provider,
fallback, validation, rule-component, implementation, limitation, and identity
material. It never mutates or impersonates provider Evidence.

It contains no approval, activation, Shadow, retirement, rejection, promotion,
or Product Owner state. Those remain PR12 governance concerns. Its identity is
determined solely by material executable specification inputs and versions, not
wall-clock time, filesystem or repository state, Product Owner identity, or
governance lifecycle.

Forecast Policy is a separate implemented PR11 production contract. A PR10
Policy Hypothesis is analytical, measurable, replayable, and non-executable; a
Policy Proposal is advisory. Neither automatically becomes a Forecast Policy.
Future Product Owner governance may authorize a distinct complete Forecast
Policy based on those Research artifacts, while their contracts remain separate.

## Product Owner Governance

PR12 implements Product Owner governance. `GovernanceRecord` is one immutable
append-only Product Owner decision about
exactly one immutable Forecast Policy. It never governs a provider, policy
family, multiple policies, or Policy Hypothesis, and it is Governance rather
than Evidence, Forecast Intelligence, Forecast Policy, or Policy Forecast.

Each action creates a new record; nothing is updated in place. Records preserve
the governed policy, immutable Governance Scope, decision and material
`decision_effective_at`, Product Owner identity, governance algorithm/schema
version, rationale, notes, limitations, and references to supporting Policy
Proposals, Forecast Intelligence Reports, and a Policy Hypothesis. Supporting
Analysis is referenced rather than duplicated.
Material governance inputs determine identity; wall-clock generation metadata,
repository location, filesystem timestamps, and derived lifecycle do not.
Changing scope or effective time changes identity. `generated_at`, `recorded_at`,
`imported_at`, input order, and file order never establish governance chronology.
The stable Product Owner ID is material; an optional display name is descriptive
metadata and does not change Governance Record identity.

The initial Governance Scope is deterministically defined by the governed
Forecast Policy's sport, competition, and proposition type, such as
`baseball / MLB / winner`. A record must agree with its policy's scope. Policies
in different scopes resolve independently; no policy lineage is introduced.

The five decisions are:

- `Research`: research-only use, with no production authority;
- `Shadow`: parallel production measurement that may execute and produce Policy
  Forecasts but cannot influence Opportunity Analysis or wagering;
- `Production`: production authority for the governed Forecast Policy;
- `Retire`: withdrawal of production authority without invalidating historical
  Analysis; and
- `Reject`: permanent rejection of that immutable policy. Reconsideration
  requires a new Forecast Policy.

Lifecycle is always replay-derived from append-only Governance Records and is
never stored on a policy or record. The latest decision for a policy derives
`Research`, `Shadow`, `Production`, `Retired`, or `Rejected`; Reject is terminal.
`GovernanceHistory` preserves deterministic chronology, rejects duplicate
record IDs, and reconstructs lifecycle at any historical boundary.

At an explicit historical `as_of` boundary, policy-level replay includes only
records effective by that boundary and derives each policy's lifecycle.
Scope-level replay separately resolves at most one production-authorized policy
across every policy in that scope. A later Production decision displaces prior
authority; a later non-Production decision removes authority only when it
governs the currently authorized policy. Earlier policies never resume
implicitly, while non-Production decisions for other policies do not disturb
current authority. With no current authority or with materially conflicting
same-time decisions, resolution returns none and fails closed. Shadow policies
are resolved separately and exist solely for measurement.

Replay never breaks a material tie with record ID, input order, serialization
order, filenames, or filesystem time. It also fails closed on a decision after
terminal Reject, different same-time policy decisions, simultaneous Production
decisions within one scope, unknown policy identity, policy/scope mismatch, or missing
effective time or Product Owner identity.

Equivalent records with the same policy, scope, decision, effective time, and
stable Product Owner ID are one lifecycle effect with every supporting record
preserved. Different same-time decisions conflict. A conflict involving current
or candidate Production authority fails scope resolution closed; an unrelated
Research/Shadow-only conflict remains visible without changing otherwise
unambiguous production authority.

Research never creates authority. A Policy Hypothesis and Policy Proposal may
support the Product Owner's decision about a separate Forecast Policy, but only
a Governance Record can grant production authority. PR12 does not modify
Forecast Policy execution or Opportunity Analysis. PR14 remains responsible for
consuming a production-authorized Policy Forecast with Market Evidence.
Specifically, PR14 must eventually select a Policy Forecast produced by the
governance-authorized Forecast Policy; PR14 timing and execution-selection rules
remain deliberately undesigned here.

```text
Policy Hypothesis
        ↓
Policy Proposal
        ↓
Product Owner defines a separate immutable Forecast Policy
        ↓
Governance Record governing exactly that Forecast Policy
        ↓
Derived production authority, if the decision is Production
```

## Forecast Policy Execution

A Forecast Policy Execution is an immutable batch context recording one
deterministic application of one supplied Forecast Policy to one explicit input
scope. One execution may cover an MLB slate or other competition/date scope and
produce multiple independently identified, replayable Policy Forecasts. It
preserves policy and algorithm identity; scope and analysis-as-of boundary;
candidate, included, and excluded observation identities and reasons; immutable
identified event contexts and conflicts; event and output identities; stage
versions; digest, statistics, warnings, and limitations. Its identity is fixed
from material inputs before outputs exist; completed output references cannot
feed back into it. It does not discover events, fetch provider data, or determine
whether the supplied policy is active.

## Policy Forecast

A Policy Forecast is the immutable canonical analytical result of one specific
Forecast Policy Execution for exactly one Canonical Event and proposition. It
preserves execution and policy identity; candidate, included, and excluded
Forecast Observation identities; provider/model/version and input probability
provenance; every eligibility, selection, provider-selection, transformation,
weighting, normalization, fallback, and validation decision; complete output
distribution and outcome semantics; precision, validation, issues, limitations,
identified event context, digest, and as-of boundary. Wall-clock generation time
is not canonical analytical content.

A Policy Forecast is derived Analysis, not provider Evidence, and never claims
a provider published the derived distribution. It contains no market price,
expected value, wager recommendation, Kelly sizing, bankroll or position data,
order, governance state, or Product Owner approval.

Different policies or executions may produce distinct valid Policy Forecasts
for the same event and proposition. Neither validity nor creation grants global
or production authority. PR12 governance will be the only bridge that selects a
production-authoritative Policy Forecast; PR14 will migrate Opportunity Analysis
to consume that authorized result. PR11 implements neither selection nor
consumer migration.

Execution uses deterministic versioned stages: Input Compatibility, Observation
Eligibility, Observation Selection, Provider Selection, Transformation,
Weighting, Normalization, Output Validation, then Policy Forecast. Each material
stage preserves its ID, version, parameters, result, and limitations. PR11 does
not require a dynamic plug-in framework; explicit stage provenance is sufficient
for the initial bounded implementations and later replacement.

PR11 production observation eligibility is distinct from PR9 historical
Evaluation Eligibility. The initial selection rule chooses the unique latest
eligible observation before the analysis-as-of boundary and fails closed on a
latest-timestamp tie; it never uses input order. Provider
weights, precision, unavailable-provider treatment, redistribution, fallback,
normalization, and validation are material policy inputs. Invalid, incomplete,
ambiguous, stale, unsupported, or irreproducible inputs fail closed unless the
policy contains an explicit versioned fallback; market probabilities are never
an implicit fallback.

## Opportunity Analysis

Opportunity Analysis is intended to consume a Policy Forecast together with
compatible current Market Evidence. PR11 now produces policy-relative canonical
analytical results but does not designate a production-authoritative result or
redesign the PR8 consumer. PR12 governance will make that designation. A bounded
PR14 will migrate Opportunity Analysis and the Opportunity Board to the
authorized Policy Forecast identity.
It remains separate from wagering Policy, Kelly sizing, bankroll management,
recommendation thresholds, and Execution.

The current MLB workflow compares DRatings Forecast Observations directly with
Kalshi market Evidence under deterministic PR7 valuation. That is the present
single-provider precursor to the fuller Forecast Policy capability. PR10
Forecast Intelligence and the PR11 Forecast Policy execution foundation are
implemented; their Opportunity Analysis integration remains planned for PR14.

PR11's implemented initial demonstration is a supplied DRatings MLB winner
policy selecting the latest eligible validated pregame observation before an
explicit analysis-as-of boundary, applying identity transformation and weight
`1.0`, validating a complete two-outcome distribution without silent correction,
and failing closed with no fallback when DRatings is absent. It demonstrates the
contract, not empirical approval, active status, or production authority.

PR9 implements authoritative MLB Outcome Evidence, explicit Evaluation
Eligibility Decisions, and immutable Forecast Evaluations. It uses the
Forecast Observation's Pops' Edge collection timestamp for strict pregame
eligibility when no row-specific provider timestamp exists, without relabeling
collection provenance as provider publication time. Official ordinary,
extra-inning, shortened, and later-completed suspended finals are eligible;
non-final, postponed, cancelled, no-contest, unresolved suspended, tied, and
at-or-after-start cases are ineligible. Forfeits and administrative rulings are
preserved as Outcome Evidence but deferred by Policy. Eligibility depends only
on immutable Forecast, Outcome, and supplied Outcome History evidence plus the
versioned Policy—not on whether an evaluation already exists. Outcome History
makes a forecast collected before authoritative postponement evidence
ineligible, permits a later post-reschedule pregame forecast, and makes missing
schedule chronology indeterminate. Duplicate pairs are rejected by immutable
Forecast Evaluation History. Decisions preserve exactly the material Outcome
Observation IDs used for chronology, so unrelated history does not become a
hidden Policy input.

An exact zero probability for the realized winner remains positive-infinite log
loss without clipping. It is stored through portable tagged JSON, and summaries
separately disclose finite and infinite log-loss counts.

Correcting an authoritative final appends a new Outcome Observation and creates
a new immutable Forecast Evaluation; it never rewrites the earlier evaluation.
A derived current view selects the evaluation for the latest authoritative
final, retains prior evaluations as superseded history, and excludes them from
current summaries to avoid counting one game twice.

The minimal PR9 history summary exists only to verify deterministic replay. It
is not Forecast Intelligence. PR10 Forecast Intelligence consumes that
immutable Measurement without changing it.

Historical learning and Policy governance follow this conceptual flow:

```text
Forecast Observations + Outcome Observations
                    ↓
          Forecast Evaluations
                    ↓
         Forecast Intelligence
                    ↓
Forecast Policy selection and configuration
```

Current-event execution follows a separate flow:

```text
Eligible current Forecast Observations
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

Forecast Intelligence does not replace current Forecast Observations, and
Forecast Policy execution does not turn its derived output into Evidence.

## Product philosophy

Research is not an end in itself. Measurement exists to improve future
decisions, and every adopted Forecast Policy remains subject to continuous
validation against empirical Evidence.

1. **Every Forecast Policy must earn the right to exist.** Require empirical,
   reproducible Measurement rather than intuition alone.
2. **Evidence before implementation.** Research sources and semantics before
   building adapters or shared contracts.
3. **Preserve provenance.** Retain what each source reported, when it reported
   it, when it was collected, and how it was transformed.
4. **Fail closed on ambiguity.** Missing an opportunity is preferable to
   presenting a false edge caused by uncertain Identity, timing, mapping,
   freshness, or settlement meaning.
5. **Prefer interchangeable providers.** Provider-specific behavior must not
   become product logic.
6. **Keep sport-specific rules in adapters.** Shared concepts must not erase
   schedules, identifiers, participants, or settlement semantics.
7. **Earn shared architecture.** Reuse should emerge from multiple working
   implementations rather than speculative generalization.
8. **Compare external forecasts.** Building a proprietary prediction model is
   outside the current product vision.
9. **Evaluate commercial data deliberately.** Judge value, cost, rights,
   reliability, coverage, and maintainability together.
10. **Decide consequential questions explicitly.** Product and architecture
   decisions precede substantial coding.
11. **Optimize for long-term coherence.** Implementation speed does not justify
    hidden Policy, lost provenance, or unstable boundaries.

Generated workbooks and HTML remain derived outputs, human judgment remains
central, new sports must not destabilize a working sport, and each PR remains
bounded and reviewable.

## Product language

- A **forecast provider** is the durable source that owns one or more
  **forecast models**; each model may have separately identified **forecast
  versions**. A **forecast series** identifies one provider/model/version
  forecast for one Canonical Event. A **forecast observation** is immutable
  Evidence of what that Series published at one point in time, including its
  complete structured outcome distribution.
- A **market provider** lists tradable contracts; a **market observation** is a
  timestamped price, depth, volume, rules, and side mapping from that provider.
- An **outcome observation** is immutable Outcome Evidence from the
  authoritative facts provider for one Canonical Event. Corroborating provider
  results remain separate Evidence.
- A **Forecast Evaluation** is immutable derived Analysis comparing one
  Forecast Observation's complete distribution with one Outcome Observation;
  Evaluation Eligibility remains Policy.
- A **canonical event** is Pops' Edge's normalized immutable event Identity,
  including authoritative sport-native identifiers. Provider-native mappings
  are separate immutable records linked to that Identity so later discovery
  does not mutate the event.
- An **edge** is a derived comparison between an eligible forecast observation
  and an executable market price.
- A **recommendation** is a Policy-governed proposed action based on an edge;
  it is not the forecast itself.
- A **position** is exposure to a contract; the **portfolio** is the collection
  of positions and their risk and performance.
- An **outcome** is the settlement-relevant event result.
- **Measurement** evaluates forecasts, Forecast Policies, opportunities,
  decisions, prices, positions, and outcomes while retaining their original
  information state.

Event facts, observations, comparisons, recommendations, positions, and
outcomes are distinct records. A later value must not silently overwrite an
earlier observation needed for audit or historical evaluation.

Pops' Edge uses a consistent Series / Observation pattern where Evidence
naturally changes over time: durable Identity owns append-only observations,
and current state is derived rather than stored. A Forecast Series represents
the conceptual “one forecast”; every provider update is a new immutable
Forecast Observation. Latest forecast, latest pregame forecast, forecast
history, and forecast movement are computed views, not source Evidence.

Provider, model, and version metadata is referenced rather than duplicated in
each observation. Provider assumptions are preserved as reported and remain
separate from authoritative event facts. Published values and precision are
preserved; inconsistent distributions are flagged, never silently normalized.
Unknown provider timestamps and versions remain explicitly unknown rather
than being inferred from collection time.

Pops' Edge distinguishes Identity, Evidence, and Policy. Identity—including
Canonical Event, Forecast Series, Provider, Model, and Version—defines what
exists; Evidence records what a source reported at a point in time; Policy
decides how Pops' Edge evaluates and acts on that Evidence. Approval, weights,
freshness, eligibility, edge requirements, Kelly settings, and portfolio
limits are Policy. They may change without rewriting immutable Identity or
historical Evidence.

Series identify the thing being observed. Observations preserve what was known
at a point in time. Derived views answer operational questions without
rewriting history. Durable objects are referenced rather than duplicated, and
observations are never updated in place.

> Identity is immutable. Evidence is immutable. Policy is mutable.

> Forecast Observations report what a provider published; they do not decide
> whether Pops' Edge should wager.

## Commercial data philosophy

Pops' Edge may use commercial data when it materially improves long-term
quality, reliability, permitted automated use, legal clarity, stable
identifiers, historical coverage, or operational maintainability. A source
decision must consider monthly and annual cost, pricing structure, minimum
contract term, API limits, retention rights, attribution, historical access,
source quality, and realistic value to this personal-use product.

As a present preference, approximately USD 100 annually may be reasonable;
approximately USD 100 monthly generally would not be. Higher cost requires
explicit product approval supported by demonstrated value. This is guidance,
not a universal architecture budget.

Naming a provider does not approve it. Sportradar, SportsDataIO, DRatings,
FanGraphs, The Odds API, and all other providers remain candidates until their
access method, permitted use, retention rights, reliability, and actual cost
are understood and explicitly approved.

For v1.1.0, the MLB Stats API is approved as the first read-only MLB facts
source for this personal, noncommercial project. This approves a bounded facts
adapter, not a permanent architecture dependency and not any forecast, market,
or commercial provider. Canonical Event and downstream observation contracts
remain provider-neutral so a licensed facts source can replace it later.
Adapter Evidence distinguishes exact response-byte Identity from canonical
JSON equivalence, and every game reports an explicit complete, partial, or
rejected outcome. Provider timestamps are never invented from collection time.

PR6 approves DRatings only as a manually captured local source of forecast
Evidence; it does not approve automated access. The adapter preserves the
Upcoming table's ordered matchup names, exact UTC time, displayed pitcher
assumptions, and two published win probabilities. A page-level update time is
not a row timestamp. DRatings supplies neither MLB `gamePk` nor authoritative
team/pitcher Identity, a disclosed model version, or a proven stable forecast
record ID. Separately captured MLB Evidence establishes event Identity and
home/away roles. Complete, partial, ambiguous, and rejected outcomes keep
uncertainty visible and create a Forecast Series only with a valid first
observation.

## Supported sports

| Sport | Status | Product version |
|---|---|---|
| FIFA World Cup | Production baseline | v1.0.0 |
| MLB | Implemented manual Opportunity Board workflow | v1.1.0 |
| Other sports | Deferred | Future |

“Supported” means the sport has documented sources, contracts, valuation rules,
reports, tests, and an operator workflow. Product documentation must not imply
support before those conditions are met.

## Platform and adapter relationship

Reusable platform components should address concerns that genuinely recur:

- configuration and sport registration;
- forecast and market provider boundaries;
- immutable observations, provenance, and freshness;
- canonical events and source mappings;
- edge analysis, recommendations, positions, portfolios, and performance
  evaluation;
- validation and quality reporting;
- deterministic fixture testing;
- output isolation and archives; and
- common presentation utilities where schemas actually align.

Sport-specific adapters should retain:

- provider acquisition, authentication, native schemas, parsing, identifiers,
  and timestamps;
- team, event, game, and market identifiers;
- calendars, stages, doubleheaders, postponements, and cancellations;
- starting pitchers, knockout rounds, and penalty shootouts;
- market matching and settlement assumptions;
- sport-specific probability and valuation Policy; and
- sport-specific reports when operator needs differ.

The boundary is empirical. Shared abstractions must be earned through multiple
working implementations. World Cup and MLB justify common product concepts,
but not a broad rewrite of the production World Cup system.

## Long-term direction

Pops' Edge should evolve into a set of independently operable domain adapters
on a small, well-tested quantitative decision foundation. Sports remain the
current proving ground. Future releases may add sports, forecast providers,
source comparisons, calibration, Forecast Policies, portfolio analytics, and
operational tooling; still later product decisions may validate applications
outside sports. Automated trading, generalized hosting, additional domains,
and broad architecture rewrites require separate approval and are not implicit
in this direction.
