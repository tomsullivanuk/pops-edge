# Developer Guide

## Workflows

`wcup` is the main board refresh workflow. It should run the same sequence as `update_worldcup.sh`:

1. `process_silver.py` normalizes the latest Silver forecast CSV into `Silver_Current.xlsx`.
2. `kalshi_pull.py` pulls current Kalshi World Cup markets into `Kalshi_Current.xlsx`.
3. `build_value_board.py` combines Silver probabilities, Kalshi prices, and active wager exposure into `WorldCup_ValueBoard.xlsx`.
4. `build_web_betsheet.py` creates `WorldCup_BetSheet.html`.

`update_wagers.sh` is intentionally separate from `wcup`. It activates `venv/` when needed, runs `import_wagers.py`, prints a short wager summary, and opens `World_Cup_Bet_Log.xlsx`.

After placing a wager, download Kalshi Activity -> All -> This Month, run `./update_wagers.sh`, then run `wcup` if the new wager should appear on the Value Board.

## Pipeline Dependencies

The pipeline is file-based:

```text
data-*.csv -> process_silver.py -> Silver_Current.xlsx
Kalshi API -> kalshi_pull.py -> Kalshi_Current.xlsx
Silver_Current.xlsx + Kalshi_Current.xlsx + World_Cup_Bet_Log.xlsx -> build_value_board.py -> WorldCup_ValueBoard.xlsx
WorldCup_ValueBoard.xlsx -> build_web_betsheet.py -> WorldCup_BetSheet.html
Kalshi-Recent-Activity-*.csv + WorldCup_ValueBoard.xlsx + prior World_Cup_Bet_Log.xlsx -> import_wagers.py -> World_Cup_Bet_Log.xlsx
```

Shared filenames, sheet names, archive paths, and common column names live in `config.py`.

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
WorldCup_BetSheet.html
World_Cup_Bet_Log.xlsx
archive/
```

## Tests

Run the full test suite with:

```bash
./venv/bin/python -m unittest discover -s tests
```

Tests use temporary directories and sample fixtures under `tests/fixtures/` so they do not overwrite live workbooks.

## Git Workflow

Use small commits. Before committing, run tests and inspect staged files:

```bash
./venv/bin/python -m unittest discover -s tests
git status
git diff --stat
git diff --cached --stat
```

Commit source, docs, tests, and fixtures. Do not commit generated workbooks, HTML reports, archives, virtualenvs, downloaded activity files, lock files, or secrets.

