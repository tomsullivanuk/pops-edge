# Pops' Edge Roadmap

## v1.0.0 — World Cup

First production release: forecast and market ingestion, match/futures value
boards, portfolio and ladder views, wager log, CLV, archives, and web reports.

## v1.1.0 — MLB Research and Multi-Sport Foundation

1. Establish product and documentation foundations.
2. Research and select MLB sources.
2A. Document approved product-management and architecture decisions.
3. Define MLB domain contracts and edge cases.
3A. Document external forecast architecture.
4. Define provider-neutral Forecast Observation contracts.
5. Implement the MLB Stats API facts adapter.
5A. Document the Series / Observation architecture.
6. Implement Forecast Series and the first external forecast-provider adapter.
7. Implement MLB valuation.
8. Add MLB reports and operating workflow.
9. Extract proven multi-sport boundaries.
10. Harden, document, and release.

The authoritative PR scope and gates are in
`docs/RELEASE_PLAN_v1.1.0.md`.

PR2 selected a licensed official MLB feed as the production identity/pitcher
strategy, with MLB `gamePk` canonical, and made forecast-provider licensing a
prerequisite rather than assuming public pages may be scraped. See
`docs/MLB_SOURCE_RESEARCH_v1.1.0.md`.

## Later releases

Potential directions, subject to research and explicit planning:

- calibration and source-comparison reporting;
- cross-sport portfolio and exposure analytics;
- additional market providers;
- additional sports through isolated adapters;
- stronger provenance, observability, and operator recovery;
- configurable bankroll and policy profiles; and
- packaging or deployment beyond the current local workflow.

Items here are directional, not commitments. `BACKLOG.md` records deferred
ideas without assigning them to a release.
