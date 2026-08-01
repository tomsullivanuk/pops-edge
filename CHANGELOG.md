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

PR2 research selects MLB `gamePk` as canonical identity and a licensed
official-data feed for production schedule/pitcher facts; identifies DRatings
and FanGraphs as conditional forecast candidates; documents Kalshi
`KXMLBGAME`, provenance, backfill, reconciliation, and fail-closed gates; and
defers sportsbook ingestion without changing production behavior.

PR2A documents Pops' Edge as an external-forecast evaluation platform,
establishes commercial-data cost and rights review, separates reusable concepts
from adapter semantics, makes immutable provenance and fail-closed validation
core principles, and formalizes the product-manager/architect and Codex
implementation-engineer workflow.

PR3 adds deterministic offline Canonical Event and MLB identity contracts,
immutable schedule/pitcher/status observations, explicit provenance and
schedule lineage, structured matched/ambiguous/rejected reconciliation, and
fixture-backed semantic validation. It adds no provider client, persistence,
market comparison, report, wagering behavior, or World Cup integration.
Canonical identity is restricted to authoritative sport-native identifiers;
later provider mappings remain separate, and rejected reconciliation preserves
candidate-evaluation evidence without exposing an eligible candidate.

PR3A documents the external-forecast architecture without implementing it. It
establishes Provider → Model → Version → Observation as distinct domain
concepts; requires complete structured outcome distributions, preserved
published precision, precision-aware validation, distinct timestamps,
immutable revision and correction history, provider-reported assumptions, and
fail-closed event reconciliation; and separates immutable identity and evidence
from mutable weighting, eligibility, and wagering policy. No provider is
approved or privileged.

PR4 implements deterministic offline Forecast Provider, Model, Version,
Outcome, Published Probability, Distribution, provider-assumption, Observation,
validation, disposition, relationship, and timing contracts. Exact decimal
values and published precision drive aggregate rounding-tolerance validation;
outcomes serialize in canonical non-semantic order; inconsistent distributions
remain preserved without normalization; and PR3 provenance and reconciliation
semantics are reused. It adds fixtures and semantic tests but no provider
adapter, persistence, weighting, market, valuation, report, or wagering work.

PR5 adds a bounded read-only MLB Stats API facts adapter for the personal,
noncommercial project. It separately preserves exact-response and canonical-
JSON digests, uses authoritative `gamePk` and MLB team IDs, constructs canonical
games and schedule/status/pitcher observations, returns explicit deterministic
complete/partial/rejected results, and fails closed on unsafe identity without
inventing source timestamps or lineage. Fixture-backed tests remain offline;
an explicit concise smoke path is not run automatically. Persistence,
scheduled collection, forecasts, markets, valuation, reports, and wagering
remain deferred.

PR5A documents Durable Identity → Immutable Observations → Derived Views as the
shared architecture for time-varying evidence. It defines Forecast Series as
the durable identity for one Provider, Model, Version, and Canonical Event;
keeps probabilities, timestamps, assumptions, provenance, validation,
disposition, and relationships on immutable Forecast Observations; and makes
latest, pregame, history, evolution, and movement computed views. It strengthens
the Identity / Evidence / Policy boundary and scopes PR6 to implement Forecast
Series plus the first external provider adapter without changing contracts or
runtime behavior in PR5A.

PR6 implements immutable Forecast Series, append-only Forecast History, and a
provider-neutral offline adapter-result boundary with explicit complete,
partial, ambiguous, and rejected states. Its first provider implementation
parses a faithful manually captured DRatings Upcoming table, preserving exact
published probabilities and precision, pitcher assumptions, scheduled UTC
times, page-level update evidence, source URLs, row locators, and raw/canonical
digests. Separately captured MLB schedule evidence supplies `gamePk`, team
identity, home/away roles, and exact-time reconciliation; the controlled
`Oakland Athletics` → `Athletics` alias is explicit. No provider row timestamp,
stable record ID, or disclosed model version is invented. The local inspection
command performs no provider network access, and automation, persistence,
freshness, weighting, markets, valuation, reports, and wagering remain deferred.

The documentation checkpoint in `docs/V1.1.0_CHECKPOINT_THROUGH_PR6.md`
records the implemented platform baseline before PR7. It changes no runtime
behavior, does not release v1.1.0, and preserves the planned PR7–PR10 sequence.

PR7 implements provider-neutral Winner Propositions, provider-specific Market
Series, immutable capture-session Market Observations, and the first bounded
read-only Kalshi MLB market adapter. Explicit participant/date and YES/NO
evidence is required; ambiguous doubleheaders and unsafe mappings expose no
series or valuation. Exact-Decimal executable-depth analysis and explicit fee
models produce reproducible expected value without recommendation, sizing,
bankroll, freshness, liquidity, portfolio, or wagering policy. A separate
non-persisting smoke command is provided but was not run.

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
- Add bounded retry handling for transient Kalshi API failures without
  advancing the pagination cursor.
