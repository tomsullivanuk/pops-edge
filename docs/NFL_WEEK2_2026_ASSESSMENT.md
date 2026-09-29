# NFL Week 2 clarification — September 28, 2026

The Product Owner authorized the four-part resolution in the ELWAY performance
assessment chat: preserve and annotate the original comparison, assess the
September 17 workbook separately, show a clearly labelled whole-week exclusion
sensitivity, and make the pre-kickoff baseline check visible. This authorizes
local implementation and analysis, not deployment or alteration of Evidence.

## Recorded facts

The September 17 workbook has SHA-256
`996203f540a9a59b29518def3f57a8e92333daaa541204a350338d9917defa35`.
Its preserved source receipt records arrival at 2026-09-17T14:38:34.736572Z.
Three refreshes failed timestamp validation that morning. The earliest is
`7e4dc32d67244c4d891082e8aa7915d7`; its error is
“Include heading, game count and published update time”.
The Owner identifies September 17 as the vendor publication date and the release
as its freshest forecast. This is an Owner attestation, distinct from the
pregame archive receipt and the file-creation metadata.

The frozen Week 2 baseline selected a September 9 publication imported September
14. Its forecast semantic identity is
`4d187fb9173dd8b2cf6d81e17f6eb055a66ad9f6fb50c02b7110b87daddf7da0`.
All 16 payout estimates differ from the September 17 workbook. No Kalshi capture
was found in the inspected NFL capture archive between the September 17 arrival
and the September 18 00:15Z weekly cutoff. This is scoped archive discovery,
not a claim about all possible external market archives.

## Must hold

- Original weekly reports, activation, event history, source bytes, selection,
  capture eligibility and scoring stay unchanged and replayable.
- The reader's incident note applies only to 2026 Week 2 with the identified
  older semantic forecast, not to arbitrary Week 2 reports or other seasons.
- The original cumulative comparison remains primary. A separate sensitivity
  omits the entire affected Week 2 and discloses omitted/remaining scored counts.
  It is a retrospective sensitivity, not a newly prospective freshest-release
  study. Match rows and exact report downloads remain unchanged.
- The September 17 analysis is descriptive historical Derived Analysis over all
  16 forecast rows and replay-verified official outcomes. It has no Kalshi
  comparator. No September 14 prices, reconstructed quotes, synthetic chronology,
  prospective enrollment or Policy authority may be added.
- Before evaluating the historical results, fix the source digest, all-game
  population, home-equivalent payout formula, official outcome authority and
  source/report boundaries. Retain exact per-game calculations and input IDs.
- The refresh summary identifies the selected workbook and publication/proxy
  time, actual import time, weekly cutoff, eligible capture count and whether
  the requested workbook's semantic forecast is the selected baseline.
  A rejected refresh must not retain a previous success as the current check.
- A complete capture means all eligible games have usable comparison records,
  not merely non-null quote fields on excluded rows. This is a saved check,
  not proof of vendor freshness or live validity after the check timestamp.

## Accepted limitations and exclusions

Manual pre-kickoff checking and refresh remain required; no scheduler, automatic
retry, notification system, generic incident registry or recovery subsystem is
added. The supplementary assessment is delivered outside the evidence store.
Original missing-date validation and the September 18 amendment remain pinned.
The amendment cannot retrospectively validate the rejected Week 2 import.
Statistical superiority, profitability, calibration policy, model blending and
release/deployment actions are outside scope.

## Pre-kickoff procedure

After selecting the intended workbook and refreshing, read **Weekly baseline
check** in Import & Refresh. Confirm the workbook matches, the correct target
week/cutoff is shown, and all eligible games have usable prices. If a newer
workbook is rejected, resolve the reported input issue and refresh before the
cutoff. Missing-price retries remain explicit. After cutoff, preserve the gap;
do not backfill it. A Bet Sheet success does not independently establish a
successful baseline check.
