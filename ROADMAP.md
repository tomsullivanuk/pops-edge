# Pops' Edge Roadmap

Canonical research inventory: [MLB model experiment register](docs/MLB_MODEL_EXPERIMENT_REGISTER.md) — 23 completed campaigns/studies/diagnostics/evaluations, with stable IDs, source lineage and current decisions. Use it for cross-experiment discussion; dated proposals and decisions below retain their history.

## September 15, 2026 — Performance slice adopted

Part 2 exposes existing NFL weekly results alongside the established MLB reader. Weekly scope is adopted; cumulative NFL charts and Administration controls are deferred. See [contract](docs/PERFORMANCE_READERS_v1.3.md). This is an implementation candidate, not a deployed or published release.

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

## 2027 regular-season in-house pregame track — October 12, 2026

Separate from release acceptance and existing T−6h studies, the Owner has reopened native-model planning toward a paper-alert prototype for selective manual decisions at Kalshi executable prices. This supersedes the earlier deferral solely for planning and documentation; no release target, model execution, production collection or wagering is authorized.

Next decision: discuss the [single strength-rating experiment](docs/MLB_2027_PREGAME_MODEL.md), its five-day cap and continuation gate. If approved, freeze inputs/evaluation before execution and record failures as well as gains. A passing development comparison earns consideration for a separately governed same-time regular-season paper trial, whose forecast and selected net-return evidence remain distinct. Availability timing investigation continues separately without blocking offline modeling or duplicating the current observer.

October 12 follow-up: Tom approved the single offline strength-rating comparison, five focused working-day cap and continuation gate after discussion. The [execution protocol](research/pregame_2027/experiment_01/PROTOCOL.md) freezes inputs and evaluation before fitting. This supersedes the preceding pending-model-execution statement for that comparison only. Paper-alert implementation, new collection, wagering and production changes remain unapproved.

October 12 result: the [single strength experiment](research/pregame_2027/experiment_01/RESULTS.md) completed and failed its continuation gate (average annual Brier gain 0.000334 <0.001). Keep the existing native reference; no challenger promotion or further model sweep is authorized. Paper workflow discussion remains possible but forecast and selected-return evidence are unestablished. Existing studies and production state remain unchanged.

October 12 research discussion: Tom’s hypothesis is that modern AI methods may improve native forecasts against the agreed sportsbook proxy. The [current modern-ML proposal](docs/MLB_2027_MODERN_ML_PROPOSAL.md) recommends a conditional single TabPFN core comparison with a bounded boosting control, before larger player/pitch models. This is not approved training, model admission, access/license acceptance or production scope; the failed strength challenger remains closed.

October 12 setup review: the [actual license/access and compute assessment](docs/MLB_2027_MODEL_ACCESS_COMPUTE_REVIEW.md) identifies 3.5 consumer eligibility as unresolved for the personal hobby use. Local compute is plausible but unbenchmarked; v2 is an explicit, unapproved alternative. No installation, license acceptance, model acquisition or training has occurred.


## Completed bounded v2 comparison — October 12

The authorized local comparison is complete; this supersedes earlier pending-status entries. [Experiment 02 results](research/pregame_2027/experiment_02/RESULTS.md) record exact reference replay, 7,280 chronological development forecasts, and independent score/bootstrap verification. TabPFN-v2 improved average annual Brier by 0.000057915 versus the required 0.001; CatBoost worsened it by 0.000479901. Both fail their frozen gates. Sportsbook opening consensus remains better on both proper scores in each year on the original common population. These are reused development seasons, not untouched holdouts. Retain the reference and promote neither learner; no further tuning is authorized automatically.

The pinned v2 checkpoint worked on local Metal without paid compute or model-service uploads. The separate 3.5 licensing inquiry remains pending. Existing collectors, T−6h studies, production pins and schedules remain intact; draft PR 86 remains for review and is not approved for merge.


## Proposed next readiness gate — October 12

The authorized read-only [player-component feasibility review](docs/MLB_2027_COMPONENT_FEASIBILITY.md) is complete. Extensive player-game totals do not supply a validated season-scale PA/pitch corpus; only four distinct detailed games are retained. Propose one bounded Retrosheet PA readiness pass, then one starter–batter categorical outcome experiment against a strong matchup baseline if Tom agrees its frozen protocol. Acquisition, fitting and integration remain unapproved. Component accuracy is a separate gate from game-winner improvement against the sportsbook proxy.


## Approved readiness pass completed — October 12

Tom approved the one-season pass. [Results](research/pregame_2027/component_readiness/RESULTS.md): 100 frozen games, 7,496 PA, exact sampled count reconciliation, usable IDs/labels and distinct suspended-play dates; 17.44 MB transferred. Sample-level feasibility passes, with whole-season/multi-season validation still required. This supersedes preceding unapproved-readiness status, without changing prior failed experiments. The [concrete experiment 03 protocol](research/pregame_2027/component_experiment/PROTOCOL.md) is proposed for agreement before additional seasons or fitting. No model fit occurred.


## Experiment 03 authorized; numerical stop — October 12

Tom approved the bounded PA component experiment. Full-source validation and feature preparation passed across 2022–2025; implementation was frozen at `0e0f94f`. The first baseline training fit then failed the absolute summed-gradient convergence requirement and stopped before any validation scores, challenger fit or outer forecast. [The failure record](research/pregame_2027/experiment_03/RESULTS.md) is a numerical stop, not evidence that the component failed its accuracy gate. [A narrow numerical amendment](research/pregame_2027/experiment_03/NUMERICAL_AMENDMENT.md), preserving the model objective's minimizer through whole-objective normalization, remains for Tom's agreement before a restart. No more fit is authorized automatically.


## Normalized restart stopped — October 12

Tom approved whole-objective normalization; the first baseline configuration passed, but the next configuration failed the amended gradient gate (2.67e-9 versus 1e-9). No challenger or outer evaluation occurred. [Failure record](research/pregame_2027/experiment_03/RESULTS.md) and [proposed 1e-8 tolerance amendment](research/pregame_2027/experiment_03/TOLERANCE_AMENDMENT.md) preserve the stopped run and next decision. No accuracy conclusion or automatic restart.


## Experiment 03 complete — October 12

After Tom approved the final numerical criterion, the bounded conditional PA comparison completed with all sixteen fits accepted and exact saved-forecast replay. [Results](research/pregame_2027/experiment_03/RESULTS.md): average annual relative log-loss reduction 0.095041%, 14-day interval [0.077841%, 0.113720%], below the agreed 0.5% gate. Both years and Brier improve, but the practical-size gate fails. Close this specification without automatic tuning, promotion or game-level integration. Preserve this small conditional component gain and both earlier numerical stops; no winner-probability or market-edge conclusion. The separate 3.5 inquiry remains pending.


## Player-information assessment and final lineup evidence — October 12

The [WAR/player-input gap assessment](docs/MLB_2027_PLAYER_INFORMATION_GAPS.md) distinguishes retained winner inputs, tested extensions, owned raw information and missing player-quality measures. Recommend discussing one timestamped preseason lineup-offense projection comparison against our lagged rates, holding lineups/weights/game learner fixed; external vintage, membership/export access and identity readiness must be verified first. This is a read-only proposal, with no new acquisition or fit authorized.

The [final two-game lineup observation](docs/MLB_2027_LINEUP_OBSERVATION_FINAL.md) supersedes interim pending status: all four complete orders appeared more than three hours before scheduled starts. Preserve the process-loss gap, first-game premature Warmup stop and corrected second-game stop; actual first pitch and explicit pitcher confirmation remain unknown. The single observer has ended. This supports the practical working assumption for two games, not general reliability or model edge; T−6h studies remain intact.


## Projection repository feasibility resolved — October 12

The [updated player-information assessment](docs/MLB_2027_PLAYER_INFORMATION_GAPS.md#the-scientific-question-our-checks-and-toms-decisions) specifies four preseason hitter files (2022–2025), rate/vintage/ID fields and exact populations. All 9,704 native games join uniquely to retained initial lineups, with 174,672 slots / 1,022 unique batter RetroIDs; independent post-join scores and lineup registry checks pass. No external projection files or provider-player bridge are retained, and actual forecast coverage/vintages remain unverified. Read-only provider discovery is already authorized and owned by the coordinating researcher. No further routine approval is needed; only a concrete paid/new-account option or the eventual frozen experiment requires Tom's decision. No acquisition or training occurred.


## Projection data comparison ready for agreement

All four Owner-supplied exports are readable locally, with high measured coverage and a conflict-free 1,022-player official/Retrosheet bridge. [One concrete proposal](docs/MLB_2027_PROJECTION_COMPARISON_PROPOSAL.md) compares fixed preseason event-rate estimates with our lagged estimates under the same winner learner/lineup weights, retaining missing-player fallbacks. Year assignment of the numbered additional files awaits one specific confirmation. No model fit is authorized or executed. Information-improvement and market-competitiveness gates remain distinct.


## Projection year assignments resolved

Four Owner-labelled replacement exports match the original four CSVs byte-for-byte and by normalized records. The previous provisional year mapping is confirmed by the supplied provenance, with no data correction. Year-specific coverage audits pass again; raw originals/replacements remain private. [The comparison proposal](docs/MLB_2027_PROJECTION_COMPARISON_PROPOSAL.md) is ready for explicit experiment agreement. No further year-confirmation question is needed; no training has started. Historic archive publication/revision limitations remain explicit.


## Approved Steamer comparison completed

Tom approved the matched winner comparison at `1d64e15`; implementation was frozen at `43d8161` before fitting. [Experiment 04 results](research/pregame_2027/experiment_04/RESULTS.md): 2024 control-minus-Steamer Brier +0.001005688, 2025 −0.000057538; average +0.000474075 versus required +0.001, with 14-day interval [−0.000423151,+0.001021038]. Both information-improvement and sportsbook-competitiveness gates fail. Exact prediction replay and separate measurement/bootstrap checks pass, with every game retained and declared missing-player fallbacks. Close this tested specification without retuning, promotion or integration. Reused-development and archive-vintage limitations remain explicit; production/T−6h protocols stay intact.


## Approved information-chain diagnostic completed

Tom approved a one-session no-fit batting/translation diagnostic, frozen at `b87d364`. [Decision memo](research/pregame_2027/information_chain/DECISION.md): 349,025 comparable initial-nine opportunities; Steamer is slightly worse in 2024 and better in 2025, with equal-year MSE gain +0.000070274 and 14-day interval [−0.000049266,+0.000172273]. Saved winner models visibly respond (about 2.23 pp mean absolute probability change). Weighted side-level accuracy is worse, but it is not the model's home-away differential target and does not locate a causal aggregation failure. Independent raw-value, score, trace and block verification passes. Conclusion inconclusive; explicitly stop without a fifth fit or translator rewrite. Existing failed gates remain failed; raw events/traces stay private.
