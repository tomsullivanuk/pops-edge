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
9. Introduce Outcome Measurement and Forecast Intelligence boundaries, while
   extracting only proven multi-sport interfaces.
10. Derive provider-neutral Forecast Intelligence Reports, immutable Policy
    Hypotheses, and analytical Policy Proposals from explicit current Forecast
    Evaluations.
11. Implement provider-neutral immutable Forecast Policy definitions,
    versioned rule stages, deterministic batch execution, and independently
    replayable policy-relative Policy Forecasts.
12. Add Product Owner governance records and Research, Shadow, Active, Retired,
    and Rejected lifecycle transitions.
13. Add the Forecast Research Workspace.
14. Migrate Opportunity Analysis and the Opportunity Board from direct provider
    forecasts to Policy Forecast identities without changing wagering policy.
15. Harden, document, and release.

The authoritative PR scope and gates are in
`docs/RELEASE_PLAN_v1.1.0.md`.

The implemented and validated baseline through PR6 is recorded in
`docs/V1.1.0_CHECKPOINT_THROUGH_PR6.md`. PR8 is complete. PR9's approved
architecture adds Outcome Evidence and Forecast Evaluation; those PR9
capabilities are implemented. PR10's provider-neutral Forecast Intelligence
Report, Policy Hypothesis, and advisory Policy Proposal foundation is also
implemented. PR11's executable Policy definitions, deterministic batch
execution, and Policy Forecast foundation are implemented pending review.
Governance lifecycle remains PR12, the Research Workspace remains PR13, and
Policy Forecast consumer integration remains PR14. v1.1.0 remains unreleased.

PR2 selected a licensed official MLB feed as the production identity/pitcher
strategy, with MLB `gamePk` canonical, and made forecast-provider licensing a
prerequisite rather than assuming public pages may be scraped. See
`docs/MLB_SOURCE_RESEARCH_v1.1.0.md`.

## Later releases

Potential directions, subject to research and explicit planning:

- additional calibration and source-comparison reporting;
- cross-sport portfolio and exposure analytics;
- additional market providers;
- additional sports through isolated adapters;
- stronger provenance, observability, and operator recovery;
- configurable bankroll and policy profiles; and
- packaging or deployment beyond the current local workflow.

Items here are directional, not commitments. `BACKLOG.md` records deferred
ideas without assigning them to a release.
