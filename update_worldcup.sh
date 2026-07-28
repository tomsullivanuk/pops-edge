#!/bin/bash

set -eE

STAMP=$(date +"%Y-%m-%d_%H%M")

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
    notify "World Cup update failed" "A board refresh step failed. Check Terminal for details."
    exit "$exit_code"
}

trap notify_failure ERR

SILVER_CURRENT_FILE=$(python3 -c 'from config import SILVER_CURRENT_FILE; print(SILVER_CURRENT_FILE)')
SILVER_FUTURES_CURRENT_FILE=$(python3 -c 'from config import SILVER_FUTURES_CURRENT_FILE; print(SILVER_FUTURES_CURRENT_FILE)')
KALSHI_CURRENT_FILE=$(python3 -c 'from config import KALSHI_CURRENT_FILE; print(KALSHI_CURRENT_FILE)')
VALUE_BOARD_FILE=$(python3 -c 'from config import VALUE_BOARD_FILE; print(VALUE_BOARD_FILE)')
FUTURES_VALUE_BOARD_FILE=$(python3 -c 'from config import FUTURES_VALUE_BOARD_FILE; print(FUTURES_VALUE_BOARD_FILE)')
LADDER_BOARD_FILE=$(python3 -c 'from config import LADDER_BOARD_FILE; print(LADDER_BOARD_FILE)')
WEB_VALUE_BOARD_FILE=$(python3 -c 'from config import WEB_VALUE_BOARD_FILE; print(WEB_VALUE_BOARD_FILE)')
WEB_FUTURES_VALUE_BOARD_FILE=$(python3 -c 'from config import WEB_FUTURES_VALUE_BOARD_FILE; print(WEB_FUTURES_VALUE_BOARD_FILE)')
WEB_LADDER_BOARD_FILE=$(python3 -c 'from config import WEB_LADDER_BOARD_FILE; print(WEB_LADDER_BOARD_FILE)')
BET_LOG_FILE=$(python3 -c 'from config import BET_LOG_FILE; print(BET_LOG_FILE)')
SILVER_RUN_ARCHIVE_DIR=$(python3 -c 'from config import SILVER_RUN_ARCHIVE_DIR; print(SILVER_RUN_ARCHIVE_DIR)')
KALSHI_RUN_ARCHIVE_DIR=$(python3 -c 'from config import KALSHI_RUN_ARCHIVE_DIR; print(KALSHI_RUN_ARCHIVE_DIR)')
VALUE_BOARDS_RUN_ARCHIVE_DIR=$(python3 -c 'from config import VALUE_BOARDS_RUN_ARCHIVE_DIR; print(VALUE_BOARDS_RUN_ARCHIVE_DIR)')

mkdir -p "$SILVER_RUN_ARCHIVE_DIR"
mkdir -p "$KALSHI_RUN_ARCHIVE_DIR"
mkdir -p "$VALUE_BOARDS_RUN_ARCHIVE_DIR"

echo "Processing Silver forecasts..."
python3 process_silver.py
cp "$SILVER_CURRENT_FILE" "$SILVER_RUN_ARCHIVE_DIR/Silver_Current_$STAMP.xlsx"

echo
echo "Pulling Kalshi odds..."
python3 kalshi_pull.py
cp "$KALSHI_CURRENT_FILE" "$KALSHI_RUN_ARCHIVE_DIR/Kalshi_Current_$STAMP.xlsx"

echo
echo "Processing Silver futures forecasts..."
python3 process_silver_futures.py
cp "$SILVER_FUTURES_CURRENT_FILE" "$SILVER_RUN_ARCHIVE_DIR/Silver_Futures_Current_$STAMP.xlsx"

echo
echo "Building value board..."
python3 build_value_board.py
cp "$VALUE_BOARD_FILE" "$VALUE_BOARDS_RUN_ARCHIVE_DIR/WorldCup_ValueBoard_$STAMP.xlsx"

echo
echo "Building futures value board..."
python3 build_futures_value_board.py
cp "$FUTURES_VALUE_BOARD_FILE" "$VALUE_BOARDS_RUN_ARCHIVE_DIR/WorldCup_Futures_ValueBoard_$STAMP.xlsx"

echo
echo "Building ladder board..."
python3 build_ladder_board.py
cp "$LADDER_BOARD_FILE" "$VALUE_BOARDS_RUN_ARCHIVE_DIR/WorldCup_Ladder_Board_$STAMP.xlsx"

echo
echo "Done."
echo "Created $VALUE_BOARD_FILE"
echo "Created $FUTURES_VALUE_BOARD_FILE"
echo "Created $LADDER_BOARD_FILE"
echo "Archived copies using timestamp: $STAMP"

echo
echo "Building web bet sheet..."
python3 build_web_betsheet.py

echo
echo "Building web futures bet sheet..."
python3 build_web_futures_betsheet.py

echo
echo "Building web ladder board..."
python3 build_web_ladder_board.py

echo
echo "Copying reports to iCloud Drive..."

ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/WorldCup"

mkdir -p "$ICLOUD_DIR"

cp "$WEB_VALUE_BOARD_FILE" "$ICLOUD_DIR/"
cp "$VALUE_BOARD_FILE" "$ICLOUD_DIR/"
cp "$WEB_FUTURES_VALUE_BOARD_FILE" "$ICLOUD_DIR/"
cp "$FUTURES_VALUE_BOARD_FILE" "$ICLOUD_DIR/"
cp "$WEB_LADDER_BOARD_FILE" "$ICLOUD_DIR/"
cp "$LADDER_BOARD_FILE" "$ICLOUD_DIR/"
cp "$BET_LOG_FILE" "$ICLOUD_DIR/" 2>/dev/null || true

echo "Copied reports to iCloud Drive."

if [ "${KALSHI_SKIP_OPEN:-0}" != "1" ]; then
    echo
    echo "Opening web value boards..."
    open "$ICLOUD_DIR/$WEB_VALUE_BOARD_FILE" "$ICLOUD_DIR/$WEB_FUTURES_VALUE_BOARD_FILE" "$ICLOUD_DIR/$WEB_LADDER_BOARD_FILE"
fi

echo
echo "Done."
