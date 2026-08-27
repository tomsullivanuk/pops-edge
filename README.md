# Pops' Edge

**Current release:** v1.0.0<br>
**Next release:** v1.1.0

Pops' Edge is a quantitative decision platform whose Mission is to identify
opportunities with demonstrable statistical advantage. Sports wagering is its
current proving ground, not its defining purpose. The current system combines
forecast and market Evidence with position context; approved future
Measurement, Forecast Intelligence, and Forecast Policy capabilities will make
the empirical basis of Opportunity Analysis reproducible.

The durable product name is **Pops' Edge**. Names such as “World Cup Betting
System,” `kalshi`, and World Cup-prefixed output filenames describe the
original implementation, repository location, data provider, or a sport-specific
artifact; they are not the product name.

## Version history

### v1.0.0 — World Cup baseline

The existing World Cup system is the v1.0.0 product baseline. It:

- ingests Silver match and futures forecasts;
- pulls supported Kalshi World Cup markets;
- produces match, futures, portfolio, and ladder workbooks and web boards;
- imports Kalshi activity into a unified wager log;
- calculates the existing edge, ROI, Kelly-sizing, proxy, ladder, CLV, and
  position-monitoring fields; and
- archives local inputs and generated reports.

PR1 does not change any v1.0.0 calculations, reports, filenames, market
coverage, or operating workflows. Detailed baseline behavior remains in
[DEVELOPER.md](DEVELOPER.md).

### v1.1.0 — MLB Research and Multi-Sport Foundation

v1.1.0 adds MLB research and the first reusable multi-sport boundaries while
preserving the World Cup baseline. The release uses bounded, reviewable pull
requests, including documentation checkpoints when durable architecture must
be settled before implementation. The scope, sequencing, gates, and release
criteria are defined in
[docs/RELEASE_PLAN_v1.1.0.md](docs/RELEASE_PLAN_v1.1.0.md).

Across event facts and forecasts, Pops' Edge treats durable identity as the
owner of append-only observations. “Current” state is a derived view;
historical evidence is never updated in place.

PR9 implements authoritative Outcome Evidence and immutable Forecast
Evaluation; PR10 derives provider-neutral Forecast Intelligence from current
evaluations. That intelligence may justify future Forecast Policy selection and
configuration. Planned policy execution will consume eligible current Forecast
Observations to produce immutable Policy Forecasts, which later Opportunity
Analysis integration will combine with current Market Evidence. Derived objects
never become Evidence.

PR9 now implements the first half of that direction: immutable MLB Outcome
Observations, explicit eligibility decisions, deterministic forecast-quality
scoring, and append-only evaluation history.

PR10 implements the bounded Research foundation while preserving the separation
from Production Mode. Provider-neutral Forecast Intelligence derives immutable
reports and non-executable Policy Hypotheses and Policy Proposals from explicit
current Forecast Evaluations, demonstrated with DRatings as the sole implemented
MLB Forecast Provider. PR11 Forecast Policies remain separate executable
production definitions. Only later Product Owner governance may bridge a
hypothesis to production authority: research itself cannot create or activate a
policy or alter current decisions.

The MLB intelligence demonstration calibrates one fixed home-win target per
game, reconciles evaluation-level result/favorite/probability segments, excludes
forecast ties from directional-accuracy denominators, and derives advisory
proposal actions from a versioned rule with factual benchmark-absence reasons.

PR11 implements a Forecast Policy as a provider-neutral immutable executable
specification, applies it through an immutable explicit batch Forecast Policy
Execution, and emits one independently replayable Policy Forecast per Canonical
Event. Rule stages and production
observation eligibility/selection are explicit, versioned, deterministic, and
fail closed. Each Policy Forecast is canonical only to its specific policy
execution; multiple outputs may coexist for an event. Policies and forecasts
contain no approval or lifecycle state; PR12 governance alone determines which
policy, if any, has production authority. PR22 remains responsible for selecting
a compatible Policy Forecast execution for consumption. The current Opportunity
Board continues to consume DRatings directly until that bounded migration.

PR12 implements governance as immutable Product Owner
decisions over exactly one Forecast Policy. Append-only Governance History
derives Research, Shadow, Production, Retired, and terminal Rejected lifecycle
views and resolves at most one production-authorized policy per immutable
sport/competition/proposition scope at an explicit historical boundary.
Material effective decision time—not input or file order—governs replay, and
simultaneous same-scope conflicts fail closed. Shadow remains
measurement-only, Research artifacts cannot grant authority, and PR12 does not
change Forecast Policy execution or the Opportunity Board. The fixture-only
inspection command is `inspect_forecast_governance.py`.

The stable Product Owner ID is identifying; its optional display label is not.
Equivalent same-time decisions preserve all supporting records without false
ambiguity. Production-material conflicts fail scope resolution closed, while
unrelated research-only conflicts remain visible diagnostics without erasing
an otherwise unambiguous authorization.

PR13 implements immutable, deterministic Research Protocol, Edge Claim,
Research Review, historical Market Edge, and Drift Surveillance contracts with
typed scientific rules and fail-closed graph validation. Its offline fixture
and inspector demonstrate the research-contract boundary without provider or
network access.

PR14 implements Research Capture Opportunity identity, immutable Research
Snapshots and historical correction replay, pair-specific Comparative
Measurement, cumulative claim/domain Comparative Performance, deterministic
paired uncertainty and Calibration, extended-real Log Loss, and
failure-inclusive Coverage derived from authoritative boundary-specific
population eligibility. Its local
synthetic inspector is `inspect_forecast_comparative_research.py`. Time-bounded
Comparative Performance, comparative Drift analysis, and the canonical
Comparative Performance Report are implemented by PR15 in
`forecast_comparative_reporting.py`; its offline inspector is
`inspect_forecast_comparative_reporting.py`. Complete report membership is
governed by the immutable `ProtocolClaimSet` effective at the report boundary.
PR16A defines the documentation authority for standalone Probability Source
performance. PR16B implements the deterministic provider-neutral path, first
exercised with synthetic offline Kalshi-shaped MLB Market Evidence. PR17A now
defines separate retrospective historical-candlestick and prospective point-in-
time order-book Kalshi MLB standalone Protocols. Both use the home-team YES
representation; preserve independent populations, Coverage, Measurements,
performance, uncertainty, limitations, and reports; and create no scientific,
Policy, Governance, wagering, or production authority. PR17B–PR17D retain
implementation, activation, collection, and separate-report ownership. Current
Scientific Applicability and Policy Recommendation remain future PR19 work. The Forecast Intelligence
Workspace remains a later product surface. Research contracts create neither
Governance nor production authority.

PR17A also distinguishes the new `StandaloneProbabilitySourceProtocol` and
`ProbabilitySourcePerformanceReport` from the unchanged comparative Protocol
and report contracts. Retrospective candles use their own immutable Evidence and
derivation path rather than PR16B positive-depth order-book semantics. The
prospective window contains five non-backdating slots: slots 0–3 are half-open
and slot 4 includes the exact `target_at + 5 minutes` endpoint. Delayed
execution cannot catch up or relabel a current quote as an earlier attempt, and
anything later than the endpoint is prohibited.

Retrospective archive acquisition remains retrospective even though its
standalone Protocol is fixed before querying and analysis. Historical effective
time and later acquisition time remain distinct, and this Evidence cannot repair
or enter prospective research or support paired authority.

## Documentation

- [Developer guide](DEVELOPER.md) — current World Cup workflows and behavior
- [Product](docs/PRODUCT.md) — vision, principles, and platform direction
- [Architecture](ARCHITECTURE.md) — current system boundaries and dependencies
- [Roadmap](ROADMAP.md) — ordered product direction
- [Backlog](BACKLOG.md) — deferred and uncommitted work
- [Changelog](CHANGELOG.md) — version history
- [v1.1.0 release plan](docs/RELEASE_PLAN_v1.1.0.md) — PR1–PR23 sequence, including PR16A/PR16B and PR17A–PR17D
- [v1.1.0 checkpoint through PR6](docs/V1.1.0_CHECKPOINT_THROUGH_PR6.md) —
  implemented platform baseline before MLB market valuation
- [Codex workflow](docs/CODEX_WORKFLOW.md) — pull-request and completion-report
  standard
- [Release checklist](RELEASE_CHECKLIST.md) — release readiness and handoff
- [Repository rename plan](docs/REPOSITORY_RENAME.md) — documented migration
  from `kalshi` to `pops-edge`

## Current operation

Run the complete v1.0.0 World Cup refresh:

```bash
./update_all.sh
```

Run only the board or wager workflows:

```bash
./update_worldcup.sh
./update_wagers.sh
```

Generated workbooks, HTML boards, archives, downloaded data, local virtual
environments, and credentials are intentionally excluded from version control.

## Development

Pops' Edge is currently developed and validated with Python 3.14.5.

Create a local virtual environment and install the pinned direct dependencies:

```bash
cd /path/to/pops-edge
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Run the automated test suite with:

```bash
python3 -m unittest discover -s tests
```

Use the validation and handoff process in
[docs/CODEX_WORKFLOW.md](docs/CODEX_WORKFLOW.md). Do not mix changes to
v1.0.0 calculations or reports into documentation-only foundation work.
