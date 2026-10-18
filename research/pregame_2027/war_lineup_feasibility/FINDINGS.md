# Starting-nine WAR: retained-input audit complete; six-arm execution blocked

October 18, 2026. **Approved design preserved; no model fits or performance results.** Numeric projected WAR/PA is available in four retained exports, but the strictly prior-game observed position-player WAR needed by four of the six arms is not established. The entire matched six-arm execution stops at this data gate; we did not silently run only preseason or substitute an offense metric. [Bounded protocol](PROTOCOL.md), [reproducible audit](audit.py), [aggregate receipt](audit_results.json).

## What is available

Read the actual four Owner-labelled FanGraphs projection CSVs and verified their existing hashes. Each contains WAR,PA,Fld,Off,Def,BsR and player IDs; all identified usable rows have finite WAR and positive PA. Negative WAR is legitimate, retained, and common. The files contain no explicit season, publication date or projection-system columns. Year association is the Owner's labelled replacement provenance, reconciled byte-for-byte with prior imports—not independently established original preseason release timestamps or immutable vintage.

| Year | Identified usable projection rows | Required starters matched | Matched initial-nine slots | Games with both nines' WAR/PA available |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 3,303 | 676/678 | 43,612/43,722 | 2,319/2,429 |
| 2023 | 3,590 | 641/643 | 43,571/43,614 | 2,380/2,423 |
| 2024 | 3,710 | 645/645 | 43,668/43,668 | 2,426/2,426 |
| 2025 | 4,138 | 660/661 | 43,552/43,668 | 2,310/2,426 |

There are 269 missing-projection slots across four years; no joined projection has zero PA or invalid WAR/PA. This is raw coverage, **not a proposed complete-case model cohort**. The protocol declares missing-projection fallbacks to preserve all original targets. Four exports have 3,304/3,591/3,711/4,140 total rows; respectively 1/1/1/2 unidentified rows do not join. Identity comes from the retained unique official-game/designated-side/initial-slot bridge, not player-name inference. No retained 2026 projection is included in the scoped inputs. The approved feasibility window therefore supports 2024/2025 evaluation after 2022/2023 training, conditional on the missing observed inputs.

## Exact observed-WAR gap

The scoped projection files contain season forecasts, not dated observed WAR. Inspected all 20 extracted Retrosheet CSV headers (2022–2025 plays,gameinfo,pitching,allplayers,teamstats): no observed WAR column or complete FanGraphs advanced fielding/baserunning component set. Retained archives can contain unextracted traditional fielding data, and event rows record positions/outs/basic plays; that is not evidence that FRV/OAA, catcher evaluation and advanced baserunning WAR components are available. Basic putouts/errors or hitting-event counts cannot simply be relabelled as the same FanGraphs total position-player WAR.

Provider documentation reinforces the chronology check:

- FanGraphs' [2024 WAR update](https://blogs.fangraphs.com/2024-fangraphs-war-update/), April 5, 2024, describes revised fielding/baserunning components and retrospective changes back to 2016. Retrospective current WAR can therefore differ from the metric originally published for an earlier season. We have not established the precise revision convention embedded in these projection files or a compatible daily observed archive.
- The [custom-date-range announcement](https://blogs.fangraphs.com/instagraphs/leaderboards-update-introducing-custom-date-range/), May 31, 2019, states that defensive WAR components are prorated from the entire season. This is a documented historical behavior and a reason to validate current semantics—not proof we inspected every current export implementation. A date cutoff alone is insufficient evidence that future defense/season information is excluded.
- The [position-player WAR overview](https://library.fangraphs.com/war/war-position-players/) describes all-around batting, baserunning, fielding/positional and replacement/league adjustments. The older Library explanation must be read alongside later updates; it is not a ready-to-run current as-of reconstruction from the retained offense counts.

The specific missing input is a player-ID-linked, dated cumulative position-player **WAR and corresponding PA** source (and its definition/version/publication basis), or all components needed to reconstruct it consistently using only information before each target. We have neither established in the retained inputs. This is not a claim that no historical WAR archive exists or that a new source necessarily costs money.

## What is fixed and what is not authorized

The protocol preserves six challengers: preseason/raw observed/player-level PA-dependent blend, each replacing the six recent-team terms/interactions while retaining progress+starter inputs, and each adding to the unchanged baseline. No batting-order weights on total WAR; no extra exposure input. Training-only blend selection, zero/low-PA rules, common targets, per-year/April–May breakdown, paired metrics and practical gates are defined before any outcome comparison.

Completed experiment count remains 24. This is **P05: approved, feasibility blocked**, not a failed predictive experiment or a completed seventh learner. Payroll remains separate. No v3.5, logistic or blend-weight fit, new raw data acquisition, credentials, spending, data upload or production change occurred. Only permitted audit code/aggregate receipts/protocol/decision documentation are proposed for draft PR #86, after [independent review](REVIEW.md).

## Smallest next decision

Locate an applicable provider-supported daily/archive source or valid component reconstruction with explicit cutoff/version semantics, then audit it before activating this protocol. If only retrospectively revised/reconstructed data is obtainable, discuss its exact limitations and whether Tom wants that exploratory experiment before fitting. A preseason-only test, different WAR definition or offense-only substitute would materially change the approved comparison and is not silently authorized. We stop the dependent execution here and report the blocker; no conclusion about the usefulness of lineup WAR follows.

## Subsequent source-access investigation

The retained-input audit above is preserved as its original scope. The later [browser/export follow-up](SOURCE_FOLLOWUP.md) obtained six small date-filtered exports through existing access: access is technically established, but sampled historical defensive values match full-season PA proration within 6×10⁻⁸ runs. These exports cannot supply strictly prior-game WAR unchanged. The official preseason archive is accessible, while exact original vintage remains unresolved. No fits or protocol changes occurred; P05 stays data-blocked.
