# Release direction — September 12, 2026

## Decision and authority

The Product Owner agreed to narrow v1.2 to MLB Kalshi collection and baseline
market-performance presentation, tentatively target a unified NFL/MLB experience
for v1.3, and continue external MLB model/supplier investigation independently.
The Product Owner explicitly requested this roadmap update.

Baseline: authoritative GitHub main
`6c91f0ebfc0aca124e31a0cceed293a2252d888c` (PR #46). NFL v1.1.0 has been
published and deployed locally. This decision changes future release allocation
and sequencing; it does not relabel historical releases, PRs, evidence or contract
versions, and it does not declare v1.2 or v1.3 complete.

## v1.2 — MLB market baseline

Deliver existing Kalshi MLB collection with visible health and coverage, separate
retrospective and prospective performance reports, and an understandable baseline
performance display. Show observation periods, eligible/captured/scored/missing
populations, protocol-governed probability scores and simple baselines,
calibration, uncertainty, provenance and limitations. Include documented local
operation and recovery.

Must hold: immutable evidence and truthful chronology; deterministic replay;
failure-inclusive coverage; separate retrospective/prospective populations;
visible invalid or missing material; no reconstructed prospective observations;
no implied Market Edge, policy approval or wagering authority. Acceptance does
not depend on Kalshi beating a baseline. Insufficient evidence is a valid result.

Accepted limitations: local operation, documented manual intervention, visible
collection failures and missed observations under the existing operating posture.
Reports may show an explicitly dated in-progress study, without claiming protocol
closure or final findings. Existing study windows and close/report obligations
remain unchanged.

Deferred: external-source admission, further native-model development, current
scientific applicability and policy recommendation, policy alignment, the broader
Forecast Intelligence Workspace, policy-driven Opportunity Analysis integration,
automated wagering and hosting migration. Implemented foundations are retained.

## v1.3 — Unified experience (tentative target)

Provide one Pops' Edge entry point and consistent navigation, branding and
interaction across NFL and MLB. Start design with a shared shell and sport
selector, with consistent comparison/performance/data-status destinations where
capabilities exist. User journeys, detailed scope and acceptance criteria remain
to be agreed before implementation. Preserve sport-specific workflows and
scientific/operational boundaries. Do not require a shared scientific population,
universal schema, hosted deployment or full Forecast Intelligence Workspace.

## Independent investigation

External MLB model/supplier investigation continues alongside v1.2 and v1.3.
Admission still requires sufficient access and retention rights, identity,
chronology, usable probabilities, market independence and acceptable cost.
Supplier integration requires its own scope and approval. Existing native-model
results and admission gates remain intact; no new native development is scheduled.
No successful candidate or track-closure decision is required to ship either
release. This decision itself authorizes no outreach, trial, spending or provider
acquisition.

## Sequencing amendment

This decision supersedes the whole-programme release allocation and mandatory
release ordering in `RELEASE_PLAN_v1.1.0.md` and the September 8 allocation wherever
they would require PR18/PR19 closure or PR20–PR24 completion for v1.2. Historical
filenames, completed records, PR identifiers and scientific acceptance criteria
remain intact.

- PR17 collection and standalone reporting remain the scientific foundation of
  the v1.2 scope. The baseline display can consume those validated reports without
  implementing current applicability, policy recommendations or governance UI.
- PR17C/PR17D protocol closure and final-report obligations remain in force. An
  in-progress display cannot impersonate either final report or change its window.
- PR18 external and PR19 native tracks are outside the v1.2/v1.3 critical path;
  this amendment does not falsely close either track or admit a source.
- PR20/PR21 applicability and policy alignment, PR22's broader Workspace and
  PR23 policy integration have no assigned release. Their scientific dependencies
  remain in force when those capabilities are separately resumed.
- The historical PR24 whole-lifecycle gate is not the narrowed v1.2 release gate.
  v1.2 instead requires validation of the scope above, World Cup/NFL compatibility,
  operator documentation and an honest limitations review.
- The tentative unified UX is separately scoped; it does not inherit the full
  PR22 research/governance surface by virtue of sharing a user interface.

Next planning step: assess existing collection/reporting/display capabilities
against the narrowed v1.2 boundary and define the smallest remaining work with
observable acceptance criteria. Do not invent PR numbers, delivery dates, new
metrics or protocol changes in that assessment.

Only documentation edits are authorized by this request. Code implementation,
commit, push, PR creation/merge, deployment, activation and release publication
remain separately authorized actions.
