# NFL game matching and comparison board

Use the project's Python environment from the checkout containing NFL-2B.
Each board uses three explicitly chosen inputs: a verified ELWAY image record,
a captured official NFL weekly schedule, and a captured Kalshi market run.

## Weekly workflow

1. Import and check the new ELWAY screenshot using the [import guide](NFL_IMPORT_GUIDE.md).
2. Capture the official weekly schedule:

```bash
python nfl_schedule.py --season 2026 --week 1
```

3. Refresh Kalshi prices following the [retrieval guide](NFL_RETRIEVAL_GUIDE.md):

```bash
python retrieve_kalshi_nfl.py capture --start-date 2026-09-09 --end-date 2026-09-14
```

4. Build immediately using the exact paths printed by those commands:

```bash
python nfl_comparison_board.py build \
  --verified /absolute/path/to/verified/VERIFICATION_ID.json \
  --forecast-store /absolute/path/to/NFL \
  --schedule /absolute/path/to/schedule-RUN_ID \
  --kalshi /absolute/path/to/run-RUN_ID
```

The forecast store is the directory containing `sources/` and `verified/` from
the image importer. Schedule, market and board stores default to subdirectories
of `~/PopsEdgeData/NFL`. Each collector and builder accepts `--store` for an
alternate directory. Keep inputs/output outside the repository.

Open the printed `board.html` file. Search by team abbreviation or show only
games that had comparisons when built. All official games remain available,
including those lacking a verified forecast or usable market. Expand a team's
details for the exact YES/NO routes, quantities, quote times and exclusion reasons.

## Reading the comparison

ELWAY's team win percentage is shown unchanged. Model payout includes the 50¢
tie payout and uses both teams' probabilities. The range reflects rounding to
the nearest displayed percentage unit; it is not a model confidence interval.
No exact tie probability is claimed from the rounded percentages.

For each team, its YES contract and its opponent's NO contract are separate
purchase routes to the same normal full-game payout. The board shows the lower
usable observed cost including an estimated fee for one contract; it does not
pool depth or suggest a stake. It requires at least one contract at the best
offer. Costs use the standard taker fee, multiplier 1, centicent trade-fee rounding
and cent-aligned acquisition cost. Multi-fill rebates, maker fees, fractional
orders, account arrangements and third-party fees are not modeled.

Games rank by their largest lower-bound model-payout-minus-cost difference.
Equal scores share rank. Positive differences reflect disagreement, not proof
that the model is accurate or a recommendation to place a wager. A postponed
match's fair-price settlement is not modeled.

The default display guards require quotes/catalog no older than five minutes,
schedule no older than 24 hours, and ELWAY source no older than eight days at
build time. Games that have reached kickoff or are not scheduled are unranked.
These guards are fixed in this version and recorded in the saved output; they
are not approved wagering policy. New model/quote/schedule inputs require a new
board. The page warns as saved prices age or previously comparable games start.
It has no background retrieval and never claims live quotes.

## Integrity and recovery

Each board creates a new directory, copies its source inputs, and saves
`comparison.json`, `board.html`, and a digest manifest. The output is derived
analysis, not a new forecast or source observation. It records actual build
time; there is no command to backdate an operational comparison.

```bash
python nfl_comparison_board.py replay /absolute/path/to/board-RUN_ID
```

Replay checks hashes, the forecast/image verification, schedule parsing and
market replay, and reproduces comparison data and HTML at the saved build time.
It is offline and does not make old quotes current. The board additionally checks
the Kalshi started receipt and recognizes complete supported secondary rules,
addressing the two NFL-2A limitations at the comparison boundary.

A missing terminal `complete.json` means the build was interrupted or failed.
Retain that directory for inspection and start a new build after correcting the
input selection. Do not edit historical snapshots. Website-layout/rule changes,
unknown team aliases or inconsistent data must be investigated rather than
silently guessed. Local storage and manual backups remain your responsibility.

See [acceptance boundary and sources](NFL_BOARD_SLICE.md). This guide does not
activate a research study, policy, scheduler or order workflow.

## Bet-sheet presentation amendment — September 9, 2026

The owner requested a refactor matching the World Cup Bet Sheet, focused on the
largest ELWAY–Kalshi discrepancies. Replace game cards with a compact sortable
table, one row per team outcome. Default order is descending signed difference
between central tie-adjusted ELWAY contract value and the lowest usable observed
offer, before fees. The separate After fee column shows central value minus
one-contract cost; Details retains rounding ranges and all quote routes.
Original ELWAY win percentages remain separate from contract values. A positive
raw difference is not automatically positive after fees.

The data bundle retains conservative after-fee game scores for traceability;
the table's before-fee order is a deterministic presentation derived from its
underlying routes. This supersedes earlier text describing the default visual
order by after-fee lower bound. All missing/stale/game-status guards remain.
Show both outcomes, a positive-difference filter, team search and sortable column
headings. Use available depth rather than historical volume. Positions, Kelly
and stake columns from the reference sheet remain outside this NFL slice.
Existing snapshots may be re-rendered as a new presentation without refreshing
or backdating their data. Preserve original source/build times and record the
new render time separately. Never overwrite the original snapshot.


Display clarification: monetary figures are dollars per contract, with up to four
decimal places to preserve model-value precision. “Model value / contract”
replaces “ELWAY value”; “Contracts available” means the quantity at the displayed
observed offer. Each team outcome displays the lower usable price among its YES
contract and its opponent’s NO contract, then lower total estimated cost and
contract ID/side break ties. Both routes remain in Details. The full game's four
contracts are therefore retained across the two outcome rows.


Latest display amendment: dollar amounts use two decimals; all visible times are
rounded to the nearest minute in Central time. Official game IDs are omitted
from the visual details. Contract availability appears only in Details, rounded
to whole contracts with thousands separators. Exact timestamps, quantities and
values remain in source data and continue to govern calculations and sorting.


## Identify wagers from a Kalshi activity export

Download the latest activity CSV from Kalshi manually. To add it to an existing
saved board without refreshing prices:

```bash
python nfl_comparison_board.py activity \
  --board /absolute/path/to/existing-board \
  --activity /absolute/path/to/Kalshi-Recent-Activity-All.csv
```

This creates a new board with a Recorded wager column, preserving the original
quote/forecast times and recording activity import time separately. The build
command also accepts `--activity /absolute/path/to/export.csv` when generating
a fresh board. Each import uses only the selected file; it does not accumulate
or double-count earlier exports.

A NO contract is associated with the opposing team's outcome, even if the main
sheet displays an equivalent YES route. Details show the actual held/traded
contract recorded in the file, reported quantity, recorded price, fee and trade time.
Order rows are not counted again as trades. Non-NFL rows are outside this view.

These are recorded wagers, not confirmed current open balances: this export
lacks an explicit buy/sell action. Opposite directions are not netted; a visible
settlement is noted without deleting the historical trade. Duplicate/invalid or
unmatched NFL records appear in activity diagnostics. “None in export” means
only that no matching trade is in this file. “Not loaded” means no file was
provided. Importing activity does not refresh the older price comparison.
See [activity boundary](NFL_ACTIVITY_SLICE.md).

### Wager totals and compact comparison columns

ELWAY Contract replaces the separate main-table probability/value columns.
Difference after fee replaces before-fee and after-fee columns and controls the
initial sort and positive filter. Details retain the original win probability and
gross difference. Wagered includes recorded fees; Expected payout is ELWAY's
expected gross return on the recorded quantity, with the win payout below it.
Each row totals one team's recorded outcome within that game. These illustrations
assume recorded purchases remain held; the export cannot verify current holdings.
Payout is not profit. Settlement or ambiguous duplicate records require review.


## Local NFL refresh app

The owner-authorized Excel import, selected-week review, public price refresh and
settlement display are described in [the refresh guide](NFL_REFRESH_GUIDE.md).
Run `python nfl_refresh.py` or open `Open NFL Bet Sheet.command`. This is a local
candidate; prior CLI imports remain supported.
