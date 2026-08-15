# The Empirical Research Methodology of Pops' Edge

**Version:** 1.0 (Draft)  
**Status:** Draft for Editorial Review

---

# Preface

## Purpose

This document defines the **Empirical Research Methodology** governing Pops' Edge.

It establishes the principles by which empirical evidence is collected, measured, interpreted, and translated into operational decisions.

The methodology exists independently of any particular software architecture, implementation technology, forecasting model, market provider, or sporting domain. Those components may evolve over time. The methodology defines the standards by which they are evaluated.

Accordingly, this document is the highest-level governing artifact of the Pops' Edge project.

---

## Scope

The methodology described herein defines:

- the purpose of Pops' Edge;
- the vocabulary used throughout the project;
- the research principles governing empirical investigation;
- the structure of Research Protocols;
- the collection and measurement of empirical evidence;
- the generation of Comparative Performance Reports;
- the evaluation of Edge Claims;
- the identification of Evidence-Supported Positive Expected Value; and
- the relationship between empirical research and operational decision-making.

This document intentionally does **not** prescribe software architecture, implementation technologies, programming languages, databases, user interfaces, or operational workflows except where necessary to preserve methodological integrity.

---

## Authority

The Empirical Research Methodology is the highest-level design authority for Pops' Edge.

Its authority flows downward through the project:

```text
Empirical Research Methodology
            ↓
         Product
            ↓
      Architecture
            ↓
      Implementation
```

Accordingly:

- Product decisions shall conform to the Empirical Research Methodology.
- Architectural decisions shall conform to the Product.
- Implementation decisions shall conform to the Architecture.

When conflicts arise, the higher-level authority governs.

---

## Guiding Philosophy

Pops' Edge is not fundamentally a forecasting system, a betting application, or a model-comparison tool.

It is an empirical research platform whose purpose is to determine whether statistically and practically meaningful Market Edges exist, to measure the strength of the evidence supporting those edges, and to identify only those current opportunities whose positive expected value is supported by that evidence.

The methodology therefore begins from scientific neutrality.

It does not presume that any Alternative Probability Source outperforms the Market Benchmark.

It does not presume that Market Edges exist.

It does not presume that wagering is appropriate.

Instead, it requires those conclusions to be earned through prospective experimental design, reproducible evidence collection, rigorous statistical analysis, and disciplined interpretation.

---

## Scientific Integrity

The methodology is founded upon several enduring principles.

Evidence is collected prospectively.

Measurements are reproducible.

Research remains falsifiable.

Scientific conclusions remain provisional.

Operational decisions remain distinct from scientific conclusions.

Throughout this document, one principle serves as the foundation for all others:

> **Evidence is permanent. Conclusions are provisional.**

---

## Versioning

This document is intentionally versioned.

Editorial improvements and clarifications may be incorporated without changing the methodology.

Material changes to the empirical research methodology require a new methodology version because they alter the meaning of the scientific conclusions produced by Pops' Edge.

The methodology is expected to evolve more slowly than the Product, Architecture, or Implementation.

Its purpose is to provide a stable intellectual foundation upon which those other components may safely evolve.

# Chapter 1 — Purpose

## 1.1 Mission

Pops' Edge is an empirical research platform that accumulates empirical evidence to determine whether statistically and practically meaningful Market Edges exist, and informs operational decisions only when that evidence supports Evidence-Supported Positive Expected Value.

The purpose of Pops' Edge is not to maximize wagering activity. Its purpose is to determine whether the available evidence justifies wagering activity.

Prediction markets aggregate substantial information about the likely outcomes of future events. A forecasting model that produces plausible probabilities—or even predicts outcomes accurately—does not therefore possess a Market Edge. To establish a Market Edge, an Alternative Probability Source must demonstrate superior comparative forecasting performance relative to the Market Benchmark within a defined research domain.

Pops' Edge treats that proposition as an empirical question. It does not presume that any Alternative Probability Source, regardless of reputation or methodology, outperforms the market. It must remain equally willing to conclude that the Market Benchmark itself represents the best available estimator of event probabilities.

If the evidence supports that conclusion, the appropriate operational decision is:

> **No wager.**

---

## 1.2 Purpose

The purpose of Pops' Edge is to:

1. Measure the predictive performance of market-based and alternative Probability Sources.
2. Compare every Alternative Probability Source against the Market Benchmark under equivalent research conditions.
3. Determine whether any Alternative Probability Source demonstrates statistically and practically meaningful superior comparative forecasting performance.
4. Accumulate empirical evidence through reproducible Research Protocols.
5. Measure the strength of the evidence supporting every Edge Claim.
6. Identify only those current opportunities whose expected value is supported by an applicable Market Edge.
7. Recommend restraint whenever the available evidence fails to justify operational confidence.

The methodology is intentionally designed to produce trustworthy conclusions rather than frequent opportunities.

---

## 1.3 The Market as the Benchmark

The Market Benchmark occupies a unique role within Pops' Edge.

It is not merely another Probability Source.

It is the benchmark against which every Alternative Probability Source is evaluated.

Accordingly, the first empirical question is:

> **How accurately does the Market Benchmark predict outcomes under the defined research conditions?**

Only after establishing the benchmark may Pops' Edge ask:

> **Does an Alternative Probability Source perform better?**

The burden of proof always rests with the challenger.

An Alternative Probability Source does not establish a Market Edge merely by forecasting accurately. It must demonstrate superior Comparative Performance relative to the Market Benchmark.

The Market Benchmark is not a default wagering strategy.

In the absence of a demonstrated Market Edge, transaction costs, market frictions, and statistical uncertainty generally make wagering inappropriate.

The default operational conclusion therefore remains:

> **No wager.**

---

## 1.4 Evidence-Supported Positive Expected Value

A disagreement between an Alternative Probability Source and the Market Benchmark may imply theoretical positive expected value.

Such disagreement alone does not establish a Market Edge.

Nor does it justify wagering.

Pops' Edge therefore distinguishes between:

**Theoretical Positive Expected Value**

The mathematical expected value implied by a probability estimate and a current market price.

and

**Evidence-Supported Positive Expected Value**

Positive expected value whose underlying probability estimate is supported by a currently applicable Market Edge established through empirical evidence under a Research Protocol.

This distinction is fundamental.

A large disagreement between a forecasting model and the market may produce substantial theoretical expected value while lacking empirical support.

Conversely, a scientifically supported Market Edge may exist while no current market price offers attractive expected value.

Research credibility and current economic opportunity must both be present before Pops' Edge considers action.

---

## 1.5 Empirical Neutrality

Pops' Edge begins every investigation from empirical neutrality.

Its purpose is not to prove that Market Edges exist.

Its purpose is to determine what the evidence supports.

Accordingly, the methodology is equally capable of concluding that:

- an Alternative Probability Source outperforms the Market Benchmark;
- the Market Benchmark performs better than an Alternative Probability Source;
- comparative performance differs across prospectively defined research domains;
- the available evidence is insufficient to distinguish among Probability Sources; or
- no statistically and practically meaningful Market Edge has been demonstrated.

Each represents a successful scientific outcome.

The absence of a demonstrated Market Edge is not failure.

It is evidence.

---

## 1.6 Scope

Version 1.0 of this methodology applies to pregame probabilistic forecasting for sporting events.

Pregame and in-game forecasting represent different prediction problems because they incorporate fundamentally different information sets.

Accordingly, this methodology does not combine pregame and in-game observations within the same body of empirical evidence.

Within this scope, Pops' Edge seeks to:

- measure the forecasting performance of the Market Benchmark;
- measure the forecasting performance of Alternative Probability Sources under equivalent research conditions;
- compare those sources using reproducible statistical methods;
- determine whether observed differences are statistically and practically meaningful;
- identify research domains, if any, in which Market Edges exist;
- monitor whether previously demonstrated Market Edges remain representative of current comparative performance; and
- allow those findings to inform operational decision-making without permitting research conclusions themselves to execute operational actions.

Although Version 1.0 is limited to pregame sports forecasting, the methodology is intended to remain applicable as sports, Probability Sources, market providers, statistical methods, and implementation technologies evolve.

---

## 1.7 Standard of Success

The scientific standard of success for Pops' Edge is not profitability.

The scientific standard is the production of trustworthy, reproducible comparative evidence from which reliable operational decisions may be made.

Realized profitability is an important downstream consequence of a successful methodology.

It is not the evidence by which the methodology is validated.

Accordingly, Pops' Edge seeks to distinguish reliably among:

- demonstrated comparative advantage;
- insufficient evidence; and
- absence of demonstrated comparative advantage.

Only the first may support a Market Edge.

Only a currently applicable Market Edge may support Evidence-Supported Positive Expected Value.

Only Evidence-Supported Positive Expected Value may justify consideration of operational action.

This hierarchy intentionally places empirical evidence before economic activity.

---

## 1.8 Governing Principle

The purpose of Pops' Edge is not to identify more wagering opportunities.

Its purpose is to determine which opportunities, if any, deserve trust.

Accordingly, the governing sequence of Pops' Edge is:

```text
Research
        ↓
Evidence
        ↓
Confidence
        ↓
Opportunity
        ↓
Operational Decision
```

When the available evidence does not justify confidence, Pops' Edge does not infer a Market Edge.

The correct conclusion is:

> **No Evidence-Supported Positive Expected Value has been demonstrated.**

The willingness to reach that conclusion is one of the defining strengths of the Empirical Research Methodology.

# Chapter 2 — Definitions

## 2.1 Purpose

The Empirical Research Methodology of Pops' Edge depends upon precise terminology.

The terms defined in this chapter establish the vocabulary used throughout this methodology.

Where a term has broader meanings in statistics, forecasting, finance, software engineering, or common usage, the definitions contained herein govern its use within Pops' Edge.

These definitions are normative.

---

## 2.2 Probability Source

A **Probability Source** is any source that produces probabilistic estimates for future events before those outcomes are known.

Probability Sources may include:

- prediction markets;
- sportsbooks or market-derived consensus estimates;
- published forecasting services;
- statistical models;
- ensemble models; and
- internally developed forecasting models.

A Probability Source is evaluated only by the probabilities it actually produces under the conditions defined by a Research Protocol.

---

## 2.3 Market Benchmark

The **Market Benchmark** is the market-derived Probability Source against which Alternative Probability Sources are evaluated.

Its purpose is to establish the comparative standard for Edge Claims.

The Market Benchmark is itself measured.

It is not presumed to be efficient or superior merely because it is market-derived.

The benchmark probability is determined using the canonical methodology prospectively defined by the governing Research Protocol.

---

## 2.4 Alternative Probability Source

An **Alternative Probability Source** is any Probability Source evaluated against the Market Benchmark.

Its purpose is to determine whether superior Comparative Performance can be demonstrated under the governing Research Protocol.

The burden of proof always rests with the Alternative Probability Source.

---

## 2.5 Research Protocol

A **Research Protocol** is the immutable specification governing one empirical investigation.

A Research Protocol defines, at minimum:

- the scientific question;
- the Research Population;
- the Market Benchmark;
- participating Alternative Probability Sources;
- canonical probability representations;
- Research Snapshot timing;
- capture and synchronization tolerances;
- outcome-resolution rules;
- Approved Research Dimensions;
- primary and supporting performance measures;
- statistical methodology;
- Practical Significance requirements;
- Burden of Proof;
- Time-Bounded Surveillance;
- Drift criteria; and
- Research Review schedule.

A material change to any scientific rule creates a new protocol version.

One Research Protocol may investigate multiple Alternative Probability Sources.
Each distinct Alternative Probability Source-versus-Market Benchmark hypothesis
within the applicable Research Domain is represented by a distinct Edge Claim.

---

## 2.6 Research Population

A **Research Population** is the prospectively defined population of events to which a Research Protocol applies.

Eligibility and exclusion criteria are established before outcomes are known.

Evidence belongs to a Research Population because it satisfies those criteria—not because it is recent.

Evidence does not become invalid merely because it becomes old.

---

## 2.7 Research Snapshot

A **Research Snapshot** is the immutable record of one qualifying event at the protocol-defined pregame capture point.

A Research Snapshot preserves:

- event identity;
- proposition identity;
- scheduled start;
- capture chronology;
- Market Benchmark observation;
- Alternative Probability Source observations;
- Approved Research Dimension classifications;
- provenance; and
- capture diagnostics.

The Research Snapshot represents the pregame information state used for subsequent scientific evaluation.

---

## 2.8 Synchronized Evidence

**Synchronized Evidence** consists of Probability Source observations captured sufficiently close in time to represent materially equivalent information states.

Synchronization requirements are defined prospectively by the governing Research Protocol.

Observations that violate synchronization requirements remain historical Evidence but do not contribute to Comparative Performance under that protocol.

---

## 2.9 Evidence

**Evidence** is an immutable observation of reality.

Evidence records what was observed.

It does not interpret what those observations mean.

Evidence includes, where applicable:

- Probability Source observations;
- market observations;
- contextual observations required by the Research Protocol; and
- authoritative Outcome Observations.

Evidence is permanent.

Interpretation is replaceable.

---

## 2.10 Outcome Observation

An **Outcome Observation** is immutable Evidence recording the authoritative resolution of an event.

The authoritative outcome source and resolution rules are defined prospectively by the governing Research Protocol.

---

## 2.11 Measurement

A **Measurement** is a deterministic quantitative result derived from Evidence according to the methodology defined by the governing Research Protocol.

Examples include:

- Brier Score;
- Log Loss;
- Calibration;
- coverage; and
- event-level Comparative Performance.

Measurements are reproducible.

They are not observations of reality.

---

## 2.12 Comparative Performance

**Comparative Performance** is the measured difference in forecasting quality between the Market Benchmark and an Alternative Probability Source over their common qualifying evidence set.

Comparative Performance is pair-specific.

It is the principal scientific subject investigated by Pops' Edge.

---

## 2.13 Approved Research Dimension

An **Approved Research Dimension** is a prospectively approved explanatory variable used to investigate whether Comparative Performance differs across scientifically meaningful portions of a Research Population.

Every Approved Research Dimension must satisfy:

1. Scientific Plausibility.
2. Comparative Relevance.
3. Prospective Definition.
4. Stability.
5. Snapshot Availability.
6. Operational Utility.

Approval of individual Research Dimensions does not authorize arbitrary combinations among them.

---

## 2.14 Progressive Refinement

**Progressive Refinement** is the controlled process by which broader scientific questions justify progressively narrower investigation.

Pops' Edge prefers:

> **deeper evidence before narrower segmentation.**

Progressive Refinement exists to reduce overfitting, data dredging, and uncontrolled multiple comparisons.

---

## 2.15 Comparative Performance Report

A **Comparative Performance Report** is the immutable scientific report summarizing Comparative Performance under one Research Protocol through one analysis boundary.

It presents findings.

It does not establish Market Edges.

It does not authorize operational decisions.

---

## 2.16 Cumulative Evidence

**Cumulative Evidence** is the complete qualifying body of Evidence belonging to the applicable Research Population through a defined analysis boundary.

It represents the historical scientific record.

---

## 2.17 Time-Bounded Surveillance

**Time-Bounded Surveillance** is the protocol-defined evaluation of recent Comparative Performance used to determine whether current behavior remains consistent with the historical relationship established by Cumulative Evidence.

Its purpose is surveillance.

It does not replace Cumulative Evidence.

---

## 2.18 Drift

**Drift** is a prospectively defined material departure of current Comparative Performance from the historical relationship established by Cumulative Evidence.

Drift is a scientific finding.

It triggers Research Review.

It does not independently change an Edge Claim.

---

## 2.19 Research Review

A **Research Review** is the process by which Pops' Edge evaluates the findings contained within a Comparative Performance Report against the Burden of Proof established by the governing Research Protocol.

Each completed Research Review assesses exactly one Edge Claim and records
exactly one completed scientific conclusion. One Comparative Performance Report
may provide empirical support for multiple claim-specific Research Reviews.

Research Reviews occur:

- at scheduled review intervals; or
- following predefined material events.

Evidence accumulates continuously.

Research conclusions change discretely.

---

## 2.20 Burden of Proof

The **Burden of Proof** is the prospectively defined scientific standard an Edge Claim must satisfy before Pops' Edge recognizes a Market Edge.

At minimum it includes:

- primary endpoint;
- statistical significance;
- Practical Significance;
- supporting measures;
- Evidence validity;
- and protocol compliance.

The Burden of Proof is defined before outcomes are known.

---

## 2.21 Edge Claim

An **Edge Claim** is an explicit scientific hypothesis that an Alternative Probability Source outperforms the Market Benchmark within a defined research domain under a specified Research Protocol.

An Edge Claim begins as a hypothesis.

It becomes supported only through Research Review.

Each Edge Claim represents one Alternative Probability Source-versus-Market
Benchmark hypothesis under one Research Protocol and Research Domain.

---

## 2.22 Market Edge

A **Market Edge** is the scientific conclusion that an Alternative Probability Source has demonstrated statistically and practically meaningful superior Comparative Performance relative to the Market Benchmark within a defined research domain under a governing Research Protocol.

A Market Edge is historical scientific knowledge.

A Market Edge is established when an Edge Claim first receives a qualifying
completed Research Review conclusion of Supported or Strongly Supported. At most
one historical Market Edge is established for an Edge Claim. It identifies that
Edge Claim and the first qualifying completed Research Review.

Later Research Reviews do not mutate, replace, erase, or recreate the Market
Edge. A later qualifying completed Research Review may restore Current
Scientific Applicability to the same historical Market Edge; restoration does
not create another Market Edge.

It is bounded by:

- the Research Protocol;
- the Research Population;
- the applicable research domain;
- and the Evidence supporting it.

---

## 2.23 Current Scientific Applicability

**Current Scientific Applicability** is the condition in which a Market Edge whose latest completed conclusion is Supported or Strongly Supported remains eligible to inform current Opportunity Analysis.

Such a Market Edge may lose Current Scientific Applicability because of:

- Drift;
- Research Review;
- an unresolved scheduled Research Review obligation;
- protocol incompatibility;
- Research Population incompatibility; or
- another prospectively defined material event.

Historical support remains intact.

Operational reliance is suspended.

---

## 2.24 Evidence-Supported Positive Expected Value

**Evidence-Supported Positive Expected Value** is the property of a current opportunity in which:

- a currently applicable Market Edge provides empirical justification for trusting an Alternative Probability Source over the Market Benchmark; and
- the current market price produces positive expected value after applicable costs and operational constraints.

A Market Edge establishes scientific credibility.

Evidence-Supported Positive Expected Value establishes current operational opportunity.

---

## 2.25 Scientific Inference

A **Scientific Inference** is the interpretation of Measurements under a Research Protocol.

Scientific Inferences remain provisional.

They evolve as Evidence accumulates.

Changing a Scientific Inference does not alter the Evidence from which it was derived.

---

## 2.26 Operational Decision

An **Operational Decision** determines whether and how to act upon Evidence-Supported Positive Expected Value.

Operational Decisions consider, among other factors:

- current market conditions;
- liquidity;
- transaction costs;
- position sizing;
- portfolio exposure;
- and operational policy.

Operational Decisions consume scientific conclusions.

They do not create them.

---

## 2.27 Relationship Among the Terms

The empirical research process may be summarized as:

```text
Reality
        ↓
Immutable Evidence
        ↓
Measurement
        ↓
Comparative Performance
        ↓
Comparative Performance Report
        ↓
Research Review
        ↓
Edge Claim Assessment
        ↓
Market Edge
        ↓
Evidence-Supported Positive Expected Value
        ↓
Operational Decision
```

Throughout this methodology, Pops' Edge preserves one fundamental distinction:

> **Evidence is permanent. Conclusions are provisional.**

# Chapter 3 — Research Principles

## 3.1 Purpose

The Empirical Research Methodology of Pops' Edge is governed by a set of enduring Research Principles.

These principles establish how empirical evidence is collected, interpreted, and translated into operational decisions.

They are intentionally independent of:

- sports;
- Probability Sources;
- statistical implementations;
- software architecture; and
- implementation technology.

Every Research Protocol, product decision, architectural decision, and implementation shall conform to these principles.

---

## 3.2 Principle 1 — Empirical Neutrality

> **Pops' Edge begins every investigation without assuming that a Market Edge exists.**

The purpose of research is to determine what the Evidence supports.

It is not to prove that an Alternative Probability Source outperforms the Market Benchmark.

The methodology must remain equally capable of concluding that:

- an Alternative Probability Source demonstrates superior Comparative Performance;
- the Market Benchmark performs better;
- comparative differences vary across approved research domains;
- the available Evidence is insufficient; or
- no Market Edge exists.

The absence of a demonstrated Market Edge is a valid scientific conclusion.

---

## 3.3 Principle 2 — The Market Is the Benchmark

> **Every Edge Claim begins by establishing the predictive performance of the Market Benchmark under the same research conditions used to evaluate the challenger.**

The Market Benchmark is not presumed to be correct.

It is measured.

Alternative Probability Sources are judged only through direct comparison with the Market Benchmark under equivalent research conditions.

The burden of proof rests entirely with the challenger.

---

## 3.4 Principle 3 — Prospective Experimental Design

> **Every empirical investigation is completely specified before the relevant outcomes are known.**

Research Protocols prospectively define:

- the scientific question;
- the Research Population;
- participating Probability Sources;
- capture timing;
- Approved Research Dimensions;
- statistical methodology;
- Burden of Proof;
- and Research Review schedule.

Research questions are not rewritten after observing results.

---

## 3.5 Principle 4 — Pregame Research

> **Pregame forecasting and in-game forecasting are distinct research domains.**

Pregame probabilities and live probabilities represent different information states.

Accordingly, they are not combined within the same Research Protocol unless a future methodology explicitly establishes a new research domain.

---

## 3.6 Principle 5 — Synchronized Evidence

> **Direct comparative evaluation requires materially equivalent information states.**

Each Research Protocol therefore defines:

- one automated pregame capture point;
- capture tolerance; and
- synchronization tolerance.

Information timing must never be mistaken for forecasting skill.

---

## 3.7 Principle 6 — Reproducibility

> **Independent researchers applying the same Research Protocol to the same Evidence should obtain materially identical Measurements and findings.**

Accordingly:

- Evidence is immutable.
- Measurements are deterministic.
- Research Protocols are versioned.
- Analytical provenance is preserved.

Scientific conclusions must be reproducible.

---

## 3.8 Principle 7 — Evidence Before Action

> **Research precedes operational decision-making.**

The governing sequence is:

```text
Research
        ↓
Evidence
        ↓
Confidence
        ↓
Opportunity
        ↓
Operational Decision
```

Scientific research determines whether a Market Edge exists.

Operational analysis determines whether that Market Edge creates a current Evidence-Supported Positive Expected Value opportunity.

---

## 3.9 Principle 8 — Default to No Wager

> **When the Burden of Proof has not been satisfied, Current Scientific Applicability is absent, or operational requirements fail, the default operational conclusion is No Wager.**

This includes situations in which:

- Evidence is insufficient;
- uncertainty remains excessive;
- Practical Significance is absent;
- supporting measures fail;
- Current Scientific Applicability has been suspended;
- or operational constraints eliminate Evidence-Supported Positive Expected Value.

Restraint is an intended capability of Pops' Edge.

---

## 3.10 Principle 9 — Explicit Burden of Proof

> **Every Research Protocol prospectively defines the Burden of Proof required to establish a Market Edge.**

The Burden of Proof distinguishes:

- statistical significance;
- Practical Significance;
- primary endpoint;
- supporting measures;
- and protocol validity.

It is never altered retrospectively because the observed results appear favorable.

---

## 3.11 Principle 10 — Progressive Refinement

> **Research progresses from broader questions toward narrower questions only after the broader Evidence justifies refinement.**

Pops' Edge therefore prefers:

> **deeper evidence before narrower segmentation.**

This principle exists to reduce:

- overfitting;
- data dredging;
- uncontrolled multiple comparisons;
- retrospective hypothesis construction; and
- false discovery.

Research Dimensions are approved prospectively.

Cross-dimensional combinations require explicit justification.

---

## 3.12 Principle 11 — Evidence Evolves; History Does Not

> **Evidence accumulates continuously. Research conclusions change discretely.**

Evidence is never rewritten.

Earlier Comparative Performance Reports remain historically correct.

Later Research Reviews may strengthen, weaken, or overturn previous scientific conclusions.

Historical conclusions remain part of the permanent scientific record.

---

## 3.13 Principle 12 — Missing Evidence Remains Missing

> **Evidence not validly captured under the governing Research Protocol is not retrospectively manufactured.**

Missing observations remain missing.

Historical archives may support separate retrospective research.

They do not repair prospective Evidence.

Coverage is itself scientific Evidence.

---

## 3.14 Principle 13 — Comparative Evidence Is Pair-Specific

> **Each Alternative Probability Source is evaluated against the Market Benchmark using its own common eligible Evidence set.**

Different challengers may legitimately possess different sample sizes.

Pair-specific populations are reported explicitly.

Comparability is never implied where it does not exist.

---

## 3.15 Principle 14 — Historical Evidence and Current Applicability

> **Cumulative Evidence establishes historical knowledge. Time-Bounded Surveillance evaluates whether that knowledge remains applicable.**

Historical Evidence is preserved.

Current performance is monitored separately.

The methodology therefore rejects arbitrary recency weighting in favor of explicit surveillance.

---

## 3.16 Principle 15 — Drift Requires Research Review

> **Drift detection triggers Research Review. It does not independently alter an Edge Claim.**

When a protocol-defined Drift threshold is crossed:

```text
Time-Bounded Surveillance
        ↓
Material Event
        ↓
Operational reliance suspended
        ↓
Research Review
        ↓
Edge Claim reassessment
```

Scientific conclusions change only through Research Review.

---

## 3.17 Principle 16 — Research and Operations Remain Separate

> **Scientific conclusions inform operational decisions. They do not replace them.**

Research establishes Market Edges.

Operational analysis determines whether those Market Edges create current Evidence-Supported Positive Expected Value.

Execution remains a separate concern.

---

## 3.18 Principle 17 — Research Questions Must Be Scientifically Legitimate

> **Pops' Edge investigates only prospectively approved Research Dimensions possessing scientific and operational justification.**

Every Approved Research Dimension must satisfy:

- Scientific Plausibility;
- Comparative Relevance;
- Prospective Definition;
- Stability;
- Snapshot Availability; and
- Operational Utility.

Methodological discipline reduces multiple-comparison risk.

It does not repeal statistics.

---

## 3.19 Principle 18 — Falsifiability

> **Every Edge Claim must remain capable of being disproved by future Evidence.**

A historical Market Edge remains permanently preserved as the record of the conclusion reached at its original review boundary. Its Current Scientific Applicability is not permanent.

Every Market Edge remains subject to:

- additional Evidence;
- Time-Bounded Surveillance;
- Drift;
- Research Review;
- and possible withdrawal of Current Scientific Applicability.

An Edge Claim whose current scientific support cannot be weakened or withdrawn by future Evidence is not scientifically falsifiable.

---

## 3.20 Governing Principle

Taken together, these principles establish the philosophy of Pops' Edge.

The methodology exists to produce trustworthy empirical knowledge.

That knowledge is created through:

- prospective experimental design;
- reproducible Evidence collection;
- disciplined statistical measurement;
- controlled scientific interpretation; and
- deliberate separation between empirical research and operational decision-making.

Throughout the methodology, one principle governs all others:

> **Evidence is permanent. Conclusions are provisional.**

# Chapter 4 — Research Protocols

## 4.1 Purpose

A **Research Protocol** is the governing specification for one reproducible empirical investigation within Pops' Edge.

Its purpose is to define, before the relevant outcomes are known, the scientific question being investigated, the evidence that will be collected, the methodology by which that evidence will be measured, and the standard required before a Market Edge may be recognized.

A Research Protocol is therefore:

- not a forecast;
- not an Edge Claim;
- not a Comparative Performance Report;
- not a Research Review; and
- not an operational policy.

It is the prospective specification that governs how valid empirical evidence is created.

---

## 4.2 Scientific Question

Every Research Protocol shall define one explicit scientific question.

That question shall identify:

- the Market Benchmark;
- the Alternative Probability Source or Sources;
- the Research Population;
- the proposition under investigation; and
- the comparative relationship to be evaluated.

For example:

> **Does DRatings produce superior pregame MLB winner probabilities relative to the Kalshi Market Benchmark under the defined Research Population?**

A Research Protocol investigates one scientific question.

It may examine that question across Approved Research Dimensions.

It does not investigate multiple unrelated questions simultaneously.

---

## 4.3 Protocol Identity and Versioning

Every Research Protocol possesses a durable identity and explicit version.

Protocol versions are immutable.

A material change to the scientific methodology governing a protocol creates a new protocol version.

Material changes include, at minimum:

- the scientific question;
- the Research Population;
- the Market Benchmark;
- participating Alternative Probability Sources;
- canonical probability representations;
- Research Snapshot timing;
- capture or synchronization tolerances;
- outcome-resolution methodology;
- Approved Research Dimensions or partitions;
- primary endpoint;
- supporting measures;
- statistical methodology;
- Practical Significance threshold;
- Burden of Proof;
- Time-Bounded Surveillance;
- Drift criteria; or
- Research Review schedule.

Evidence collected under materially different protocol versions is not automatically pooled.

---

## 4.4 Research Population

Every Research Protocol prospectively defines its Research Population.

The Research Population specifies the events to which the scientific conclusions are intended to apply.

Eligibility and exclusion criteria shall be fully specified before outcomes are known.

Typical criteria may include:

- sport;
- competition;
- proposition type;
- season boundaries;
- regular season versus postseason;
- event status;
- postponements;
- cancellations;
- or other protocol-specific conditions.

Evidence belongs to a Research Population because it satisfies those criteria.

It is not excluded merely because it becomes old.

---

## 4.5 Automated Pregame Capture

Every Research Protocol defines exactly one automated pregame capture point.

The capture point is expressed as a fixed offset from scheduled event start.

For example:

> Six hours before scheduled first pitch.

A fixed offset ensures that all observations represent materially equivalent stages of the pregame information cycle.

If a different pregame horizon is scientifically desired, it constitutes a different research condition and therefore requires a separate protocol or other prospectively defined protocol structure.

---

## 4.6 Capture Tolerance

Every Research Protocol defines an allowable tolerance around the target capture point.

For example:

> Six hours before scheduled start ± five minutes.

Capture tolerance exists because automated collection cannot occur at an exact instant.

Observations outside the permitted tolerance remain historical Evidence but are not valid comparative evidence under that protocol.

---

## 4.7 Synchronization Tolerance

Capture tolerance and synchronization tolerance are distinct.

Capture tolerance determines whether an individual observation satisfies the protocol's target capture horizon.

Synchronization tolerance determines whether two observations represent materially equivalent information states.

A direct comparison requires both observations to satisfy the synchronization requirement defined by the protocol.

Observations that fail synchronization remain Evidence but do not contribute to Comparative Performance.

---

## 4.8 Market Benchmark Specification

Every Research Protocol defines exactly one Market Benchmark.

The protocol specifies:

- market provider;
- proposition;
- canonical probability derivation;
- treatment of bid, ask, midpoint, last trade, or other market state;
- transformations, where applicable; and
- validity conditions.

The benchmark methodology is established prospectively and applied uniformly to every qualifying event.

The methodology may never select the market representation retrospectively because it produces a more favorable result.

If the Market Benchmark is unavailable within the protocol-defined capture conditions, the event is ineligible for Comparative Performance.

---

## 4.9 Alternative Probability Source Specification

Every participating Alternative Probability Source is specified prospectively.

For each source, the protocol defines:

- source identity;
- model or published product, where known;
- canonical probability representation;
- proposition semantics;
- permitted transformations;
- availability requirements; and
- known limitations.

If a source publishes multiple probabilities for the same proposition, the protocol identifies exactly one canonical representation.

No retrospective selection among alternative published estimates is permitted.

---

## 4.10 Missing Probability Sources

Failure to capture an Alternative Probability Source does not invalidate otherwise eligible comparisons.

Provided that:

- the Market Benchmark is valid;
- the event is valid;
- capture timing is valid; and
- synchronization requirements are satisfied,

other benchmark-versus-challenger comparisons remain scientifically valid.

Missing observations are explicitly preserved.

They contribute to coverage measurement.

They are never retrospectively reconstructed.

---

## 4.11 Event Identity and Proposition Compatibility

Every observation participating in Comparative Performance must refer unambiguously to the same event and proposition.

The protocol defines deterministic compatibility rules for:

- event identity;
- participants;
- proposition semantics;
- outcome orientation;
- scheduled start; and
- other material characteristics.

Identity ambiguity fails closed.

---

## 4.12 Authoritative Outcome Resolution

Every Research Protocol specifies:

- the authoritative Outcome Observation source; and
- deterministic outcome-resolution rules.

Outcome Evidence is independent of forecasting Evidence.

The authoritative outcome is never selected retrospectively according to which source produces the preferred comparative result.

---

## 4.13 Event-Level Measurement

Following authoritative outcome resolution, every valid benchmark-versus-challenger pair is evaluated automatically.

Measurements include, at minimum:

- Brier Score;
- Log Loss; and
- information required for Calibration analysis.

Measurements are deterministic.

They are preserved.

They are not regenerated each time a Comparative Performance Report is requested.

---

## 4.14 Primary Endpoint

Every Research Protocol defines one primary comparative endpoint.

Within Version 1.0 of this methodology, the primary endpoint is:

> **Brier Score improvement relative to the Market Benchmark.**

The protocol specifies:

- calculation methodology;
- sign convention;
- uncertainty methodology; and
- Practical Significance threshold.

The primary endpoint answers:

> **Does the Alternative Probability Source forecast probabilities more accurately than the Market Benchmark?**

---

## 4.15 Supporting Measures

Every Research Protocol defines required supporting measures.

Version 1.0 requires:

- Log Loss; and
- Calibration.

Supporting measures do not independently establish a Market Edge.

Instead, they function as scientific safeguards.

A protocol-defined material deterioration in either supporting measure prevents an Edge Claim from satisfying the Burden of Proof.

---

## 4.16 Statistical Uncertainty

Every Research Protocol specifies how uncertainty surrounding the primary endpoint is estimated.

The Comparative Performance Report shall present:

- point estimate;
- paired sample size;
- uncertainty interval;
- confidence level; and
- applicable statistical assumptions.

The methodology therefore evaluates sample adequacy through uncertainty rather than arbitrary universal sample thresholds.

---

## 4.17 Practical Significance

Every Research Protocol defines a minimum practically meaningful improvement in the primary endpoint.

Practical Significance is evaluated separately from statistical significance.

An Edge Claim requires both.

Statistically significant but economically trivial differences do not establish a Market Edge.

---

## 4.18 Approved Research Dimensions

Every Research Protocol identifies the Approved Research Dimensions applicable to the investigation.

Each dimension satisfies the methodological requirements established in Chapter 2.

The protocol prospectively defines every permitted partition.

Partition boundaries may not be retrospectively modified because observed results appear favorable.

---

## 4.19 Snapshot Classification

Research Dimension classifications are determined using information available at the Research Snapshot.

The resulting classifications become part of the preserved scientific record.

Later reporting aggregates existing classifications.

It does not retrospectively classify events using information unavailable at capture.

---

## 4.20 Cross-Dimensional Analysis

Approval of individual Research Dimensions does not authorize arbitrary combinations among them.

Cross-dimensional investigation requires either:

- explicit prospective approval within the Research Protocol; or
- scientifically justified Progressive Refinement.

This constraint reduces overfitting and uncontrolled multiple comparisons.

---

## 4.21 Broad Comparison First

Every Research Protocol requires the broad, unsegmented comparison across the complete qualifying Research Population to appear before any segmented analysis.

Broad conclusions establish the scientific context.

Segmented findings refine that context.

They do not replace it.

---

## 4.22 Pair-Specific Evidence Sets

Comparative Performance is pair-specific.

Each benchmark-versus-challenger comparison uses the complete set of qualifying synchronized observations available to that pair.

Different challengers may therefore possess different paired sample sizes.

Those differences are explicitly reported.

---

## 4.23 Cumulative Analysis

Scheduled Comparative Performance Reports use the complete qualifying body of Cumulative Evidence through the report's analysis boundary.

Incremental evidence since the previous review may be reported separately.

It does not replace the cumulative analysis.

---

## 4.24 Time-Bounded Surveillance

Every Research Protocol defines at least one Time-Bounded Surveillance window appropriate to its Research Population.

The surveillance window evaluates whether current Comparative Performance remains consistent with the historical relationship established by Cumulative Evidence.

Surveillance complements historical analysis.

It does not replace it.

---

## 4.25 Drift Criteria

Every Research Protocol prospectively defines Drift.

Drift evaluates whether current Comparative Performance has materially departed from the historical comparative relationship.

Crossing the Drift threshold constitutes a material event requiring Research Review.

Drift itself does not alter an Edge Claim.

---

## 4.26 Research Review Schedule

Every Research Protocol defines:

- scheduled Research Reviews; and
- material events requiring unscheduled Research Review.

The protocol prospectively defines each scheduled review boundary, including
any scientifically justified grace period. No implicit or
implementation-defined grace period applies.

When a scheduled review boundary is reached without a qualifying completed
Research Review that explicitly addresses it, an unresolved review obligation
exists. The relevant scientific conclusion is procedurally Under Review and its
Current Scientific Applicability is suspended.

A valid protocol-defined material-event artifact likewise creates an unresolved
review obligation. A later completed Research Review resolves only the scheduled
boundary or material-event artifact that it explicitly addresses.

Evidence accumulates continuously.

Research conclusions change only through Research Review.

---

## 4.27 Comparative Performance Reports

The protocol defines when Comparative Performance Reports are generated.

Reports are produced:

- at scheduled Research Reviews; and
- following protocol-defined material events.

Reports summarize preserved Measurements.

They do not reinterpret historical Evidence.

---

## 4.28 Report Reproducibility

Every Comparative Performance Report identifies sufficient provenance to permit deterministic reproduction.

At minimum, this includes:

- protocol identity;
- protocol version;
- report methodology;
- analysis boundary;
- qualifying Measurement identities;
- pair-specific evidence populations;
- and applicable limitations.

---

## 4.29 Report Immutability

Comparative Performance Reports are immutable.

Later reports supplement rather than replace earlier reports.

Historical reports preserve what the available Evidence justified believing at each Research Review boundary.

---

## 4.30 Probability Source Changes

When a material Probability Source change is announced, the protocol preserves the distinction between source versions.

Evidence collected under materially different source versions is not automatically pooled when evaluating current Comparative Performance.

Where changes are unannounced, Time-Bounded Surveillance provides the primary mechanism for detecting possible unobserved regime change.

---

## 4.31 Burden of Proof

Every Research Protocol explicitly defines the Burden of Proof required to establish a Market Edge.

At minimum, the Burden of Proof requires:

- favorable primary endpoint;
- statistical significance;
- Practical Significance;
- satisfactory supporting measures;
- valid protocol compliance;
- and complete Evidence eligibility.

The Burden of Proof is never weakened retrospectively because observed results appear attractive.

---

## 4.32 Relationship to Edge Claims

A Research Protocol governs how an Edge Claim is tested.

It does not determine whether that Edge Claim is supported.

The sequence remains:

```text
Research Protocol
        ↓
Evidence Collection
        ↓
Measurement
        ↓
Comparative Performance Report
        ↓
Research Review
        ↓
Edge Claim Assessment
```

The protocol governs the experiment.

Research Review governs the conclusion.

---

## 4.33 Relationship to Operational Decisions

Research Protocols govern empirical investigation.

They do not govern operational execution.

They neither:

- authorize wagers;
- determine position sizing;
- evaluate liquidity;
- nor execute operational policy.

Those decisions occur only after a currently applicable Market Edge has established Evidence-Supported Positive Expected Value for a current opportunity.

---

## 4.34 Governing Principle

A Research Protocol exists so that Pops' Edge can state, before observing outcomes:

> **This is the question we intend to investigate, this is the evidence we will collect, this is how we will measure it, and this is the standard the result must satisfy before we will believe it.**

That commitment is the foundation of the empirical integrity of Pops' Edge.

# Chapter 5 — Evidence Collection and Measurement

## 5.1 Purpose

This chapter defines how empirical Evidence is collected and transformed into reproducible Measurements.

Its purpose is to ensure that all scientific conclusions within Pops' Edge are derived from immutable observations collected prospectively under a governing Research Protocol.

The collection and measurement process answers one question:

> **What actually happened?**

It deliberately does not answer:

> **What should we believe because of it?**

That question belongs to Research Review.

---

## 5.2 Evidence Collection Is Protocol-Governed

Empirical Evidence is collected only under an active Research Protocol.

The protocol determines:

- the Research Population;
- participating Probability Sources;
- the Market Benchmark;
- capture timing;
- synchronization requirements;
- event eligibility;
- Approved Research Dimensions;
- and authoritative outcome methodology.

Evidence collection never improvises around missing or inconvenient observations.

Scientific validity is established prospectively.

---

## 5.3 Automated Pregame Capture

Probability collection is automated.

For every eligible event, Pops' Edge attempts to capture:

- the Market Benchmark;
- every participating Alternative Probability Source;
- event identity;
- proposition identity;
- scheduled start;
- protocol-defined contextual information;
- and collection provenance.

Automation minimizes:

- selective observation;
- inconsistent timing;
- manual intervention;
- and hindsight bias.

The methodology therefore measures what was actually available under the Research Protocol rather than what might later be reconstructed.

---

## 5.4 Research Snapshots

A successful capture produces one immutable Research Snapshot.

Each Research Snapshot represents:

- one event;
- one proposition;
- one Research Protocol;
- one pregame information state.

A Research Snapshot preserves:

- event identity;
- proposition identity;
- scheduled start;
- capture chronology;
- Market Benchmark observation;
- Alternative Probability Source observations;
- Approved Research Dimension classifications;
- provenance;
- validity status; and
- synchronization diagnostics.

Research Snapshots are immutable.

Later Evidence, Measurements, Reports, and Research Reviews reference them without modification.

---

## 5.5 Benchmark Capture

The Market Benchmark is required for Comparative Performance.

If the Market Benchmark cannot be captured within the protocol-defined requirements, the event cannot contribute to Comparative Performance.

The Research Snapshot may still be preserved as historical Evidence.

It simply cannot support comparative analysis under that protocol.

---

## 5.6 Alternative Probability Sources

Alternative Probability Sources are independently evaluated.

Failure to capture one Alternative Probability Source does not invalidate otherwise eligible benchmark-versus-challenger comparisons.

Missing observations are explicitly recorded.

Coverage therefore becomes part of the scientific record rather than an implementation detail.

---

## 5.7 No Retrospective Reconstruction

Evidence not validly captured under the governing Research Protocol remains missing.

Historical archives, cached pages, screenshots, reconstructed probabilities, or later published values do not repair prospective Evidence.

Such information may support separate retrospective research.

It does not alter the prospective Evidence collected by Pops' Edge.

---

## 5.8 Canonical Probability Representation

Each participating Probability Source contributes exactly one prospectively defined probability representation.

The governing Research Protocol determines:

- which published probability is used;
- any permitted transformations;
- and all interpretation rules.

Retrospective selection among multiple available probabilities is prohibited.

---

## 5.9 Event and Proposition Integrity

Comparative evaluation requires that every participating Probability Source refer to the same event and proposition.

Compatibility is determined prospectively.

Identity ambiguity fails closed.

Events are not compared merely because they appear similar.

---

## 5.10 Capture Validation

Every collected observation receives an explicit validity determination.

Validation considers:

- event identity;
- proposition identity;
- capture timing;
- synchronization;
- probability validity;
- source integrity;
- and protocol compliance.

Invalid observations remain part of the historical record.

They do not contribute to Comparative Performance.

---

## 5.11 Synchronization Validation

Direct comparison requires synchronized observations.

Synchronization is evaluated pairwise between the Market Benchmark and each Alternative Probability Source.

Consequently:

- one challenger may produce a valid comparison;
- another may fail synchronization;
- a third may be missing entirely.

Each comparison is evaluated independently.

---

## 5.12 Approved Research Dimension Classification

Every valid Research Snapshot records the protocol-defined classifications for each Approved Research Dimension.

These classifications are determined only from information available at the Research Snapshot.

They are preserved with the Evidence.

Later reports aggregate existing classifications rather than creating new ones retrospectively.

---

## 5.13 Outcome Collection

Following event completion, Pops' Edge records the authoritative Outcome Observation specified by the governing Research Protocol.

Outcome Evidence includes:

- event identity;
- proposition resolution;
- authoritative source;
- resolution chronology;
- provenance; and
- validation.

Outcome Evidence is appended.

Previously collected Evidence remains unchanged.

---

## 5.14 Outcome Eligibility

Only events satisfying the protocol's outcome rules contribute completed Measurements.

Cancelled, abandoned, unresolved, or otherwise incompatible events are handled exactly as specified by the governing Research Protocol.

Outcome ambiguity fails closed.

---

## 5.15 Event-Level Measurement

Once authoritative outcomes exist, Pops' Edge automatically evaluates every valid benchmark-versus-challenger pair.

Measurements include, at minimum:

- Brier Score;
- Log Loss;
- and the information required for Calibration.

Every participating Probability Source is evaluated against the same realized outcome.

---

## 5.16 Comparative Measurement

For every valid benchmark-versus-challenger pair, Pops' Edge creates one immutable Comparative Measurement.

Each Comparative Measurement preserves:

- protocol identity;
- Research Snapshot identity;
- benchmark identity;
- challenger identity;
- benchmark probability;
- challenger probability;
- outcome;
- Brier Scores;
- Log Loss;
- Approved Research Dimension classifications;
- provenance;
- methodology version;
- validation status;
- and limitations.

Comparative Measurements become the fundamental units aggregated by later Comparative Performance Reports.

---

## 5.17 Primary Measurement

The primary Measurement within Version 1.0 is Brier Score.

The governing Research Protocol specifies:

- calculation methodology;
- sign convention;
- uncertainty methodology;
- and Practical Significance threshold.

Every Comparative Measurement therefore produces one deterministic contribution to later Comparative Performance.

---

## 5.18 Supporting Measurements

Log Loss and Calibration provide required supporting evidence.

They are not alternative primary endpoints.

Their purpose is to identify weaknesses that may undermine confidence in an otherwise favorable Brier result.

Their interpretation occurs later during Research Review.

### Calibration safeguard

Calibration uses exactly the same paired Comparative Measurement population as
the corresponding mean Brier Scores, mean paired Brier improvement, and Log
Loss safeguard. Benchmark and challenger Calibration therefore describe the
same events and authoritative Outcomes. Unmatched forecasts, different source
subsets, and post hoc filtered populations are not substituted.

Each source is calibrated using the probability assigned to the canonical
binary proposition represented by the Comparative Measurement. The realized
Outcome is encoded in that same orientation. Labels such as home, YES, or
favorite are valid only when they are the canonical proposition orientation
already established by the Research Protocol and Evidence lineage. Calibration
does not silently reverse that orientation.

The prospective `calibration-safeguard` rule version 2 uses these fixed exact
decimal probability bins:

```text
[0.00, 0.10)
[0.10, 0.20)
[0.20, 0.30)
[0.30, 0.40)
[0.40, 0.50)
[0.50, 0.60)
[0.60, 0.70)
[0.70, 0.80)
[0.80, 0.90)
[0.90, 1.00]
```

Every bin is lower-bound inclusive. Every bin except the final bin is
upper-bound exclusive; the final bin includes probability exactly `1.00`.
Probability `0.00` belongs to the first bin, and every valid probability
belongs to exactly one bin. Benchmark and challenger use identical boundaries.
The boundaries are prospective and immutable under the rule version; adaptive,
quantile, equal-count, or other data-dependent bins are not part of version 2.

For each bin, Calibration reports:

- count;
- mean forecast probability;
- observed Outcome frequency; and
- calibration gap, defined as observed Outcome frequency minus mean forecast
  probability.

A positive gap means Outcomes occurred more frequently than forecast in that
bin; a negative gap means they occurred less frequently. Empty bins remain in
the canonical structure with count zero. Their mean probability, observed
frequency, and gap are absent or not applicable, not numerical zero.

The descriptive scalar safeguard is **weighted absolute calibration error**:

```text
WACE = Σ_b (n_b / N) × |observed_frequency_b - mean_probability_b|
```

Here `n_b` is the bin count and `N` is the total paired Calibration sample
size. When `N > 0`, the sum is evaluated over nonempty bins. Empty bins have
zero weight without requiring fabricated statistics.

When the complete paired Calibration population is empty (`N = 0`), all ten
canonical bins remain represented with count zero. Every per-bin mean forecast
probability, observed Outcome frequency, and calibration gap remains absent or
not applicable, and weighted absolute calibration error is also absent or not
applicable. It must not be represented as numerical zero, because zero would
falsely communicate perfect Calibration rather than absence of Evidence.

Calibration uses exact decimal scientific arithmetic. For an identical paired
Measurement population and rule version, bin membership, counts, means,
frequencies, gaps, and weighted absolute calibration error are deterministic
and independent of input order. Binary floating point is not scientific
authority.

Every nonempty bin remains visible even when its count is small. Version 2
introduces no minimum-bin-size exclusion, smoothing, Bayesian shrinkage, or
pseudocount. Small-sample limitations are reported and interpreted downstream.

Calibration is descriptive supporting Measurement. Comparative Performance
reports the bins and weighted absolute calibration error for both sources, but
does not produce a Calibration pass/fail status, hypothesis test, confidence
interval, or Burden-of-Proof conclusion. Research Review interprets Calibration
alongside Brier improvement, paired uncertainty, Practical Significance, and
Log Loss. Calibration alone neither establishes nor rejects a Market Edge.

The under-specified `calibration-safeguard` rule version 1 remains immutable
historical Protocol material and is not silently reinterpreted. Future
Protocols requiring this canonical deterministic Calibration methodology use
rule version 2, which prospectively identifies the fixed exact-decimal bin
boundaries and weighted absolute calibration error summary method.

---

## 5.19 Coverage Measurement

Coverage is a required scientific Measurement.

Coverage distinguishes among:

- successful captures;
- missing observations;
- synchronization failures;
- invalid observations;
- unresolved outcomes;
- and protocol exclusions.

Coverage provides scientific context for later interpretation.

---

## 5.20 Pair-Specific Measurement

Comparative Measurements are pair-specific.

Each Alternative Probability Source contributes using its own common eligible evidence set with the Market Benchmark.

Different challengers may therefore possess different paired sample sizes.

This difference is preserved rather than hidden.

---

## 5.21 Measurement Immutability

Once validly produced, Measurements are immutable.

Changes to:

- statistical methodology;
- protocol interpretation;
- implementation;
- or software

do not rewrite existing Measurements.

Instead, new versioned Measurements may be generated from the same underlying Evidence.

Evidence itself never changes.

---

## 5.22 Provenance

Every Measurement must be traceable to:

- the governing Research Protocol;
- the originating Research Snapshot;
- participating Probability Source observations;
- authoritative Outcome Observation;
- and the methodology used to derive the Measurement.

Scientific conclusions therefore remain fully auditable.

---

## 5.23 Measurement Failure

Measurement fails closed whenever required Evidence is invalid or incompatible.

Examples include:

- missing Market Benchmark;
- proposition mismatch;
- synchronization failure;
- unresolved outcome;
- invalid probability;
- or protocol incompatibility.

The reason for exclusion is preserved.

Failure of one comparison does not invalidate unrelated valid comparisons.

---

## 5.24 Collection Failure Is Evidence

Failure to collect a valid observation is itself scientifically meaningful.

Coverage therefore becomes part of the empirical record.

Pops' Edge reports collection failures rather than concealing them.

---

## 5.25 Continuous Accumulation

Evidence and Measurements accumulate continuously.

Every qualifying event contributes new empirical information.

Accumulation alone does not alter scientific conclusions.

New Measurements become inputs to future Comparative Performance Reports and future Research Reviews.

---

## 5.26 Separation Between Evidence and Interpretation

Evidence Collection and Measurement establish:

- what was observed;
- and what those observations quantitatively imply.

They do not determine:

- whether a Market Edge exists;
- whether an Edge Claim is supported;
- or whether operational action is appropriate.

Those determinations belong to later stages of the methodology.

---

## 5.27 Governing Principle

Evidence Collection and Measurement exist so that Pops' Edge never needs to reconstruct the past.

Instead, the methodology preserves exactly what was observed, when it was observed, and how every subsequent Measurement was derived.

Everything that follows in the Empirical Research Methodology depends upon the integrity of this preserved scientific record.

Accordingly:

> **Evidence is collected once. Measurements are derived once. Every subsequent scientific conclusion is built upon those preserved artifacts.**

# Chapter 6 — Comparative Performance Reports

## 6.1 Purpose

A Comparative Performance Report is the principal scientific reporting artifact of Pops' Edge.

Its purpose is to summarize the accumulated empirical evidence collected under one Research Protocol through one defined analysis boundary and present that evidence in a form suitable for Research Review.

The report answers one question:

> **How has each Alternative Probability Source performed relative to the Market Benchmark under the conditions defined by this Research Protocol?**

A Comparative Performance Report presents findings.

It does not determine whether a Market Edge exists.

It does not change an Edge Claim.

It does not authorize operational decisions.

Those responsibilities belong to Research Review.

---

## 6.2 One Protocol, One Investigation

Every Comparative Performance Report represents one Research Protocol.

Accordingly, every report inherits:

- the Research Population;
- the Market Benchmark;
- participating Alternative Probability Sources;
- canonical probability representations;
- Approved Research Dimensions;
- primary endpoint;
- supporting measures;
- statistical methodology;
- Practical Significance threshold;
- Time-Bounded Surveillance methodology;
- Drift criteria; and
- Burden of Proof

defined by that protocol.

Measurements generated under materially different Research Protocols are never silently combined within the same report.

---

## 6.3 Analysis Boundary

Every report has one explicit analysis boundary.

Only qualifying Evidence and Measurements available through that boundary contribute to the report.

Later observations never alter earlier reports.

A new analysis boundary produces a new report.

Historical reports remain valid records of what the available Evidence supported at that point in time.

---

## 6.4 Immutable Scientific Record

Comparative Performance Reports are immutable.

They are historical scientific artifacts.

For example:

```text
May Review
850 paired observations

↓

June Review
1,140 paired observations

↓

July Review
1,460 paired observations
```

Each report accurately represents the Evidence available at its own Research Review boundary.

Subsequent reports extend the scientific record.

They do not rewrite it.

---

## 6.5 Reproducibility

Every report identifies sufficient provenance to permit deterministic reproduction.

At minimum this includes:

- Research Protocol identity and version;
- report methodology;
- analysis boundary;
- qualifying Measurement identities;
- participating Probability Sources;
- pair-specific sample populations;
- exclusions;
- and material limitations.

Independent researchers using the same inputs should obtain materially identical findings.

---

## 6.6 Broad Comparison First

Every Comparative Performance Report begins with the broad comparison across the complete qualifying Research Population.

This establishes the scientific baseline.

Only after presenting the broad comparison does the report present findings for Approved Research Dimensions.

Segmented findings refine the broad result.

They do not replace it.

---

## 6.7 Market Benchmark Performance

The report first presents the performance of the Market Benchmark itself.

At minimum:

- paired sample size;
- Brier Score;
- Log Loss;
- Calibration;
- coverage;
- exclusions; and
- limitations.

This answers the first research question:

> **How accurately did the Market Benchmark forecast events under these research conditions?**

---

## 6.8 Alternative Probability Source Performance

For each Alternative Probability Source, the report presents:

- paired sample size;
- Brier Score;
- Log Loss;
- Calibration;
- coverage;
- exclusions; and
- limitations.

Absolute forecasting quality provides useful scientific context.

It does not establish a Market Edge.

---

## 6.9 Comparative Performance

The principal findings of the report are comparative.

For every benchmark-versus-challenger pair, the report presents:

- Market Benchmark Brier Score;
- Alternative Probability Source Brier Score;
- estimated Brier improvement;
- uncertainty interval;
- paired sample size; and
- protocol-defined Practical Significance threshold.

The report therefore presents:

- effect size;
- uncertainty; and
- practical relevance.

It does not interpret them.

---

## 6.10 Statistical Uncertainty

Every comparative result is accompanied by the uncertainty measure required by the Research Protocol.

Where confidence intervals are used, the report presents:

- point estimate;
- lower bound;
- upper bound;
- confidence level; and
- paired sample size.

The report communicates uncertainty rather than merely declaring significance.

---

## 6.11 Practical Significance

The report presents the protocol-defined Practical Significance threshold alongside the observed comparative result.

Scientific interpretation therefore distinguishes among:

- statistically uncertain effects;
- statistically significant but practically trivial effects; and
- statistically and practically meaningful effects.

The report does not determine whether the threshold has been satisfied.

It reports the evidence necessary for Research Review to do so.

---

## 6.12 Supporting Measures

The report presents required supporting measures.

Version 1.0 requires:

- Log Loss; and
- Calibration.

These are reported using the methodology defined by the governing Research Protocol.

Supporting measures function as scientific safeguards.

They do not independently establish a Market Edge.

---

## 6.13 Coverage

Coverage is reported for every participating Probability Source.

Coverage includes:

- successful observations;
- missing observations;
- synchronization failures;
- invalid observations;
- unresolved outcomes; and
- protocol exclusions.

Coverage provides important scientific context.

Strong forecasting performance over a narrow portion of the Research Population is scientifically different from comparable performance over nearly complete coverage.

---

## 6.14 Pair-Specific Populations

Every benchmark-versus-challenger comparison identifies its own paired evidence population.

Different challengers may legitimately possess different paired sample sizes.

Those differences remain explicit throughout the report.

Direct challenger-versus-challenger comparisons require their own common paired population.

---

## 6.15 Approved Research Dimensions

Following the broad comparison, the report presents results across the Approved Research Dimensions defined by the governing Research Protocol.

Only prospectively approved dimensions and partitions are reported.

No new partitions or combinations are introduced because observed results appear favorable.

---

## 6.16 Segmented Findings

Segmented findings remain subordinate to the broad comparison.

The report therefore supports conclusions such as:

> Overall Comparative Performance does not support a Market Edge.

while simultaneously reporting:

> One prospectively defined probability band demonstrates superior Comparative Performance.

Both findings are scientifically important.

Neither replaces the other.

---

## 6.17 Cumulative Performance

The principal report presents Cumulative Evidence through the analysis boundary.

This answers:

> **What has this Alternative Probability Source demonstrated across the full Research Population?**

Historical Evidence is preserved.

It is never silently discounted.

---

## 6.18 Time-Bounded Surveillance

The report separately presents the protocol-defined Time-Bounded Surveillance analysis.

This answers:

> **Does current Comparative Performance remain consistent with the historical relationship established by the cumulative Evidence?**

The surveillance analysis is presented separately from the cumulative analysis.

The two are never blended through undocumented recency weighting.

---

## 6.19 Drift

Where the governing Research Protocol defines Drift, the report identifies:

- current surveillance performance;
- historical comparative performance;
- measured departure;
- uncertainty;
- and Drift status.

The report may conclude that protocol-defined Drift has been detected.

It does not alter an Edge Claim.

Drift becomes an input to Research Review.

A valid surveillance result may instead find that the available evidence is
insufficient to determine Drift. That result is distinct from a structurally
invalid artifact or incompatible input, which cannot produce a scientific
finding. The governing Research Protocol defines the consequence of valid
insufficient evidence. If it does not, Current Scientific Applicability remains
indeterminate and unavailable for operational reliance.

---

## 6.20 Current Scientific Applicability

The report presents the findings needed to determine whether any currently
Supported Market Edge remains scientifically applicable.

It reports:

- current applicability;
- Drift status;
- protocol compatibility;
- and other relevant scientific limitations.

The report does not decide whether operational reliance should continue. Current
Scientific Applicability follows the latest completed Research Review, unresolved
scheduled and material-event obligations, and all applicable protocol,
population, domain, Evidence, and compatibility requirements.

---

## 6.21 Findings, Not Conclusions

The report presents findings.

Examples include:

- estimated Brier improvement;
- uncertainty interval;
- Practical Significance threshold;
- Log Loss;
- Calibration;
- coverage;
- and Drift.

The report does not state:

> A Market Edge exists.

That conclusion belongs to Research Review.

---

## 6.22 Limitations

Every report explicitly presents material limitations.

Examples include:

- insufficient paired observations;
- incomplete coverage;
- protocol exclusions;
- synchronization failures;
- unresolved outcomes;
- suspected unannounced model changes;
- market changes;
- and Research Population limitations.

Limitations are scientific findings.

They are not implementation details.

---

## 6.23 Scientific Communication

A Comparative Performance Report is intended to communicate scientific findings to the Product Owner.

Its primary audience should understand:

- the research question;
- the Evidence base;
- comparative performance;
- uncertainty;
- supporting measures;
- historical performance;
- current surveillance;
- and limitations

without requiring knowledge of the underlying software architecture.

Detailed provenance remains available for audit.

The report itself is a scientific communication artifact rather than an architectural inspection interface.

---

## 6.24 Relationship to Research Review

The Comparative Performance Report is the principal empirical input to Research Review.

The report answers:

> **What does the accumulated Evidence show?**

Research Review answers:

> **What are we justified in believing because of it?**

Those responsibilities remain intentionally separate.

---

## 6.25 Governing Principle

The Comparative Performance Report exists so that the Product Owner can answer:

- How good is the Market Benchmark?
- How good is the Alternative Probability Source?
- How large is the measured difference?
- How certain are we?
- Is the difference practically meaningful?
- Do supporting measures agree?
- Does current performance remain consistent with historical performance?

The report presents those findings faithfully.

Research Review determines what they mean.

# Chapter 7 — Research Review and Edge Claims

## 7.1 Purpose

Research Review is the process by which Pops' Edge determines what scientific conclusions are justified by the findings contained within a Comparative Performance Report.

Its purpose is to answer:

> **Given the accumulated empirical evidence collected under this Research Protocol, what are we justified in believing about the claimed Market Edge?**

Research Review forms the boundary between Measurement and Scientific Inference.

It does not:

- collect Evidence;
- recalculate Measurements;
- modify a Research Protocol;
- rewrite historical reports; or
- authorize operational action.

Research Review evaluates the findings already produced under the governing Research Protocol against the prospectively defined Burden of Proof.

A durable Research Review artifact records a completed, immutable scientific
review. It records only the scientific conclusion reached by that completed
review. An unresolved obligation or review in progress does not create a partial
or mutable Research Review artifact.

Each artifact assesses exactly one Edge Claim. It may explicitly cover multiple
scheduled review obligations or valid material-event artifacts relevant to that
claim. One Comparative Performance Report may support multiple Research Review
artifacts, but each Review remains claim-specific.

---

## 7.2 Research Review Is Discrete

Evidence accumulates continuously.

Research conclusions change discretely.

Research Review occurs only:

- at scheduled review intervals defined by the Research Protocol; or
- following predefined material events requiring unscheduled review.

Individual observations never change an Edge Claim directly.

They contribute to the next Comparative Performance Report, which becomes the empirical basis for the next Research Review.

---

## 7.3 Research Review Is Protocol-Governed

Every Research Review is governed by one Research Protocol.

The review applies the protocol's predefined:

- Research Population;
- primary endpoint;
- supporting measures;
- uncertainty methodology;
- Practical Significance threshold;
- Approved Research Dimensions;
- Drift criteria;
- limitations; and
- Burden of Proof.

Research Review interprets findings.

It does not redefine the experiment.

---

## 7.4 Edge Claims

An Edge Claim is an explicit scientific hypothesis that an Alternative Probability Source demonstrates superior Comparative Performance relative to the Market Benchmark within a defined research domain.

Every Edge Claim identifies:

- governing Research Protocol;
- Market Benchmark;
- Alternative Probability Source;
- proposition;
- applicable research domain; and
- applicable Approved Research Dimensions.

A Research Protocol may govern multiple Edge Claims, but each distinct
Alternative Probability Source-versus-Market Benchmark hypothesis within the
applicable Research Domain is a separate Edge Claim.

Edge Claims begin as hypotheses.

They become supported only through Research Review.

---

## 7.5 Broad Claims Before Narrow Claims

Research proceeds from broader claims toward narrower claims through Progressive Refinement.

A broad Edge Claim may be unsupported while a prospectively approved research domain demonstrates superior Comparative Performance.

Research Review therefore recognizes that:

- broad claims;
- and narrower claims

are scientifically distinct.

Neither replaces the other.

---

## 7.6 No Automatic Edge Discovery

Comparative Performance Reports may reveal interesting statistical findings.

Those findings do not automatically become Edge Claims.

Research Review determines whether the findings represent:

- insufficient evidence;
- an existing Edge Claim;
- justification for Progressive Refinement; or
- a scientifically legitimate new Edge Claim.

The methodology therefore separates:

Observation

↓

Finding

↓

Edge Claim

↓

Market Edge

---

## 7.7 Burden of Proof

An Edge Claim becomes supported only when it satisfies the Burden of Proof defined by the governing Research Protocol.

At minimum, the Burden of Proof requires:

- favorable primary endpoint;
- statistical significance;
- Practical Significance;
- satisfactory supporting measures;
- valid Evidence; and
- protocol compliance.

No individual requirement compensates for failure of another.

---

## 7.8 Statistical Significance

Statistical significance establishes that the measured Comparative Performance is unlikely to be explained solely by ordinary sampling variation under the assumptions of the governing Research Protocol.

It does not establish that the observed advantage matters economically.

Accordingly:

> Statistical significance is necessary but not sufficient.

---

## 7.9 Practical Significance

Practical Significance establishes that the observed Comparative Performance is large enough to matter.

It does not establish that the estimate is statistically reliable.

Accordingly:

> Practical Significance is necessary but not sufficient.

Only together do statistical and Practical Significance satisfy the primary scientific requirement.

---

## 7.10 Supporting Measures

Supporting measures function as scientific safeguards.

Version 1.0 requires:

- Log Loss; and
- Calibration.

Research Review applies the protocol-defined safeguards.

An Alternative Probability Source that satisfies the primary endpoint while materially failing a required supporting measure does not satisfy the Burden of Proof.

Calibration itself supplies no automatic pass/fail result. Research Review
interprets its descriptive findings under the Protocol's Burden of Proof, and
Calibration alone neither establishes nor rejects a Market Edge.

---

## 7.11 Evidence Classification

Each completed Research Review records a scientific conclusion about the Edge Claim.

Version 1.0 recognizes:

- Insufficient Evidence
- Emerging Evidence
- Supported
- Strongly Supported
- Weakening
- No Longer Supported
- Rejected

These conclusions describe completed scientific assessment.

They do not authorize operational action.

---

## 7.12 Supported

A Supported Edge Claim satisfies the complete Burden of Proof established by the governing Research Protocol.

Support establishes a Market Edge.

If the Edge Claim already has a historical Market Edge, a later Supported Review
does not establish another one. It may restore Current Scientific Applicability
to the existing Market Edge when all other applicability requirements are met.

Support remains bounded by:

- Research Protocol;
- Research Population;
- applicable research domain;
- available Evidence; and
- known limitations.

Support does not imply universal superiority.

---

## 7.13 Strongly Supported

Where defined by the governing Research Protocol, Strongly Supported represents a higher evidentiary standard than Supported.

Like Supported, Strongly Supported establishes a Market Edge only when the Edge
Claim has no existing historical Market Edge. Later Strongly Supported Reviews
may restore applicability to that same Market Edge but never recreate it.

The distinction is based upon prospectively defined scientific criteria.

It is never assigned merely because the findings appear persuasive.

---

## 7.14 Weakening

Weakening is a scientific conclusion reached during Research Review.

It indicates that:

- historical support remains; but
- current empirical evidence demonstrates material deterioration relative to the historical relationship.

Weakening preserves the historical scientific record.

It questions current applicability.

---

## 7.15 Under Review

Under Review is a temporary, derived procedural condition. It is not a completed
scientific conclusion and is not stored as a Research Review classification.

At an explicit timezone-aware `as_of` boundary, Under Review exists when either
of the following remains unresolved:

- a protocol-defined scheduled review boundary that is due; or
- a valid protocol-defined material-event artifact, including a material Drift
  finding.

An obligation is resolved only by a later completed Research Review that
explicitly addresses that scheduled boundary or material-event artifact. A newer
review does not implicitly resolve unrelated obligations.

While an obligation remains unresolved, Current Scientific Applicability is
suspended. The latest completed scientific conclusion, prior Research Reviews,
the Edge Claim, and any historical Market Edge remain intact.

Under Review is independent of Governance approval and production authority. It
cannot create, revoke, or modify Governance state.

---

## 7.16 Drift

Time-Bounded Surveillance may detect protocol-defined Drift.

Drift is an empirical finding.

It is not an Edge Claim decision.

Only a valid protocol-defined material Drift finding creates a review obligation.
A valid insufficient-evidence surveillance result is not silently treated as
either Drift or no Drift; its consequence follows the governing Research
Protocol. A structurally invalid artifact or incompatible input cannot produce a
scientific finding.

Each valid Drift Surveillance finding concerns exactly one Edge Claim under its
governing Research Protocol and records one protocol-defined disposition: no
material Drift, material Drift, or insufficient evidence to determine Drift.
Only a disposition that the protocol defines as a qualifying material event
creates a review obligation. Drift Surveillance never restores Current
Scientific Applicability by itself.

The sequence is therefore:

```text
Time-Bounded Surveillance
        ↓
Drift detected
        ↓
Material Event
        ↓
Research Review
        ↓
Edge Claim reassessment
```

Only Research Review changes the scientific status of an Edge Claim.

---

## 7.17 Current Scientific Applicability

A historically Supported Market Edge remains operationally relevant only while it retains Current Scientific Applicability.

Current Scientific Applicability may be suspended because of:

- Drift;
- an unresolved scheduled Research Review obligation;
- protocol incompatibility;
- Research Population incompatibility;
- or another predefined material event.

Historical support remains part of the scientific record.

Operational reliance does not.

At an explicit timezone-aware `as_of` boundary, Current Scientific Applicability
is determined by:

1. identifying the latest completed scientific conclusion for the Edge Claim;
2. identifying every protocol-defined scheduled obligation due by `as_of` and
   every valid protocol-defined material-event artifact effective by `as_of`;
3. excluding only obligations explicitly covered by qualifying completed
   Research Reviews;
4. suspending applicability while any qualifying obligation remains unresolved;
   and
5. otherwise applying the completed-conclusion consequences and all protocol,
   Research Domain, Research Population, Evidence, analytical, and compatibility
   requirements.

Supported and Strongly Supported are the only completed conclusions eligible to
support Current Scientific Applicability. Weakening, No Longer Supported,
Insufficient Evidence, Emerging Evidence, and Rejected are not eligible. A
completed Review may resolve every obligation it covers without restoring
applicability when its conclusion or another requirement remains ineligible.

This determination does not mutate the Market Edge or create Governance or
operational authority.

---

## 7.18 Restoration

Time-Bounded Surveillance may identify that current Comparative Performance has become consistent with historical expectations.

This observation does not automatically restore Current Scientific Applicability.

Restoration requires a qualifying completed Research Review applying the complete
Burden of Proof and explicitly addressing every obligation whose resolution it
claims. Surveillance alone cannot restore Current Scientific Applicability.

Accordingly:

> Surveillance may challenge operational confidence.

> Only Research Review restores it.

---

## 7.19 No Longer Supported

An Edge Claim becomes No Longer Supported when the accumulated Evidence no longer satisfies the Burden of Proof.

Historical reports remain valid.

The scientific conclusion changes because the body of Evidence has changed.

History is preserved.

Knowledge evolves.

---

## 7.20 Rejected

Rejected represents a stronger conclusion than Insufficient Evidence.

Insufficient Evidence means:

> We do not know.

Rejected means:

> The available empirical evidence weighs against the claim under the governing Research Protocol.

Rejected claims remain part of the permanent scientific record.

---

## 7.21 Progressive Refinement

Research Review may conclude that Progressive Refinement is scientifically justified.

Such refinement produces a new, prospectively defined Edge Claim.

Historical segmentation never becomes proof merely because it motivated further investigation.

---

## 7.22 Product Owner

The Product Owner governs the research program.

The Product Owner:

- approves Research Protocols;
- approves Research Populations;
- approves Approved Research Dimensions;
- approves Progressive Refinement;
- evaluates methodological limitations; and
- governs changes to the empirical research program.

The Product Owner does not override deterministic empirical findings.

Human judgment governs the research methodology.

It does not replace the evidence.

---

## 7.23 Research Automation

Deterministic work should be automated whenever possible.

Automation includes:

- Evidence validation;
- Measurement;
- Comparative Performance;
- uncertainty estimation;
- Drift detection;
- and report generation.

Research Review remains responsible for scientific interpretation where judgment is legitimately required.

---

## 7.24 Falsifiability

Every Edge Claim remains falsifiable.

Future Evidence may:

- strengthen support;
- weaken support;
- leave the conclusion unchanged;
- or eliminate support entirely.

Elimination of current support does not erase the historical Market Edge. An Edge Claim whose current scientific support cannot be weakened or eliminated by future Evidence is not scientifically falsifiable.

---

## 7.25 Relationship to Operational Decisions

Research Review establishes scientific conclusions.

Operational analysis determines whether those conclusions create current Evidence-Supported Positive Expected Value.

The sequence remains:

```text
Comparative Performance Report
        ↓
Research Review
        ↓
Edge Claim Assessment
        ↓
Market Edge
        ↓
Current Opportunity Analysis
        ↓
Evidence-Supported Positive Expected Value
```

Research establishes what is justified.

Operations determine what, if anything, should be done because of it.

---

## 7.26 Governing Principle

Research Review exists to answer one question:

> **Given the accumulated empirical evidence collected under this Research Protocol, what are we justified in believing?**

It does not create Evidence.

It does not execute operational decisions.

It establishes the scientific conclusions that later operational processes may rely upon.

Accordingly:

> **Research Review transforms empirical findings into trustworthy scientific knowledge.**

# Chapter 8 — Evidence-Supported Positive Expected Value and Operational Decisions

## 8.1 Purpose

This chapter defines how a scientifically supported Market Edge may inform current operational decisions.

Its purpose is to answer:

> **When does a scientifically supported Market Edge create a current opportunity possessing Evidence-Supported Positive Expected Value?**

Research establishes what is justified scientifically.

Operational analysis determines whether that scientific knowledge creates a current economic opportunity.

These are intentionally separate questions.

---

## 8.2 From Scientific Knowledge to Operational Opportunity

A Supported Market Edge establishes that an Alternative Probability Source has demonstrated statistically and practically meaningful superior Comparative Performance relative to the Market Benchmark within a defined research domain.

That conclusion does **not** imply that every current event within that domain should be wagered.

A current opportunity exists only when:

- the Market Edge remains currently applicable;
- the current event belongs to the validated research domain;
- the current Alternative Probability Source estimate is valid;
- the current Market Benchmark observation is valid;
- the resulting expected value is positive;
- the expected advantage remains economically meaningful after market frictions; and
- operational constraints permit action.

Scientific trust and current economic opportunity must both exist.

---

## 8.3 Theoretical Positive Expected Value

Theoretical Positive Expected Value arises whenever an Alternative Probability Source and the current Market Benchmark imply a favorable expected return.

Theoretical Positive Expected Value answers:

> **If this probability estimate is correct, is the current market price favorable?**

It does **not** answer:

> **Why should this probability estimate be trusted more than the market?**

Accordingly, theoretical Positive Expected Value is necessary but not sufficient for operational action.

---

## 8.4 Evidence-Supported Positive Expected Value

Evidence-Supported Positive Expected Value exists only when:

- a currently applicable Market Edge provides empirical justification for trusting the Alternative Probability Source; and
- the current market price produces positive expected value after applicable costs and operational constraints.

A current disagreement with the market is therefore insufficient.

The underlying probability estimate must first earn scientific credibility through the empirical research process.

---

## 8.5 Market Edge as Scientific Prerequisite

Operational opportunity is always downstream from empirical research.

Conceptually:

```text
Research
        ↓
Market Edge
        ↓
Current Forecast
        ↓
Current Market Price
        ↓
Theoretical Positive Expected Value
        ↓
Evidence-Supported Positive Expected Value
```

Market Edges establish scientific trust.

Current market prices determine whether that trust can presently be exploited.

---

## 8.6 Research Domain Compatibility

A current opportunity may rely upon a Market Edge only when it belongs to the same research domain in which that Market Edge was demonstrated.

Research domains are not broadened by implication.

If an event falls outside the validated domain, the supporting Market Edge does not apply.

Domain compatibility is deterministic.

Ambiguity fails closed.

---

## 8.7 Current Scientific Applicability

Only a currently applicable Market Edge may support operational decisions.

Historical scientific support alone is insufficient.

Market Edges whose latest completed scientific conclusion is:

- Insufficient Evidence;
- Emerging Evidence;
- Weakening;
- No Longer Supported; or
- Rejected

do not support new operational opportunities.

A Market Edge that is procedurally Under Review likewise does not support new
operational opportunities, regardless of its latest completed scientific
conclusion.

Supported and Strongly Supported are eligible to support Current Scientific
Applicability only when no qualifying review obligation remains unresolved and
all other protocol, Research Domain, Research Population, Evidence, analytical,
and compatibility requirements are satisfied. Eligibility grants neither
Governance nor operational authority.

Historical knowledge remains preserved.

Operational reliance does not.

---

## 8.8 Current Forecast Validity

The Alternative Probability Source used for a current opportunity must satisfy all applicable validity requirements.

Historical trust in a Probability Source does not validate:

- stale forecasts;
- incompatible propositions;
- invalid observations;
- or incomplete provenance.

Current forecasts must be independently valid.

---

## 8.9 Current Market Validity

Operational decisions depend upon the current market.

Historical Market Benchmark observations established scientific trust.

Current market observations determine current economic opportunity.

The methodology therefore distinguishes carefully between:

- historical benchmark evidence; and
- present executable market conditions.

---

## 8.10 Current Expected Value

Once scientific trust has been established, Pops' Edge estimates current expected value using:

- the trusted probability estimate;
- the current market price;
- applicable payoff structure; and
- all material transaction costs.

Expected value remains an estimate.

Individual wagers may succeed or fail regardless of expected value.

The methodology evaluates long-term decision quality rather than individual outcomes.

---

## 8.11 Economic Materiality

Current opportunities must satisfy Economic Materiality.

Economic Materiality asks:

> **Is today's expected advantage large enough to justify action after market frictions?**

This question differs from Practical Significance.

Practical Significance establishes a Market Edge.

Economic Materiality evaluates a current opportunity.

Both are required.

---

## 8.12 Operational Constraints

Operational decisions remain subject to considerations including:

- transaction costs;
- liquidity;
- position sizing;
- portfolio concentration;
- correlated exposure;
- bankroll policy;
- and execution constraints.

A scientifically valid Market Edge may legitimately produce no actionable opportunity under current market conditions.

---

## 8.13 Opportunity Qualification

A current opportunity qualifies as Evidence-Supported Positive Expected Value only when every required condition is satisfied.

Conceptually:

```text
Current Market Edge
        AND
Current Scientific Applicability
        AND
Domain Compatibility
        AND
Valid Current Forecast
        AND
Valid Current Market
        AND
Positive Expected Value
        AND
Economic Materiality
        AND
Operational Constraints
        ↓
Evidence-Supported Positive Expected Value
```

Failure of any condition returns the methodology to:

> **No operational opportunity demonstrated.**

---

## 8.14 Opportunity Strength

The scientific strength of a Market Edge and the attractiveness of a current opportunity are separate concepts.

Scientific confidence answers:

> **Why should this probability estimate be trusted?**

Opportunity strength answers:

> **How attractive is today's market price?**

A large current discrepancy cannot compensate for weak scientific support.

Likewise, a strongly supported Market Edge does not require action when today's market offers insufficient value.

---

## 8.15 Position Sizing

Position sizing is not part of the empirical research methodology.

Position sizing depends upon operational policy.

Possible considerations include:

- estimated advantage;
- uncertainty;
- bankroll;
- concentration;
- liquidity;
- and portfolio exposure.

The methodology establishes scientific trust.

Operational policy determines commitment.

---

## 8.16 Portfolio Management

Operational decisions consider the portfolio as a whole.

Current opportunities may be declined because of:

- correlated positions;
- concentration;
- existing exposure;
- liquidity limitations;
- or other operational constraints.

Scientific validity remains unchanged.

Operational suitability changes.

---

## 8.17 Provenance

Every operational opportunity shall preserve complete scientific provenance.

The Product Owner should always be able to answer:

> **Why do we trust this probability estimate more than the market?**

That provenance includes:

- governing Research Protocol;
- applicable Market Edge;
- latest Research Review;
- supporting Comparative Performance Report;
- research domain;
- and current scientific status.

Scientific trust is never detached from operational action.

---

## 8.18 Research Never Executes

Research establishes knowledge.

It does not execute operational decisions.

Research Protocols,
Comparative Performance Reports,
Research Reviews,
Edge Claims,
and Market Edges

never:

- place wagers;
- size positions;
- submit orders;
- or otherwise execute operational actions.

Execution belongs to a separate operational process.

---

## 8.19 Operational Feedback

Operational experience may motivate future research.

Examples include:

- unexpected transaction costs;
- changing market behavior;
- deteriorating liquidity;
- or persistent operational limitations.

Such observations may justify:

- new Research Protocols;
- revised Research Populations;
- additional Approved Research Dimensions;
- or future Research Reviews.

Operational experience informs future research.

It does not rewrite historical evidence.

---

## 8.20 No Wager

The methodology intentionally treats:

> **No Wager**

as a complete operational recommendation.

No Wager may result because:

- no Market Edge exists;
- the Market Edge lacks Current Scientific Applicability;
- the event lies outside the validated research domain;
- expected value is not positive;
- Economic Materiality is insufficient;
- operational constraints dominate;
- or scientific uncertainty remains excessive.

No Wager represents successful application of the methodology.

It is not absence of output.

---

## 8.21 Governing Principle

The empirical research methodology of Pops' Edge exists to answer one operational question:

> **Does the available empirical evidence justify trusting this probability estimate more than the market strongly enough to support action today?**

Only when the answer is yes does Pops' Edge recognize Evidence-Supported Positive Expected Value.

Every other circumstance returns the methodology to its default conclusion:

> **No operational opportunity has been demonstrated.**

# Chapter 9 — Methodology Governance and Versioning

## 9.1 Purpose

The Empirical Research Methodology is the highest-level governing document of Pops' Edge.

Its purpose is to define the principles by which empirical evidence is collected, measured, interpreted, and translated into operational decisions.

This methodology is intended to evolve more slowly than the Product, Architecture, or Implementation.

Accordingly, changes to this methodology require deliberate empirical justification rather than implementation convenience.

---

## 9.2 Governing Authority

The authority of Pops' Edge flows downward through four levels:

```text
Empirical Research Methodology
            ↓
         Product
            ↓
      Architecture
            ↓
      Implementation
```

Accordingly:

- Product decisions shall conform to the Empirical Research Methodology.
- Architectural decisions shall conform to the Product.
- Implementation decisions shall conform to the Architecture.

When conflicts arise, the higher-level authority governs.

---

## 9.3 Purpose of Versioning

The methodology is versioned to preserve the historical meaning of empirical conclusions.

Material methodological changes alter:

- how Evidence is collected;
- how Evidence is measured;
- how Comparative Performance is evaluated;
- how Edge Claims are assessed; or
- how operational decisions are informed.

Accordingly, material methodological changes require a new methodology version.

Editorial improvements, examples, clarifications, and improved explanations do not.

---

## 9.4 Material Methodological Change

A new methodology version is required whenever the governing empirical philosophy changes.

Examples include:

- redefining the Burden of Proof;
- changing the relationship between research and operational decisions;
- adopting a fundamentally different statistical methodology;
- changing the philosophy of Progressive Refinement;
- redefining Market Edges;
- redefining Evidence-Supported Positive Expected Value; or
- altering another foundational principle of empirical research.

Methodology versions exist to preserve scientific reproducibility rather than software compatibility.

---

## 9.5 Relationship to Research Protocols

Research Protocols implement this methodology.

A Research Protocol may become more specific than the methodology.

It may not contradict it.

For example, a protocol may define:

- one Market Benchmark;
- one Research Population;
- one surveillance window;
- one Practical Significance threshold;
- one confidence standard; or
- one capture horizon.

Those are protocol decisions.

The methodology governs how such decisions are made.

---

## 9.6 Relationship to Product Evolution

The Pops' Edge product is expected to evolve continuously.

Future releases may introduce:

- additional Probability Sources;
- additional sports;
- additional market providers;
- improved statistical techniques;
- additional Research Protocols;
- improved visualization;
- new operational capabilities; or
- new implementation technologies.

Such changes do not necessarily alter the methodology.

The methodology should remain stable across many product releases.

---

## 9.7 Relationship to Architecture

Architecture exists to implement this methodology.

Architectural components—including:

- data models;
- workflows;
- persistence mechanisms;
- services;
- user interfaces;
- and operational systems—

may evolve substantially while the methodology remains unchanged.

Implementation convenience does not justify changing the empirical research process.

---

## 9.8 Relationship to Implementation

Implementation choices are intentionally absent from this methodology.

This document does not prescribe:

- programming languages;
- databases;
- APIs;
- scheduling technologies;
- visualization frameworks;
- cloud providers;
- file formats;
- or statistical software.

Those decisions belong to implementation.

They may change without altering the methodology.

---

## 9.9 Empirical Integrity

The methodology exists to protect Pops' Edge from:

- hindsight bias;
- confirmation bias;
- overfitting;
- uncontrolled multiple comparisons;
- retrospective hypothesis construction;
- and implementation-driven methodological compromise.

Accordingly, implementation convenience never justifies:

- rewriting historical Evidence;
- relaxing prospective experimental design;
- weakening the Burden of Proof;
- silently redefining Research Populations;
- or otherwise compromising empirical integrity.

Empirical rigor takes precedence over implementation convenience.

---

## 9.10 Future Evolution

The methodology is expected to evolve.

However, it should evolve because a better empirical methodology has been demonstrated—not because a different implementation would be easier to build.

Future versions should preserve the enduring principles established by this document, including:

- empirical neutrality;
- reproducibility;
- falsifiability;
- prospective experimental design;
- separation of Evidence, Measurement, Research Review, and Operational Decision;
- and the distinction between Market Edges and Evidence-Supported Positive Expected Value.

---

## 9.11 Relationship to Historical Versions

Every methodology version remains part of the permanent historical record.

Later methodology versions do not invalidate earlier versions.

Rather, they establish the empirical framework governing future work.

Historical Research Protocols, Comparative Performance Reports, Research Reviews, and Market Edges should always be interpreted according to the methodology version under which they were produced.

The methodology therefore preserves not only scientific conclusions, but the scientific standards by which those conclusions were reached.

---

## 9.12 Governing Principle

The Empirical Research Methodology exists to ensure that the conclusions produced by Pops' Edge remain trustworthy regardless of how the software evolves.

Software will change.

Markets will change.

Probability Sources will change.

Statistical techniques will improve.

The methodology provides the stable intellectual foundation that allows those changes to occur without compromising the integrity of the empirical research process.

Accordingly:

> **The methodology governs the Product. The Product governs the Architecture. The Architecture governs the Implementation.**

That hierarchy preserves the enduring identity of Pops' Edge.

# Chapter 10 — Summary of the Empirical Research Method

## 10.1 Purpose

The purpose of Pops' Edge is not to maximize wagering activity.

Its purpose is to determine whether empirical evidence justifies wagering activity.

Accordingly, Pops' Edge begins from skepticism rather than optimism.

It assumes neither that Market Edges exist nor that Alternative Probability Sources outperform the Market Benchmark.

Those conclusions must be earned through evidence.

---

## 10.2 The Central Research Question

Every empirical investigation conducted by Pops' Edge ultimately asks one question:

> **Can an Alternative Probability Source estimate event probabilities more accurately than the Market Benchmark within a defined research domain?**

Everything contained within this methodology exists to answer that question rigorously, reproducibly, and honestly.

---

## 10.3 The Empirical Research Process

The methodology follows one governing sequence.

```text
Research Protocol
        ↓
Prospective Evidence Collection
        ↓
Research Snapshots
        ↓
Authoritative Outcomes
        ↓
Event-Level Measurements
        ↓
Comparative Performance
        ↓
Comparative Performance Report
        ↓
Research Review
        ↓
Edge Claim Assessment
        ↓
Market Edge
        ↓
Evidence-Supported Positive Expected Value
        ↓
Operational Decision
```

Each stage answers a different question.

No stage bypasses the one before it.

---

## 10.4 The Fundamental Distinctions

The Empirical Research Methodology deliberately separates concepts that many analytical systems combine.

Evidence is not Measurement.

Measurement is not Scientific Inference.

Scientific Inference is not Operational Decision.

Likewise:

A Comparative Performance Report is not a Market Edge.

A Market Edge is not Evidence-Supported Positive Expected Value.

Evidence-Supported Positive Expected Value is not a wager.

Each concept builds upon the previous one while remaining logically distinct.

Those distinctions preserve the integrity of the methodology.

---

## 10.5 The Role of the Market

The Market Benchmark is the foundation of every empirical investigation.

It is not merely another Probability Source.

It is the standard against which every Alternative Probability Source must be evaluated.

Accordingly, the first empirical question is always:

> **How accurately does the market predict outcomes under these research conditions?**

Only then does Pops' Edge ask:

> **Can another Probability Source do better?**

Without the benchmark, there can be no Market Edge.

---

## 10.6 Trust Must Be Earned

Pops' Edge does not infer trust from:

- reputation;
- intuition;
- historical profitability;
- model complexity;
- popularity;
- or isolated forecasting success.

Trust is earned only through accumulated empirical Evidence.

That Evidence must satisfy the Burden of Proof defined by the governing Research Protocol before Pops' Edge recognizes a Market Edge.

The methodology therefore distinguishes carefully between:

- theoretical Positive Expected Value; and
- Evidence-Supported Positive Expected Value.

Only the latter may support operational decisions.

---

## 10.7 Scientific Knowledge Evolves

Empirical knowledge is cumulative.

Evidence accumulates continuously.

Comparative Performance Reports summarize that Evidence.

Research Reviews determine what conclusions remain justified.

Edge Claims strengthen, weaken, or disappear as new Evidence accumulates.

Historical conclusions are never rewritten.

The methodology therefore treats knowledge as:

- reproducible;
- falsifiable;
- cumulative; and
- continuously open to revision.

---

## 10.8 Operational Discipline

A scientifically supported Market Edge does not require a wager.

It merely permits consideration of one.

Current opportunities remain subject to:

- current market prices;
- Economic Materiality;
- transaction costs;
- liquidity;
- portfolio constraints;
- operational policy; and
- Current Scientific Applicability.

Accordingly, the default operational conclusion remains:

> **No Wager**

until every required scientific and operational condition has been satisfied.

---

## 10.9 The Purpose of the Methodology

This methodology exists to protect Pops' Edge from the most common failures of quantitative decision systems.

It protects against:

- hindsight bias;
- confirmation bias;
- overfitting;
- uncontrolled multiple comparisons;
- retrospective hypothesis construction;
- implementation-driven methodological compromise; and
- unwarranted operational confidence.

It does so through:

- prospective experimental design;
- reproducible Evidence collection;
- disciplined statistical measurement;
- controlled Research Review; and
- explicit separation between empirical research and operational decision-making.

---

## 10.10 The Purpose of Pops' Edge

Pops' Edge is not fundamentally:

- a betting application;
- a forecasting system; or
- a model-comparison tool.

It is an empirical research platform whose purpose is:

- to determine whether statistically and practically meaningful Market Edges exist;
- to measure the strength of the Evidence supporting those edges;
- to monitor whether those edges remain applicable over time; and
- to identify only those current opportunities whose expected value is supported by that Evidence.

The ultimate objective is not more wagers.

It is better decisions.

---

## 10.11 Closing Principle

Everything contained within this methodology ultimately rests upon one enduring principle:

> **Evidence is permanent. Conclusions are provisional.**

Evidence is collected prospectively.

Measurements are reproducible.

Research remains falsifiable.

Market Edges are continuously subject to new Evidence.

Operational decisions are informed by scientific conclusions rather than replacing them.

Through this discipline, Pops' Edge seeks not merely to identify profitable opportunities, but to determine whether those opportunities deserve trust.

When the Evidence supports that trust, Pops' Edge acts.

When it does not, Pops' Edge is equally willing to conclude:

> **No Market Edge has been demonstrated.**

That willingness to refrain from action is not a limitation of the methodology.

It is one of its defining strengths.
