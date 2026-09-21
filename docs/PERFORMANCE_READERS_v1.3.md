# v1.3 Performance readers — adopted Part 2

## NFL usability amendment — September 21, 2026

Owner-approved NFL Results filters mirror MLB: Last 7/14/60/90 Days,
This Season, inclusive Custom Period and Team. Season and optional Week remain;
the default is all saved weeks in the latest saved season. This Season means all
saved games within that selected scope, not a claim of complete season coverage.
Each week independently selects and replay-validates its latest saved report.
Conflicts/corruption remain visible and are not bypassed. Each summary and exact
download remains weekly; a cumulative NFL metric/chart is still deferred.

Filters affect match rows only, not scores, coverage counts or weekly populations.
This supersedes the earlier unfiltered summary/rows presentation requirement;
the distinction is explicit on screen. Presets end on the latest selected saved
analysis's Central date, not today's date. Custom dates include both endpoints,
reject blank/invalid/reversed/future-to-data dates, and default to the saved range
on first selection. Team and week filters remain explicit. Unknown kickoff games
remain visible under This Season, not arbitrarily assigned a date.

Kickoffs are a display-only projection of validated archived schedules within each
report's exact event prefix and analysis boundary, including the initial cohort
receipt. Later schedule observations do not change an older report's filter dates.
Conflicting team identity yields unknown date. No report identity, source evidence,
activation, scoring or provider behavior changes. Older weekly links remain valid.

September 15, 2026: the Owner adopted and authorized implementation of weekly NFL
results alongside the established MLB reader. This source candidate adds Bet Sheet /
Performance navigation and sport selection to the existing local application.
Implementation completion is separate from review, integration and deployment.

## User journeys

Performance → NFL → Season / Week → View week opens a saved weekly report. The
latest saved analysis boundary for the selected week governs, not file modification
time. Equal-boundary conflicts are visible; corrupt saved reports are not bypassed.
A report is replay-validated against its original source boundary before display or
download. Disposable replay work does not publish a new report or mutate the store.

The reader presents official population, paired scored count, coverage dispositions,
baseline status/cutoff and saved analysis time. Partial 2026 Week 1 distinguishes 16
official games from the fixed 14-game starting cohort. The game rows show home-team
equivalent values, official results, squared contract-value errors and Details.
Per-game evaluation labels (scored, outside starting cohort, unresolved result)
appear in Details only. The Match cell shows the matchup and validated final score
when available; weekly coverage counts and unavailable metric cells remain visible.
ELWAY and Kalshi means use the identical paired game set. NFL ties retain payout
0.5. These are descriptive errors, not binary Brier scores, profit or edge findings.

Performance → MLB opens the established saved Performance Report inside the local
application. Its Historical candle report, Details, exact downloads and independently
dated collection status are retained. The reader validates retained live package,
anchor and verification references without source acquisition or scientific replay.
Historical package validation occurs when its saved page/evidence is requested.
The saved display is not regenerated. Unavailable dependencies remain visible.

Neither reader updates anything on open, filtering or downloading. NFL Import &
Refresh and the existing MLB report-generation/status commands remain the separate
manual update workflows. No new update or recovery command is provided here.

## Local configuration and safety

`nfl_refresh.py --root ROOT` reads NFL reports from `ROOT/Data/NFL/performance`.
`--mlb-reports OUTPUT` selects the existing reporting output directory. The default
is `~/PopsEdgeReports/mlb/real/2026-09-13-accepted/reports`, matching the established
local saved entry. A missing directory produces an unavailable state, never creation.
Opening a reader does not initialize, activate, save, score new reports or acquire data.

Only supported delivery assets reachable from the saved MLB entry are served. There
is no directory listing, arbitrary file endpoint or collector access. Traversal and
symlink aliases within configured roots are rejected. Saved HTML runs without
scripts, under a restrictive response policy and iframe sandbox. Existing package
HTML/JSON bytes remain unchanged; downloads retain full precision.

## Acceptance boundaries

Must hold: truthful provenance and dates, unchanged sport-specific populations and
scoring, visible failures/gaps, matching NFL summary/rows, no write/provider side
effects, protected local file access, and usable existing Bet Sheet workflows.
Readable metrics have at most two decimal places. Central timestamps are display
conversions only; stored scientific dates and MLB's existing reader dates are retained.

Accepted limits: local/manual updates, early/empty samples, older saved outcomes until
an explicit update, different sport-specific metrics and separately pinned deployments.
The MLB frame retains its existing presentation and scrolling. NFL report-store
corruption can block the reader until manually investigated; it never silently falls
back to older results. Validation can require a short wait with larger saved stores.

Deferred by Owner: cumulative NFL chart and season aggregate, Administration/update
controls, automatic refresh, new inference or model admission, holdings/profit,
cloud/services, universal schemas, collector changes, study closure and release.

## Status reconciliation

Product's dated current-state clarification supersedes its older NFL “not yet
implemented” and MLB “documentation candidate” headings. NFL capture/measurement
already exists and its refresh integration supersedes the original implementation
note saying it was disconnected. This slice adds the reader only. Keep the pinned
NFL protocol and starting-cohort documents unchanged; their original design-status
phrasing does not undo subsequent activation.

Roadmap's old tentative v1.3/publication-pending v1.2 rows and older MLB delivery
publication/candidate prose are historical. v1.2.0 publication did not align runtime
pins or close studies. The full v1.3 release remains incomplete.

### Owner readability refinement

Above the NFL table, retain season/week controls, Results as of, scored/enrolled
count, three error metrics and a short lower-is-better caption. Move baseline,
cutoff, cohort/coverage detail and scoring/interpretation explanations into the
collapsed Report details and evidence. Selection and validation failures remain
visible. This changes presentation only, not report dates, selection or scores.

### Owner-adopted 50% reference preview

The summary compares ELWAY and Kalshi with a fixed 0.50 home-team contract value, on exactly the same paired scored games. Average reference squared error uses actual payouts: 0.25 for either win, 0.00 for a tie. Empty samples are unavailable. Improvement over reference is reference error minus source error. The direct Kalshi-minus-ELWAY comparison moves into Report details; the short lower-error caption is removed. This descriptive display projection was adopted September 15, 2026 after study commencement. It neither alters saved scientific reports nor grants new inference authority.

## Owner terminology decision — September 15, 2026

The NFL reader uses **Payout-adjusted Brier score** as a descriptive product label
for the existing squared contract-value error. The summary is its paired-sample
mean; game columns are ELWAY score and Kalshi score. Details define the squared
error against payout 1 for home win, 0 for away win and 0.5 for tie. This is not a
claim of standard binary/multiclass Brier scoring. Calculations, canonical field
names, protocol identifiers, saved reports and activation digests are unchanged.
The pinned weekly protocol remains the scientific authority; this display alias
does not rename its metric or require editing/re-pinning its historical contents.

The same paired games govern the 50% reference and both improvements over it.
Direct Kalshi-minus-ELWAY comparison stays in Details. No profit, statistical
superiority or wagering authority follows. Additional MLB redesign remains deferred.


## MLB Performance presentation — September 16, 2026

The Owner authorized the [NFL-style MLB reader](MLB_PERFORMANCE_READER_v1.3.md), including cumulative Kalshi/reference summary, complete retained opportunity rows, Period/Custom Period and Team display filters, Central dates, compact Details and bottom historical link. It supersedes the earlier iframe-presentation limitation and redesign deferral for this bounded slice. Scientific packages, scoring, populations and collector authority remain unchanged. Explicit manual match-display preparation is separate from browser reads. Implementation and independent review are authorized; integration/deployment/release are separate gates.
