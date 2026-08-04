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

The approved PR9 direction adds authoritative Outcome Evidence and immutable
Forecast Evaluation, then derives provider-neutral Forecast Intelligence from
many evaluations. That intelligence will justify Forecast Policy selection and
configuration; Policy execution will consume eligible current Forecast
Observations to produce an immutable derived Policy Forecast. Opportunity
Analysis will consume that Policy Forecast with current Market Evidence. These
are architectural decisions, not claims of implemented PR9 functionality.
Derived objects never become Evidence.

PR9 now implements the first half of that direction: immutable MLB Outcome
Observations, explicit eligibility decisions, deterministic forecast-quality
scoring, and append-only evaluation history. Forecast Intelligence remains the
next planned step; no Forecast Policy or Policy Forecast engine is implemented.

The approved PR10 direction separates Research Mode from Production Mode.
Provider-neutral Forecast Intelligence will derive immutable reports and
non-executable Policy Hypotheses and Policy Proposals from explicit current
Forecast Evaluations, demonstrated with DRatings as the sole implemented MLB
Forecast Provider. PR11 Forecast Policies remain separate executable production
definitions. Only later Product Owner governance may bridge a hypothesis to
production authority: research itself cannot create or activate a policy or
alter current decisions.

## Documentation

- [Developer guide](DEVELOPER.md) — current World Cup workflows and behavior
- [Product](docs/PRODUCT.md) — vision, principles, and platform direction
- [Architecture](ARCHITECTURE.md) — current system boundaries and dependencies
- [Roadmap](ROADMAP.md) — ordered product direction
- [Backlog](BACKLOG.md) — deferred and uncommitted work
- [Changelog](CHANGELOG.md) — version history
- [v1.1.0 release plan](docs/RELEASE_PLAN_v1.1.0.md) — PR1–PR14 sequence
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
