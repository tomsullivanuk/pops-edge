# PRODUCT

## Purpose

Pops' Edge is a quantitative decision platform for discovering and acting upon positive expected value opportunities.

Its distinguishing characteristic is not simply producing forecasts. Pops' Edge determines which Probability Sources deserve operational trust through Forecast Intelligence grounded in empirical Evidence and Measurement. It then applies governed Forecast Policies to identify positive expected value opportunities.

The product follows a clear authority hierarchy:

- **Methodology** establishes how knowledge is discovered.
- **Product** defines the capabilities that transform knowledge into operational decisions.
- **Architecture** defines how those capabilities are implemented.

This document defines the product.

## Product Mission

Pops' Edge exists to identify positive expected value opportunities supported by empirically validated evidence.

It fulfills that mission by collecting durable Evidence, measuring the comparative performance of Probability Sources, developing Forecast Intelligence through reproducible research, governing Forecast Policy, and applying approved policy to current market opportunities.

Sports wagering is the current proving ground for this decision framework, not the platform's defining purpose. The durable product model applies wherever forecasts, outcomes, and market prices can be observed and evaluated.

## Product Principles

### Evidence before opinion

Operational decisions begin with durable observations rather than intuition or anecdote. Evidence records what happened; interpretation follows.

### Uncertainty before assumption

Uncertainty is a legitimate product state.

When Evidence is insufficient, Pops' Edge preserves uncertainty rather than manufacturing confidence.

### Research before trust

Probability Sources are not trusted by reputation. They earn operational trust through Forecast Intelligence grounded in empirical Evidence and Measurement against the Market Benchmark.

### Policy before execution

Research does not directly produce operational behavior. Forecast Intelligence supports Policy Hypotheses, and Product Owner Governance determines which become approved Forecast Policies.

### Governance before automation

Automation executes approved policy; it does not invent policy. Operational recommendations must remain traceable to explicit governance decisions and their empirical support.

### Continuous learning

Operational trust is conditional, not permanent. Forecast Intelligence continues to evaluate Probability Sources, Market Edges, and the empirical foundations of Forecast Policies as new Evidence accumulates.

## Product Capability Hierarchy

Pops' Edge is organized as a sequence of capabilities that transforms observation into governed action:

```text
Research

Identity
        ↓
Evidence
        ↓
Measurement
        ↓
Forecast Intelligence

────────────────────

Policy

Policy Hypothesis
        ↓
Product Owner Governance
        ↓
Forecast Policy

────────────────────

Operations

Forecast Policy Execution
        ↓
Policy Forecast
        ↓
Opportunity Analysis
        ↓
Execution
```

The hierarchy separates empirical discovery from operational decision making. Evidence records what was observed. Forecast Intelligence establishes what the evidence justifies believing. Policy defines what the product has decided to do. Execution records what action was taken.

## Identity

Identity provides the durable foundation for accumulating observations about the same object over time. Significant objects—including events, competitions, participants, Probability Sources, Market Benchmarks, markets, and Forecast Policies—retain stable identities as Evidence changes.

Identity contains no opinion or conclusion. It answers:

> **What object are we observing?**

## Evidence

Evidence consists of durable observations from the outside world, including probability estimates, market prices, event outcomes, and closing market prices. Evidence represents what was observed, not what the platform believes.

Historical integrity is essential: later corrections or updated observations must not erase what was previously known. Evidence answers:

> **What happened?**

## Measurement

Measurement transforms Evidence into reproducible quantitative observations without introducing policy or operational recommendations. Examples include forecast accuracy, calibration, Brier Score, Log Loss, market movement, Closing Line Value, and Comparative Performance metrics.

Measurement supplies objective inputs to Forecast Intelligence. It does not, by itself, grant a Probability Source operational relevance. Measurement answers:

> **What do the observations objectively tell us?**

## Probability Sources

A Probability Source is an external or internal source of probability estimates about uncertain outcomes. It may be a forecasting or statistical model, a prediction system, an expert forecast, a market-derived estimate, or an internally developed model.

No Probability Source is inherently authoritative. All are evaluated under common empirical standards, and all earn operational trust through Forecast Intelligence grounded in empirical Evidence and Measurement.

A recorded probability estimate becomes Evidence. Its provenance must be sufficient to identify the source, forecasted outcome, probability, and observation context while preserving the historical observation.

A Probability Source answers:

> **What probability does this source assign to the outcome?**

### Forecast Providers

A Forecast Provider is a Probability Source that publishes externally generated forecasts. Provider identity determines where an observation originated, not the empirical standard by which it is evaluated.

## Market Benchmark

The Market Benchmark is the role assigned to a Probability Source within a Research Protocol; it is not an intrinsic global identity of that source. It represents wager-backed quoted market pricing: the probability implied by participants' demonstrated willingness to commit capital in the captured two-sided market. Pops' Edge does not claim to observe participants' private beliefs or correct for popularity, loyalty, entertainment, hedging, or unwillingness to wager.

It has three product roles:

- it provides current economic Evidence for Opportunity Analysis; and
- it is the primary empirical comparator for evaluating alternative Probability Sources; and
- its absolute probabilistic performance can be measured independently over its complete eligible population.

Market prices reflect wager-backed quoted behavior under incentives, so Pops' Edge does not assume that an alternative forecast is more informative. They do not provide direct access to private participant belief. Superior absolute forecasting accuracy alone does not establish a Market Edge. Forecast Intelligence must determine whether a Probability Source contributes useful information beyond the Market Benchmark.

Market Benchmark observations preserve market state over time so research and operational decisions can be evaluated against the prices that were actually available. The Market Benchmark answers:

> **What probability is currently embedded in the market price?**

## Forecast Intelligence

Forecast Intelligence is the umbrella product capability that transforms accumulated Evidence and Measurement into reproducible knowledge about the absolute and comparative performance of Probability Sources.

It establishes the basis on which operational trust may be granted, limited, reconsidered, or withdrawn. Forecast Intelligence answers:

> **What does the accumulated evidence justify believing about the comparative performance of Probability Sources?**

Forecast Intelligence encompasses the following capabilities.

### Standalone Probability Source Performance

Standalone Probability Source Performance evaluates one Probability Source over its complete prospectively defined eligible population, independently of every challenger.

It answers:

> **How accurately did this Probability Source estimate eligible outcomes?**

For a source serving as the Market Benchmark, the product presents this result as Market Benchmark Performance. Absolute accuracy is not comparative superiority and is not profitability. Good Calibration does not automatically establish market efficiency, and poor Calibration does not automatically establish an exploitable edge.

For 2026 MLB, PR17 studies Kalshi alone in the regular-season game-winner
domain through two separate standalone Protocols: one retrospective historical-
candlestick Protocol and one prospective point-in-time order-book Protocol.
Each owns its population, Coverage, Measurement, cumulative and time-bounded
performance, uncertainty, limitations, and report. Neither is governed by a
challenger, Edge Claim, paired population, or comparative report.

Both studies use exactly one authoritative representation per event: the
home-team YES probability. Away-team contract information is diagnostic only
and cannot replace, adjust, normalize, average with, validate, or repair the
home-team value or its population membership. MLB Stats API is authoritative
for schedule, status, and Outcome; Kalshi timing and settlement metadata only
corroborate. The motivating hypothesis that Kalshi's MLB probabilities may not
be particularly accurate does not predetermine a finding.

The retrospective population covers qualifying ordinary games before the
immutable activation boundary and uses a same-candle home-team bid/ask-close
midpoint near T-6h. Those candle aggregates are not represented as simultaneous,
executable, or positive-depth quotes. The prospective population begins at the
boundary, keeps every schedule-derived opportunity and failure visible, and uses
the existing positive-depth two-sided home-team order-book midpoint within five
fixed slots from `target_at` through the inclusive exact
`target_at + 5 minutes` endpoint. Slots 0–3 are half-open; slot 4 is closed at
the upper endpoint. A delayed invocation may use only its current slot and
actual acquisition time, with at most one provider call per slot; it never
backdates a quote or catches up missed slots. A later timestamp is prohibited.
Historical data cannot repair a missed prospective capture.

The retrospective Evidence path is separate: an immutable historical candle
observation preserves raw provider aggregates and distinct retrieval/candle
times, and supporting candle derivation selects the authorized home-team
midpoint. It is not an order-book snapshot and cannot satisfy PR16B positive-
depth derivation. A versioned successor Measurement accepts the one derivation
kind authorized by its standalone Protocol without changing historical PR16B
contracts.

The retrospective Protocol and all selection, Coverage, scoring, and reporting
rules are fixed before its archive query and any result calculation or
interpretation. This prevents result-directed selection but does not make later
archive acquisition prospective. Retrospective Evidence cannot enter or repair
a prospective population or support paired comparison under current authority;
its report preserves archive availability, survivorship, revision, timestamp,
schedule-history, aggregation, and non-simultaneity limitations.

The reports remain separate. A Product summary may display them side by side but
cannot pool observations or create a combined 2026 metric. Their descriptive
findings create no Current Scientific Applicability, Market Edge, Policy,
Governance, wagering, Opportunity Analysis, profitability, or production
authority.

### Research Protocols

A Research Protocol defines a reproducible empirical investigation. Pops' Edge
has two sibling families. A `ComparativeResearchProtocol` governs benchmark-
versus-challenger questions, Edge Claims, paired populations, Practical
Significance, Burden of Proof, surveillance, Drift, and Research Review.
Existing `ResearchProtocol` and `ResearchProtocolV2` implementations retain
that comparative meaning unchanged.

A `StandaloneProbabilitySourceProtocol` governs exactly one Probability Source
and descriptive standalone performance. It is not an empty-challenger mode of a
comparative Protocol and has no Claim Set, Edge Claim, pair, comparative
significance, Burden of Proof, Drift, or Review obligation. A source's Market
Benchmark role elsewhere does not make the standalone investigation comparative.

It answers:

> **How will we test this question?**

### Standalone Probability Source Performance Reports

A `ProbabilitySourcePerformanceReport` is the canonical immutable standalone
communication artifact for exactly one standalone Protocol, source, role,
domain, and analysis boundary. It references compatible cumulative and
time-bounded standalone performance, Coverage, uncertainty, limitations, and
provenance without recomputing them. It truthfully reports empty populations and
fails closed on ambiguous or incompatible authority. It contains no challenger,
Claim Set, Edge Claim, comparative result, scientific conclusion, Policy,
Governance, or production authority. The existing
`ComparativePerformanceReport` remains a distinct unchanged artifact.

### Comparative Performance

Comparative Performance evaluates a Probability Source relative to the Market Benchmark. It determines whether observed forecasting performance contains useful information beyond what the market already reflects, including the conditions and limitations under which that conclusion holds.

It answers:

> **How did this Probability Source perform relative to the Market Benchmark?**

Comparison with the Market Benchmark remains the required foundation for Market Edge and operational-trust conclusions. Standalone and Comparative Performance may use different populations and answer different questions; challenger availability or validity never changes the standalone denominator.

### Comparative Performance Reports

A Comparative Performance Report is a durable Forecast Intelligence artifact that communicates an empirical analysis, its supporting population and measurements, its limitations, and its findings. It records analysis and supports review; it does not establish operational policy.

### Edge Claims

An Edge Claim is an explicit empirical assertion under evaluation that a Probability Source outperforms the Market Benchmark under defined conditions. It must be testable through a Research Protocol and grounded in reproducible Evidence and Measurement.

An Edge Claim is narrower than a general judgment that a source is good, and it does not establish a Market Edge or authorize operational use.

### Research Reviews

A Research Review evaluates the current body of Forecast Intelligence relevant to a research question, Edge Claim, Market Edge, or Policy Hypothesis. It may confirm, qualify, contradict, or narrow prior findings; identify a need for more research; or recommend reconsideration of policy.

### Drift Surveillance

Drift Surveillance monitors whether the comparative performance supporting an Edge Claim, Market Edge, or Forecast Policy has materially changed. Markets and Probability Sources evolve, so previously supported advantages may weaken, disappear, or reverse.

Drift Surveillance produces Forecast Intelligence. It does not change Forecast Policy without Product Owner Governance.

### Policy Recommendations

A Policy Recommendation advises that empirical findings be considered for operational use, further research, policy revision, suspension, or retirement. It is an output of Forecast Intelligence, not an approval decision.

## Market Edge

A Market Edge is an empirically demonstrated comparative advantage of a Probability Source relative to the Market Benchmark under defined conditions.

A difference between a Probability Source and the Market Benchmark is not automatically an edge. For example:

```text
Probability Source = 62%
Market Benchmark   = 57%
Difference         =  5%
```

The difference is observable, but it becomes a Market Edge only when Forecast Intelligence provides sufficient empirical support that such differences contain useful information under defined conditions.

The conceptual progression is:

```text
Research Question / Investigation
        ↓
Edge Claim
        ↓
Empirical Support
        ↓
Market Edge
        ↓
Policy Hypothesis
```

Forecast Intelligence establishes and monitors Market Edges. Opportunity Analysis applies their operational expression through approved Forecast Policy; it does not discover them.

## Policy Hypothesis

A Policy Hypothesis is a proposed operational strategy for exploiting one or more empirically supported Market Edges.

It translates research findings into a strategy that Product Owner Governance can evaluate. It may propose which Probability Sources to use, the conditions for use, operational thresholds, eligibility rules, sizing approaches, or risk constraints.

A Policy Hypothesis:

- is not Evidence;
- does not establish a Market Edge;
- does not imply operational approval; and
- may compete with other Policy Hypotheses based on the same empirical evidence.

It separates what the evidence justifies believing from what the product might choose to do.

## Product Owner Governance

Product Owner Governance is the explicit decision boundary between Forecast Intelligence and operational policy. Forecast Intelligence may develop empirical findings, Edge Claims, Research Reviews, Market Edges, and Policy Recommendations; it may not promote them directly into operational behavior.

The Product Owner may approve, reject, narrow, suspend, revise, or retire a Policy Hypothesis or Forecast Policy, or request further research. Those decisions remain traceable to the Forecast Intelligence available at the time.

This preserves the core distinction:

- **Evidence** — what was observed;
- **Forecast Intelligence** — what the evidence justifies believing; and
- **Policy** — what the product has decided to do.

Product Owner Governance answers:

> **Given what we currently know, what operational behavior should the product authorize?**

## Forecast Policy

A Forecast Policy is an approved, durable set of operational rules that translates empirically supported Forecast Intelligence into authorized probability estimates and decisions.

Every Forecast Policy must earn the right to exist through empirical research and reproducible measurement.

A Forecast Policy defines the operational choices required for its purpose, such as eligible Probability Sources, conditions of use, probability rules, thresholds, exclusions, sizing, and risk constraints.

Forecast Policies remain reviewable, reproducible, traceable, and governed. Their history and empirical basis are preserved, and they fail closed when required Evidence is insufficient. New Evidence, Research Reviews, or Drift Surveillance may return a Forecast Policy to Product Owner Governance for reconsideration.

Forecast Policy answers:

> **What operational rules has the product explicitly authorized?**

## Forecast Policy Execution

Forecast Policy Execution applies an approved Forecast Policy to current Evidence. It performs the authorized rules reproducibly without reinterpreting the research or inventing policy.

If policy requirements cannot be satisfied, Forecast Policy Execution fails closed. It answers:

> **Given this approved Forecast Policy and the Evidence currently available, what probability should the product use?**

## Policy Forecast

A Policy Forecast is the durable result of applying an approved Forecast Policy to the Evidence available for a specific event or market at a specific time. It is the probability estimate Pops' Edge has authorized for operational use.

A Policy Forecast is derived product state, not Evidence. It remains traceable to the applicable identity, Evidence, and Forecast Policy so the result can be reproduced and evaluated in its historical context.

It answers:

> **What probability did the approved Forecast Policy produce for this opportunity?**

## Opportunity Analysis

Opportunity Analysis compares an approved Policy Forecast with the current Market Benchmark to identify positive expected value opportunities. This is where Pops' Edge moves from probability estimation to economic decision analysis.

Opportunity Analysis applies upstream research and policy; it does not decide whether a Probability Source deserves trust, establish a Market Edge, or invent Forecast Policy. It answers:

> **Given the probability authorized by Forecast Policy and the price currently offered by the market, does this opportunity have positive expected value?**

### Expected Value

Expected Value measures the economic attractiveness of an opportunity from its operational probability estimate, current market price, and payoff structure.

For a simple binary contract priced at `C`, with an operational probability `P`, expected value per unit is:

```text
EV = P - C
```

when price and payoff use the same normalized scale. Positive Expected Value exists when `P > C`. Transaction costs, liquidity, execution uncertainty, and policy constraints may still make an apparent opportunity ineligible for action.

### Evidence-Supported Positive Expected Value

> **Evidence-Supported Positive Expected Value** is positive expected value produced by an approved Forecast Policy whose operational probability estimate has earned trust through sufficiently current Forecast Intelligence.

Arithmetic identifies a disagreement whenever a selected probability estimate exceeds the market price. That disagreement becomes Evidence-Supported Positive Expected Value only when the opportunity also satisfies the policy's operational requirements.

**This distinction is central to Pops' Edge.** The product does not merely identify disagreements with the market. It identifies positive expected value opportunities for which there is empirical reason to trust the operational probability estimate.

## Opportunity

An Opportunity is a current market state that satisfies an approved Forecast Policy and exhibits positive Expected Value under Opportunity Analysis.

An Opportunity is transient as market conditions change, but it remains explainable through the Market Benchmark, Policy Forecast, Forecast Policy, and Expected Value that produced it.

## Position Sizing

Position Sizing translates an eligible Opportunity into a proposed level of exposure under approved policy. Expected Value alone does not determine exposure.

Sizing may use fixed amounts, fractional Kelly methods, exposure caps, or other explicitly governed approaches. Its inputs, rules, and risk constraints must be reproducible, and missing required inputs cause it to fail closed.

## Execution

Execution is action taken in response to an approved Opportunity, such as recording a wager or position, submitting an order, managing exposure, or recording an operational outcome.

An Opportunity does not require Execution; the Product Owner may choose not to act. Execution answers:

> **What action, if any, was actually taken?**

An individual win or loss does not establish forecast quality. Operational outcomes become Evidence and may contribute to Forecast Intelligence through appropriate Research Protocols. Forecast quality is evaluated across relevant populations, not inferred retrospectively from isolated results.

## Opportunity Board

The Opportunity Board is the principal operational surface for current Opportunities. It presents the outputs of Opportunity Analysis, including the relevant market state, Policy Forecast, Expected Value, policy eligibility, sizing where applicable, and warnings that prevent action.

It does not conduct research or grant operational trust. It answers:

> **What opportunities does the approved policy currently identify, and why?**

## Operational Traceability

Operational recommendations and actions must be traceable through the product capabilities that justified them:

```text
Execution
        ↓
Opportunity and Opportunity Analysis
        ↓
Policy Forecast and Forecast Policy
        ↓
Product Owner Governance
        ↓
Forecast Intelligence
        ↓
Measurement and Evidence
        ↓
Identity
```

This product property allows the Product Owner to understand what was known, what policy authorized, what the product recommended, what action was taken, and what ultimately occurred—without rewriting history. Architecture defines the mechanism that provides this traceability.

## Product Surfaces

Pops' Edge separates research, governance, and operational decision making through purpose-specific surfaces.

### Forecast Intelligence Workspace

The Forecast Intelligence Workspace is the principal interactive surface for Forecast Intelligence. It supports Research Protocols, Comparative Performance, Comparative Performance Reports, Edge Claims, Research Reviews, Drift Surveillance, Policy Recommendations, Policy Hypotheses, and Product Owner Governance.

It answers:

> **What have we learned, how strong is the evidence, and what should we consider doing about it?**

### Opportunity Board

The Opportunity Board is the principal operational surface for current Opportunities. It consumes approved Forecast Policy and current Evidence to show what is actionable now; it does not perform empirical research.

### Reports

Reports provide durable or shareable views of product state and analysis with appropriate provenance. They communicate product state; they do not become hidden sources of policy.

## Product Extensibility

The durable empirical decision framework must survive changes in providers, market venues, sports, and application domains.

Probability Sources and market venues are replaceable participants in common product concepts. Provider-specific acquisition does not define product meaning, and equivalent observations should be evaluated under consistent empirical standards.

Sports wagering is a useful proving ground because it supplies probabilistic forecasts, observable prices, objective outcomes, repeated decisions, and measurable consequences. Those characteristics—not sports itself—define the kind of environment to which Pops' Edge may eventually apply.

Expansion into another domain should not require redefining the core product model.

## Current Product Scope

The current objective is to prove the complete empirical decision lifecycle within sports prediction markets.

The current scope connects durable observation, reproducible empirical research, governed policy, Opportunity Analysis, Position Sizing, and traceable Execution as one complete lifecycle. It proves that Forecast Intelligence can establish operational trust and that approved policy can turn that trust into Evidence-Supported Positive Expected Value opportunities.

The objective is not to maximize integrations, sports, models, or reports. It is to demonstrate that the lifecycle operates coherently, reproducibly, and transparently from Evidence through operational decision.

## What Pops' Edge Is Not

Pops' Edge is not primarily:

- a sports-betting application;
- a forecast aggregator;
- a tip service;
- a system that blindly follows external forecasters;
- a black-box prediction model; or
- a hidden automated trading system.

Pops' Edge is an empirical decision platform that discovers when evidence justifies disagreement with a market and translates that knowledge into governed operational decisions.

## Product Vision

Pops' Edge should become a durable empirical decision platform that learns which Probability Sources deserve operational trust, under what conditions, and when that trust should be reconsidered.

Its defining discipline is distinguishing among three empirical states:

> **The evidence supports an edge.**

> **The evidence does not support an edge.**

> **We do not yet know.**

The product must not manufacture an edge when evidence is absent or insufficient.

**Pops' Edge identifies positive expected value opportunities supported by empirically earned operational trust.**
