# Pops' Edge Architecture

## Current state

The v1.0.0 architecture is a file-based World Cup pipeline. Python modules
ingest forecasts and markets, normalize them into workbooks, calculate value
boards, import wager history, and render Excel/HTML outputs. Shell scripts
coordinate local execution, archives, iCloud copies, notifications, and report
opening.

This document describes the present system; it does not introduce a refactor.

## Component inventory

### Reusable or potentially reusable platform components

- `config.py`: filenames, archive paths, sheet names, and shared column names.
- `kalshi_pull.py`: paginated/retried market API acquisition, currently filtered
  to World Cup event families.
- Wager ingestion foundations in `import_wagers.py`: activity discovery,
  preservation of manual fields, status and P/L handling.
- Workbook/report utilities and patterns in the board and web builders.
- Quality checks, run metadata, archival patterns, and fixture-based tests.
- Shell orchestration patterns: virtual-environment activation, failure
  handling, summaries, and child-workflow coordination.

These are candidates, not declarations of already sport-neutral architecture.

### World Cup-specific components

- `process_silver.py` and `process_silver_futures.py`: Silver World Cup schemas,
  team/stage normalization, and archives.
- `build_value_board.py`: World Cup match matching and valuation report.
- `build_futures_value_board.py`: World Cup advancement/champion valuation,
  Champion Proxy logic, and sell ladders.
- `build_ladder_board.py`: active World Cup position ladder report.
- `build_web_betsheet.py`, `build_web_futures_betsheet.py`, and
  `build_web_ladder_board.py`: World Cup board views.
- World Cup event ticker families, filenames, sheet semantics, iCloud
  destination, wager enrichment, fixtures, and workflow commands.

`build_web_betlog.py`, `import_wagers.py`, and the update scripts mix reusable
patterns with World Cup-specific filenames and operating assumptions.

## Data flow

```text
Silver match CSV ──> process_silver.py ──────────────> Silver_Current.xlsx
Silver futures CSV -> process_silver_futures.py ────> Silver_Futures_Current.xlsx
Kalshi API ─────────> kalshi_pull.py ────────────────> Kalshi_Current.xlsx
Activity CSV ───────> import_wagers.py ──────────────> World_Cup_Bet_Log.xlsx

Normalized inputs + wager log
        ├──> match value board ──> Excel + HTML
        ├──> futures value board -> Excel + HTML
        └──> ladder board ───────> Excel + HTML
```

Detailed schemas and operating behavior are documented in `DEVELOPER.md`.

## Boundaries and dependencies

- Local state is workbook/CSV based; generated artifacts are not canonical.
- `config.py` hard-codes `PROJECT_DIR` as `~/kalshi`.
- Manual inputs are discovered in the project directory or `~/Downloads`.
- Current market ingestion depends on the public Kalshi trade API.
- Forecast ingestion depends on manually downloaded Silver exports.
- macOS workflows depend on `open`, optional `osascript`, and a World Cup
  iCloud Drive directory.
- A local Python virtual environment and its third-party packages are assumed.
- External aliases, schedulers, IDE/Codex paths, GitHub integrations, and other
  clones may depend on the current repository name and location.

The complete rename dependency inventory is in
`docs/REPOSITORY_RENAME.md`.

## v1.1.0 direction

MLB will first be implemented behind explicit sport-specific contracts and
isolated artifacts. PR7 may extract platform interfaces demonstrated by both
sports. No current World Cup calculation or report is changed merely to make
the repository appear multi-sport.
