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
policy, if any, has production authority. PR14 remains responsible for selecting
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

The approved PR13 architecture defines a Forecast Research Workspace as the
Product Owner's deterministic, read-only projection over immutable PR9–PR12
inputs. One explicit `ResearchWorkspaceContext` keeps provider, policy,
hypothesis, evaluation-window, analysis, and governance scope consistent across
an executive overview, provider performance, policy candidate comparison,
proposal and governance review, a non-authoritative Governance Decision Draft, and
diagnostics. The planned v1.1 output is one self-contained local HTML document
with no server, persistence, write action, production execution, Opportunity
Analysis migration, or wagering behavior. Implementation remains PR13; PR14
retains Policy Forecast consumer integration.

The workspace does not mistake PR9 provider Forecast Evaluations for historical
Forecast Policy evaluations. Candidate support comes from supplied PR10
Forecast Intelligence, Policy Proposals, benchmark evidence, and governance
context; missing Policy Forecast, Shadow, or policy-evaluation history is shown
explicitly. Decision drafts come only from a Proposal or explicit Product Owner
selection and carry no authority. Context compatibility fails closed, while
wall-clock generation metadata remains outside deterministic projection
identity. Policy backtesting is not a PR13 capability.

## Documentation

- [Developer guide](DEVELOPER.md) — current World Cup workflows and behavior
- [Product](docs/PRODUCT.md) — vision, principles, and platform direction
- [Architecture](ARCHITECTURE.md) — current system boundaries and dependencies
- [Roadmap](ROADMAP.md) — ordered product direction
- [Backlog](BACKLOG.md) — deferred and uncommitted work
- [Changelog](CHANGELOG.md) — version history
- [v1.1.0 release plan](docs/RELEASE_PLAN_v1.1.0.md) — PR1–PR15 sequence
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

Use the validation and handoff process in
[docs/CODEX_WORKFLOW.md](docs/CODEX_WORKFLOW.md). Do not mix changes to
v1.0.0 calculations or reports into documentation-only foundation work.
