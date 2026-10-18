# Focused MLB correction — implementer review (October 17, 2026)

Source authority: GitHub `main` `9564b12dcd80f0b3347b4860b95984763f2e3061`; complete root `AGENTS.md` read before implementation. This is an isolated candidate, not an activated revision. The production checkout and archive were not changed.

## Problem and correction

The October 17 outcome reconciliation received a two-date union for `mlb:849817` repeating an unresolved postponed state and the already-current scheduled state. The previous derivation (`mlb-outcome-sequential-history-2`) appended both as new history, then correctly failed graph validation because the resulting Schedule opportunities had not been admitted. Derivation `mlb-outcome-sequential-history-3` suppresses only a complete, ordered semantic replay that ends at the current state. An incoming new state or a terminal reversion is not suppressed and still faces the normal fail-closed graph check. Version 2 and unversioned saved acquisitions retain their original replay rules.

The prospective selector previously aggregated identity rejections from every market in the current catalog. For `mlb:849808`, no target market was present in the retained catalog, yet unrelated Tampa Bay–Cleveland rules yielded `market-identity-rejected:malformed-settlement-identity`. The corrected diagnostic attributes parser rejections only where structured participant labels point to the target matchup; absent target evidence remains `market-unavailable`. Selection, capture timing, and date-only reschedule abstention are unchanged.

No past capture is backfilled or relabeled. No provider call, archive write, report refresh, recovery retry, deployment, or scheduler action is part of this candidate.

## Local validation and limits

New regressions cover repeated unresolved two-date lineage, legacy version-2 derivation, a genuinely new schedule instant, an unrelated malformed market, and a target-related malformed market. The three targeted tests pass. An initial 100-test run passed 97, with three launch-job rehearsals blocked by sandbox kernel boot-ID access (`startup-identity-unavailable`). With approved boot-ID access, those three tests passed individually and the complete 100-test suite passed. Another 55 reporting, source-replay, projection, and phase-evaluation tests passed. All runs used offline fixtures, not production providers or jobs. This is implementer evidence, not independent acceptance.

Before any activation, the PM/Chief Architect should review whether suppressing an ordered, complete semantic replay adequately preserves scientific chronology in the presence of repeated unresolved schedule rows. An independent reviewer should verify both derivation-version replay and target-specific diagnostic attribution against retained read-only fixtures, then review the exact candidate diff. Production rollout requires a separately authorized controlled deployment gate.

See [handoff](MLB_FOCUSED_CORRECTION_2026-10-17_HANDOFF.md).
