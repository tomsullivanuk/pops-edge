#!/bin/bash

STAMP=$(date +"%Y-%m-%d_%H%M")

SILVER_CURRENT_FILE=$(python3 -c 'from config import SILVER_CURRENT_FILE; print(SILVER_CURRENT_FILE)')
KALSHI_CURRENT_FILE=$(python3 -c 'from config import KALSHI_CURRENT_FILE; print(KALSHI_CURRENT_FILE)')
VALUE_BOARD_FILE=$(python3 -c 'from config import VALUE_BOARD_FILE; print(VALUE_BOARD_FILE)')
WEB_BETSHEET_FILE=$(python3 -c 'from config import WEB_BETSHEET_FILE; print(WEB_BETSHEET_FILE)')
BET_LOG_FILE=$(python3 -c 'from config import BET_LOG_FILE; print(BET_LOG_FILE)')
SILVER_RUN_ARCHIVE_DIR=$(python3 -c 'from config import SILVER_RUN_ARCHIVE_DIR; print(SILVER_RUN_ARCHIVE_DIR)')
KALSHI_RUN_ARCHIVE_DIR=$(python3 -c 'from config import KALSHI_RUN_ARCHIVE_DIR; print(KALSHI_RUN_ARCHIVE_DIR)')
VALUE_BOARDS_RUN_ARCHIVE_DIR=$(python3 -c 'from config import VALUE_BOARDS_RUN_ARCHIVE_DIR; print(VALUE_BOARDS_RUN_ARCHIVE_DIR)')

mkdir -p "$SILVER_RUN_ARCHIVE_DIR"
mkdir -p "$KALSHI_RUN_ARCHIVE_DIR"
mkdir -p "$VALUE_BOARDS_RUN_ARCHIVE_DIR"

echo "Processing Silver forecasts..."
python3 process_silver.py || exit 1
cp "$SILVER_CURRENT_FILE" "$SILVER_RUN_ARCHIVE_DIR/Silver_Current_$STAMP.xlsx"

echo
echo "Pulling Kalshi odds..."
python3 kalshi_pull.py || exit 1
cp "$KALSHI_CURRENT_FILE" "$KALSHI_RUN_ARCHIVE_DIR/Kalshi_Current_$STAMP.xlsx"

echo
echo "Building value board..."
python3 build_value_board.py || exit 1
cp "$VALUE_BOARD_FILE" "$VALUE_BOARDS_RUN_ARCHIVE_DIR/WorldCup_ValueBoard_$STAMP.xlsx"

echo
echo "Done."
echo "Created $VALUE_BOARD_FILE"
echo "Archived copies using timestamp: $STAMP"

open "$VALUE_BOARD_FILE"
echo
echo "Building web bet sheet..."
python3 build_web_betsheet.py || exit 1

echo
echo "Copying reports to iCloud Drive..."

ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/WorldCup"

mkdir -p "$ICLOUD_DIR"

cp "$WEB_BETSHEET_FILE" "$ICLOUD_DIR/"
cp "$VALUE_BOARD_FILE" "$ICLOUD_DIR/"
cp "$BET_LOG_FILE" "$ICLOUD_DIR/" 2>/dev/null || true

echo "Copied reports to iCloud Drive."

echo
echo "Opening web bet sheet..."
open "$ICLOUD_DIR/$WEB_BETSHEET_FILE"

echo
echo "Done."
