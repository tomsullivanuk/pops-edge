# NFL comparison board

The primary workflow is [Import & Refresh](NFL_REFRESH_GUIDE.md): select the
ELWAY workbook and Kalshi activity export, then refresh all workbook weeks.
The Bet Sheet tab shows the resulting season view. The manual CLI below remains
supported with its original storage defaults.

## Reading the Bet Sheet

Each game has one row per team outcome. A team YES contract and its opponent's
NO contract have the same normal full-game payout. The table selects the lower
usable observed offer, then lower total estimated cost, then contract ID/side
as deterministic tie breakers. Both alternatives remain in Details.

- **ELWAY Contract:** central expected payout per contract, including $0.50 on a
  tie. It uses both teams' win probabilities: (1 + team win − opponent win) / 2.
- **Kalshi price:** the selected observed offer, requiring at least one contract
  at that level. Availability is in Details, not historical volume.
- **Difference after fee:** central expected payout minus offer and the estimated
  fee for one contract. Default sort is descending signed difference. Internal
  conservative game scores remain in comparison data; they are not the table's
  default sort. Click headings to change sorting.
- **Recorded wager (incl. fees):** each recorded trade's actual contract and
  quantity × purchase price + recorded fee, on separate lines. No matched activity
  leaves a blank cell; that does not establish that the account has no position.
- **Payout:** supported settlement gross payout when available, otherwise ELWAY
  expected gross return for the recorded purchase illustration, with gross return
  if the outcome wins below it. Unavailable/ambiguous calculations remain blank
  or marked for review as appropriate. Payout includes returned stake, not profit.

Dollars display to two decimals; source values and sorting retain precision.
Visible times are rounded to the nearest minute in Central time. Details retain
win probabilities, rounding ranges, before-fee differences, both contract routes,
whole-number comma-formatted availability, source times and activity diagnostics.
Rounding ranges are not confidence intervals. No exact tie probability or model
accuracy claim is inferred from rounded ELWAY percentages.

Week, team, omit-completed and difference-after-fee filters combine. Thresholds
are All or strictly greater than $0.00, $0.05, $0.075 or $0.10, using unrounded
values. Counts below the filters describe visible games/outcomes. Filtering does
not retrieve prices. TBD games remain in their official week; completed and
other exceptional states stay visible. Routine captured-price labels are omitted.

## Freshness and interpretation

Comparison guards require pregame scheduled status, quotes/catalog no older than
five minutes, schedule no older than 24 hours and ELWAY no older than eight days
at build time. The season view additionally reevaluates saved quote age/kickoff
when loaded. Missing or excluded offers have no active numeric difference.
An already-open season page does not reevaluate time until reloaded; use Refresh
Bet Sheet for new prices. Standalone weekly HTML retains its age-warning banner.
See [known limitations](NFL_REFRESH_GUIDE.md#known-limitations-and-recovery).

Fees illustrate a standard taker contract with multiplier 1, centicent fee
rounding and cent-aligned acquisition cost. Maker arrangements, multi-fill
rebates, third-party fees and fractional sizing are excluded. The board does not
pool depth, suggest a stake or execute orders. Model/market disagreement does not
establish a demonstrated Market Edge. Postponement fair-price payout is not modeled.

## Manual weekly CLI alternative

1. Prepare a verified screenshot using the [manual import guide](NFL_IMPORT_GUIDE.md).
2. Capture the official schedule and a matching bounded date window:

```bash
python nfl_schedule.py --season 2026 --week 1
python retrieve_kalshi_nfl.py capture --start-date 2026-09-09 --end-date 2026-09-14
```

3. Build immediately using the exact paths returned:

```bash
python nfl_comparison_board.py build \
  --verified /absolute/path/to/verified/VERIFICATION_ID.json \
  --forecast-store /absolute/path/to/NFL \
  --schedule /absolute/path/to/schedule-RUN_ID \
  --kalshi /absolute/path/to/run-RUN_ID
```

The forecast store contains the importer's sources and verified records.
Standalone schedule, market and board stores default under `~/PopsEdgeData/NFL`;
`--store` selects an alternative. Keep source data outside Git. Open the printed
board.html. Weekly CLI HTML has its own search/positive controls; the season
app has the filters described above.

To attach a newer activity export without refreshing saved prices:

```bash
python nfl_comparison_board.py activity \
  --board /absolute/path/to/existing-board \
  --activity /absolute/path/to/Kalshi-Recent-Activity-All.csv
```

The build command also accepts `--activity`. Each activity import creates a new
bundle using only that export, preserving original comparison times. No exports
are accumulated. See [activity semantics](NFL_ACTIVITY_SLICE.md).

## Integrity and recovery

A new immutable directory stores exact inputs, comparison.json, board.html and
a digest manifest. These are derived comparisons, not new observations or
human verification. No command backdates a comparison. Replay offline with:

```bash
python nfl_comparison_board.py replay /absolute/path/to/board-RUN_ID
```

Replay verifies inputs and reconstructs the saved derivation. It does not make
old quotes current. Retain incomplete or failed bundles, correct inputs and run
again; never edit historical snapshots. Local backups remain the owner's task.
See the [comparison boundary](NFL_BOARD_SLICE.md).

The season view shows the week beside Date / time. Match shows status or a
validated official final score, for example “Final (OT): NO 30–DET 31”. Scores
are repeated on both team-outcome rows. Neutral-site labels stay with Match.
Details identifies the official NFL source and when it was observed. These are
saved results, not a live scoreboard. “Result needs review” means the latest
saved evidence could not establish a supported result; it is never hidden by
Omit completed games. Account settlement information remains separate from the
sporting result and final scores do not establish cash-out proceeds or profit.

Completed games have grey Contract badges; other games retain green badges,
including games in progress. Badge colour represents completion, not quote
freshness. The repetitive Historical comparison and Historical ELWAY labels
are omitted beneath their values. Capture dates remain visible without the word Captured; the repeated Historical
difference label is omitted. Full historical provenance stays in Details.

The result icon precedes the grey Contract badge: ✓ matched the final result,
× did not match, and — denotes a tie. It evaluates the displayed YES/NO
contract against validated final scores, not account payout or profit. Unfinished
or unresolved games and absent contracts have no result icon. Tooltips and the
legend explain this distinction. Contract and icon stay together on one line;
Contract sorting continues to use its label. Contract is 150px minimum; price
180px, ELWAY 112px, difference 140px, payout 100px, with table overflow available.
