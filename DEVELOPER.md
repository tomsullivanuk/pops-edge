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
historical candidate-strategy semantics until PR20 aligns it with the Product
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
Forecast Policy. PR22, not PR11, will separately migrate Opportunity Analysis
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

## Standalone Market Benchmark inspection (PR16B)

Run the deterministic provider-neutral PR16B inspection with:

```bash
./venv/bin/python inspect_forecast_standalone_performance.py \
  tests/fixtures/forecast_standalone_performance_cases.json
```

This uses synthetic offline Evidence only. It reports the three standalone
population levels, both Coverage reconciliations, cumulative and `(start, end]`
performance, Calibration/WACE, deterministic uncertainty, and report references.
It makes no scientific conclusion and performs no provider access or operation.

Capture-boundary eligibility is evaluator-owned and replays the prospectively
available population context. Outcome histories select the authoritative final
at each boundary, and Measurements are resolved by both Snapshot and Outcome
identity so corrected and historical versions may coexist. Time-bounded replay
requires complete timezone-aware schedule authority. Canonical report v2 uses
typed references to reproduced v2 paired cumulative, bounded, and Drift
authorities; unrestricted child identifiers are not accepted.

Prospective population eligibility is frozen exactly at the capture boundary;
Coverage calculates due/not-due independently at each analysis boundary from
complete Schedule Evidence. Forecast-backed replay reconstructs evaluation
eligibility and `ForecastEvaluation` from the captured observation and selected
Outcome. Paired v2 aggregation filters the complete Measurement registry by the
exact Edge Claim, so multi-challenger Claim Sets remain isolated. Aggregated
market bounds retain every canonically ordered equal-price contributing level,
including its direct or derived Evidence provenance.
Snapshot replay also reconstructs schedule and target-capture authority before
using any source capture. Coverage registries are isolated by exact Protocol
generation, and paired synchronization is recomputed from the two captured
Evidence timestamps and the Protocol rule rather than trusted as caller input.
Snapshot corrections resolve their immediate predecessor, preserve all
scientific capture history, and permit changes only to explicit correction
metadata and provenance. Direct Coverage construction now receives the typed
Market, Forecast, evaluation, and Outcome registries and reproduces the complete
capture-to-Measurement chain before assigning `successfully-measured`.
The same Snapshot-authority replay now governs direct paired and Coverage
construction, and Market Evidence must match the Protocol benchmark provider,
Market Series, and native provider-market identity.

## PR17A acquisition and replay boundaries

PR17A is documentation authority only. Kalshi is the sole Probability Source
for two separate 2026 MLB regular-season game-winner standalone Protocols. Both
fix the home-team YES proposition as authoritative; away-team markets are
diagnostic and cannot repair or influence derivation or population membership.
MLB Stats API owns schedule, state, and Outcome facts.

These are `StandaloneProbabilitySourceProtocol` siblings, not empty-challenger
uses of implemented comparative `ResearchProtocol`/`ResearchProtocolV2`.
Existing comparative contracts and all PR16B v1/v2 identities remain unchanged.
PR17B1 implements the standalone Protocol and canonical
`ProbabilitySourcePerformanceReport`; the latter references exactly one
compatible cumulative and applicable time-bounded performance plus Coverage,
uncertainty, limitations, and provenance and never requires Claim Sets or pairs.

The retrospective Protocol covers rule-derived ordinary games before the future
activation boundary. Its collector will select the latest real one-minute candle
strictly within `(T-6h-5m, T-6h]` only when that candle has both home-team YES
bid and ask closes. Treat these as same-candle aggregates, never simultaneous
quotes, positive depth, or executable spread. Do not enable synthetic
continuity, fallbacks, null filling, away-side substitution, or late repair.
Persist the response as `HistoricalMarketCandleObservation`, including complete
returned bid/ask/transaction OHLC and distinct retrieval/effective times. Derive
with `HistoricalCandleProbabilityDerivation`. Never pass candle Evidence to
`MarketProbabilityDerivation` or represent it as `MarketObservation`.
Freeze the retrospective population, selection, representation, scoring,
Coverage, and report rules before querying the archive or calculating results.
This precommitment does not make acquisition prospective. Never use the result
to repair or enter a prospective population or paired Comparative Performance.
Preserve archive availability, survivorship, provider revision, timestamp,
schedule-history, aggregation, and non-simultaneity limitations.

The prospective Protocol includes every schedule-derived opportunity at or
after activation. It has exactly five slots: slots 0–3 are half-open one-minute
intervals from `target_at` through minute 4, while slot 4 is
`[target_at + 4m, target_at + 5m]`. Exact equality at the upper endpoint belongs
to slot 4; later acquisition is prohibited. The first invocation in a current
slot may execute at most one provider call only if no earlier slot succeeded.
It preserves actual acquisition time and exact target distance, never backdates
or catches up a missed slot, and is idempotent within a slot.
Append deterministic non-acquisition `missed` dispositions for earlier elapsed
unresolved slots. Select the earliest successful slot; after the inclusive
endpoint mark all unresolved slots missed, acquire nothing, and append one idempotent terminal
failure if no slot succeeded. Preserve every slot disposition. Postponements, reschedules,
doubleheaders, suspensions, cancellations, ambiguous mappings, and operational
failures remain explicit; reschedules create new opportunities and never rewrite
prior Evidence.

PR17B2 implements one bounded application CLI with explicit acquisition times.
It owns discovery, due-attempt calculation, fixture-safe acquisition,
validation, atomic persistence, failure dispositions, daily Outcome
reconciliation, backup invocation/status, and diagnostics. A thin `launchd`
wrapper may invoke it periodically but owns no scientific semantics and does not
wake the Mac. Late, asleep, or offline execution produces visible failure.

Raw bodies and versioned append-only manifests belong outside Git in a local
content-addressed archive. Writes must be atomic and duplicate-safe; semantic
content conflicts fail closed; interrupted writes are invalid. Scientific
identity excludes paths, host/user identity, filesystem timestamps, scheduler
identity, and incidental ordering. A derived index is rebuildable and
non-authoritative. One digest-verified secondary copy protects completed objects
and manifest material, but primary persistence alone determines capture success;
backup lag and health are Operations diagnostics.

The operational entry point is `operate_forecast_standalone_research.py` with
`acquire-schedule`, `acquire-classification`, `acquire-retrospective`,
`capture-prospective`, `reconcile-outcomes`, `sync-secondary`, `rebuild-index`,
`status`, `preflight`, and `inspect`. Acquisition accepts an explicit offline
fixture transport in PR17B2; no live client is selected or invoked. Stable exit
categories are 0 success, 2 not ready, 3 integrity failure, 4 configuration
error, and 5 operational failure. JSON and terminal diagnostics derive from the
same typed result. Configuration may set deployment paths, endpoint selection,
bounded retries/timeouts, lock wait, logs, and scheduling only.

PR17C2 adds the activated CLI commands `refresh-retrospective-supporting` and
`acquire-retrospective`. Supporting batches require explicit inclusive ISO date
bounds, contain at most 31 completed Eastern dates, and preserve every exact MLB
page plus both completely paginated Kalshi MLB catalog partitions. Candle
acquisition requires an explicit maximum of 1–100 pending opportunities. It
retrieves the current public historical cutoff once, routes each settled market
by its preserved settlement timestamp, requests only the strict five-minute
one-minute-candle interval, and performs no fallback or synthetic continuity.
These commands are manual and are not added to the PR17C1 scheduler group.

Retrospective supporting acquisition persists each bounded MLB response, the
cutoff response, and every catalog page immediately as non-authoritative
supporting-session material. Only a complete manifest-last envelope may bind
those pages to scientific contracts. Cross-partition duplicates are selected
solely by the preserved cutoff rule: settlement before the cutoff is historical;
equality and later settlement are live. Failure output and heartbeats count all
calls attempted through the failure point; partial sessions remain inspectable
but cannot satisfy replay or Coverage.

Scientific authority is atomic at the complete retrospective supporting-session
boundary. Provider acquisition bundles inside a session remain non-authoritative
until exactly one valid session-completion envelope references both providers,
the cutoff, every page, the derived unions and contracts, chronology, and call
count. `complete-retrospective-supporting-session --session-id ...` performs a
zero-network, append-only completion from verified archived session pages; it
never rewrites, deletes, or promotes an incomplete or conflicting session. One
authoritative completion verifier is shared by replay, inspection, and archive
completion. It validates the exact session/provider identities, complete page
sets and chronology, cutoff lineage and reconciliation, union and contract
digests, and exact call accounting. Repeating completion for an already valid
session is a zero-write no-op that returns the existing manifest identities;
an invalid or duplicate completion fails closed.

Previously completed retrospective authority may use
`kalshi-mlb-explicit-rules-schedule-instant-3`. Its MLB multi-date component is
`mlb-explicit-reschedule-lineage-1`: byte-identical repeated `gamePk` records
deduplicate, while materially different records require one explicit,
chronologically forward, non-branching reschedule lineage with stable season,
sport, competition, and oriented participants. Preserve all raw pages and both
postponed and successor observations; never use page order, dictionary order,
description text, or last-record-wins selection. Reconciliation requires an
explicitly binary market, structured YES, and a narrow settlement-rule template
that names the winner, opponent, professional-baseball matchup, original local
date/time, and supported New York timezone. Rule participants and the aware
instant must exactly equal MLB authority. A repeated NO label is a proposition
label and becomes the complement only after that proof. Expiration and close
times remain metadata. Never fall back to participant-only matching.
Retrospective ordinary-game eligibility uses valid
classification, regular-season phase, and `ordinary_game`; preserve `game_type`
as provider evidence without imposing a second spelling gate. The only approved
archive correction reason is `pr17c2-settlement-rule-reconciliation-eligibility-v2`.

New supporting sessions use
`kalshi-mlb-explicit-rules-schedule-instant-4` with
`provider-pages-canonical-union-3` and
`mlb-explicit-schedule-evolution-lineage-2`. Resume fields must be reciprocal
and must never cross-match reschedule fields. Preserve both final snapshots,
use the original official date for the only opportunity, and carry
`explicit-mlb-resume-lineage` in classification so retrospective eligibility
and candle selection exclude the event without fabricating a Suspended status.
Correction is zero-network and append-only: preserve the root completion, reuse
its pages, publish new versioned bundles, then publish exactly one unbranched
manifest-last supersession.

`refresh-retrospective-supporting` alone uses bounded per-logical-page transport
retries for MLB schedule pages, the Kalshi historical cutoff, and historical
and live catalog pages. The request endpoint, encoded cursor/date, partition,
and position are identical on every attempt. The fixed policy is 3 attempts,
5 seconds each, backoffs of 1 and 2 seconds, a 20-second total envelope, and a
2-second `Retry-After` cap. Timeout, connection failure, HTTP 429, 5xx, and a
late response with actual status 200, 429, or 5xx are retryable. Late redirects,
oversized responses, and non-rate-limited client rejections are not retryable.
A late response keeps its actual chronology, status, and permitted bytes under
`late-response`, but it is never validated or admitted as the page success.
Malformed, incomplete, oversized, or redirected responses,
client rejections, secret or validation failures, and archive, pagination,
reconciliation, or scientific failures stop after one attempt. Schema-2 pages
preserve complete attempt chronology and safe raw bodies while counting every
call; a terminal failure is durable and non-authoritative. Legacy schema-1
sessions replay unchanged.

Schema-2 separates observed chronology from governed scheduling. Preserve each
trusted-clock attempt start and completion unchanged. Record null
`retry_scheduled_at` for attempt 1 and, for later attempts, derive it exactly as
the prior observed completion plus `max(policy backoff, bounded Retry-After)`.
An observed retry may start later but never earlier; its lag remains evidence.
Verification adds no tolerance and enforces each five-second request bound and
the twenty-second observed first-start-to-terminal envelope from
`RETROSPECTIVE_SUPPORTING_RETRY_POLICY`. The exact replay verifier must accept
the complete prospective session envelope before manifest-last completion is
written; the CLI must not report success for a completion replay would reject.
If an older immutable completion nevertheless fails that verifier, reject that
session locally: it contributes no bundles or contracts, remains named in
inspection with `rejected_supporting_sessions`, and cannot poison replay of an
independent valid session. Missing or corrupt archive objects remain globally
blocking. Verified preserved pages from a different session may still be
completed archive-only with zero provider calls.

Each primary and secondary path must include `dry-run/<namespace>` (or, after a
future authorized activation, `activated/<namespace>`). Mutation is prohibited
for activated mode in PR17B2. Every mutation first takes the namespace advisory
lock; temporary `.partial` files are ignored and reported. The three wrapper
groups in `operations/launchd/` contain no timing, retry, repair, activation, or
scientific logic.

`capture-prospective` accepts configuration only. The library replays the exact
configured Protocol plus archived activation, Schedule, classification,
eligibility, opportunity, and Market Series authority under its namespace lock,
then reads the actual timezone-aware execution clock. Tests inject a fake clock
directly; no normal CLI time override exists. The prospective wrapper contains
no event, market, opportunity, Protocol, target, slot, or time value.

Prospective chronology separates discovery, the fresh trusted request start
immediately before transport, and request completion. Request start fixes
`slot` and `invocation_at`; completion fixes `effective_at` and manifest
acquisition time. Boundary-crossing completion persists one typed disposition
in the start slot and cannot trigger an automatic second call.
Validate provider `collected_at` inside the inclusive request interval within
the acquisition-classification boundary. Chronology-invalid responses must use
the typed captured-invalid path, retain permitted raw bytes and completion-time
manifest chronology, and must not register valid Market Evidence.
Decode provider-supplied PR17 contracts only through the narrow adapter helper.
It translates JSON syntax, missing/type-shape, and repository `ContractError`
validation failures into sanitized provider-data dispositions. Do not broaden
that boundary to archive, clock, invariant, runtime, or unexpected exceptions.
The predecoder must keep parity with all reserved markers in the authoritative
shared decoder, require exact scalar-marker dictionaries, reject conflicting or
duplicate tags, validate finite ordinary Decimals and aware datetimes, and walk
nested lists/objects under a deterministic depth limit without coercion.
After marker validation, `_validate_provider_schema(...)` derives the exact
expected structure from `dataclasses.fields` and `typing.get_type_hints` for
`MarketObservation` and every nested contract. Keep this structural only:
constructors and replay retain semantic authority, and unsupported annotations
or unexpected runtime errors must remain visible programming failures.

Normalized `pr17b1-contract-bundle` records contain canonical existing serializer
output. `replay_pr17_archive(...)` version-dispatches it with
`deserialize_v3(...)` and calls the existing graph validator. Run
`reconcile_archive(...)` to derive referenced-valid, missing, corrupt, orphaned,
malformed, incompatible, and partial sets. Orphans are never indexed or copied
to secondary storage. Deterministic publication failpoints support recovery
tests; only an identical retry may complete interrupted manifest-last work.

### Explicit retrospective publication (limited PR17C3)

`inspect-retrospective-publication` reports the verified `source_snapshot` without
provider calls. After independent approval of that snapshot, invoke
`operate_forecast_standalone_activation.py --config <authorized-config>
publish-retrospective-analysis --protocol-id <canonical-retrospective-id>
--source-snapshot <scientific-input:digest>`. These are manual commands, never
scheduled. Real execution requires separate operational authorization.

Publication accepts no category lists or analysis-time override (`--trusted-at`
is rejected). Canonical constructors build all qualifying derivations and
Measurements, then reconstruct cumulative Coverage from the complete registry.
One normalized-only bundle is published with a narrowly scoped `derived`
manifest disposition and truthful `pops-edge-archive-analysis` provenance;
`archive_pr17_authority` is not used. Provider response limits do not apply to
local derived serialization. No aggregate analysis or report is calculated.

`retrospective-publication-stage.json` freezes the actual trusted boundary,
Protocol, scientific-input snapshot, bundle digest, and exact candidate bytes.
It remains immutable and non-authoritative. An explicit retry validates and
resumes only this exact stage; other orphans, source changes, conflicting authority,
and integrity failures are not repaired. A completed repeat verifies the existing
publication first and returns its identities with `unchanged`, zero provider
calls, and zero scientific writes. This focused path intentionally refuses a new
publication after scientific inputs change; further incremental-publication
policy requires separate review. PR #19 rejected-session isolation is unchanged.

Historical publication replay binds `source_authority.source_manifest_ids` and
`source_authority.dependency_manifest_ids` inside the immutable publication.
The closure includes the exact supporting completion/correction lineage that
admitted provider contracts, their pages, bundles, references, and predecessors.
The publication-local read-only authority view reconstructs only those manifests
with the existing strict validators, after checking global archive integrity.
The frozen timestamp alone is not source authority: a later completion with old
acquisition timestamps cannot add bundles to historical replay. Missing, corrupt,
substituted, incomplete, or inconsistent pins fail closed. No existing material
is rewritten or reinterpreted. An explicit staging/repeat invocation compares the current
verified source snapshot and refuses changed inputs rather than silently extending
the publication. Global archive integrity remains checked across the namespace.

Pre-pinning offline sizing: a fully graph-validated 64-event synthetic candidate contains
129 scientific objects in 356,208 normalized bytes. A 3,879-object repeated-payload
serialization-only probe is 9,889,632 bytes (not a valid scientific graph or a
publication). A distinct 1,939-event full-validation stress run was interrupted
in the existing canonical manifest-lineage validator; full-population runtime
remains unverified. Do not infer deployment readiness or fragment authority from
these size probes. Full-snapshot rehearsal and any validator performance work
require review; the correction below changes lookup work, not validation semantics.

The focused PR17C3 performance correction groups classification and manifest
records once per validator invocation and uses local parent/child lookups.
Complete-input validation still precedes boundary selection, including future
correction checks. Existing group iteration and returned sorting are retained;
future-only classifications remain invisible, while a future-only manifest group
still fails its required-root check. No cache, trusted-validation flag, rule version,
publication gate, pinned dependency, or scientific constructor changes.

Synthetic measurements on 2026-08-31 used CPython 3.14.5 / Clang 21.0.0,
macOS 26.6.2 arm64, the repository venv, and `sized_candidate(N)` from the
publication tests. Baseline was `d7d1b38cb1bff717cb4f03f09f40544827660586`.
Each size includes fixture construction and candidate graph validation: one
`cProfile.Profile().runcall(sized_candidate, N)` followed by three unprofiled
runs (median shown). Socket connections were denied. No archive replay or
publication is measured. Profiling and cold-start overhead affect absolute times;
these are local observations, not CI timing thresholds or runtime guarantees.

| Synthetic events | Unprofiled median before / after (s) | Profiled before / after (s) |
| --- | --- | --- |
| 32 | 0.067 / 0.062 | 0.212 / 0.210 |
| 64 | 0.160 / 0.115 | 0.394 / 0.363 |
| 128 | 0.631 / 0.254 | 1.111 / 0.768 |
| 256 | 3.726 / 0.677 | 4.876 / 1.904 |

At 256 events, classification cumulative profiled time fell from 2.059 to 0.588s,
and manifest-lineage time from 1.753 to 0.254s; invocation counts remained 1,293
and 1,034. Differential tests retain the pre-change validators and compare exact
accepted outputs and rejection codes/details across malformed registries,
permutations, equality boundaries, and future corrections. Canonical candidate
bytes and identities match at identical inputs/boundaries (1/8/32 events in CI;
32/64/128/256 in the before/after profile). Deterministic attribute-work tests
cover independent groups and long chains at 16/64/128 records, with linear
per-invocation membership/traversal work rather than timing assertions. Final
sorting is unchanged. For 128 independent records, classification reads fell
from 50,688 to 2,048 and manifest reads from 50,816 to 1,920.
Validation: 235 focused tests and 652 repository tests passed. Two fixture-only
rehearsals were byte-identical (authoritative-output SHA-256
`50d5b24aa9e7853f4ba5ccdd45f5ec11951696ed5f96e7f1563f016304b85a03`),
with zero pre-activation calls and six successful fixture jobs.

Repeated full-registry invocation still contributes population-quadratic work;
these two validators retain about 44% of the 256-event profiled runtime. Archive
I/O and source dependency closure are not quantified here. The prior full-copy
rehearsal was manually interrupted after approximately 31 minutes during augmented
graph validation, without a scientific validation error or a stage/publication.
That interruption is not a correctness failure. Full-population archive-copy
publication, inspection, historical replay, and unchanged zero-write repetition
remain a separate authorized step after review and merge. Synthetic speedups do
not establish real-publication readiness; no further optimization is included.

After PR17B2 dry-run validation, the Product Owner may approve a future Eastern
calendar date before it begins. Midnight at that date becomes immutable
timezone-aware `activation_at`; PR17A sets no date. Dry-run material cannot
become Evidence, and no retrospective performance may be calculated before the
boundary is fixed. Retrospective and prospective reports remain independent;
historical candles cannot repair prospective capture, and any side-by-side
summary cannot pool or create analytical authority.

The filesystem and `launchd` are replaceable seams. Do not choose a cloud
provider, database, deployment model, or migration plan under PR17A.

PR17B1 uses explicit `ProbabilitySourceMeasurementV3` dispatch: existing
`MarketProbabilityDerivation` for prospective Protocols and
`HistoricalCandleProbabilityDerivation` for retrospective Protocols. Exactly
one typed derivation is required; mixed, wrong-kind, missing, multiple, unknown,
or foreign references fail closed. Add versioned Coverage/performance/reference/
report registries and graph validation wherever current typed v1/v2 contracts
cannot consume V3 without reinterpretation. Do not add optional fields to old
contracts.

## Forward implementation boundaries

The remaining v1.1.0 sequence after implemented PR16B analysis is:

1. **PR17A — Retrospective and Prospective Methodology and Architecture:** documentation authority only (this change).
2. **PR17B1 — Scientific Contracts and Deterministic Replay:** offline successor
   contracts, synthetic fixture/inspector, V3 registry, replay, and graph validation.
3. **PR17B2 — Acquisition, Persistence, and Operations Tooling:** implemented
   inactive provider boundary, archive, secondary copy, scheduling, CLI, and
   dry-run operations without activation.

PR17B1 constructors consume complete typed registries and replay Schedule and
eligibility authority, ordered manifest pages/corrections, attempts and Snapshot
corrections, derivations, Outcomes, Measurements, scoped Coverage, bootstrap
performance, and reports. Bounded Coverage/performance uses `(start, end]`
Schedule membership and never reuses cumulative Coverage. The inspector's two
roots are a fixture invariant only.
Coverage constructors do not accept reconciliation membership: they derive the
complete opportunity universe, eligibility denominator, category partition, and
Measurement mapping from Schedule through Evidence and Outcome authority. The
Protocol must use the supported scoring, fixed-bin Calibration/WACE, bootstrap,
and exact duration-based report-window specifications. Candle Evidence must
match exactly one retrieval page's position, archive reference/digest, and
retrieval time. `deserialize_v3(...)` handles V3 locally and explicitly delegates
the approved legacy graph families to their existing canonical deserializers.
Schedule discovery creates opportunities per changed scheduled-state Observation,
not per eventual event history, so cross-activation reschedules remain visible
on both sides. Pass the complete `StandaloneEventClassificationEvidence`
registry to eligibility, Coverage, and graph replay. Prospective Coverage uses
valid-success-first precedence; without success it applies captured-invalid,
acquisition-failed, then pure no-call missed-window. Derivation, Outcome, and
Measurement registries are filtered at the explicit boundary and ambiguous
candidates fail closed independently of ordering.
4. **PR17C — Activation, Retrospective Report, and Prospective Start:** freeze the future boundary, produce the separate retrospective report, and begin collection.
5. **PR17D — Prospective Close and Separate Report:** close after the 2026 regular season and publish the independent prospective report.
6. **PR19 — Current Scientific Applicability and Policy Recommendation:** add deterministic applicability replay and non-authoritative recommendations.
7. **PR20 — Policy Hypothesis Alignment:** align `PolicyHypothesis` with one or
   more empirically supported Market Edges while keeping it non-authoritative
   and non-executable.
8. **PR21 — Forecast Intelligence Workspace:** implement the Product Owner's
   principal research and governance surface.
9. **PR22 — Policy Forecast Opportunity Integration:** migrate Opportunity
   Analysis and the Opportunity Board to governance-authorized Policy Forecasts.
10. **PR23 — v1.1.0 Integration and Release Readiness:** validate the integrated
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
## PR17C1 offline activation development

The exact proposed activation is `2026-09-05T00:00:00-04:00` in `America/New_York` (`2026-09-05T04:00:00Z`), contingent on explicit Product Owner authorization and reviewed squash merge by September 3. Run `python3 inspect_forecast_standalone_activation.py` twice for the deterministic fixture rehearsal. Tests inject transports and credentials: never use the real Keychain, network, live endpoint, scheduler, or activated archive during development.

The inert local-Mac templates invoke prospective discovery every 30 seconds, supporting refresh hourly, and outcomes, maintenance, secondary synchronization, and health reporting daily. Keep primary, secondary, and logs physically separate; same-drive secondary storage is not independent backup. Never promote dry-run objects. PR17C1/PR17C2/PR17C3 preserve unchanged PR17D numbering, and scientific, operational, reporting, Policy, Governance, cloud, and production authority remain separate.

Use the typed `render-launchd` command with an absolute activated configuration and output directory to produce deployable absolute-path plists; it does not install them. Command attempts append sanitized operational heartbeats beneath the configured log root, and `health-report` derives readiness from those records plus archive, index, secondary, and actual disk inspection. Missing fixture/live composition fails nonzero. Signing tests inject fixture keys and never invoke the real Keychain.

Run `initialize-activation` once against an empty activated namespace; it is create-only and idempotent for the pinned canonical bundle. `refresh-supporting` and `reconcile-outcomes` consume provider-native MLB/Kalshi shapes, while `capture-prospective` strictly adapts documented fixed-point order books. Catalog and order-book GETs are public and must not retrieve signing keys. Use `maintain` for the ordered inspect, safe rebuild, and post-rebuild verification path. Fixture configuration may supply a deterministic trusted time only alongside an explicit fixture directory.
PR17C1 supporting composition must process complete MLB authority before per-opportunity Kalshi mapping. Treat empty catalogs as valid, ambiguity as event-local, and refreshes as append-only semantic corrections. Preserve exact provider pages and bind contracts through the typed acquisition manifest; never label the canonical union as raw provider Evidence. Follow and validate the entire bounded cursor chain with standard query encoding. Select MLB dates with `eastern-unresolved-obligations-lookback-2`: unresolved non-terminal histories have no age cutoff, while resolved corrections use the bounded lookback. Pass the single trusted command-start time into every loader and never call ambient wall time behind that boundary. In `orderbook_fp`, complement provider NO bids into canonical YES offers and provider YES bids into canonical NO offers, retaining every level and requiring positive depth on both sides. Offline tests must inject all transports and must not access the network, Keychain, or `launchctl`.

Record every provider request's trusted aware start and completion; enforce monotonic non-overlapping page chronology and keep obligations fixed across midnight. Acquisition pages and their sole envelope form one crash-reconciled group. A page-only, missing-page, extra-page, or competing-envelope group is blocking partial authority: do not replay, index, synchronize, or rebuild until an idempotent create-only retry completes it.

Ordinary replay regenerates the versioned union and correction-aware expected contracts from the exact pages, command chronology, canonical Protocol, and boundary-effective predecessors, then requires exact canonical equality with the envelope contract set.

Run `reconcile-acquisitions` after inspecting an interrupted page-only group. It deterministically creates at most one exact-page `abandon-incomplete-acquisition-1` artifact, refuses ambiguous or backdated material, and is idempotent. Then run the normal provider command as a fresh attempt; never reuse timestamps, attach new pages to the old group, or delete archived pages.

## PR17C1 commissioning with travel outages

The approved local laptop model accepts sleep and connectivity interruptions.
Before September 5 midnight America/New_York, scheduled capture, supporting and
Outcome commands resolve authority but do not enter provider loaders. The offline
activation rehearsal now tests pre-boundary capture before performing supporting
acquisition at the boundary, rather than pre-seeding it through an early live path.
There is no requirement to prevent sleep, wake the machine, or move to a server.

`reconcile-prospective-schedule --start-date YYYY-MM-DD --end-date YYYY-MM-DD`
(on `operate_forecast_standalone_activation.py --config <activated-config>`)
is a manual MLB-only operation, never a launchd job. After an outage, explicitly
review and invoke inclusive batches of at most 31 completed Eastern dates since
September 5, 2026. To account for the whole elapsed prospective calendar, cover
all elapsed dates in such batches; do not select date ranges from performance.
The operation skips dates already backed by complete verified post-date MLB
schedule acquisition, including explicit empty dates. A same-day or advance
schedule read is not a completed-date receipt. A later independent invocation
continues remaining dates after failure; there is no automatic retry policy.
Dates beyond 2026, pre-activation dates, current/future dates, noncanonical date
strings and unbounded ranges are rejected. A caller-supplied live clock is rejected.

Only MLB schedule data is fetched: no historical price or current quote repair,
no Kalshi catalog, no credentials, no index rebuild, secondary sync, aggregate
publication or reporting. Each successfully acquired date has a durable, empty-
contract receipt; empty responses require explicit `totalGames: 0`. Scientific
completion is separate and requires all declared related observations to satisfy
the existing lineage rules. Reciprocal suspension/resumption preserves one original
opportunity and nonordinary classification, never two ordinary opportunities.
`schedule-lineage-incomplete` reports missing related dates without fetching beyond
the explicit bounds. Request those dates in a separately authorized manual batch;
already preserved receipts are reused, not reacquired or rewritten. At most 31
dates may participate in a completion. Diagnostics distinguish `requested_dates`,
`reused_dates`, and `scientifically_completed_dates`, including previously authorized
related receipts outside the current request range. A missing or conflicting counterpart cannot
certify scientific completeness merely because its calendar request succeeded.
Independent completed groups remain visible after later failures; unresolved
receipt groups remain inspectable but scientifically incomplete. A repeated
completed reconciliation performs zero calls and zero scientific writes. Raw page
chronology is preserved; contracts become available at `schedule_reconciled_at`,
the actual later reconciliation time. Unrecoverable historical schedule states
and availability selection remain disclosed limitations.

Outcome collection may run first after an outage. If its proposed full graph lacks
Schedule/opportunity authority, `outcome-authority-deferred` is a nonzero failure,
not success: all received pages remain immutable non-authoritative failure records,
and the heartbeat retains the exact attempted-call count. Manually reconcile the
missing completed schedule dates, then retry Outcome collection independently.
No invalid partial graph is published, no validation gate is bypassed, and no
undocumented always-online or command-order requirement is imposed. Conflicting
preserved receipts and irrecoverable historical states fail closed; this is not an
archive-repair mechanism or a promise of automatic recovery.

Tests inject transports into `load_live_supporting` and `reconcile_schedule`, use
temporary activated fixture namespaces, and never access real providers/Keychain.
`--fixture <directory>` uses `mlb-YYYY-MM-DD.json` for each manual date. Verify both
nonzero CLI failure and failed heartbeat, exact request counts, later success,
never-seen and empty dates, exact-repeat no-op, date tampering rejection and expired
capture with zero provider calls. An uninstrumented fixture loader error reports
unknown call count rather than guessing; live loaders supply exact counts.

Commissioning-review follow-up validation (2026-08-31): both blocking findings
were first reproduced with temporary fixtures. The corrected candidate passes 22
commissioning tests (including nine new regression cases), 231 focused tests and
all 674 repository tests. Two deterministic fixture rehearsals are byte-identical,
with zero pre-activation provider calls and six successful fixture jobs. These
results supersede neither the review gate nor the requirement for explicit
commissioning/deployment authorization. Existing immutable review receipts remain
unchanged; no real archive or provider was used for this correction.

Commissioning still requires review and deployment of this correction before
installing/loading the six existing plists. Verify installed executable/config
paths and actual pre-boundary no-call heartbeats. No change to activation authority
or laptop power settings is needed. Do not call a pre-boundary staging result proof
of post-boundary connectivity, cadence or prospective readiness. Manual calendar
accounting and final scientific Coverage/reporting remain separate checks.


## PR17C3 aggregate input ordering correction

The August 31 local descriptive review exposed caller-order Decimal accumulation
in `create_probability_source_performance_v3`: reversing 1,939 archived
Measurements changed mean log loss by 2e-49 and changed aggregate identity.
The correction uses the existing duplicate-rejecting canonical ordering helper
before aggregate reductions. It preserves 50-digit precision, extended-real log
loss, calibration bins/weights, bootstrap seed/version/resampling, and all
Measurement and Protocol identities. No global identity version is changed.
Canonical-order inputs retain their previous aggregate bytes. Previously
noncanonical input order may yield a last-digit and content-address change;
rounding display output is not a reproducibility fix.

Constructor regressions cover original, reversed, shuffled, and generator input
for cumulative and time-bounded results, fixed-provenance serialized equality,
ambient precision, empty/singleton/infinite loss, and rejection of duplicate,
foreign, and Coverage-mismatched populations. The synthetic Coverage fixture is
constructor-level material, not a substitute for the existing full graph tests.

The real archive check is read-only and exercises the published 1,939-Measurement
population. Aggregate results remain review artifacts; this change adds no
publication, acquisition, scheduler, or final-report capability. No authoritative
V3 aggregate was present in the reviewed archive. If an external archive contains
an old noncanonical aggregate, preserve its serialized history and resolve
versioned reconstruction explicitly before applying this correction there.
