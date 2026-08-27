#!/bin/sh
set -eu
: "${POPS_EDGE_PR17B2_CONFIG:?set POPS_EDGE_PR17B2_CONFIG}"
: "${POPS_EDGE_PR17B2_SCHEDULE_FIXTURE:?set POPS_EDGE_PR17B2_SCHEDULE_FIXTURE}"
: "${POPS_EDGE_PR17B2_CLASSIFICATION_FIXTURE:?set POPS_EDGE_PR17B2_CLASSIFICATION_FIXTURE}"
: "${POPS_EDGE_PR17B2_RETROSPECTIVE_FIXTURE:?set POPS_EDGE_PR17B2_RETROSPECTIVE_FIXTURE}"
: "${POPS_EDGE_PR17B2_OUTCOME_FIXTURE:?set POPS_EDGE_PR17B2_OUTCOME_FIXTURE}"
python3 operate_forecast_standalone_research.py --config "$POPS_EDGE_PR17B2_CONFIG" acquire-schedule --fixture "$POPS_EDGE_PR17B2_SCHEDULE_FIXTURE"
python3 operate_forecast_standalone_research.py --config "$POPS_EDGE_PR17B2_CONFIG" acquire-classification --fixture "$POPS_EDGE_PR17B2_CLASSIFICATION_FIXTURE"
python3 operate_forecast_standalone_research.py --config "$POPS_EDGE_PR17B2_CONFIG" acquire-retrospective --fixture "$POPS_EDGE_PR17B2_RETROSPECTIVE_FIXTURE"
exec python3 operate_forecast_standalone_research.py --config "$POPS_EDGE_PR17B2_CONFIG" reconcile-outcomes --fixture "$POPS_EDGE_PR17B2_OUTCOME_FIXTURE"
