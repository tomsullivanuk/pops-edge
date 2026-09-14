# MLB v1.2.0 reporting contract

Status: documentation-only candidate, September 12, 2026. Product decisions and
layout were approved by the Product Owner; this document specifies their reporting
contract for review before code. It does not claim implementation, empirical
validation, study closure, deployment or release.

Baseline: GitHub main `1f1c033f7b0250f390aee597f85246cbdeba564c` (PR #47),
verified when drafting. Apply [Methodology](../EMPIRICAL_RESEARCH_METHODOLOGY.md)
> [Product](PRODUCT.md) > [Architecture](../ARCHITECTURE.md) >
[September 12 release direction](RELEASE_DIRECTION_2026-09-12.md) > implementation.
The corresponding amendments in those governing documents adopt this contract
within their respective authority; this file does not independently outrank them.

## 1. Product outcome and report names

Answer: **How well do observed Kalshi MLB probabilities predict outcomes, and
how complete is the evidence?** Acceptance does not depend on a favorable score.

The main page is **Performance Report**, reporting the live-quote study. It owns
most of the page: cumulative performance, coverage, uncertainty and expandable
report details. A compact, separately dated collection-status section follows.
A small **Historical candle report** link opens a separate static report; historical
results do not occupy a second summary panel on the main page.

Both are reports about observed outcomes. In scientific metadata, retain the
existing prospective and retrospective design tags, Protocol identities and
meanings. The labels do not merge their populations or estimands. Both use the
canonical home-team YES proposition; away contracts remain diagnostic only.
MLB supplies schedule/status/outcome authority. Kalshi candles and live quotes
remain different probability representations under their existing rules.

The historical study period is fixed. Its final report is not routinely updated.
Its existing interim publication must not be labelled final merely because the
period has elapsed. The link identifies the exact interim or final report, or
states that no validated report is available. Any necessary later correction
preserves the original and has a separate explicit identity and correction reason.
Normal Performance Report updates never regenerate the historical report.

## 2. Scientific population and chronology

### 2.1 Typed reporting context

The successor reporting path must carry one immutable, versioned
`StandaloneReportContext` per study report. This is a logical contract, not a
requirement for a particular programming layout. Its required material is:

| Field | Meaning and validation |
|---|---|
| `context_version` | Explicit successor contract identifier; legacy records never acquire these meanings implicitly. |
| `protocol_id`, `design_tag`, `source_id`, `source_role`, `domain` | Exactly one existing standalone study and its compatible probability representation. |
| `source_boundary` | Namespace/mode, exact selected manifest IDs and complete dependency closure, source digests and evidence cutoff. Complete selection is independently reconstructed, not caller-selected successes. |
| `evidence_cutoff_at` (K) | Time through which source facts, acquisition authority and corrections are available for this analysis. Later source facts are excluded. |
| `cumulative_scope` | Complete Protocol population from its governed origin, known through K; no caller-selected lower bound or successful-event filter. |
| `bounded_scopes` | Exact Protocol-required event-time intervals and endpoint semantics, independently named from K. |
| `computation_started_at` (C), `computation_completed_at` | Actual times of initial derivation. Newly produced analytical objects retain truthful computation/effective provenance. |
| `report_generated_at` (R) | Actual report composition time, no earlier than completion of its referenced analytical work. |
| `report_status`, `closure_reference` | `in-progress`, `interim`, `final`, or an explicitly identified correction; final requires the applicable accepted closure record. No inferred closure. |
| `rule_references` | Exact scoring, representation, calibration, uncertainty, reference-baseline and successor replay/identity versions. |

K must not be after C. Source availability must be proved using archived acquisition
and completion authority, not inferred from an event's scheduled time or a provider's
historical candle timestamp. A new run freezes a verified source boundary at a
trusted time. A historical source boundary is accepted only when its exact retained
selection and dependencies can be reconstructed; a caller-supplied date alone is
not proof that a manifest set was then available. Concurrent source additions do
not enter a frozen run. If a consistent complete selection cannot be established,
fail visibly and allow a later independent attempt; do not stop collection or
mutate its locks, markers, indexes or checkpoint for report generation.

Preserve the existing namespace-wide archive-integrity gate before pinned replay.
Missing/corrupt archive objects cannot be hidden by selecting a convenient source
subset. Session-local rejected or abandoned material remains visible and excluded
under its existing rules; it does not acquire scientific authority from packaging.

Correction, classification, schedule and capture selection retain their original
Protocol-specific chronology rules. K limits available source authority; it does
not replace the capture/population boundary at which prospective eligibility must
be evaluated. Later discovered calendar material can expose gaps with its actual
retrieval times, but cannot invent earlier schedule knowledge or quotes.

### 2.2 Exact observation scopes

**Historical candle report:** keep the fixed bounded interval
`(2026-03-25T00:00:00-04:00, 2026-09-05T00:00:00-04:00]`, duration
14,169,600 seconds, with the independent strict pre-activation rule excluding
starts at the upper endpoint. K may be later; it must not slide either endpoint.
Cumulative and bounded artifacts remain separate even if their populations match.
An interim report identifies incomplete calendar/acquisition coverage within this
fixed period; it must not relabel the known subset as the whole study.

**Performance Report:** preserve cumulative standalone opportunity accounting
under the prospective Protocol, starting at activation. Do not restrict its
cumulative Coverage universe to games already played. Known future scheduled
opportunities remain visible; capture-not-yet-due is classified using the capture
target and K. A target already due can precede a game's start by six hours, so
scheduled start after K does not by itself remove the opportunity from cumulative
accounting. Scored performance still requires an eligible authoritative outcome.

The required prospective bounded interval remains exactly `(K − 18,000 seconds, K]`
in scheduled-event time, with Protocol population rules independently applied.
Keep it in report detail, separate from cumulative results. Do not clamp its lower
endpoint to activation, change its duration, or substitute a recent sample of
scored games. Protocol membership naturally excludes pre-activation opportunities.
No new owner-adjustable windows, rolling averages or segment searches are added.

The prospective study's final closure remains after the final 2026 regular-season
games and satisfaction of its existing obligations. Postseason is excluded.
Release timing does not close either study, change activation or erase final-report
obligations. The meaning of cumulative scope is unchanged by a shorter visible
summary such as “collected since September 5.”

### 2.3 Newly computed Analysis and legacy compatibility

Current V3 Coverage uses `analysis_boundary` for available Evidence, derived
object effectiveness and the bounded event-window end. V3 performance/report
validation also measures required duration against that same boundary. Merely
setting `report_boundary` later does not separate these meanings.

Introduce explicit successor dispatch only in the reporting analytical path where
this separation is necessary. Source Evidence, acquisition Protocols, capture
algorithms, original derivation/Measurement records, V3 serialization and old
report replay remain unchanged. Do not add optional fields that silently change
old constructor semantics or assign a historical effective time to a new object.

The successor validator must:

1. Independently replay the complete pinned source graph under its original
   versions and availability rules through K, including visible failure dispositions.
2. Derive the complete Protocol opportunity and eligibility sets before selecting
   captures, resolving outcomes, or constructing scores. Apply event-window
   membership separately from source availability.
3. Compute report-local derivations/measurements from those inputs at their actual
   computation times, with references to K and their exact upstream authority.
   A new computation after K is permissible Analysis of earlier available Evidence;
   it is never claimed to be an analytical object available at K.
4. Admit those newly computed objects only through exact deterministic reconstruction
   against that context. Do not globally relax a V3 `effective_at <= analysis_boundary`
   check, admit arbitrary post-K objects, or let post-K outcomes enter selection.
5. Reuse an existing analytical object only when its type, source pins, selection,
   context and original temporal meaning match exactly. Otherwise produce an
   explicitly typed successor with unchanged arithmetic and selection rules.
   Each analytical result resolves to one compatible type/version; mixed or
   ambiguous versions cannot win by input order.

The successor context must participate in analytical identity and reference
compatibility. The implementation may reuse exact arithmetic helpers, but cannot
bypass source/graph validation or union older report populations. This is bounded
reporting support, not a change to live acquisition or a generic version store.

### 2.4 Worked chronology cases

- **Later historical retrieval:** an eligible August 20 game's candle is acquired
  September 10. A report with K on September 12 may score it under the original
  candle rule, retaining September 10 retrieval and actual later computation times.
  Its event window still ends September 5. A pinned report with K September 5 does
  not gain that candle later.
- **Missed live capture:** a September 10 capture window expires with no valid quote.
  A September 12 report preserves its missing/failed classification and includes
  it in eligible Coverage. A later outcome or historical candle cannot supply the
  missing quote. Later collection for another game can proceed independently.
- **Later outcome correction:** an MLB correction available September 13 cannot
  alter a report pinned through September 12. A new report with a later K resolves
  the original correction lineage and derives a new compatible score/report.
  The earlier report's bytes and meaning remain intact.
- **Game not yet started:** a known game starts at 20:00 and its capture target is
  14:00. At K=15:00 it may have a valid capture awaiting outcome and remains in due
  cumulative accounting. It is not removed merely because kickoff is in the future.

## 3. Coverage and presentation mappings

Coverage is independently derived from the complete available schedule authority,
not supplied by the caller, successful provider requests or report rows. Preserve
valid-empty sets and the Methodology's exact partition:

```text
schedule universe = not yet due + protocol-ineligible + eligible due
eligible due = all disjoint failure/non-measured categories + scored
```

Required labels and sets:

| Display | Definition |
|---|---|
| Known schedule opportunities | Complete scope-specific schedule-derived universe, including not-yet-due and excluded identities. |
| Eligible opportunities | Protocol-eligible opportunities whose capture obligation is due, independent of capture and outcome success. |
| Captured | Distinct eligible opportunities with the authoritative valid in-tolerance home-team source observation at the capture-validation stage. For candles, the rule-selected valid candle; for live quotes, the selected valid Snapshot/MarketObservation. Count once, never by slot, manifest or request. This does not imply valid derivation or scoring. |
| Valid probability observations | Captured subset with the compatible validated probability derivation, independent of whether an outcome can yet be scored. Optional explanatory detail, not a new denominator. |
| Scored | Exact compatible authoritative Measurement population; all scores, calibration and sample size use this set. |
| Unscored | Eligible opportunities minus scored, with the full disjoint reasons retained. Never label all unscored cases “missing capture.” |

Require `scored ⊆ valid probability observations ⊆ captured ⊆ eligible` and expose
identities supporting each count. Source validation and category precedence govern;
a successful network response is not a valid capture. For the primary overview,
show eligible/captured/scored, followed by missing/invalid/awaiting-outcome details.
Do not merge excluded or not-yet-due cases into eligible denominators.

Prospective reconciliation retains `missed_window`, `acquisition_failed`,
`captured_invalid`, `timing_invalid`, `derivation_unavailable`, `outcome_unresolved`
and `measured`, plus the not-yet-due/ineligible categories. Retrospective retains
`archive_unavailable`, `archive_invalid`, `candle_unavailable`, `candle_invalid`,
`derivation_unavailable`, `outcome_unresolved`, `measured` and its corresponding
not-yet-due/ineligible categories. Existing precedence and detailed reasons remain
visible; presentation cannot change category assignment.

Historical reporting additionally derives the unambiguous qualifying-market set
from market-mapping authority. Show offered-market coverage over eligible games
and scored/measurable-market coverage over offered games separately, alongside the
existing overall scored/eligible rate. Do not infer “no market” from an absent
retrieval manifest: absent acquisition and absence of a qualifying market are
different facts. When offered membership is unverified, report that limitation
and withhold the rate that requires it rather than inventing membership.

All rates name numerator and denominator; zero denominators yield unavailable, not
0% or 100%. Calendar dates not verified by authoritative acquisition remain
explicit gaps outside known-game counts. Do not invent the number of games on
unknown dates. Corrupt or ambiguous authority fails closed; visible non-authoritative
session failures remain auditable without being silently admitted or discarded.

## 4. Probability scores and simple reference

Retain the existing Protocol's exact-decimal, 50-digit arithmetic: binary Brier
`(p(realized) − 1)^2` on the 0–1 scale, and extended-real log loss
`−ln(p(realized))`, with positive infinity at zero. No doubled Brier convention,
clipping, win-rate substitute, profit metric or execution-price adjustment.

The initial reference rule is `constant-home-probability-0.5`, version 1. It was
approved September 12, 2026 as a **descriptive reporting addition after study
commencement**, not a precommitted challenger. It does not change Protocol identity
or claim comparative-research authority. The report records its rule and adoption
date independently of the original Protocol.

For each exact nonempty measured set, evaluate home/away probabilities 0.5/0.5
against the same outcomes and scoring convention: mean Brier 0.25 and mean log
loss ln(2). For an empty set, both are absent. Its sample size and measurement-set
reference must equal the Kalshi report's. Do not evaluate it on missing outcomes
or fit a home-win rate on the reported sample. No additional baseline is in scope.

Retain Kalshi's deterministic one-sample 95% bootstrap with 200 resamples and its
current sampling/quantile rule. Bind seed material to the successor context,
Protocol/source/scope, actual bounded interval, canonical Measurement IDs and the
existing rule parameters. Preserve the original seed construction for legacy
objects. A successor seed encoding must be explicitly versioned; it adds the
separate context, not a new statistical procedure. Verification replays the saved
context and seed; it must not resample from the verification wall clock or renderer.
Show unavailable empty intervals and explicit singleton/constant-score limitations.
An interval measures sampling uncertainty, not every acquisition or selection bias.
No difference interval, significance classification, Market Edge or wagering
recommendation is created by comparison to the constant reference.

Calibration uses the same scored set, existing ten fixed 0.1-width bins, left-closed/
right-open semantics with final endpoint closed, sample-share absolute-gap WACE and
empty-bin rule. Detailed display may project bin counts, mean home probability
and realized home-win frequency from exact referenced measurements. Empty bins
have zero count and unavailable means/frequencies and do not contribute to WACE.
This projection is derived Analysis with explicit rule/input references, not new
Evidence. No adaptive bins, smoothing, extra intervals or new calibration estimator.

## 5. Report contents, output packages and replay

Each report references exactly one compatible cumulative performance and the exact
required bounded performance set, their complete Coverage, uncertainty, baseline
reference, limitations and provenance. No report pools the two studies, selects
only favorable results, attributes their difference solely to capture method, or
claims policy/scientific applicability authority.

The report package contains its report root, referenced derived analytical objects,
source-boundary/Protocol/rule references, machine-readable representation and
readable HTML. Include software revision, all frozen scientific context needed for
replay, package digest and clear reproduction instructions against retained source
Evidence. It need not duplicate the whole archive. Unknown/foreign/extra/conflicting
analytical references fail validation; a digest alone is not semantic validation.

Packages are immutable derived Analysis outside the Evidence archive and source
checkout. They do not pass through the existing singleton retrospective publication
command or alter its staging. Inputs are never “all earlier reports”: independently
reconstruct from source Evidence. Existing frozen publications can be inspected or
referenced only at their exact compatible scope, never concatenated into a new set.

A candidate freezes truthful initial computation provenance and payload before
publication. Exact verification reconstructs its bytes and IDs using those recorded
inputs/times; this verifies earlier computation rather than pretending a new
computation occurred earlier. Verification time belongs to a separate receipt.
Reopening or explicitly verifying an existing package does not create a fresh
scientific result or date. A genuinely new context/correction creates a new package.
Ordering, filesystem enumeration and ambient arithmetic context cannot alter replay.
Formatting-only regeneration may create a new rendering receipt but never changes
scientific values, seed, membership or original report generation time.

## 6. Local delivery and failures

- **Open Performance Report:** open the last saved main page. No scoring, provider
  access, archive write, job execution or service dependency.
- **Update Performance Report:** explicitly generate a new live-quote report from
  already archived inputs, validate it, complete its package, and only then replace
  the non-authoritative current-report reference. It does not repair collection.
- **Historical candle report:** open its own explicitly selected static package.
  Generation/completion is separate; routine updates retain its link and dates.

A small mutable entry/attempt-status artifact outside the archive records the
current valid package reference and last generation outcome. Partial output is
not current. On failure, retain the prior package and its dates with a visible
failed-update notice. If none exists, show “No validated report available.” A
valid empty report is different from a report that could not be validated.
Missing or unavailable historical content does not block a valid live-quote
update; it remains visible and still must be addressed for release acceptance.
No silent selection among competing package roots is allowed.

Collection status is non-authoritative and independently dated. Consume existing
sanitized operational material through a read-only path; do not invoke a command
that writes a heartbeat, refreshes a checkpoint or collects data to draw the page.
Show current observed readiness, last valid completions, failures/skips and existing
recovery guidance. Missing/stale operational status is not scientific completeness
and need not invalidate a valid report. Opening a frozen page does not imply live
status. Display its observation time and avoid an undated “all healthy” indicator.

Minimum delivery states: no validated report → candidate → validated package →
current reference. A failed candidate leaves current reference unchanged and
records a visible failure. Study closure is a separate governed transition.
Source failures retain their existing visible non-authoritative/valid-completion
transitions; report generation grants no acquisition or recovery authority.

## 7. Acceptance examples and boundaries

| Scenario | Required observable outcome |
|---|---|
| Late historical retrieval | Fixed historical event window, actual later source/computation times; earlier pinned report unchanged. |
| Post-K outcome correction | Excluded from old report; new context selects corrected lineage without rewriting old result. |
| Missing live quote | Eligible failure remains; historical candle or later quote cannot repair it. |
| Future game with due capture | Retained in cumulative accounting; no score until authoritative eligible outcome. |
| Empty / one / identical-score samples | Absent / explicitly degenerate uncertainty as governed; no invented confidence or sufficiency. |
| Invalid, partial, ambiguous or corrupt authority | No fabricated valid result; reasons visible; integrity failures do not become a cosmetic warning on an admitted report. |
| Unknown calendar dates | Disclosed outside known-game counts; no invented denominator/completeness. |
| Permuted inputs / changed ambient precision | Exact same saved-context analytical IDs, values and replay bytes. |
| Package/input tampering or foreign study reference | Validation rejects; last validated current report remains intact. |
| Failed update / unavailable status | Prior report dates preserved; failure/status absence visible and independently scoped. |
| Historical link on routine update | Same selected static historical package and dates; no historical recomputation. |
| NFL/World Cup regression | Existing workflows, schemas, outputs and evidence unchanged. |

Must hold: trustworthy source authority, failure-inclusive Coverage, truthful time,
exact replay, separate populations, useful offline display and safe visible local
failure. Full historical/prospective report obligations remain, but an explicitly
dated in-progress release is permitted without claiming final study closure.

Accepted limitations: local manual generation, frozen status, sleep/network outages,
visible missed observations, insufficient samples, same-device secondary storage
and existing documented safe manual intervention. No numerical capture target or
minimum favorable performance is introduced.

Deferred: server/shared shell, automated refresh/recovery, cloud hosting, arbitrary
windows, fitted baselines, external-source admission, further native models,
applicability/policy/governance UI, wagering and generalized publication services.

This candidate changes documentation only. Implementation, source acquisition,
report publication into operational use, protocol closure, commit/push/PR actions,
deployment and release remain separate authorization gates.

## 8. Owner-approved simple-report hierarchy — September 13, 2026

The [simple-report correction](MLB_SIMPLE_REPORT_DECISION_v1.2.0.md) governs the
principal presentation of the delivery candidate. Cumulative live performance,
friendly study/report dates, incomplete status, eligible/captured/scored counts,
material missing/awaiting counts, Brier versus 50% and governed uncertainty precede
all technical evidence. Exact values remain unchanged; display-only rounding is
explicit. Technical IDs/JSON/provenance, internal timestamps, log loss, detailed
calibration, bounded results, complete categories and supporting links are in
collapsed Details. The local entry shows the principal report and a small independent
historical link; failed attempts use a readable notice with metadata in Details.
This is a presentation correction, not a scientific-rule change or full shared shell.
