# Generate the NFL Bet Sheet

Open `~/PopsEdge/Open NFL Bet Sheet.command` and leave its Terminal running.
The local app is at http://127.0.0.1:8766/.

1. Save the complete ELWAY All weeks table in a single-sheet Excel workbook,
   including heading, game count, footnotes and Updated time. Put it in
   `~/PopsEdge/Downloads/NFL/` along with a recent Kalshi activity CSV.
2. Select the two inbox files and click **Refresh Bet Sheet**.
3. The program validates the files, archives copies, retrieves each workbook
   week's official schedule and available Kalshi prices, and builds comparisons.
   Progress identifies the week being processed. The resulting sheet shows every
   workbook game; absent markets/dates/prices remain visibly unavailable.
4. Use week, team, difference-after-fee thresholds and omit-completed filters
   to narrow the display. Filtering never controls the scope of generation or
   triggers retrieval. The summary counts follow the selected filters.

There is no Review import button, reviewer field, confirmation checkbox, external
file chooser or archive selector. Returning focus to the app reloads inbox file
lists while idle. Generating again reuses the selected workbook's archived bytes
and deterministic validation records internally, while capturing new prices.

## Validation and provenance

Machine-validation records use elway-excel-validation-v2 and explicitly attest no
human review. Check source identity, required fields, published time, row counts,
per-week team uniqueness, probability ranges/sums and full-season coverage. Keep
source percentages at ELWAY's one-decimal precision even if Excel displays two.
Starred conditional rows and inconsistent data stop generation with a specific
error. Copying can lose gray-only conditional shading or preserve a plausible
wrong value; these remain source-copy limitations. No manual certification of
all clean values is required. Original screenshot/manual Excel records remain
replayable; no existing evidence is relabeled as machine- or human-reviewed.

## Storage, captures and failures

Inbox originals are unchanged; private data is archived under
`~/PopsEdge/Data/NFL/`. Existing legacy `~/PopsEdgeData/NFL` is not moved.
The collectors retain their weekly one-to-eight-day request bounds; the app
iterates all workbook weeks, capturing and building each immediately. This is
one owner action, not a single simultaneous season-wide quote timestamp. Per-game
source times are shown in Details; stale or started games have no active price
difference. Completed requires explicit final schedule status or supported
settlement, not merely elapsed kickoff. Unknown status remains visible.

Failures are recorded per week in a partial attempt manifest, explicitly named
in the status message, and do not prevent later weeks being attempted. Successful
weeks are retained. Older captures for failed weeks keep original times and are
not represented as refreshed. Invalid files fail before provider retrieval.
Only one generation runs per local app instance; use one instance per data root.
No automatic retries, scheduled refresh, order placement or hosted service.

## Recorded wagers and settlements

Only the newest selected export is reparsed across known games; exports do not
accumulate. Order rows do not double-count trades. Supported YES/NO settlement
quantities/results must reconcile with the exported amount before showing actual
gross payout. Gross payout is not realized profit. Duplicate/unsupported results
require attention, and conflicting settlement average cost versus trade history
is flagged. Unsettled amounts remain recorded-purchase illustrations, not a
confirmed account portfolio. Missing current markets do not erase settled wagers.

## Local preview

The owner launcher currently points to the candidate worktree. Its Python must
have openpyxl and requests; POPS_EDGE_PYTHON can select an existing environment.
The launcher falls back to the existing project venv and installs no packages.
Stop with Control-C. Localhost requests use host/origin/token checks and fixed
actions; inbox selection accepts neither arbitrary paths nor file uploads.

## Folder tabs

Import & Refresh contains the two inbox selectors and Refresh Bet Sheet button.
Progress appears in a compact status area with an indeterminate activity indicator,
current operation and a status marker on the tab. Bet Sheet contains the full-season
table and filters. Switching tabs does not refresh data or reset the table. Successful
refreshes display the Bet Sheet automatically; partial/failed runs keep their
explanation visible on Import & Refresh. Both tabs support arrow-key navigation.


TBD-date amendment: confirmed official schedule rows with missing kickoff times
are informational, not failed refreshes. An entirely undated week records its
schedule reference in pending_dates and skips price capture without inventing a
date window. The refresh completes normally if no actual errors occur. Full-season
rendering uses replay-validated latest schedule-only captures to keep undated games
in their official week with Date/time TBD. They remain incomplete/unpriced and do
not pass positive filters. Mixed dated/TBD weeks retain their existing valid
comparisons, with individual undated games labeled TBD. The redundant import-tab
heading was removed. Prior snapshots/failed-attempt records are not rewritten.

Bet Sheet display refinement: the season view filters by week, team, completion,
and difference after fee (All, strictly greater than $0.00, $0.05, $0.075, or
$0.10). Thresholds use unrounded differences; the summary follows the filters.
Specific-game omission is no longer offered. Routine “Captured prices” labels
are omitted; other schedule/status labels remain. The combined recorded-wager
column lists each imported trade's contract and purchase amount including fees,
with separate lines for multiple trades and blank cells for no matched activity.
Ambiguous trade amounts remain flagged; settlement-only activity does not invent
a purchase amount. Recorded trades do not establish current holdings.
