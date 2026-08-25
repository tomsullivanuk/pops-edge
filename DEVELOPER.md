# Pops' Edge Developer Guide

Pops' Edge is the durable product name. The workflows documented below are the
World Cup implementation shipped as v1.0.0. World Cup-prefixed artifacts remain
unchanged for baseline compatibility.

The planned v1.1.0 work and the repository rename procedure are documented in
`docs/RELEASE_PLAN_v1.1.0.md` and `docs/REPOSITORY_RENAME.md`. The standard PR
workflow and completion-report format are in `docs/CODEX_WORKFLOW.md`.

`DEVELOPER.md` documents implementation guidance. The Empirical Research
Methodology, Product, Architecture, Release Plan, and Roadmap are governed by
their respective authoritative documents and take precedence over this guide.

## Offline event contracts

PR3 adds an offline contract layer without connecting it to the v1.0.0 World
Cup workflow:

- `event_contracts.py` defines reusable canonical event identity, native
  identifiers, independently discovered source mappings, participants,
  provenance, structured validation reasons, candidate evaluations, and
  matched/ambiguous/rejected reconciliation results.
- `mlb_contracts.py` defines MLB teams and games, preserves `gamePk`, and keeps
  schedule, pitcher, status, and explicit lineage evidence outside immutable
  event identity.
- `tests/fixtures/mlb_contract_cases.json` and
  `tests/test_event_contracts.py` exercise the contracts entirely offline.

`gamePk` is authoritative for MLB identity. A retained `gamePk` remains the
same event through schedule changes; a new `gamePk` creates a distinct event
that may be linked by explicit lineage. Similar teams, dates, or times never
override conflicting `gamePk` evidence.

`CanonicalEvent.native_identifiers` and participant native identifiers accept
only authoritative `SportNativeIdentifier` values. Forecast, market, and other
provider mappings use separate frozen `SourceMapping` records linked by
canonical entity ID. Discovering such a mapping therefore does not reconstruct
or mutate event identity. `MLBGame` repeats season, teams, and `gamePk` only as
MLB-specific convenience fields; construction rejects any disagreement with
the nested canonical event.

Observations are frozen, timezone-aware records. Missing pitchers create a
valid incomplete pitcher observation rather than invalidating the game.
Changed pitchers, schedule changes, and status changes create new observations
instead of replacing prior evidence. Same-identity postponements and
suspensions are represented by successive observations; lineage relates
distinct events only when a source explicitly supplies that relationship.
Suspension/resumption lineage is therefore valid only if the source explicitly
relates distinct event identities; self-lineage is rejected.

Rejected reconciliation retains no selected or eligible candidate.
`CandidateEvaluation` records may nevertheless preserve each considered
canonical event ID, mappings evaluated, evidence, and structured conflict
reasons. This audit information survives deterministic serialization without
making a candidate operationally available.

Deterministic tagged JSON is the adapter/fixture boundary. No database,
provider client, market contract, forecast ingestion, persistence, or World Cup
integration is part of PR3.

## Offline forecast contracts

PR4 adds `forecast_contracts.py` without connecting it to a provider or the
World Cup workflow. It defines immutable Forecast Provider, Model, Version,
Outcome, Published Probability, Distribution, provider-assumption, validation,
disposition, relationship, Observation, and collection-timing contracts.
Durable objects use one stable chain: Model references Provider, Version
references Model, and Observation references only Version. Observations do not
copy provider, model, or version metadata. A bundle validator checks the full
assembled hierarchy, including the provenance provider.

Published probabilities use exact `Decimal` values and separately preserve the
source representation, source scale, and declared decimal precision. A
distribution canonicalizes its non-semantic outcome order by outcome ID,
retains the exact observed total, and calculates its tolerance as the sum of
the half-rounding intervals implied by every published value. Percent values
convert their interval to probability scale. Totals outside that tolerance are
preserved and classified invalid; values are never rounded or normalized.

Forecast validation (`valid`, `incomplete`, `invalid`) remains separate from
provider disposition (`active`, `corrected`, `withdrawn`) and from PR3 event
reconciliation (`matched`, `ambiguous`, `rejected`). Unresolved observations
retain source evidence and candidate evaluations without claiming a Canonical
Event. Provider assumptions explicitly represent reported, undisclosed, or
unknown states. Revision relationships are separate immutable records rather
than fields on an observation; a helper validates appended evidence and derives
latest-known and effective disposition without rewriting history. Collection timing reports before-start,
at-or-after-start, or unknown-start facts from supplied schedule evidence; it
does not decide actionability.

The shared tagged serializer now supports exact decimals and dates in addition
to its existing timezone-aware datetimes and enums. Tuple-like collections are
canonicalized by their contracts before serialization, and round trips retain
the original published evidence. PR4 adds no network collection, provider
approval, persistence, weights, freshness rules, markets, edges, reports, or
wagering behavior.

## Series / Observation implementation guidance

PR5A establishes a general rule for time-varying evidence:

```text
Durable Identity -> Immutable Observations -> Derived Views
```

Canonical Event already owns successive schedule, pitcher, and status
observations; Current Game State is computed. PR6 introduces Forecast Series
as the durable identity for one Provider, Model, Version, and Canonical Event
combination. Each provider update appends a Forecast Observation.
Current Forecast, Latest Pregame Forecast, Forecast History, and Forecast
Movement must be derived without mutating or replacing observations.

Keep probabilities, timestamps, assumptions, provenance, validation,
disposition, and observation relationships on Forecast Observation rather than
Forecast Series. Reference Provider, Model, Version, Canonical Event, and Series
instead of duplicating their durable metadata. Policy such as approval,
weighting, freshness, eligibility, edge thresholds, and sizing must remain
outside identity and evidence.

## Offline DRatings snapshot adapter

`dratings_adapter.py` parses manually captured DRatings HTML and never retrieves
the provider page. It selects only the Upcoming table, preserves both displayed
probabilities and their precision, ordered pitcher assumptions, exact UTC game
time, page-level update time, detail-path locator, raw digest, canonical parsed-
evidence digest, canonical source URL, and separate Product Owner access URL.
The local command is:

```bash
./venv/bin/python inspect_dratings_snapshot.py SNAPSHOT --mlb-fixture MLB_JSON
```

MLB `gamePk`, team IDs, home/away roles, and schedule observations come only
from the separately captured MLB fixture. The controlled source alias currently
needed is `Oakland Athletics` → `Athletics`. Row publication/update timestamps,
provider version, and stable provider record identifiers remain unknown.
Provider table order is preserved as source position, not treated as away/home;
participant reconciliation assigns roles and rejects an unsafe orientation.
Missing row-specific timestamps do not make an otherwise complete row partial
because DRatings does not publish them. `complete` means the source row has its
published matchup, schedule time, complete valid distribution, displayed
pitcher assumptions, required snapshot metadata, and one MLB match. Missing
metadata the source structure is expected to publish, or missing displayed
assumptions, produces `partial` after a unique match.
Ambiguous and unmatched rows emit no Series or Observation. This boundary adds
no automated collection, persistence, freshness, weighting, valuation, market,
report, or wagering behavior.

## MLB Stats API facts adapter

`mlb_stats_api.py` contains the bounded read-only schedule client and facts
adapter. `MLBStatsAPIClient.schedule_request()` constructs the supported
`/api/v1/schedule` route and stable parameters. `fetch_schedule()` accepts an
injectable transport, uses an explicit timeout, retries only transient transport
failures and HTTP 429/500/502/503/504 responses, and treats other client errors
as permanent. Importing the module or constructing the adapter performs no
network request.

The client captures exact response bytes before JSON parsing. Raw evidence
stores `raw_response_sha256` for those bytes and `canonical_json_sha256` for
the parsed JSON serialized with sorted keys and compact separators. The raw
digest proves byte identity; the canonical digest supports deterministic
semantic comparison. Evidence also retains the endpoint, parameters, status,
collection time, record IDs, source URL, and adapter version.

The adapter uses source `gamePk` and MLB team IDs to construct the existing
`MLBGame`, then emits independent immutable `ScheduleObservation`,
`GameStatusObservation`, and `PitcherObservation` values. Each game result has
an explicit `complete`, `partial`, or `rejected` outcome. Rejected results
cannot expose a Canonical Event or normalized observations. Results and issues
are sorted deterministically and round-trip through tagged JSON.

Parsing is deliberately partial-success. Missing optional venue, probable
pitchers, source update time, or paired doubleheader metadata creates stable
issues and incomplete component provenance without invalidating trustworthy
event identity. Missing or malformed `gamePk`, team identity, or required
timezone-aware start time withholds the event and all dependent observations
while retaining raw evidence. Same-`gamePk` schedule and pitcher changes create
new observations. Collection time is always preserved, but source timestamps
remain `None` unless `lastUpdated` is explicitly present and valid; collection
time is never substituted. Unsupported status affects only status evidence.
`explicit_lineage()` requires a named direct relation field and the related
`gamePk`; it never infers lineage from similarity.

## Kalshi MLB market evidence and valuation

PR7 adds `market_contracts.py`, `kalshi_mlb_adapter.py`, and
`market_valuation.py`. Explicit participant/date evidence and controlled
aliases—not ticker alone—reconcile Kalshi MLB markets. Ambiguous doubleheaders
and side labels fail closed. Metadata and book calls retain separate times and
digests inside one capture session.

Executable acquisition consumes side asks (or explicitly transformed
complementary resting bids) without extrapolating beyond depth. Exact-Decimal
valuation requires a named fee model and reports economics, partial fill, and
timing evidence. It has no recommendations, thresholds, Kelly, bankroll,
position, or wagering behavior. Production fees remain unresolved explicit
configuration; zero fee is a fixture model only.

The current Kalshi `orderbook_fp` response supplies `yes_dollars` and
`no_dollars` bid levels, not asks. Each derived offer preserves its provider
bid side, price, and quantity alongside the exact complement and labels the
transformation. Top-level quote fields remain direct metadata evidence.
Contradictory top-of-book components fail closed. Component timestamps and
digests remain separate; timing spread is reported without a freshness limit.
Valuation assumes USD and a $1 winning payout only after settlement evidence
establishes that economics. Non-open or depthless evidence cannot produce an
executable valuation.

The explicit read-only smoke command is `./venv/bin/python
smoke_kalshi_mlb.py MLB_FIXTURE.json --limit 10`. Tests and imports do not run it; it persists
nothing and accesses no portfolio or order endpoint.

## Outcome Evidence and Forecast Evaluation

`outcome_contracts.py` defines immutable provider-neutral Outcome Observations
and append-only Outcome History. `mlb_outcome_adapter.py` translates the
existing bounded `MLBStatsAPIResponse` and Canonical Event path; it creates no
second HTTP client. MLB Stats API is authoritative for MLB results. Other
provider results are not accepted as official Outcome Evidence.

The adapter preserves scheduled, in-progress, delayed, postponed, suspended,
final, cancelled, no-contest, forfeit, and unknown provider states. Finality is
accepted only from MLB status Evidence, never inferred from score, settlement,
market data, or a forecast provider. Ordinary, extra-inning, shortened, and
later-completed suspended finals can be authoritative; tied or contradictory
finals fail closed. Corrections append later observations, and
`latest_authoritative_final` remains a derived view.

`forecast_evaluation.py` implements versioned Policy
`mlb-winner-evaluation-eligibility-v1`. Every candidate Forecast/Outcome pair
produces an immutable eligibility decision. The forecast collection timestamp
must be strictly before scheduled start; equality is ineligible. Collection
time is Pops' Edge provenance, not provider publication time. Forfeits and
administrative rulings remain preserved but Policy-deferred. Eligibility is
state-independent: it consumes only the immutable Forecast Observation,
Outcome Observation, optional immutable Outcome History, and Policy version.
It does not inspect existing evaluations. Repeated inputs produce the same
decision and evaluation identities, while `ForecastEvaluationHistory` rejects
a duplicate pair on append. Chronology-sensitive decisions serialize the exact
material Outcome Observation IDs used by Policy; irrelevant observations do not
change identity, and the same canonical observation set is order-independent.

When Outcome History records a postponement or material reschedule, a forecast
that predates the postponement evidence is ineligible. A newly collected
forecast after that evidence and strictly before the revised start can be
eligible. If the earlier schedule chronology is absent, the decision is
indeterminate. Suspension is separate: unresolved suspension is ineligible,
but an authoritative later-completed suspended final remains eligible under
the ordinary strict-pregame rule.

An eligible pair produces one immutable Forecast Evaluation of the complete
two-participant distribution. The stored binary Brier definition is
`(p_realized - 1)^2`. Log loss is `-ln(p_realized)` at 50-digit Decimal context;
an exact zero probability for the winner is positive infinity, never silently
clipped. Positive infinity serializes as a tagged JSON object, never as a bare
non-standard JSON numeric token. Directional correctness requires a unique favorite. Calibration
buckets are `[0.0,0.1)` through `[0.8,0.9)`, with `[0.9,1.0]` closed at one.
The history summary reports count, mean Brier, mean finite log loss, explicit
finite and infinite log-loss counts, and directional counts for deterministic
PR9 validation; it is not Forecast Intelligence.
`summary` describes all stored evaluations for replay. Given immutable Outcome
Histories, `current_evaluations` selects evaluations tied to each latest
authoritative final, `superseded_evaluations` preserves older corrected-result
evaluations, and `current_summary` counts only the selected current set.
Ambiguous corrected-final chronology fails closed.

Run the offline inspection explicitly:

```bash
./venv/bin/python inspect_forecast_evaluation.py \
  tests/fixtures/mlb_outcome_cases.json \
  tests/fixtures/forecast_evaluation_inspection.json
```

The command performs no network or Kalshi access. PR9 does not change the
Opportunity Board. Forecast Intelligence begins in PR10; Forecast Policy,
Policy Forecast, market-relative evaluation, and wagering evaluation remain
deferred.

## Forecast Intelligence research boundary

`forecast_intelligence.py` implements provider-neutral Research Mode over an
explicit immutable selection of PR9 current Forecast Evaluations,
authoritative Outcome History when needed for that selection, an immutable
evaluation-window definition, and versioned intelligence rules. DRatings is the
sole currently implemented MLB Forecast Provider and demonstrates the
architecture without introducing provider-specific intelligence contracts or a
second provider.

The immutable `ForecastIntelligenceReport` implementation preserves
provider/domain, window, eligibility, evaluation and intelligence algorithm
identities; included, excluded, and superseded evaluation IDs; deterministic
input digest; coverage; Brier and finite/infinite log-loss results; calibration;
bounded segments and trends; sample-adequacy assessment; gaps; adverse evidence;
and limitations. It uses current corrected-final selection by default and never
silently uses all repository history or stores mutable cumulative totals.

This implemented symbol is a provider-level analytical precursor to the
canonical Comparative Performance Report. It does not yet provide the complete
Market-Benchmark-relative Comparative Performance required by the finalized
Product and Architecture.

Primary MLB calibration is an evaluation-level home-win view: every included
game contributes its published home-win probability once and a realized
home-win indicator of zero or one. Segment contracts separately identify
actual home/away results, strict-favorite wins/losses/ties, and home-win
probability bands. Directional accuracy divides correct calls only by games
having a unique strict favorite; an all-tie sample reports it as unavailable.
Aggregates, buckets, segments, adequacy, and proposal suggestions retain their
canonically ordered contributing Forecast Evaluation IDs.

Evaluation windows and explicit analysis-as-of boundaries are material
identity inputs because they select the analytical evidence set. Wall-clock
`generated_at` or `derived_at` records operational provenance only and does not
change report or proposal identity unless it is explicitly declared as the
analysis-as-of boundary. Filesystem time, irrelevant input ordering, and
unstated repository state are never identity inputs. Identical immutable
material inputs and algorithm versions reproduce identical analytical identity
and content regardless of rerun time.

The implemented `PolicyProposal` is immutable advisory Analysis tied to one
report and one immutable, versioned `PolicyHypothesis`. That PR10 hypothesis
describes the non-executable provider/model, eligibility, selection, weighting,
normalization, missing-provider, fallback, assumption, and domain rules being
evaluated. It is Research input or derived Analysis—not Evidence, a Forecast
Policy, or a Policy Forecast—and has no lifecycle authority. A proposal may
suggest a Product Owner action but cannot create, enter Shadow, activate,
replace, retire, or reject a Forecast Policy. PR11 owns the separate executable
Forecast Policy definition and Policy Forecast; PR12 owns governance records
and lifecycle transitions.

`PolicyProposal` is the current implementation precursor to the canonical
Policy Recommendation. The implemented `PolicyHypothesis` retains its
historical candidate-strategy semantics until PR19 aligns it with the Product
definition: a proposed operational strategy for exploiting one or more
empirically supported Market Edges. Neither implementation symbol should be
treated as though that migration has already occurred.

Proposal actions are derived by an explicit versioned suggestion rule from
adequacy, factual benchmark availability, comparisons, metrics, and
limitations. Missing benchmarks remain absent; deterministic reason codes
explain the advisory action without modifying production configuration.

> **Research never changes production. Governance changes production.**

Run the bounded inspection explicitly:

```bash
./venv/bin/python inspect_forecast_intelligence.py \
  tests/fixtures/forecast_intelligence_cases.json
```

The command consumes fixtures only. It performs no network, Kalshi, Opportunity
Board, governance, Forecast Policy, Policy Forecast, or Execution action.

## Forecast Policy production forecast boundary

`forecast_policy.py` implements three separate immutable PR11 contracts:

- `Forecast Policy`: a complete provider-neutral executable specification with
  domain/provider constraints and versioned compatibility, production
  eligibility, observation/provider selection, transformation, weighting,
  normalization, missing-provider, fallback, and output-validation stages;
- `Forecast Policy Execution`: one deterministic explicit batch context with
  scope/as-of boundary, candidate/included/excluded observation identities and
  reasons, identified event contexts and conflicts, event/output identities,
  statistics, warnings, and limitations; and
- `Policy Forecast`: the independently identified event-level canonical output
  of its specific execution, with complete input, context, and stage-decision
  provenance. It is not globally or production canonical.

Execution consumes supplied immutable Forecast Observations; it never discovers
events, fetches providers, or reads mutable production configuration. Each stage
has an ID, version, parameters, deterministic result, and limitations, without a
dynamic plug-in framework. PR9 historical Evaluation Eligibility is not reused
as PR11 production observation eligibility. The initial rule selects the unique
latest eligible observation before the explicit analysis-as-of boundary and
fails closed on a latest-timestamp tie rather than using input order.
Execution identity is derived from material inputs before output creation;
completed output IDs are reconciliation references only. Canonical execution and
forecast serialization omit wall-clock run time. Reason-code counts are
overlapping observation- and event-level occurrences and need not sum to a
population count.

The initial offline demonstration selects the latest eligible validated
DRatings MLB winner observation before an explicit analysis-as-of boundary,
applies identity transformation and weight `1.0`, validates the complete binary
distribution without silent correction, and fails closed with no fallback when
the provider is absent. This neither approves nor activates the policy. PR12
owns governance and lifecycle state and selects the production-authoritative
Forecast Policy. PR21, not PR11, will separately migrate Opportunity Analysis
and the Opportunity Board to governance-authorized Policy Forecast input.

Run the bounded fixture inspection with:

```bash
./venv/bin/python inspect_forecast_policy.py \
  tests/fixtures/forecast_policy_cases.json
```

The inspection consumes supplied fixtures only. It performs no provider,
market, governance, Opportunity Board, wagering, or network action.

> **Research never changes production. Governance changes production.**

## PR12 governance boundary

PR12 implements two immutable contracts and derived resolvers:

- `GovernanceRecord`: one append-only Product Owner decision governing exactly
  one immutable Forecast Policy, with deterministic Governance Scope, material
  `decision_effective_at`, Product Owner, rationale, limitations,
  schema/algorithm identity, and references to supporting Analysis;
- `GovernanceHistory`: an ordered immutable collection that rejects duplicate
  record IDs and supports deterministic current and historical replay; and
- derived lifecycle, production-policy, and Shadow-policy resolution. No
  lifecycle value is stored or mutated.

The supported decisions are `Research`, `Shadow`, `Production`, `Retire`, and
terminal `Reject`. Their derived lifecycle values are respectively `Research`,
`Shadow`, `Production`, `Retired`, and `Rejected`. Research and Shadow do not
grant production authority. Historical Policy Forecast evaluation and automated
Shadow measurement are not implemented and require separate architectural
approval. Retire withdraws authority while preserving historical Analysis.
Reject permanently closes that immutable policy; reconsideration requires a new
Forecast Policy.

Production resolution chronologically replays Governance Records and returns at
most one Forecast Policy per Governance Scope. The initial scope is the policy's
sport/competition/proposition tuple. A later Production decision selects a
policy and displaces prior authority in that scope; a later non-Production
decision removes authority only for the selected policy; earlier policies do not
resume implicitly. Non-Production decisions for other policies do not disturb
the selected policy. Missing or conflicting authority fails closed. Supporting
Policy Proposals, Forecast Intelligence Reports, and Policy Hypotheses remain
referenced non-executable Analysis rather than copied content or authority
sources.

Replay includes records effective at or before an explicit historical `as_of`
boundary and orders only by `decision_effective_at`. Operational timestamps,
record IDs, filenames, serialization order, and input order never resolve a
material tie. Same-time policy conflicts, simultaneous Production decisions in
one scope, policy/scope mismatch, unknown policy, missing effective time or
Product Owner, and any decision after terminal Reject fail closed.

The stable Product Owner ID—not the optional display name—is material to record
identity. Equivalent same-time records with the same policy, scope, decision,
effective time, and stable owner ID preserve their complete supporting record
set without conflict. Different same-time decisions conflict. Conflicts for a
current or candidate Production policy fail scope resolution closed; unrelated
Research/Shadow-only conflicts remain visible without removing otherwise
unambiguous authority. History construction canonicalizes a copied tuple,
append returns a new history, and duplicate IDs never mutate prior history.

Run the deterministic offline inspection with:

```bash
./venv/bin/python inspect_forecast_governance.py \
  tests/fixtures/forecast_governance_cases.json
```

PR12 adds governance contracts, replay, resolvers, bounded fixtures,
inspection, and focused tests only. It does not change Forecast Policy
execution, Opportunity Analysis, Opportunity Board, providers, market
valuation, wagering, or World Cup workflows. Subsequent work follows the
approved sequence in `docs/RELEASE_PLAN_v1.1.0.md`.

## Forward implementation boundaries

The remaining v1.1.0 sequence after implemented PR15 reporting is:

1. **PR16A — Standalone Probability Source Performance Methodology and Architecture:** define the documentation authority.
2. **PR16B — Standalone Market Benchmark Measurement Implementation:** implement deterministic derivation, Measurement, Coverage, performance, uncertainty, replay, and report integration.
3. **PR17 — Prospective MLB Research Operation and First Report:** collect durable prospective Evidence and produce the first real report.
4. **PR18 — Current Scientific Applicability and Policy Recommendation:** add deterministic applicability replay and non-authoritative recommendations.
5. **PR19 — Policy Hypothesis Alignment:** align `PolicyHypothesis` with one or
   more empirically supported Market Edges while keeping it non-authoritative
   and non-executable.
6. **PR20 — Forecast Intelligence Workspace:** implement the Product Owner's
   principal research and governance surface.
7. **PR21 — Policy Forecast Opportunity Integration:** migrate Opportunity
   Analysis and the Opportunity Board to governance-authorized Policy Forecasts.
8. **PR22 — v1.1.0 Integration and Release Readiness:** validate the integrated
   lifecycle, compatibility, documentation, and release gates.

The Release Plan owns detailed scope, dependencies, exclusions, and gates. Do
not infer later-PR behavior into an earlier implementation.

## Forecast Intelligence research-contract inspection

`forecast_research_contracts.py` implements the immutable PR13
`ResearchProtocol`, `EdgeClaim`, `ResearchReview`, `MarketEdge`, and
`DriftSurveillance` contracts and their bounded supporting values. It uses the
shared tagged serializer, exact Decimal rule parameters, UTC-normalized
content-addressed identity, explicit scheduled and material-Drift obligation
coverage, and pure caller-supplied graph validation.

Run the deterministic offline inspection with:

```bash
./venv/bin/python inspect_forecast_research_contracts.py \
  tests/fixtures/forecast_research_contract_cases.json
```

The module does not implement the canonical Comparative Performance Report,
Current Scientific Applicability replay, Policy, Governance, Workspace,
Opportunity Analysis, or production behavior. Those boundaries remain assigned
to later release-plan PRs.

## Comparative research inspection

`forecast_comparative_research.py` implements the PR14 Evidence → Measurement
→ cumulative Forecast Intelligence path. It preserves failed source captures,
timestamp-derived pair-specific synchronization, prospective classifications,
append-only Snapshot corrections, authoritative Forecast and Outcome lineage,
rule-derived eligibility and exact Coverage identities, deterministic paired
bootstrap, extended-real Log Loss, and version-2 Calibration.

Run its synthetic offline inspection with:

```bash
./venv/bin/python inspect_forecast_comparative_research.py \
  tests/fixtures/forecast_comparative_research_cases.json
```

The module produces no time-bounded Comparative Performance, Comparative Drift
Analysis, canonical Comparative Performance Report, Research Review conclusion,
Current Scientific Applicability, Policy, Governance, Workspace, Opportunity
Analysis, or production authority.

## Comparative performance reporting inspection

`forecast_comparative_reporting.py` implements the PR15 Forecast Intelligence
layer: rolling-days version-2 bounded Comparative Performance, deterministic
historical replay, brier-deterioration version-2 comparative Drift analysis,
complete Protocol-level Comparative Performance Reports, and exact projection
to the existing PR13 report reference. Run its offline inspection with:

```bash
./venv/bin/python inspect_forecast_comparative_reporting.py \
  tests/fixtures/forecast_comparative_reporting_cases.json
```

The implementation creates no Research Review conclusion, Current Scientific
Applicability, Policy Recommendation, Governance, Workspace, Opportunity
Analysis, mutable workflow state, or production authority.

The supporting `ProtocolClaimSet` contract and replay helper live in
`forecast_research_contracts.py`. Report completeness is derived from the
authoritative Claim Set effective at the report boundary; the analytical
children cannot define their own claim universe.

### Forecast Intelligence Workspace boundary

The future Forecast Intelligence Workspace is a deterministic, read-only,
locally generated projection and the principal research and governance surface.
It consumes Forecast Intelligence; it is not Forecast Intelligence itself. It
may orchestrate existing selection, Forecast Intelligence, advisory, and
Governance replay services, but it must not copy or fork their analytical or
transition rules.

All sections share one explicit immutable context covering domain, research and
governance boundaries, Probability Source scope, Policy Hypothesis scope, and
Forecast Policy scope. Supplied artifacts must be validated fail-closed against
that context. Incompatible identities, versions, scopes, or chronology remain
visible as exclusions and diagnostics rather than being silently blended.

The Workspace surfaces Research Protocols, Comparative Performance and
Comparative Performance Reports, Edge Claims and Market Edges, Research Reviews
and Drift Surveillance, Policy Recommendations and aligned Policy Hypotheses,
Product Owner Governance context, diagnostics, and provenance. A governance
decision draft remains explicitly non-authoritative, cannot create a Governance
Record, and cannot determine production authority.

The Workspace owns orchestration, organization, and presentation only. It adds
no authoritative business state, mutable cache, database, browser persistence,
provider collection, Forecast Policy execution, Opportunity Analysis, wagering,
or other production behavior. Identical material inputs and context must produce
substantively identical output; presentation-only generation metadata must not
alter the projection's substantive identity.

Historical Policy Forecast evaluation and automated Shadow measurement remain
unimplemented potential analytical capabilities. They are not implicit
Workspace responsibilities and require separate architectural approval.

## Opportunity Board manual workflow

`opportunity_board.py` defines derived Position, Opportunity, and BoardEntry
presentation values and renders the sortable HTML board. The required position
CSV is an authoritative current open-position summary, not transaction
history. Each active row requires `Provider` (`kalshi`), `Provider Market ID`,
`Proposition ID`, `Canonical Event ID`, `Side` (`yes` or `no`), `Open
Quantity`, `Average Entry Cost`, and optional `Captured At`; a headers-only
file authoritatively means no positions. Duplicate summaries for one
Series/side are contradictory. Separate YES and NO summaries are preserved as
offsetting components and must map to their corresponding valued rows. Missing
position input, unknown references, malformed sides, and incompatible event or
proposition mappings fail closed. Transaction reconstruction, realized P/L,
and lot accounting are outside this boundary.

`kalshi_activity_positions.py` accepts the downloaded mixed Activity CSV but
derives positions only from `Trade` rows. Opposite-side trades reduce the
opening side, settlements remove the market, and `Order` rows never create
exposure. It requires an exact reconciled provider market, preserves entry and
exit fees separately, records the source digest, and writes the normalized
summary consumed by the board. `collect_kalshi_mlb_orderbooks.py` performs only
an explicitly invoked bounded public metadata/order-book collection and
retains an actual timestamp and digest for every response.

Liquidation value consumes PR7's preserved direct provider bids for the held
side in price order. The board reports held, executable, and unpriced quantity;
gross proceeds; average and marginal exit price; original total cost basis;
and P/L and return only for the executable quantity. It never extends the top
bid beyond its visible quantity. Closed, suspended, or depthless positions
retain cost and identity while liquidation value and P/L remain unavailable.

`run_opportunity_board.py` consumes a temporary local integration bundle with
schema `pops-edge-opportunity-bundle-v1`, a fixed `generated_at` timestamp, and
`cases`. Unknown top-level/case fields, unsupported versions, credentials,
duplicate entry identities or forecast/market/side records, and malformed or
incompatible contracts fail closed. Each case supplies display game and
schedule metadata plus tagged Forecast Observation and Market Adapter Result
dictionaries, requested acquisition side and quantity, and an explicit
fixture fee input. The runner validates compatibility, invokes PR7 valuation,
creates `Opportunity_Board.html`, and prints concise counts. It performs no
provider collection or domain persistence. Run it explicitly:

```bash
./venv/bin/python run_opportunity_board.py evidence_bundle.json \
  --positions kalshi_open_positions.csv --output Opportunity_Board.html
```

Update forecast snapshots, MLB facts, and Kalshi market evidence separately
before preparing this non-persistent PR8 integration bundle. The board displays
event start, forecast capture, market-book capture range, optional position capture, and
market component timing spread without calling any observation "current" or
applying freshness thresholds. Ambiguous, rejected, partial, missing, and
non-executable inputs remain visible with inline diagnostics. Recommendation
policy, portfolio optimization, bankroll, Kelly sizing, provider automation,
durable persistence, and wagering remain deferred.

Prepared operational validation bundles request one contract per row as a
neutral analysis quantity. That value is neither inferred from activity nor a
position-sizing instruction.
`select_market_results` derives two views from immutable history: latest
strictly pregame (`captured_at < scheduled_start`) for forecast comparison and
latest overall for liquidation. Equality is in-play. Without pregame evidence,
gross edge and return are suppressed while latest-book liquidation remains
available. The zero-fee model is displayed only as gross-before-fees analysis;
production net EV is unavailable. Board status precedence is rejected,
ambiguous, settled, cancelled, suspended, in-play, partial, missing depth,
non-executable, then complete. Canonical Event participant order supplies the
away-first/home-second presentation; provider source order is not rewritten.
Dual-date validation keeps August 2 as the complete pregame/no-position case
and August 1 as the in-play/position/settlement/rejection case. August 2 MLB
facts come from one bounded `MLBStatsAPIClient.fetch_schedule` request, not a
second schedule implementation. A normalized headers-only output is
authoritative only after the full mixed activity export reconstructs to zero
open positions.

The offline fixture is `tests/fixtures/mlb_stats_api_schedule.json`, and
`tests/test_mlb_stats_api.py` covers client failures, identity, schedules,
status, pitchers, lineage, partial success, raw hashing, serialization, and
ordering. The separately invoked read-only smoke path is:

```bash
./venv/bin/python smoke_mlb_stats_api.py YYYY-MM-DD [--game-pk GAME_PK]
```

It is intentionally excluded from automated validation and must not be run
without explicit authorization. It requires a date, prints concise identifiers,
outcomes, and issue codes rather than payloads, writes nothing, and exits
nonzero on transport failure or unsafe rejection. PR5 does not persist raw
payloads or normalized contracts and does not schedule collection.

## Workflows

`update_all.sh` is the combined update workflow. It changes into the project directory, activates `venv/` when needed, then runs the standalone workflows in order:

1. `./update_wagers.sh`
2. `./update_worldcup.sh`

Keep this script thin. The wager and World Cup scripts remain usable on their own, so shared behavior should stay in the underlying Python modules or the standalone scripts unless there is a specific reason to coordinate it in `update_all.sh`.

`wcup` is the main board refresh workflow. It should run the same sequence as `update_worldcup.sh`:

1. `process_silver.py` normalizes the latest Silver forecast CSV into `Silver_Current.xlsx`.
2. `kalshi_pull.py` pulls current Kalshi World Cup markets into `Kalshi_Current.xlsx`.
3. `process_silver_futures.py` normalizes the latest Silver futures CSV into `Silver_Futures_Current.xlsx`.
4. `build_value_board.py` combines Silver probabilities, Kalshi prices, active wager exposure, and portfolio summaries into `WorldCup_ValueBoard.xlsx`.
5. `build_futures_value_board.py` creates `WorldCup_Futures_ValueBoard.xlsx`.
6. `build_ladder_board.py` creates `WorldCup_Ladder_Board.xlsx` from positions with positive remaining contracts.
7. `build_web_betsheet.py` creates `WorldCup_ValueBoard.html`.
8. `build_web_futures_betsheet.py` creates `WorldCup_Futures_ValueBoard.html`.
9. `build_web_ladder_board.py` creates `WorldCup_Ladder_Board.html`.

`update_worldcup.sh` refreshes both match and futures outputs plus the active-position Ladder Board. It archives both Silver workbooks and all board workbooks, copies Excel boards and HTML dashboards to the existing iCloud World Cup folder, and opens the three HTML boards when run standalone. `update_all.sh` suppresses the child-script open steps, then opens `World_Cup_Bet_Log.html`, `WorldCup_ValueBoard.html`, `WorldCup_Futures_ValueBoard.html`, and `WorldCup_Ladder_Board.html` exactly once. Its success notification reports wagers imported, match candidate bets, and futures candidate bets; unavailable workbook counts do not fail an otherwise successful run.

`build_futures_value_board.py` filters out `KXWCGAME-` match markets and classifies futures markets from the event ticker, market ticker, game, subtitle, and market title. `kalshi_pull.py` includes these World Cup event patterns:

```text
KXWCGAME-*              match winner markets
KXWCROUND-26RO16-*      Round of 16 qualifier markets
KXWCROUND-26QUAR-*      Quarterfinal qualifier markets
KXWCROUND-26SEMI-*      Semifinal qualifier markets
KXMENWORLDCUP-26-*      World Cup winner markets
```

The outright winner markets use two-letter ticker suffixes, such as `KXMENWORLDCUP-26-AR`, but include team names in `yes_sub_title`; the futures board matches them by normalized outcome name.

`update_wagers.sh` refreshes Bet Log outputs from the latest Kalshi activity export. It activates `venv/` when needed, runs `import_wagers.py`, builds `World_Cup_Bet_Log.html` with `build_web_betlog.py`, prints a short wager summary, and opens the web Bet Log. Closing Price is manually entered in `World_Cup_Bet_Log.xlsx`; `import_wagers.py` preserves it and automatically calculates CLV and CLV % when Closing Price is present.

After placing a wager, download Kalshi Activity -> All -> This Month, then run `./update_all.sh` to refresh wagers first and then refresh the World Cup board. You can still run `./update_wagers.sh` or `./update_worldcup.sh` independently for narrower updates.

## Pipeline Dependencies

The pipeline is file-based:

```text
data-*.csv -> process_silver.py -> Silver_Current.xlsx
Kalshi API -> kalshi_pull.py -> Kalshi_Current.xlsx
Silver_Current.xlsx + Kalshi_Current.xlsx + World_Cup_Bet_Log.xlsx -> build_value_board.py -> WorldCup_ValueBoard.xlsx
WorldCup_ValueBoard.xlsx -> build_web_betsheet.py -> WorldCup_ValueBoard.html
futures CSV -> process_silver_futures.py -> Silver_Futures_Current.xlsx
Silver_Futures_Current.xlsx + Kalshi_Current.xlsx + World_Cup_Bet_Log.xlsx -> build_futures_value_board.py -> WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.xlsx -> build_web_futures_betsheet.py -> WorldCup_Futures_ValueBoard.html
Kalshi-Recent-Activity-*.csv + match/futures Value Boards + Kalshi_Current.xlsx + prior World_Cup_Bet_Log.xlsx -> import_wagers.py -> World_Cup_Bet_Log.xlsx
World_Cup_Bet_Log.xlsx -> build_web_betlog.py -> World_Cup_Bet_Log.html
```

Shared filenames, sheet names, archive paths, and common column names live in `config.py`.

`import_wagers.py` writes one unified Bet Log for match and futures wagers. `Market Type` distinguishes `Match` from `Futures`; futures rows populate `Stage`, `Team`, and the human-readable YES proposition in `Outcome`, while `Match` and `Match Date` remain blank. Match rows retain their existing match fields, and `Team` is blank for tie contracts.

Enrichment combines `WorldCup_ValueBoard.xlsx` and `WorldCup_Futures_ValueBoard.xlsx` by `market_ticker`. `Kalshi_Current.xlsx` is the fallback source for proposition names, including champion tickers with two-letter suffixes. The importer normalizes match dates after reading prior manual values and current match Value Board values. The selection order remains prior manual value, current Value Board value, then ticker-derived fallback. It also carries forward manually entered Closing Price from the prior wager log, calculates CLV and CLV % for BUY YES and SELL YES positions, and leaves CLV fields blank when Closing Price is blank unless prior CLV values are available as a fallback.

The wager log records `Exit Contracts` and `Remaining Contracts`. Settlements
set remaining contracts to zero; early exits subtract exited contracts from
entry contracts. The Ladder Board accepts only `Open` and `Partially Closed`
rows with positive remaining contracts.

## Ladder Board

`build_ladder_board.py` combines active match and futures wagers with their
current Value Board rows. BUY YES positions use YES entry/current prices and
Silver probability. SELL YES positions are represented as NO positions using
one minus the YES entry, ask, and Silver probability.

For positive remaining edge, the three sell tiers are entry plus half the edge,
Silver fair value, and fair value plus 15 cents. Prices use half-up cent
rounding and are capped at 99 cents. Contracts are allocated 30% / 30% /
remainder, so the tiers sum to the open whole-contract count. Rows are ordered
by urgent/near status, descending current edge, event, market, ticker, and side.
`build_web_ladder_board.py` renders the same ordered data and supports both
empty and populated boards.

`kalshi_pull.py` retries timeouts, connection/incomplete-response failures, and
HTTP 429/500/502/503/504 responses with bounded backoff. Each retry repeats the
same cursor page so pagination does not skip events.

## Value Board Workbook

`build_value_board.py` writes the existing Bet Sheet outputs unchanged, then adds a `Portfolio` worksheet with four stacked sections:

```text
Portfolio Summary
Open Positions
Exposure by Team
Exposure by Match Date
```

The Portfolio worksheet reads active wagers from `World_Cup_Bet_Log.xlsx`, using `Open` and `Partially Closed` statuses, and enriches them with match, outcome, team, Silver probability, and current bid/ask data from the merged Value Board. BUY YES current value uses the current Yes Bid; SELL YES current value uses `1 - Yes Ask`.

## Futures Value Board Workbook

`build_futures_value_board.py` writes the same core workbook tabs as the match board:

```text
Bet Sheet
Run Metadata
Candidates
Value Board
Silver Normalized
Kalshi Normalized
Definitions
```

The futures Bet Sheet columns include `Stage`, `Team`, `champion_proxy_candidate`, `strong_champion_proxy`, `Action`, `Silver`, `Market Price`, `Edge`, `ROI`, `Quarter Kelly`, `proxy_kelly_dollars`, `proxy_contracts`, the four ladder price/contract pairs, `ladder_expected_return`, `ladder_expected_profit`, `Stake on $500`, `Bucket`, `Volume`, `event_ticker`, `market_ticker`, `Position`, `Current Action`, `Entry Price`, `Current Value Change`, `Stake`, and `Status`. It uses the same `BANKROLL = 500`, `MIN_EDGE = 0.05`, and A/B/C bucket thresholds as `build_value_board.py`, but divides full Kelly by four rather than two.

`champion_proxy_candidate` is `YES` when a team has positive BUY edge in R16, quarterfinal, semifinal, and Champion markets. `strong_champion_proxy` adds the requirement that Champion BUY edge is at least 35% of average R16/QF/SF BUY edge. Final markets are classified when available but are not part of either gate.

`proxy_kelly_dollars` is shown only for Champion Proxy teams. It keeps the ordinary Champion Quarter Kelly stake and adds 60% of the R16/QF/SF Quarter Kelly stakes, reflecting that Champion is being used as a proxy for several correlated advancement bets.

Champion Proxy sell ladders use the Champion BUY price as entry, allocate Proxy Kelly into contracts, then suggest four resting sell orders at 1.5x, 2.25x, 3.25x, and 4.5x entry. Contract allocation is 30% / 30% / 20% / remainder. The individual ladder price/contract columns stay in Excel for auditing, while the futures HTML shows a compact `proxy_sell_ladder` summary plus expected return/profit.

Active futures wagers come from the unified `World_Cup_Bet_Log.xlsx`, match on `market_ticker`, and include `Open` and `Partially Closed` statuses. The futures HTML view omits `event_ticker` to reduce width while retaining `market_ticker` and the active-position fields.

Silver futures CSV detection requires the columns `Team`, `R16`, `Qtr`, `Semi`, `Final`, and one of `Champ 🏆`, `Champ`, or `Champion`. The processor archives the selected source CSV under `archive/silver_futures_raw/` and the processed workbook under `archive/silver_futures_processed/`.

## Expected File Locations

The project expects to live at:

```text
~/pops-edge
```

Silver forecast downloads may be in either:

```text
~/Downloads/data-*.csv
~/pops-edge/data-*.csv
```

`process_silver.py` requires the match columns `Date`, `Team`, `Win`, `GF`, `Opponent`, `Win.1`, `GF.1`, and `Draw`. It selects the newest CSV with that schema and only archives other match-schema CSVs, so futures exports remain available to the futures processor.

Silver futures downloads may be named `data-*.csv` or include `futures` in the filename, but must have the futures columns listed above. They may be in either `~/Downloads` or `~/pops-edge`. `process_silver_futures.py` selects the newest CSV with the futures schema and skips newer match-schema files.

Kalshi activity exports may be in either:

```text
~/Downloads/Kalshi-Recent-Activity-*.csv
~/pops-edge/Kalshi-Recent-Activity-*.csv
```

Generated files are local outputs and should not be committed:

```text
Silver_Current.xlsx
Kalshi_Current.xlsx
WorldCup_ValueBoard.xlsx
WorldCup_ValueBoard.html
Silver_Futures_Current.xlsx
WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.html
WorldCup_Ladder_Board.xlsx
WorldCup_Ladder_Board.html
World_Cup_Bet_Log.xlsx
World_Cup_Bet_Log.html
archive/
```

## Tests

Run the full test suite with:

```bash
bash -n update_all.sh
bash -n update_wagers.sh
bash -n update_worldcup.sh
./venv/bin/python -m unittest discover -s tests
./venv/bin/python -m py_compile process_silver_futures.py build_futures_value_board.py build_web_futures_betsheet.py
```

Tests use temporary directories and sample fixtures under `tests/fixtures/` so they do not overwrite live workbooks. Silver processor tests include mixed match/futures downloads and verify that each processor selects the newest valid file for its own schema.

`tests/test_event_contracts.py` validates canonical MLB identity, team mappings,
doubleheaders, postponement and replacement semantics, suspension/resumption,
missing and changed pitchers, conflicting source observations, fail-closed
reconciliation, immutability, and deterministic serialization round trips.

`tests/test_forecast_contracts.py` and
`tests/fixtures/forecast_contract_cases.json` validate the provider/model/version
hierarchy, exact published probabilities, precision-aware distributions,
assumptions, timestamps, validation and disposition, immutable revision
relationships, matched/ambiguous/rejected reconciliation, neutral collection
timing, canonical serialization, and round trips entirely offline.

The Value Board pipeline test checks the Portfolio worksheet section layout, open-position enrichment, summary totals, and team/date exposure rollups while preserving the existing Bet Sheet assertions. Futures tests cover Silver futures processing, a champion edge example, an advancement edge example, and the generated sortable futures web Bet Sheet. Wager tests cover Match Date normalization, Round-of-16 settlement, two-letter champion ticker enrichment, and the generated sortable unified web Bet Log.

## Git Workflow

Use small commits. Before committing, run tests and inspect staged files:

```bash
./venv/bin/python -m unittest discover -s tests
git status
git diff --stat
git diff --cached --stat
```

Commit source, docs, tests, and fixtures. Do not commit generated workbooks, HTML reports, archives, virtualenvs, downloaded activity files, lock files, or secrets.
