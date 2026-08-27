#!/bin/sh
set -eu
: "${POPS_EDGE_PR17B2_CONFIG:?set POPS_EDGE_PR17B2_CONFIG}"
exec python3 operate_forecast_standalone_research.py --config "$POPS_EDGE_PR17B2_CONFIG" capture-prospective
