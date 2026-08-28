#!/bin/sh
set -eu
exec python3 operate_forecast_standalone_activation.py --config "${POPS_EDGE_PR17C1_CONFIG:?}" reconcile-outcomes
