# MLB date-only market identity repair — October 11, 2026

Owner approval: “let's move forward and fix the mapping.” This authorizes the bounded prospective repair, independent review and subsequent controlled rollout; it does not authorize backfill, trading or historical rewriting.

## Problem and must-hold boundary

The retained production catalog already contained both October 11 Dodgers/Brewers markets before commissioning and before the T−6h cutoff. Kalshi's rules specify a calendar date without an explicit time. The old exact-time parser rejects them. The resulting immutable missed-window snapshot is accurate about absent capture and remains unchanged.

Must hold: unique authoritative event identity, prospective chronology, T−6h/five-minute window unchanged, separate phases, identical legacy regular-season results/replay, honest rejection diagnostics. Accepted limitations: date-only regular-season markets remain unsupported; ambiguous/rescheduled date-only events abstain; provider schema may evolve; local host availability and manual commissioning remain required. Deferred: 2027 seasonal authority and explicit regular-season adoption of the new identity rule.

## Narrow identity contract

The old explicit-time path remains the default and retains its original output/provenance. The optional `kalshi-mlb-postseason-unique-date-1` path requires agreeing primary and secondary winner rules, ordered away/home participants, structured YES/NO labels, a complete verified catalog-dependent official MLB slate and exactly one same-day matchup. Official date, response date envelope and New York scheduled-start date must agree. Calendar convention follows the existing Eastern schedule discovery boundary; uncertain cross-calendar cases abstain.

Only MLB postseason game types F/D/L/W/S/C/P can use this path. Doubleheaders/game-number>1, incomplete schedule provenance, raw reschedule/resume markers, multi-date lineage and observed changes of scheduled instant block date-only admission. Exact-time matching retains its existing semantics. Expiration, occurrence_datetime, ticker clock and quotes never supply game start; accepted MLB schedule authority alone determines T−6h. A complete-slate requirement belongs to verified acquisition, not a fabricated partial list supplied to a parser.

## Versioning and architecture

The shared parser is used both in supporting derivation and current catalog selection. Both paths opt into the new behavior only for `provider-pages-canonical-union-4`; postseason gating is in the shared date-only matcher. Historical versions 1/2/3 remain accepted and reproduce the old exact-time behavior. Version 4 preserves version-3 page union/lineage semantics and explicitly changes permitted supporting interpretation. Retrospective supporting continues to reject date-only rules. Supporting-session derivation is identified as `kalshi-mlb-postseason-unique-date-5`; old derivation/union pairs remain supported.

New date-only series carry the new rule in collector_version. Precise-time series keep the old version/provenance. Protocol identities, populations, phase cutoff, scoring and capture policy do not change; no new initializer/cohort is required. No old bundle is reinterpreted to mint a series or forecast. A fresh completed compatible supporting acquisition is required before date-only capture can select a new series. The existing current schedule and series identity checks remain mandatory.

The collector merges known schedule-change histories into the date-only block set. Rejected identity codes are visible as `market-identity-rejected:<codes>` rather than all being labelled unavailable. New activated snapshots receive an activated-acquisition limitation label; historical misleading fixture text is preserved unchanged.

Regular-season date-only matching is deliberately not enabled by this repair. Therefore 2026 regular precise-time behavior is protected, but next year's date-only regular markets would still abstain until explicitly adopted with a new seasonal authority. Reuse the reviewed matcher then, rather than loosen matching globally now.

## Validation and rollout gate

Real retained six-market/three-game fixture covers both winner sides and home-only selection. Tests cover original precise-time behavior, regular date-only exclusion, disagreement/missing labels/rules, calendar conflicts, same-day ambiguity, doubleheader/game number, schedule-change/resume rejection, irrelevant ticker/expiration fields, invalid-time no-fallback, legacy bundle replay, exact-target simulated capture with no duplicates, late no-call and immutable missed snapshots.

Before production, independent reviewer must evaluate the new date-only authority contract and exact commit. After acceptance: quiesce/drain affected components, verify backups, stage all compatible pins, validate old graph/projection and immutable missed snapshot, refresh supporting through the ordinary authorized acquisition path, verify actual next-game mappings, then resume only after gates pass. No backfill or report regeneration is implied by this matching repair. After version-4 publication, rollback must retain code capable of validating version-4 authority. Stop/quiesce capture and disable the postseason protocol in configuration if needed, preserving original regular IDs and all new authority/evidence. Do not repin the old version-3-only validator or overwrite archives from backup.
