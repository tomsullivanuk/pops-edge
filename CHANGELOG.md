# Changelog

All notable Pops' Edge releases are recorded here. Dates and release status
must not imply that an untagged release has shipped.

## [Unreleased]

### v1.1.0 — MLB Research and Multi-Sport Foundation

Planned:

- MLB source research, contracts, ingestion, valuation, and reports.
- Initial multi-sport boundaries proven by World Cup and MLB.
- Durable product, architecture, workflow, roadmap, backlog, release, and
  migration documentation.

PR1 establishes documentation and planning only; it does not change production
behavior.

## [v1.0.0] — World Cup baseline

The existing production World Cup implementation is designated Pops' Edge
v1.0.0. It includes Silver forecast ingestion, supported Kalshi World Cup
markets, match and futures value boards, portfolio and ladder reporting, wager
import, CLV and position monitoring, archives, and local Excel/HTML workflows.

This designation records the baseline; PR1 does not create or backfill a tag.

### Maintenance

- Add an active-position Ladder Board workbook and sortable web view.
- Track exited and remaining contracts so closed positions are excluded and
  partially closed positions use their remaining exposure.
- Integrate Ladder Board generation, archiving, iCloud copying, and opening
  into the existing World Cup workflows.
