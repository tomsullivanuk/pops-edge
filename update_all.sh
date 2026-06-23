#!/bin/bash

set -eE

cd "$(dirname "$0")"

if [ -z "$VIRTUAL_ENV" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
else
    PYTHON_BIN=python3
fi

WEB_BETLOG_FILE=$("$PYTHON_BIN" -c 'from config import WEB_BETLOG_FILE; print(WEB_BETLOG_FILE)')
WEB_VALUE_BOARD_FILE=$("$PYTHON_BIN" -c 'from config import WEB_VALUE_BOARD_FILE; print(WEB_VALUE_BOARD_FILE)')
WEB_FUTURES_VALUE_BOARD_FILE=$("$PYTHON_BIN" -c 'from config import WEB_FUTURES_VALUE_BOARD_FILE; print(WEB_FUTURES_VALUE_BOARD_FILE)')

notify() {
    local title="$1"
    local message="$2"

    if command -v osascript >/dev/null 2>&1; then
        osascript - "$title" "$message" >/dev/null 2>&1 <<'APPLESCRIPT' || true
on run argv
    display notification (item 2 of argv) with title (item 1 of argv)
end run
APPLESCRIPT
    fi
}

notify_failure() {
    local exit_code=$?
    notify "Kalshi update failed" "A step failed. Check Terminal for details."
    exit "$exit_code"
}

success_summary() {
    "$PYTHON_BIN" - <<'PY'
import pandas as pd

from config import (
    BET_LOG_FILE,
    FUTURES_VALUE_BOARD_FILE,
    SHEET_RUN_METADATA,
    SHEET_SUMMARY,
    VALUE_BOARD_FILE,
)

def read_wagers_imported():
    wager_summary = pd.read_excel(BET_LOG_FILE, sheet_name=SHEET_SUMMARY)
    wager_values = dict(zip(wager_summary["Metric"], wager_summary["Value"]))
    return int(wager_values.get("Total Wagers", 0))

def read_candidate_bets(path):
    workbook = pd.ExcelFile(path)
    sheet_names = [SHEET_RUN_METADATA, "Metadata"]

    for sheet_name in dict.fromkeys(sheet_names):
        if sheet_name in workbook.sheet_names:
            metadata = pd.read_excel(workbook, sheet_name=sheet_name)
            metadata_values = dict(zip(metadata["Field"], metadata["Value"]))
            return int(metadata_values.get("Candidate Bets", 0))

    raise ValueError(
        "Value Board workbook has no supported metadata worksheet. "
        f"Tried: {', '.join(sheet_names)}"
    )

try:
    wagers_imported = read_wagers_imported()
except Exception:
    wagers_imported = "unavailable"

try:
    candidate_bets = read_candidate_bets(VALUE_BOARD_FILE)
except Exception:
    candidate_bets = "unavailable"

try:
    futures_candidate_bets = read_candidate_bets(FUTURES_VALUE_BOARD_FILE)
except Exception:
    futures_candidate_bets = "unavailable"

print(f"Wagers imported: {wagers_imported}")
print(f"Match candidate bets: {candidate_bets}")
print(f"Futures candidate bets: {futures_candidate_bets}")
PY
}

trap notify_failure ERR

echo "Refreshing wager log..."
KALSHI_SKIP_OPEN=1 ./update_wagers.sh

echo
echo "Refreshing World Cup value boards..."
KALSHI_SKIP_OPEN=1 ./update_worldcup.sh

echo
echo "All updates complete."

echo
echo "Opening Bet Log and value boards..."
open "$WEB_BETLOG_FILE" "$WEB_VALUE_BOARD_FILE" "$WEB_FUTURES_VALUE_BOARD_FILE"

SUMMARY=$(success_summary || printf 'Wagers imported: unavailable\nMatch candidate bets: unavailable\nFutures candidate bets: unavailable')
notify "Kalshi update complete" "$SUMMARY"
