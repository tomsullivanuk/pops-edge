#!/bin/bash

set -e

cd "$(dirname "$0")"

if [ -z "$VIRTUAL_ENV" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
else
    PYTHON_BIN=python3
fi

BET_LOG_FILE=$("$PYTHON_BIN" -c 'from config import BET_LOG_FILE; print(BET_LOG_FILE)')
WEB_BETLOG_FILE=$("$PYTHON_BIN" -c 'from config import WEB_BETLOG_FILE; print(WEB_BETLOG_FILE)')

echo "Refreshing wager log..."
"$PYTHON_BIN" import_wagers.py

echo
echo "Building web wager log..."
"$PYTHON_BIN" build_web_betlog.py

echo
"$PYTHON_BIN" - <<'PY'
import pandas as pd

from config import BET_LOG_FILE, SHEET_SUMMARY

summary = pd.read_excel(BET_LOG_FILE, sheet_name=SHEET_SUMMARY)
values = dict(zip(summary["Metric"], summary["Value"]))

open_positions = int(values.get("Open", 0))
closed_early_positions = int(values.get("Closed Early", 0))
settled_positions = int(values.get("Settled", 0))
completed_positions = closed_early_positions + settled_positions

print("Open positions:")
print(open_positions)
print()
print("Closed early positions:")
print(closed_early_positions)
print()
print("Settled positions:")
print(settled_positions)
print()
print("Completed positions:")
print(completed_positions)
print()
print("Most recent activity file:")
print(values.get("Kalshi Activity File", ""))
PY

if [ "${KALSHI_SKIP_OPEN:-0}" != "1" ]; then
    echo
    echo "Opening $WEB_BETLOG_FILE..."
    open "$WEB_BETLOG_FILE"
fi

echo
echo "Done."
