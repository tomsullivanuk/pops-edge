# Proposed handoff: starter–batter PA readiness

Status: **for Owner agreement; not authorized to execute**. October 12, 2026.
Task name: `Pops | MLB 2027 | Starter–batter PA component | Data readiness | PR #86`.

Read [the feasibility review](MLB_2027_COMPONENT_FEASIBILITY.md), current main
and AGENTS.md before execution. Main at assessment was
`9564b12dcd80f0b3347b4860b95984763f2e3061`; verify freshness. Preserve modified
local checkout and all original evidence; use the existing isolated documentation
worktree or another explicitly authorized isolated workspace.

If Tom approves this exact scope, obtain only the publicly offered Retrosheet
2023 parsed annual archive and the minimum same-season game/player metadata
needed to identify starters and dates. Keep acquisition under 100 MB compressed,
1 GB expanded and one focused working day. Record source URLs, hashes, license
notice, transfer sizes and acquisition time. No account, terms acceptance, paid
source, automated MLB collection, full multi-season ingestion or model fit.

Before outcome inspection, select 100 games deterministically by sorted stable
game ID, spread evenly across the season's game list. Audit PA keys, duplicate
plays, mutually exclusive K/unintentional-walk/other labels, intentional walks,
K-with-safe-reach, starters and substitutions, handedness/unknowns, initial
lineups, and suspended/resumed chronology. Reconcile game-level counts with
same-source game metadata, reporting every discrepancy and missing item.
Do not infer identity from names alone. No existing supplier bridge is required
for this same-source feasibility check; document what later integration needs.

Must hold: stable auditable game/player identity; target labels derivable without
pitch telemetry; actual dates/availability support strict prior-day histories;
starting-pitcher attribution auditable; no silent outcome-based exclusions;
licensed raw records and unrelated private information outside public Git.
If source metadata cannot establish chronology, stop and report that limitation.
Accepted limitations: sample audit cannot establish whole-archive completeness,
historical lineup announcement timing, future provider readiness, pitching
survival or game-level performance. Deferred: simulation, contact outcomes,
reliever availability, pitch mechanics, 2026 ingestion and model fitting.

Return a concise readiness report with aggregate coverage and any blockers.
On success, write equations, frozen baseline/challenger settings, chronological
evaluation, proposed 0.5% component gate and effort cap as a separate protocol
for Tom's agreement. Success authorizes neither that fit nor more acquisition.
Keep PR #86 draft; no merge, production changes, trades or purchases.
