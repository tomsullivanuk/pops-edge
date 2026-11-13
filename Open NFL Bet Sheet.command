#!/bin/bash
cd "$(dirname "$0")" || exit 1
nfl_python="${POPS_EDGE_PYTHON:-python3}"
if ! "$nfl_python" -c 'import openpyxl, requests' 2>/dev/null; then
  nfl_python="/Users/tom/pops-edge/venv/bin/python"
fi
if [ -n "${POPS_EDGE_NFL_INBOX:-}" ]; then
  "$nfl_python" nfl_refresh.py --inbox "$POPS_EDGE_NFL_INBOX" "$@"
else
  "$nfl_python" nfl_refresh.py "$@"
fi
