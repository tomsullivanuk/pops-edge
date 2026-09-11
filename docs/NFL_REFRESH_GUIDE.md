# Pops' Edge - NFL v1.1.0

The NFL workflow is merged through PR #33. The root VERSION file supplies the
app's version badge. A source-version label does not publish a GitHub release
or move a local deployment to a new checkout.

## Start and refresh

Open `~/PopsEdge/Open NFL Bet Sheet.command` and leave its Terminal running.
The local app is at http://127.0.0.1:8766/. The owner's launcher currently points
to the configured NFL checkout; it is not automatically repointed by a merge.
Python needs openpyxl and requests. POPS_EDGE_PYTHON can select an existing
interpreter; the launcher has a fallback to the owner's project environment.
It installs no packages. Control-C stops the app.

1. Manually copy the complete ELWAY All weeks table into a single-sheet Excel
   workbook, retaining heading, game count, footnotes and Updated timestamp.
2. Place that workbook and a recent Kalshi activity CSV in
   `~/PopsEdge/Downloads/NFL/`.
3. In **Import & Refresh**, select both inbox files and click **Refresh Bet Sheet**.
   Reuse the same workbook if only prices need updating. There is no manual
   Review import step, row checkbox, reviewer field or external file chooser.
4. The app automatically validates inputs, archives exact copies, captures each
   workbook week's official schedule and public Kalshi prices, and builds the
   comparisons. Progress identifies the operation/week. An entirely undated week
   is recorded as date/time TBD and skips price acquisition without inventing a
   date window. Its games remain visible in that week.
5. A successful refresh opens the **Bet Sheet**. Week, team, completion and
   after-fee thresholds filter the display and summary counts; they do not limit
   refresh scope. Thresholds use unrounded values and strict greater-than tests.

Tabs do not reload the sheet or reset filters. Arrow keys navigate tabs. Returning
focus reloads the inbox list while idle. Partial/failed runs keep the explanation
on Import & Refresh while retaining successful weeks.

## Validation and provenance

New Excel records use elway-excel-validation-v2 and attest automated validation,
never human review. Validation checks identity, fields, publication timestamp,
row counts, unique teams per week, probability ranges/sums and full-season
coverage. ELWAY percentages retain one-decimal source precision even if Excel
formats them with two decimals. Conditional stars and inconsistent data produce
specific errors before provider retrieval.

Copying may lose gray-only conditional shading or preserve a plausible incorrect
value; these remain source-copy limitations. Prior screenshot and manual Excel
verification records remain replayable and are not relabeled. Reusing the same
workbook reuses its preserved bytes and deterministic validation records while
creating new market captures.

## Storage and partial results

Inbox originals remain unchanged. Private inputs and captures are archived under
`~/PopsEdge/Data/NFL/`. Legacy CLI `~/PopsEdgeData/NFL` defaults remain unchanged;
no data is moved. Keep both outside Git and include them in manual backups.

Collectors remain weekly bounded; the app processes all weeks in sequence.
This is not one simultaneous season-wide quote capture. Each game retains its
source times in Details. Real failures are recorded per week and do not prevent
later weeks from being attempted. Successful captures remain; old captures for
failed weeks retain their original times. TBD dates alone require no attention.

Only one refresh runs per app instance; use one instance per data root. Local
requests use Host/Origin/token checks and fixed actions. Inbox selection accepts
neither arbitrary paths nor uploads. There is no scheduler, automatic retry,
account/order action or hosted service.

## Recorded wagers

The newest selected export alone is matched across known games. Exports do not
accumulate. Trades are not counted again as orders. Each matched trade displays
its contract and recorded cost including fees; multiple trades get separate lines.
No matching wager leaves a blank cell. This does not establish account holdings.

Supported settlement quantities/results must reconcile with the exported amount
before showing actual gross payout. Gross payout is not realized profit. Duplicate
or unsupported settlements are flagged; cost-basis discrepancies appear in
Details. The export does not establish buy/sell intent or a current portfolio.
Missing current markets do not erase supported settled activity. See the
[board guide](NFL_BOARD_GUIDE.md) and [activity boundary](NFL_ACTIVITY_SLICE.md).

## Known limitations and recovery

The [independent PR #33 review](NFL_PR33_INDEPENDENT_REVIEW.md) accepted two P2
follow-ups without blocking the local workflow:

- **Open-page freshness:** saved quote age and kickoff are reevaluated when the
  season view loads, not as time passes in an open tab. Reload to reevaluate saved
  prices; Refresh Bet Sheet obtains new captures. Filtering/tab switching alone
  does neither. Source times remain available in Details.
- **Rejected workbook after restart:** restoration scans archived workbooks, so
  one rejected workbook may prevent the sheet from opening automatically. Select
  a valid workbook and activity file and refresh to recover the in-session view.
  This may recur after another restart. Preserve rejected evidence; do not delete
  or edit archived files to work around it.

Completion requires explicit final schedule status or supported settlement,
not elapsed kickoff. Missing prices and unknown states remain visible. Invalid
inputs and failed captures never become authoritative observations or comparisons.

## Settlement-status correction (candidate)

New activity parsing uses nfl-activity-settlements-v3. A unique, exactly matched,
nonfuture YES/NO settlement event establishes game completion independently of
payout arithmetic. Unreconciled payout remains a diagnostic, not an active wager.
Closed activity with unresolved cash flow suppresses purchase-amount and expected
payout illustrations; original trade rows remain in Details. Opposite-side trades
alone do not establish a cash-out, and no realized profit is inferred. Legacy v1/v2
bundles retain their original parser for replay. This correction is not installed
in the pinned v1.1.0 release until separately integrated and deployed.
