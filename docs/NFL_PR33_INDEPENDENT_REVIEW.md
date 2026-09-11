# PR #33 independent implementation review

> Portable copy of the independent pre-merge report. PR #33 was subsequently
> merged at `d94e171`. Its original reviewed scope and decision below are
> preserved; only local link/log references were made portable.

**Decision: approve the reviewed implementation for the current local, personal NFL comparison workflow, with two nonblocking P2 findings. No P0/P1 blocker was established.** This recommendation does not authorize merge, deployment, release, acquisition, or order execution.

## Exact scope and authority

- Repository: https://github.com/tomsullivanuk/pops-edge
- Pull request: https://github.com/tomsullivanuk/pops-edge/pull/33
- Reviewed candidate: `321522a749279082b6908c340a29a8090f9a85e8` (`nfl/game-matching-board-v1.1`). Local HEAD was verified at this exact commit and the checkout was clean.
- Base and independently verified GitHub main: `e8d7469c7decabe52fa1eac444783837fd1b4e23`. Read-only `git ls-remote` confirmed this revision during review.
- Scope: all 26 changed files, including new schedule acquisition, Excel import/validation, comparison/replay, activity/settlements, full-season composition, local refresh server, HTML/filter code, tests, launcher and documentation amendments.
- Applied the complete root AGENTS.md from verified main, the methodology's authority/evidence/measurement principles, relevant Product and Architecture amendments, NFL release plan, NFL_BOARD_SLICE, NFL_ACTIVITY_SLICE, and board/refresh guides. Later owner-authorized workflow amendments supersede the earlier manual Excel confirmation and presentation requirements.

This was performed by a separate review agent. Implementation reports and the transfer self-check were context, not proof of correctness. The review did not treat local manual operation, provider availability, absent automatic recovery, screenshot/Excel copying limitations, lack of current-position reconciliation, or noncommercial hobby deployment as new blockers. This is not acceptance of a research study, a demonstrated Market Edge, an execution policy, provider rights, or predictive accuracy.

## Nonblocking findings

### P2 — An open season sheet does not reevaluate age or kickoff

Location: [nfl_season_board.py:111](../nfl_season_board.py), specifically the removal of the generated age function and interval at lines 111–112; server-side freshness checks remain at lines 62–67.

Trigger: open the season view while a quote is eligible, then leave that page open beyond the five-minute quote guard or kickoff. Filtering and switching folder tabs do not reload the sheet. The existing numeric difference and comparable-outcome count remain until a reload or refresh. There is no remaining browser-time age evaluation or warning in the generated season HTML.

Independent reproduction: a synthetic valid comparison rendered at 15:00 retained `data-gap="0.2465"`; the HTML had no `function age`, `setInterval`, or `Date.now()` evaluation. Reassembling exactly the same source snapshot at 15:05:01 correctly disabled every route. Thus the acquisition/derivation guard works, but the already-open presentation does not expire.

Scope/severity rationale: the original board boundary promised browser-time age/kickoff warnings, while the latest user-directed simplification removed the introductory warning. The current surface still describes saved snapshots, original source times, build-time guards and manual refresh. No captured evidence or chronology is rewritten and no live acquisition is claimed. Therefore this is an important presentation weakness, not evidence corruption or a new requirement for continuous retrieval. The distinction between load-time and ongoing freshness should be explicit.

Suggested bounded follow-up: use per-game expiry information to clear or visibly mark expired comparisons and update filters/counts without retrieving prices or resetting filters. Alternatively, obtain and record an explicit snapshot-only presentation decision and align the guide accordingly. The existing manual workaround is to reload the app to reevaluate saved prices, or use Refresh Bet Sheet to obtain new prices. No pre-merge correction is required by this review.

### P2 — A rejected workbook can prevent automatic season restoration after restart

Location: [nfl_season_board.py:17](../nfl_season_board.py), archive scan at lines 17–20; related [nfl_excel_import.py:68](../nfl_excel_import.py), which correctly preserves raw bytes before parsing.

Trigger: import a workbook whose declared count or other structure fails parsing, then restart the app. With no in-memory candidate, season assembly parses every archived workbook. A single rejected workbook raises before a valid candidate can be selected, so the season view fails even when valid captures and workbooks remain available. The same issue recurs on subsequent restarts while that archived input is present.

Independent reproduction: archived one valid synthetic workbook, attempted a second with an invalid declared game count, then invoked candidate-free season assembly. It failed with `Copied game count or footnotes are incomplete` rather than restoring the valid workbook.

Scope/severity rationale: failure is visible, invalid material gains no comparison authority, originals are preserved, and the owner can select a valid workbook and run Refresh Bet Sheet again to restore the in-session view. This is P2 local recovery friction rather than irreversible loss or inability to continue valid work. Do not delete or modify archived evidence as a workaround.

Suggested bounded follow-up: restore a previously successful explicit selection, or distinguish accepted/rejected archived inputs when choosing a restoration candidate; preserve and report the rejection. Add a rejected-input/restart regression. A generalized recovery subsystem is unnecessary. No pre-merge correction is required by this review.

## Validation performed

- Independently ran the full offline unittest discovery suite on the exact candidate: **774 tests passed in 44.698 seconds**, exit status 0. The execution log was temporary local review output, not a repository artifact.
- Inspected the relevant tests and source paths for exact schedule scope and identity, neutral status, timezone/date matching, rule wording, ambiguity, stale/future timestamps, incomplete captures, quote depth, single-contract fee rounding, tie-aware payout ranges, immutable bundle replay and tamper rejection.
- Examined machine-validation records and legacy verification dispatch: new automatic records do not persist a fabricated human reviewer/attestation, and legacy records retain their original format.
- Examined trade/settlement parsing and rendering: order rows are not fills; opposite sides are not netted; duplicate activity is flagged; settlement amounts are reconciled to winning quantities; cost-basis mismatches do not become realized profit; current holdings remain explicitly unconfirmed.
- Checked all-week iteration, informational TBD handling, partial failure preservation, no automatic order/account calls, inbox restrictions, local Host/Origin/token controls, and complete source inclusion in the Git diff.
- Ran separate synthetic probes reproducing the two findings above. The probe was temporary local review output.
- Executed the actual generated season filter JavaScript in Node with a small DOM stub. All/strictly-greater-than $0/$0.05/$0.075/$0.10 boundaries, missing/negative values, combined week/team/completion filtering and visible summary counts passed. The probe was temporary local review output.
- `git diff --check` passed across the complete base-to-candidate diff.

## Limits and state

No live provider calls or fresh sports/market captures were made. No claim of current external source layout availability, current fee publication, trading accuracy, or provider licensing is made. No browser visual QA was performed; generated content and JavaScript were inspected offline. No browser access restriction was bypassed. Full-suite success is supporting evidence, not a substitute for the source review above.

No implementation/repository files, commits, branches, GitHub reviews/comments, PR state, local running application, launchers, user archives, or production state were changed by this review. Only this separate project-root review artifact and temporary offline validation files were written. GitHub main verification was read-only.

## Next gate

The Product Owner may decide whether to merge PR #33 at the reviewed head, with the P2 findings recorded for a later bounded refinement. No corrective amendment or additional review round is required by this review. Any new implementation or changed PR head needs its own appropriate validation. Merge, deployment, release, and live acquisition remain separate authorizations; nothing in this review grants them.
