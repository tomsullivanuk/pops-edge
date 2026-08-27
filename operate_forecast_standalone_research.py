#!/usr/bin/env python3
"""Bounded PR17B2 Kalshi MLB operations CLI (inactive and fixture-safe)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from forecast_standalone_operations import (
    COMMAND_CAPABILITIES, DeploymentConfig, DiagnosticResult,
    Disposition, ExitCode, HTTPResponse, NamespaceArchive, OperatingMode,
    OperationsError, acquire_typed_supporting_fixture, discover_and_acquire_retrospective,
    discover_and_capture_prospective, inspect_archive, preflight,rebuild_index,status,sync_secondary,
)


class FixtureTransport:
    """One-response transport. It cannot contact a network."""
    def __init__(self, path: Path): self.path, self.calls = path, 0
    def request(self, method: str, url: str, *, params: Mapping[str,str], timeout: int, allow_redirects: bool) -> HTTPResponse:
        self.calls += 1
        raw=self.path.read_bytes()
        return HTTPResponse(200,raw,{})


def _parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,required=True)
    parser.add_argument("--json",action="store_true",dest="as_json")
    sub=parser.add_subparsers(dest="command",required=True)
    for command in COMMAND_CAPABILITIES:
        item=sub.add_parser(command,help=COMMAND_CAPABILITIES[command])
        if command in {"acquire-schedule","acquire-classification","acquire-retrospective","reconcile-outcomes"}:
            item.add_argument("--fixture",type=Path,required=True,help="offline provider fixture; live access is intentionally unavailable")
        if command=="preflight":
            item.add_argument("--mode",choices=[x.value for x in OperatingMode],required=True)
            item.add_argument("--protocol-id",action="append",default=[])
            item.add_argument("--credentials-configured",action="store_true")
    return parser


def _render(result: DiagnosticResult | Mapping[str,Any], as_json: bool) -> None:
    if isinstance(result,DiagnosticResult): print(result.to_json() if as_json else result.to_text())
    else: print(json.dumps(result,sort_keys=True,separators=(",",":")) if as_json else "\n".join(f"{key}: {value}" for key,value in sorted(result.items())))


def main(argv: list[str] | None = None) -> int:
    args=_parser().parse_args(argv)
    try: config=DeploymentConfig.from_json(args.config); archive=NamespaceArchive(config)
    except (OSError,ValueError,json.JSONDecodeError,OperationsError) as exc:
        print(str(exc),file=sys.stderr);return int(ExitCode.CONFIGURATION_ERROR)
    try:
        if args.command=="status": result=status(archive)
        elif args.command=="inspect": result=inspect_archive(archive)
        elif args.command=="preflight":
            result=preflight(archive,requested_mode=OperatingMode(args.mode),credentials_configured=args.credentials_configured,protocol_ids=args.protocol_id)
        elif args.command=="rebuild-index": result={"index_sha256":rebuild_index(archive),"state":"rebuilt"}
        elif args.command=="sync-secondary": result={**sync_secondary(archive),"state":"synchronized"}
        elif args.command=="capture-prospective":
            if config.fixture_response_path is None:raise OperationsError("configuration-error","fixture_response_path is required for inactive capture")
            outcome=discover_and_capture_prospective(archive=archive,transport_factory=lambda _opportunity,_series:FixtureTransport(config.fixture_response_path),clock=lambda:datetime.now(timezone.utc))
            result=json.loads(json.dumps({"configuration_id":outcome.configuration_id,"namespace":outcome.namespace,"trusted_now":outcome.trusted_now.isoformat(),"due_opportunity_ids":outcome.due_opportunity_ids,"provider_requests":outcome.provider_request_count,"attempt_ids":outcome.created_attempt_ids,"snapshot_ids":outcome.created_snapshot_ids,"disposition":outcome.disposition}))
        elif args.command=="acquire-retrospective":
            created=discover_and_acquire_retrospective(archive=archive,transport_factory=lambda _opportunity,_series:FixtureTransport(args.fixture),clock=lambda:datetime.now(timezone.utc),sleeper=time.sleep)
            result={"configuration_id":config.identity,"namespace":config.namespace,"created_manifest_ids":created,"disposition":"completed"}
        else:
            contracts=acquire_typed_supporting_fixture(archive=archive,command=args.command,transport=FixtureTransport(args.fixture),clock=lambda:datetime.now(timezone.utc),sleeper=time.sleep)
            result={"configuration_id":config.identity,"namespace":config.namespace,"contract_count":len(contracts),"disposition":"completed"}
        _render(result,args.as_json)
        if isinstance(result,DiagnosticResult) and not result.ready:return int(ExitCode.NOT_READY)
        if isinstance(result,dict) and result.get("conflicts",0):return int(ExitCode.INTEGRITY_FAILURE)
        return int(ExitCode.SUCCESS)
    except OperationsError as exc:
        print(str(exc),file=sys.stderr)
        return int(ExitCode.INTEGRITY_FAILURE if any(word in exc.code for word in ("integrity","corrupt","conflict","digest","identity")) else ExitCode.OPERATIONAL_FAILURE)


if __name__=="__main__": raise SystemExit(main())
