#!/bin/bash

set -e

cd "$(dirname "$0")"

if [ -z "$VIRTUAL_ENV" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "Refreshing wager log..."
./update_wagers.sh

echo
echo "Refreshing World Cup board..."
./update_worldcup.sh

echo
echo "All updates complete."
