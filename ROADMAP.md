# Pops' Edge Roadmap

MLB presentation follow-up adopted September 15: Central times, compact NFL-style rows/Details, retained last-captured quotes and one manual refresh for official results and eligible odds, plus NFL-style filters. See [feature scope](docs/MLB_BET_SHEET.md).

## September 15, 2026 adopted v1.3 direction

One website: Bet Sheet / Performance / Administration, with sport selection.
The [MLB Bet Sheet](docs/MLB_BET_SHEET.md) is the first approved implementation
slice: manually refreshed pregame team-winner market prices, before fees, with
honest expiry and missing states. Model investigation remains independent.
See [v1.3 sequencing](docs/RELEASE_PLAN_v1.3.md). Earlier tentative direction below
is historical. v1.2.0 was published September 14 at ff9c0a2; the older publication
pending statement is superseded, without repinning any deployment or closing studies.

> Product Owner direction, September 12, 2026: v1.2 focuses on MLB Kalshi
> collection and baseline market performance; v1.3 is the tentative unified
> NFL/MLB experience target. External MLB model and supplier investigation
> continues independently of both releases. See the
> [scope and sequencing decision](docs/RELEASE_DIRECTION_2026-09-12.md).

## Purpose

The Roadmap describes Pops' Edge's evolution across releases. It derives from the [Empirical Research Methodology](EMPIRICAL_RESEARCH_METHODOLOGY.md), [Product](docs/PRODUCT.md), [Architecture](ARCHITECTURE.md), and release plans without replacing them or defining implementation sequence.

It answers **where Pops' Edge is heading over multiple releases**; Release Plans answer **how an approved release is implemented**.

## Strategic direction

Pops' Edge is evolving from a sports-wagering proving ground into an empirical decision platform for positive expected value opportunities supported by validated evidence. Sports remain the proving ground, not the permanent boundary. World Cup, NFL and MLB are the implementations from which reusable capabilities are earned.

## Guiding principles

- Evidence precedes operational trust; Forecast Intelligence precedes reliance.
- Product Owner Governance remains the authorization boundary: **Research never changes production. Governance changes production.**
- Probability Sources and compatible market venues remain replaceable.
- Evidence remains immutable; derived behavior is deterministic, reproducible, traceable, and fail-closed.
- Multi-sport and multi-domain evolution remains incremental; shared abstractions must be earned.
- Pops' Edge remains personal, noncommercial, local, cost-conscious, transparent, and appropriately simple.

## Release direction

| Release / track | Outcome | Status |
|---|---|---|
| v1.1 — NFL | Personal comparison workflow and weekly evaluation evidence | Released and deployed locally; maintenance continues |
| v1.2 — MLB market baseline | Kalshi data collection, visible coverage and collection health, and baseline market-performance display | Implemented and locally activated; release publication awaits Owner approval |
| v1.3 — Unified NFL/MLB experience | One Pops' Edge entry point with consistent navigation, branding and interaction | Tentative target; user journeys and implementation scope remain to be defined |
| Parallel MLB investigation | Evaluate external forecast models and suppliers for possible later admission | Continues independently; no admission or successful challenger is required for v1.2 or v1.3 |

### v1.2 — MLB Kalshi collection and baseline performance

Make existing MLB research useful to the Product Owner: show how well observed
Kalshi probabilities predict outcomes and how complete the underlying evidence is.
Include collection status, separate retrospective and prospective reports, and a
simple baseline-performance display with observation periods, eligible/captured/
scored/missing populations, probability scores, calibration, defined simple
baselines, uncertainty and limitations under the governing protocols.

Release acceptance depends on scientifically honest collection, reproducible
measurement, understandable presentation and documented local operation. It does
not depend on a favorable performance result or demonstrated trading advantage.
Retrospective and prospective populations remain separate. In-progress evidence
must be labelled as such; a release does not close or shorten a study protocol.

External-source admission, further native-model development, policy selection,
operational policy integration, the broader Forecast Intelligence Workspace and
automated wagering are outside this release's acceptance scope. Existing
implemented foundations remain available. See the
[release amendment](docs/RELEASE_DIRECTION_2026-09-12.md) for the replacement
sequencing boundary.

### v1.3 — Unified NFL and MLB experience (tentative)

Bring NFL and MLB together through a shared entry point, consistent navigation,
branding and interaction. A shared application shell and sport selector are the
starting design direction; comparison, performance and data-status destinations
should be consistent where those capabilities exist. Detailed user journeys and
acceptance criteria must be agreed before implementation.

Preserve each sport's workflows, evidence, settlement semantics, measurement
rules and operational authority. A unified interface does not require identical
capabilities, combined scientific populations, a universal schema or the full
Forecast Intelligence Workspace. Hosting and migration decisions remain separate.

### Parallel external MLB model and supplier investigation

Continue investigating usable external forecasts and suppliers alongside both
release paths. Evaluate probability availability, identity, chronology, retention
and downstream-use rights, market independence and cost. The intended outcome is
a documented admission decision; no candidate is presumed admissible. A promising
candidate leads to a separately scoped integration proposal.

Neither v1.2 nor v1.3 waits for supplier success or formal closure of the external
or native-model tracks. Existing native-model findings remain valid historical
results; further native-model work is deferred pending a separate decision. This
roadmap does not authorize vendor messages, purchases, trials or new collection.

## Longer-term capability horizons (no release assigned)

### Horizon 1 — Complete empirical decision lifecycle

Retain the long-term progression from immutable Evidence and Measurement through
Forecast Intelligence, supported Market Edges, governed Forecast Policy, Policy
Forecasts and Opportunity Analysis. Current applicability, policy alignment, the
broader Forecast Intelligence Workspace and policy-driven operational integration
remain future capabilities, not v1.2 gates or automatic v1.3 commitments.

The historical [MLB programme](docs/RELEASE_PLAN_v1.1.0.md) preserves completed
work and future scientific dependencies. Its former whole-programme release gate
is superseded by the September 12 decision; scientific admission and governance
requirements are unchanged.

### Horizon 2 — Richer Forecast Intelligence

Forecast Intelligence matures through more Probability Sources, richer populations, stronger Research Protocols and Research Reviews, and Drift Surveillance. Better evidence produces more defensible Policy Recommendations; Product Owner Governance remains required.

The governing progression remains:

```text
Research Question
        ↓
Edge Claim
        ↓
Empirical Support
        ↓
Market Edge
        ↓
Policy Hypothesis
```

A probability disagreement never establishes a Market Edge by itself.

### Horizon 3 — Multi-Source and Multi-Market Intelligence

Pops' Edge expands comparison across multiple Probability Sources and compatible market venues. More sources do not guarantee improvement; automatic weighting requires future approval.

### Horizon 4 — Broader Domain Expansion

The framework may extend beyond sports where uncertain outcomes, competing Probability Sources, an observable benchmark, objective outcomes, repeatable decisions, and measurable consequences exist.

No non-sports domain is scheduled, and expansion assumes neither a universal schema nor enterprise infrastructure.

## Product surfaces

The planned Forecast Intelligence Workspace remains the long-term research and governance surface; the Opportunity Board remains the operational surface. The bounded v1.2 baseline display and tentative v1.3 shared experience do not require completion of that broader Workspace. Reports communicate state with provenance. None acquires hidden Policy or authority.

## Deferred strategic opportunities

Historical Policy Forecast evaluation or automated Shadow measurement may become valuable but remains unscheduled and subject to separate architectural approval.

Additional providers, venues, sports, and domains are directions, not commitments. No universal schema, broad World Cup rewrite, SaaS, or distributed services are promised.

Native-model expansion beyond one bounded MLB game-winner Model 0—including
totals, run lines, ensembles, automatic retraining, online learning, and cloud
hosting—remains deferred until prospective evidence justifies it.

## Long-term destination

Pops' Edge should become increasingly capable of distinguishing:

> **The evidence supports an edge.**

> **The evidence does not support an edge.**

> **We do not yet know.**

Supported knowledge should produce governed, traceable decisions. Insufficient evidence preserves uncertainty.
