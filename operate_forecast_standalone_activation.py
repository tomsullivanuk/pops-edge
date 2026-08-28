#!/usr/bin/env python3
"""Typed PR17C1 deployment composition; inert until explicitly invoked."""
from __future__ import annotations
import argparse,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
from forecast_standalone_activation import BoundedLiveReadOnlyTransport,KalshiRequestSigner,MacOSKeychainCredentialProvider,OperationalHeartbeat,OperationalState,ProviderPageAcquisition,acquire_kalshi_catalog_pages,adapt_kalshi_orderbook,encoded_kalshi_catalog_path,health_from_operational_state,initialize_activation,invoke_activated_prospective,merge_kalshi_catalog_pages,merge_mlb_schedule_responses,reconcile_outcomes_from_raw,refresh_supporting_from_raw,render_launchd_jobs,required_mlb_query_dates,rsa_pss_sha256_sign
from forecast_standalone_operations import DeploymentConfig,ExitCode,NamespaceArchive,OperatingMode,OperationsError,acquire_typed_supporting_fixture,index_health,inspect_archive,rebuild_index,reconcile_incomplete_acquisitions,replay_pr17_archive,sync_secondary

class FixtureTransport:
    def __init__(self,path:Path):self.path=path;self.calls=0
    def request(self,method,url,*,params,timeout,allow_redirects):
        from forecast_standalone_operations import HTTPResponse
        self.calls+=1;return HTTPResponse(200,self.path.read_bytes(),{})

def configured_kalshi_transport(config,clock):
    # Current catalog and order-book GETs are documented public market-data
    # endpoints.  Keep the signer replaceable, but do not retrieve a private key.
    def requester(url,headers,timeout,allow_redirects):
        import urllib.error,urllib.request
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        request=urllib.request.Request(url,headers=dict(headers),method="GET")
        try:
            with urllib.request.build_opener(NoRedirect).open(request,timeout=timeout) as response:return response.status,response.read(2_000_001),dict(response.headers)
        except urllib.error.HTTPError as exc:return exc.code,exc.read(2_000_001),dict(exc.headers)
    return BoundedLiveReadOnlyTransport(config.provider_base_url,requester,timeout_seconds=config.retry_policy.request_timeout_seconds)

def execute(command,config,*,clock=lambda:datetime.now(timezone.utc),transport_factory=None,supporting_loader=None,outcome_loader=None,free_disk=None):
    archive=NamespaceArchive(config);state=OperationalState(config.log_root/"operational-state");started=clock()
    calls=typed=due=None;disposition="success";failure=None
    try:
        if config.mode is not OperatingMode.ACTIVATED:raise OperationsError("deployment-mode-invalid","PR17C1 CLI requires activated namespace")
        if command=="initialize-activation":
            activation_id,protocol_id=initialize_activation(archive,started);output={"configuration_id":config.identity,"disposition":"success","activation_id":activation_id,"protocol_id":protocol_id}
        elif command=="capture-prospective":
            if transport_factory is None:raise OperationsError("adapter-unavailable","configured Kalshi order-book adapter is absent")
            result=invoke_activated_prospective(archive=archive,transport_factory=transport_factory,clock=clock,observation_adapter=lambda value,raw,started,completed,series,schedule:adapt_kalshi_orderbook(payload=value,raw=raw,started_at=started,completed_at=completed,series=series,schedule=schedule))
            calls=result.provider_request_count;typed=len(result.created_attempt_ids);due=len(result.due_opportunity_ids);disposition=result.disposition
            output={"configuration_id":result.configuration_id,"namespace":result.namespace,"trusted_now":result.trusted_now,"provider_calls":calls,"typed_dispositions":typed,"due_opportunities":due,"disposition":disposition}
        elif command=="refresh-supporting":
            if supporting_loader is None:raise OperationsError("adapter-unavailable","configured MLB/Kalshi supporting adapters are absent")
            loaded=supporting_loader(started);mlb_raw,kalshi_raw=loaded[:2];pages=loaded[2] if len(loaded)>2 else ();mlb_pages=loaded[3] if len(loaded)>3 else ();result=refresh_supporting_from_raw(archive=archive,mlb_raw=mlb_raw,kalshi_raw=kalshi_raw,collected_at=started,catalog_pages=pages,mlb_pages=mlb_pages);calls=(len(mlb_pages) if mlb_pages else 1)+(len(pages) if pages else 1);typed=result["contracts"];disposition=result["disposition"];output={"configuration_id":config.identity,"provider_calls":calls,**result}
        elif command=="reconcile-outcomes":
            if outcome_loader is None:raise OperationsError("adapter-unavailable","configured MLB outcome adapter is absent")
            loaded=outcome_loader(started);mlb_raw,mlb_pages=(loaded if isinstance(loaded,tuple) and len(loaded)==2 else (loaded,()))
            result=reconcile_outcomes_from_raw(archive=archive,mlb_raw=mlb_raw,collected_at=started,mlb_pages=mlb_pages);calls=len(mlb_pages) if mlb_pages else 1;typed=result["changed"];disposition=result["disposition"];output={"configuration_id":config.identity,"provider_calls":calls,**result}
        elif command=="inspect":output=json.loads(inspect_archive(archive).to_json());disposition="success" if output["ready"] else "not-ready"
        elif command=="reconcile-acquisitions":
            artifacts=reconcile_incomplete_acquisitions(archive,reconciled_at=started);output={"configuration_id":config.identity,"disposition":"success","reconciliation_artifacts":artifacts,"artifact_count":len(artifacts)};typed=len(artifacts)
        elif command=="maintain":
            inspection=inspect_archive(archive)
            if not inspection.ready:raise OperationsError("integrity-unsafe","archive inspection refused index rebuild")
            digest=rebuild_index(archive);index_state,_=index_health(archive)
            if index_state!="healthy":raise OperationsError("index-rebuild-failed","post-rebuild index is not healthy")
            output={"configuration_id":config.identity,"disposition":"success","inspection":"verified","index_state":index_state,"index_sha256":digest}
        elif command=="rebuild-index":output={"index_sha256":rebuild_index(archive),"disposition":"success"}
        elif command=="sync-secondary":output={**sync_secondary(archive),"disposition":"success"}
        elif command=="health-report":
            disk=free_disk or (lambda root:shutil.disk_usage(root).free)
            output=json.loads(health_from_operational_state(archive=archive,state=state,trusted_at=started,free_disk=disk).to_json());disposition="success" if output["ready"] else "not-ready"
        else:raise OperationsError("command-boundary",command)
        return output
    except OperationsError as exc:
        failure=exc.code;disposition="failed";raise
    finally:
        completed=clock()
        try:state.append(OperationalHeartbeat("1",command,started,completed,disposition,calls,typed,due,failure))
        except OperationsError:
            if failure is None:raise

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--config",type=Path);parser.add_argument("--fixture",type=Path);parser.add_argument("--trusted-at")
    parser.add_argument("command",choices=("initialize-activation","capture-prospective","refresh-supporting","reconcile-outcomes","reconcile-acquisitions","inspect","maintain","rebuild-index","sync-secondary","health-report","render-launchd"));parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    try:
        if args.config is None:raise OperationsError("configuration-error","--config is required")
        config=DeploymentConfig.from_json(args.config)
        if args.command=="render-launchd":
            if args.output is None:raise OperationsError("configuration-error","--output is required")
            result={"rendered":render_launchd_jobs(repository_root=Path(__file__).parent,python_executable=Path(sys.executable),config_path=args.config,output_root=args.output)}
        else:
            fixed=datetime.fromisoformat(args.trusted_at) if args.trusted_at else None;clock=(lambda:fixed) if fixed else (lambda:datetime.now(timezone.utc))
            fixture=FixtureTransport(args.fixture/"orderbook.json") if args.fixture else None
            live=None
            if args.command=="capture-prospective" and fixture is None:live=configured_kalshi_transport(config,clock)
            factory=(lambda _opportunity,_series:fixture or live) if (fixture or live) else None
            if args.fixture:
                supporting_loader=lambda _at:((args.fixture/"mlb.json").read_bytes(),(args.fixture/"kalshi.json").read_bytes());outcome_loader=lambda _at:(args.fixture/"mlb.json").read_bytes()
            else:
                def public_get(base,path):return BoundedLiveReadOnlyTransport(base,configured_kalshi_transport(config,clock).requester).get(path)
                def histories(at):return replay_pr17_archive(NamespaceArchive(config),analysis_boundary=at).bucket("outcome_histories")
                def mlb_material(purpose,at):
                    dates=required_mlb_query_dates(trusted_at=at,histories=histories(at),purpose=purpose)
                    pages=[]
                    for day in dates:
                        started=clock();raw=public_get("https://statsapi.mlb.com","/api/v1/schedule?sportId=1&date="+day.isoformat());completed=clock();pages.append(ProviderPageAcquisition(day.isoformat(),"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date="+day.isoformat(),raw,started,completed,len(pages),"mlb-stats-api",at.isoformat(),day.isoformat()))
                    pages=tuple(pages)
                    return merge_mlb_schedule_responses(tuple(x.raw for x in pages)),pages
                def catalog_material(at):
                    pages=acquire_kalshi_catalog_pages(lambda cursor:public_get(config.provider_base_url,encoded_kalshi_catalog_path(cursor)),clock=clock,command_start=at)
                    return merge_kalshi_catalog_pages(pages),pages
                def supporting_material(at):
                    mlb,mlb_pages=mlb_material("schedule",at);catalog,catalog_pages=catalog_material(at);return mlb,catalog,catalog_pages,mlb_pages
                supporting_loader=supporting_material;outcome_loader=lambda at:mlb_material("outcomes",at)
            result=execute(args.command,config,clock=clock,transport_factory=factory,supporting_loader=supporting_loader,outcome_loader=outcome_loader)
        print(json.dumps(result,sort_keys=True,separators=(",",":"),default=lambda x:x.isoformat()))
        return int(ExitCode.SUCCESS if result.get("disposition")!="not-ready" else ExitCode.NOT_READY)
    except OperationsError as exc:
        print(json.dumps({"code":exc.code,"detail":exc.detail,"state":"failed"},sort_keys=True,separators=(",",":")),file=sys.stderr)
        return int(ExitCode.INTEGRITY_FAILURE if any(x in exc.code for x in ("integrity","corrupt","archive")) else ExitCode.OPERATIONAL_FAILURE)
    except Exception as exc:
        print(json.dumps({"code":"internal-error","detail":f"unexpected internal failure ({type(exc).__name__})","state":"failed"},sort_keys=True,separators=(",",":")),file=sys.stderr);return int(ExitCode.OPERATIONAL_FAILURE)
if __name__=="__main__":raise SystemExit(main())
