#!/usr/bin/env python3
"""Deterministic, offline PR17B2 operational-contract inspector."""
from pathlib import Path

from forecast_standalone_operations import (
    COMMAND_CAPABILITIES, DeploymentConfig, NamespaceArchive, OperatingMode,
    RetryPolicy, canonical_bytes, inspect_archive,
)


def render() -> bytes:
    config=DeploymentConfig("synthetic-pr17b2","fixture",OperatingMode.DRY_RUN,
        Path("/synthetic/pr17b2/dry-run/fixture/primary"),Path("/synthetic/pr17b2/dry-run/fixture/secondary"),
        "https://fixture.invalid",RetryPolicy(3,5,30,(1,2),5),1,
        Path("/synthetic/pr17b2/logs"),schedule_parameters=(("prospective_interval_seconds","60"),))
    diagnostic=inspect_archive(NamespaceArchive(config))
    return canonical_bytes({"capability":"implemented-inactive","configuration_id":config.identity,
        "commands":COMMAND_CAPABILITIES,"diagnostic":diagnostic,
        "boundaries":["dry-run-cannot-be-promoted","no-live-provider-access","no-activation","no-scientific-conclusions"]})


if __name__=="__main__": print(render().decode("utf-8"))
