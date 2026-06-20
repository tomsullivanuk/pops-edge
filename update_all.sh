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

from config import BET_LOG_FILE, SHEET_SUMMARY, VALUE_BOARD_FILE

wager_summary = pd.read_excel(BET_LOG_FILE, sheet_name=SHEET_SUMMARY)
wager_values = dict(zip(wager_summary["Metric"], wager_summary["Value"]))
wagers_imported = int(wager_values.get("Total Wagers", 0))

metadata = pd.read_excel(VALUE_BOARD_FILE, sheet_name="Metadata")
metadata_values = dict(zip(metadata["Field"], metadata["Value"]))
candidate_bets = int(metadata_values.get("Candidate Bets", 0))

print(f"Wagers imported: {wagers_imported}")
print(f"Candidate bets: {candidate_bets}")
PY
}

trap notify_failure ERR

echo "Refreshing wager log..."
./update_wagers.sh

echo
echo "Refreshing World Cup board..."
./update_worldcup.sh

echo
echo "All updates complete."

SUMMARY=$(success_summary)
notify "Kalshi update complete" "$SUMMARY"
