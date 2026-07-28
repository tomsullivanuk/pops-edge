# Pops' Edge

**Current release:** v1.0.0<br>
**Next release:** v1.1.0

Pops' Edge is a reproducible sports-market research system. It combines
independent forecasts, market prices, wager history, and portfolio context to
identify and monitor potential edges.

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
preserving the World Cup baseline. Work is divided into eight reviewable pull
requests. The scope, sequencing, gates, and release criteria are defined in
[docs/RELEASE_PLAN_v1.1.0.md](docs/RELEASE_PLAN_v1.1.0.md).

## Documentation

- [Developer guide](DEVELOPER.md) — current World Cup workflows and behavior
- [Product](docs/PRODUCT.md) — vision, principles, and platform direction
- [Architecture](ARCHITECTURE.md) — current system boundaries and dependencies
- [Roadmap](ROADMAP.md) — ordered product direction
- [Backlog](BACKLOG.md) — deferred and uncommitted work
- [Changelog](CHANGELOG.md) — version history
- [v1.1.0 release plan](docs/RELEASE_PLAN_v1.1.0.md) — PR1–PR8 sequence
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
