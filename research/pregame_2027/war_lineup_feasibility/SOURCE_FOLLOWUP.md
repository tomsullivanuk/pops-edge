# WAR source follow-up: exports accessible; sampled historical defense leaks

October 18, 2026. Source feasibility only. **Do not use the sampled custom-date WAR exports as strictly prior-game WAR.** Normal browser exports work in Tom's existing Safari session without new payment or credentials, but their dated defensive components match full-season values prorated by PA. This is a concrete chronology defect for the approved six-arm experiment, not evidence against the predictive usefulness of WAR. No fits, bulk acquisition, protocol changes or production changes occurred.

## Bounded browser evidence

Used a task-owned Safari tab and FanGraphs' normal visible Export Data control. Selected the first three players in the April 30 WAR leaderboard before examining cross-cutoff behavior. Exported Dashboard and Value views for those same three IDs at three inclusive cutoffs: March 20–April 30, March 20–May 31, and March 20–September 30, 2024. Six files, three rows each, 5,641 bytes total. Raw licensed rows and browser DOM receipts remain private; [sanitized receipt](source_sample_receipt.json) records hashes, schemas and aggregate checks. No access-control workaround or browser credential/storage inspection was used.

Dashboard exports contain `WAR`, `PA`, `G`, `Off`, `Def`, `BsR`, `PlayerId` and `MLBAMID` among their 25 fields. Value exports contain `Fielding`, `Positional`, `Defense`, `Batting`, `Base Running`, `League`, `Replacement`, `RAR`, `WAR` and IDs among 16 fields; they do not contain PA. Joined by exact PlayerId, each view has the same three IDs and matching WAR at every cutoff. Visible date controls and three-result footers were checked. The initial unfiltered April page reported 995 results, but this is not a verified full-population coverage count. Only 2024 and three non-catchers were sampled; 2022/2023/2025 daily coverage, catchers, missing/zero-PA behavior, doubleheaders, correction history and original publication times remain untested.

For each of three players and two early cutoffs, compare:

`early_component − full_season_component × early_PA / full_season_PA`

| Component | Maximum absolute discrepancy across six player/cutoff pairs (runs) |
| --- | ---: |
| Fielding | 4.44 × 10⁻⁸ |
| Positional | 1.28 × 10⁻⁸ |
| Defense | 5.72 × 10⁻⁸ |

All 18 comparisons agree to below 0.00000006 runs using unrounded CSV fields. This strongly supports current full-season PA proration for these sampled defensive fields. It independently corroborates the explicit caveat in FanGraphs' [May 31, 2019 custom-date documentation](https://blogs.fangraphs.com/instagraphs/leaderboards-update-introducing-custom-date-range/). It does not prove how every other WAR component is calculated or when every value originally became available.

**Consequence:** moving the date cutoff to yesterday does not remove the sampled future-season defensive information. The date-filtered total WAR cannot be admitted unchanged as the protocol's raw observed WAR. A disclosure calling it “retrospective” would not repair that future leakage. Daily defense cannot be recovered by rescaling these prorated fields alone; additional date-specific evidence is required.

## Availability, revisions and leakage are different

| Category | What is established | Suitability |
| --- | --- | --- |
| True historical as-of | No immutable historical daily position-player WAR+PA archive with publication timestamps was established in this bounded investigation. This is not a claim that none exists. | Seek a provider-supported archive/sample before approving inputs. |
| Revised retrospective prior-period estimate | FanGraphs' [April 5, 2024 WAR update](https://blogs.fangraphs.com/2024-fangraphs-war-update/) documents component changes retroactive to 2016. A genuinely cutoff-restricted reconstruction under a later methodology could be studied with explicit qualification, after its inputs/constants are audited. | Separate exploratory design and Owner decision required; cannot establish what the old model could actually have known. |
| Future-season information in early-date inputs | The current sampled defensive values reproduce completed-season values times early PA/full-season PA. | Exclude from fair pregame evaluation. Owner approval cannot make these values leakage-free. No relabelling or silent substitution. |

Revisions alone do not prove future-outcome leakage. Conversely, the sampled proration is more than ordinary retrospective score correction. A reconstruction would have to replace the contaminating components using genuinely date-specific data and resolve baserunning, catcher evaluation, park/league/replacement and runs-per-win constants; subtracting one field is not a validated solution.

## Preseason vintage: accessible archive, incomplete provenance

FanGraphs' [January 28, 2025 announcement](https://blogs.fangraphs.com/instagraphs/introducing-new-steamer-split-projections-and-more/) documents historical full-season Steamer projections back to 2012 and ZiPS back to 2010 as member features. In the same existing Safari session, [the 2024 Steamer archive](https://www.fangraphs.com/projections?type=steamer_2024&stats=bat&pos=all) displayed Historical Preseason Projections, a 2024 choice, and 3,711 results, matching the retained 2024 export's total row count. Its generic page title said 2026 Projections; that title must not override the archive selection. No second full projection export was made and matching row counts do not establish byte identity.

This strengthens the interpretation of an official historical preseason route. It does **not** establish the exact freeze date, original release bytes, later corrections, WAR definition/version, or the provenance of each retained 2022–2025 file. The displayed October 17, 2026 site update footer is not an original preseason publication timestamp. Original-release/vintage evidence remains an admission question rather than an invented timestamp.

## Other documented routes and cost

- **Existing FanGraphs access:** the six small exports succeeded; additional spending in this investigation was $0. Broad daily access, service limits and full-cohort coverage were not tested. A bespoke archive's availability/price is unknown. Do not buy another membership on this evidence.
- **Steamer's own historical preseason downloads:** its [official access page](https://steamerprojections.com/index.php/about/memberships) offers free historical preseason downloads with free signup. The [preseason listing](https://steamerprojections.com/index.php/projections/pre-season-projections) visibly lists years including 2018–2024. No new account was created, no file schema/vintage was verified, and this route supplies forecasts, not observed WAR. Its historical weekly logs are also projections, not a substitute for observed cumulative performance. Business API licensing is separately advertised without a public price.
- **MLB Baseball Savant:** the [official fielding-run-value leaderboard](https://baseballsavant.mlb.com/leaderboard/fielding-run-value) provides a potential source of defensive components with season/month controls. This is a reconstruction lead only: no complete date-specific fWAR package, compatible catcher/baserunning inputs, matching vintage or tested daily coverage was established here. No alternative WAR definition is silently substituted.
- **Prospective capture:** FanGraphs' [June 9, 2026 Live Stats feature description](https://blogs.fangraphs.com/fangraphs-feature-focus-live-stats/) describes live/daily WAR and custom ranges. This may support an explicitly approved future snapshot process, but does not establish an immutable archive of what was published on past dates. No observer or schedule was started.

## Recommendation and smallest next action

Do not bulk-download the custom-date WAR exports or launch the approved six-arm fits. The immediate useful question for FanGraphs is whether they can supply **dated cumulative position-player WAR and PA (2022–2025), original publication/revision timestamps, component definitions, and cutoff-specific defense rather than full-season proration**, plus the freeze/revision convention of historical preseason Steamer files. Request one small dated sample before discussing a large delivery or price.

Tom's smallest action is to ask that question through his existing membership support channel, or explicitly authorize us to send a prepared inquiry; no message has been sent. Existing membership already suffices for the tested normal exports, so no new purchase or account is needed for this step. If no valid historical archive is available, return with a concrete, separately bounded reconstruction proposal for Tom's decision before acquisition or fitting. The approved protocol stays unchanged and P05 remains unexecuted/data-blocked. Completed experiment count stays 24; this follow-up is source evidence, not a model result.
