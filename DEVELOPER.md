# Developer Guide

## Workflows

`update_all.sh` is the combined update workflow. It changes into the project directory, activates `venv/` when needed, then runs the standalone workflows in order:

1. `./update_wagers.sh`
2. `./update_worldcup.sh`

Keep this script thin. The wager and World Cup scripts remain usable on their own, so shared behavior should stay in the underlying Python modules or the standalone scripts unless there is a specific reason to coordinate it in `update_all.sh`.

`wcup` is the main board refresh workflow. It should run the same sequence as `update_worldcup.sh`:

1. `process_silver.py` normalizes the latest Silver forecast CSV into `Silver_Current.xlsx`.
2. `kalshi_pull.py` pulls current Kalshi World Cup markets into `Kalshi_Current.xlsx`.
3. `process_silver_futures.py` normalizes the latest Silver futures CSV into `Silver_Futures_Current.xlsx`.
4. `build_value_board.py` combines Silver probabilities, Kalshi prices, active wager exposure, and portfolio summaries into `WorldCup_ValueBoard.xlsx`.
5. `build_futures_value_board.py` creates `WorldCup_Futures_ValueBoard.xlsx`.
6. `build_web_betsheet.py` creates `WorldCup_ValueBoard.html`.
7. `build_web_futures_betsheet.py` creates `WorldCup_Futures_ValueBoard.html`.

`update_worldcup.sh` refreshes both match and futures outputs. It archives both Silver workbooks and both Value Board workbooks, copies both Excel boards and both HTML Value Boards to the existing iCloud World Cup folder, and opens only the match HTML Value Board. `update_all.sh` invokes this workflow and includes futures candidate bets in its completion summary.

`build_futures_value_board.py` filters out `KXWCGAME-` match markets and classifies futures markets from the event ticker, market ticker, game, subtitle, and market title. `kalshi_pull.py` includes these World Cup event patterns:

```text
KXWCGAME-*              match winner markets
KXWCROUND-26RO16-*      Round of 16 qualifier markets
KXWCROUND-26QUAR-*      Quarterfinal qualifier markets
KXWCROUND-26SEMI-*      Semifinal qualifier markets
KXMENWORLDCUP-26-*      World Cup winner markets
```

The outright winner markets use two-letter ticker suffixes, such as `KXMENWORLDCUP-26-AR`, but include team names in `yes_sub_title`; the futures board matches them by normalized outcome name.

`update_wagers.sh` refreshes Bet Log outputs from the latest Kalshi activity export. It activates `venv/` when needed, runs `import_wagers.py`, builds `World_Cup_Bet_Log.html` with `build_web_betlog.py`, prints a short wager summary, and opens the web Bet Log. Closing Price is manually entered in `World_Cup_Bet_Log.xlsx`; `import_wagers.py` preserves it and automatically calculates CLV and CLV % when Closing Price is present.

After placing a wager, download Kalshi Activity -> All -> This Month, then run `./update_all.sh` to refresh wagers first and then refresh the World Cup board. You can still run `./update_wagers.sh` or `./update_worldcup.sh` independently for narrower updates.

## Pipeline Dependencies

The pipeline is file-based:

```text
data-*.csv -> process_silver.py -> Silver_Current.xlsx
Kalshi API -> kalshi_pull.py -> Kalshi_Current.xlsx
Silver_Current.xlsx + Kalshi_Current.xlsx + World_Cup_Bet_Log.xlsx -> build_value_board.py -> WorldCup_ValueBoard.xlsx
WorldCup_ValueBoard.xlsx -> build_web_betsheet.py -> WorldCup_ValueBoard.html
futures CSV -> process_silver_futures.py -> Silver_Futures_Current.xlsx
Silver_Futures_Current.xlsx + Kalshi_Current.xlsx -> build_futures_value_board.py -> WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.xlsx -> build_web_futures_betsheet.py -> WorldCup_Futures_ValueBoard.html
Kalshi-Recent-Activity-*.csv + WorldCup_ValueBoard.xlsx + prior World_Cup_Bet_Log.xlsx -> import_wagers.py -> World_Cup_Bet_Log.xlsx
World_Cup_Bet_Log.xlsx -> build_web_betlog.py -> World_Cup_Bet_Log.html
```

Shared filenames, sheet names, archive paths, and common column names live in `config.py`.

`import_wagers.py` normalizes Match Date values to `YYYY-MM-DD` after reading prior manual values and current Value Board values. The selection order remains prior manual value, current Value Board value, then ticker-derived fallback. It also carries forward manually entered Closing Price from the prior wager log, calculates CLV and CLV % for BUY YES and SELL YES positions, and leaves CLV fields blank when Closing Price is blank unless prior CLV values are available as a fallback.

## Value Board Workbook

`build_value_board.py` writes the existing Bet Sheet outputs unchanged, then adds a `Portfolio` worksheet with four stacked sections:

```text
Portfolio Summary
Open Positions
Exposure by Team
Exposure by Match Date
```

The Portfolio worksheet reads active wagers from `World_Cup_Bet_Log.xlsx`, using `Open` and `Partially Closed` statuses, and enriches them with match, outcome, team, Silver probability, and current bid/ask data from the merged Value Board. BUY YES current value uses the current Yes Bid; SELL YES current value uses `1 - Yes Ask`.

## Futures Value Board Workbook

`build_futures_value_board.py` writes the same core workbook tabs as the match board:

```text
Bet Sheet
Run Metadata
Candidates
Value Board
Silver Normalized
Kalshi Normalized
Definitions
```

The futures Bet Sheet columns are `Stage`, `Team`, `Action`, `Silver`, `Market Price`, `Edge`, `ROI`, `Half Kelly`, `Stake on $500`, `Bucket`, `Volume`, `event_ticker`, and `market_ticker`. It uses the same `BANKROLL = 500`, `MIN_EDGE = 0.05`, and A/B/C bucket thresholds as `build_value_board.py`.

Silver futures CSV detection requires the columns `Team`, `R16`, `Qtr`, `Semi`, `Final`, and one of `Champ 🏆`, `Champ`, or `Champion`. The processor archives the selected source CSV under `archive/silver_futures_raw/` and the processed workbook under `archive/silver_futures_processed/`.

## Expected File Locations

The project expects to live at:

```text
~/kalshi
```

Silver forecast downloads may be in either:

```text
~/Downloads/data-*.csv
~/kalshi/data-*.csv
```

`process_silver.py` requires the match columns `Date`, `Team`, `Win`, `GF`, `Opponent`, `Win.1`, `GF.1`, and `Draw`. It selects the newest CSV with that schema and only archives other match-schema CSVs, so futures exports remain available to the futures processor.

Silver futures downloads may be named `data-*.csv` or include `futures` in the filename, but must have the futures columns listed above. They may be in either `~/Downloads` or `~/kalshi`. `process_silver_futures.py` selects the newest CSV with the futures schema and skips newer match-schema files.

Kalshi activity exports may be in either:

```text
~/Downloads/Kalshi-Recent-Activity-*.csv
~/kalshi/Kalshi-Recent-Activity-*.csv
```

Generated files are local outputs and should not be committed:

```text
Silver_Current.xlsx
Kalshi_Current.xlsx
WorldCup_ValueBoard.xlsx
WorldCup_ValueBoard.html
Silver_Futures_Current.xlsx
WorldCup_Futures_ValueBoard.xlsx
WorldCup_Futures_ValueBoard.html
World_Cup_Bet_Log.xlsx
World_Cup_Bet_Log.html
archive/
```

## Tests

Run the full test suite with:

```bash
bash -n update_all.sh
bash -n update_wagers.sh
bash -n update_worldcup.sh
./venv/bin/python -m unittest discover -s tests
./venv/bin/python -m py_compile process_silver_futures.py build_futures_value_board.py build_web_futures_betsheet.py
```

Tests use temporary directories and sample fixtures under `tests/fixtures/` so they do not overwrite live workbooks. Silver processor tests include mixed match/futures downloads and verify that each processor selects the newest valid file for its own schema.

The Value Board pipeline test checks the Portfolio worksheet section layout, open-position enrichment, summary totals, and team/date exposure rollups while preserving the existing Bet Sheet assertions. Futures tests cover Silver futures processing, a champion edge example, an advancement edge example, and the generated sortable futures web Bet Sheet. Wager tests also cover Match Date normalization and the generated sortable web Bet Log.

## Git Workflow

Use small commits. Before committing, run tests and inspect staged files:

```bash
./venv/bin/python -m unittest discover -s tests
git status
git diff --stat
git diff --cached --stat
```

Commit source, docs, tests, and fixtures. Do not commit generated workbooks, HTML reports, archives, virtualenvs, downloaded activity files, lock files, or secrets.
