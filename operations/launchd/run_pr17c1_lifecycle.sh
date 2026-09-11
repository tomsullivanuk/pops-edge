#!/bin/sh
set -eu
exec "${POPS_EDGE_PYTHON:?}" "${POPS_EDGE_PINNED_ROOT:?}/operate_forecast_standalone_activation.py" \
  --expected-revision "${POPS_EDGE_ACCEPTED_REVISION:?}" --config "${POPS_EDGE_PR17C1_CONFIG:?}" lifecycle-cycle
