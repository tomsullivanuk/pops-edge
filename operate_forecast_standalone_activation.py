#!/usr/bin/env python3
"""Typed PR17C1 deployment composition; inert until explicitly invoked."""
from __future__ import annotations
import argparse,json,shutil,sys,time
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from forecast_standalone_activation import APPROVED_EASTERN_DATE,APPROVED_TIMEZONE,RETROSPECTIVE_WINDOW_START,BoundedLiveReadOnlyTransport,KalshiRequestSigner,MacOSKeychainCredentialProvider,OperationalHeartbeat,OperationalState,ProviderPageAcquisition,acquire_kalshi_catalog_pages,acquire_retrospective_catalog_pages,adapt_kalshi_candles,adapt_kalshi_orderbook,canonical_kalshi_candle_path,canonical_mlb_schedule_request,encoded_kalshi_catalog_path,health_from_operational_state,initialize_activation,invoke_activated_prospective,merge_kalshi_catalog_pages,merge_mlb_schedule_responses,reconcile_outcomes_from_raw,refresh_supporting_from_raw,render_launchd_jobs,required_mlb_query_dates,rsa_pss_sha256_sign
from forecast_standalone_operations import DeploymentConfig,DesignAuthority,Disposition,ExitCode,HTTPResponse,NamespaceArchive,OperatingMode,OperationsError,_entry_values,acquire_typed_supporting_fixture,discover_and_acquire_retrospective,index_health,inspect_archive,rebuild_index,reconcile_incomplete_acquisitions,replay_pr17_archive,request_identity,sync_secondary

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


class LiveRetrospectiveTransport:
    """Bounded GET-only adapter for one already-authorized candle endpoint."""
    def __init__(self,bounded,base_url):self.bounded,self.base_url,self.calls=bounded,base_url.rstrip("/"),0
    def request(self,method,url,*,params,timeout,allow_redirects):
        if method!="GET" or params or allow_redirects or timeout>self.bounded.timeout_seconds or not url.startswith(self.base_url+"/"):raise OperationsError("transport-configuration","retrospective request is noncanonical")
        self.calls+=1;return HTTPResponse(200,self.bounded.get(url[len(self.base_url):]),{})

def live_mlb_material(purpose,at,*,histories,public_get,clock):
    """Acquire obligation dates through the established MLB request contract."""
    dates=required_mlb_query_dates(trusted_at=at,histories=histories,purpose=purpose);pages=[]
    for day in dates:
        path,endpoint=canonical_mlb_schedule_request(day);started=clock();raw=public_get("https://statsapi.mlb.com",path);completed=clock();pages.append(ProviderPageAcquisition(day.isoformat(),endpoint,raw,started,completed,len(pages),"mlb-stats-api",at.isoformat(),day.isoformat()))
    pages=tuple(pages)
    return merge_mlb_schedule_responses(tuple(x.raw for x in pages)),pages

def execute(command,config,*,clock=lambda:datetime.now(timezone.utc),transport_factory=None,supporting_loader=None,outcome_loader=None,retrospective_runner=None,free_disk=None):
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
        elif command in {"refresh-supporting","refresh-retrospective-supporting"}:
            if supporting_loader is None:raise OperationsError("adapter-unavailable","configured MLB/Kalshi supporting adapters are absent")
            loaded=supporting_loader(started);mlb_raw,kalshi_raw=loaded[:2];pages=loaded[2] if len(loaded)>2 else ();mlb_pages=loaded[3] if len(loaded)>3 else ();result=refresh_supporting_from_raw(archive=archive,mlb_raw=mlb_raw,kalshi_raw=kalshi_raw,collected_at=started,catalog_pages=pages,mlb_pages=mlb_pages,acquisition_command=command);calls=(len(mlb_pages) if mlb_pages else 1)+(len(pages) if pages else 1);typed=result["contracts"];disposition=result["disposition"];output={"configuration_id":config.identity,"provider_calls":calls,**result}
        elif command=="reconcile-outcomes":
            if outcome_loader is None:raise OperationsError("adapter-unavailable","configured MLB outcome adapter is absent")
            loaded=outcome_loader(started);mlb_raw,mlb_pages=(loaded if isinstance(loaded,tuple) and len(loaded)==2 else (loaded,()))
            result=reconcile_outcomes_from_raw(archive=archive,mlb_raw=mlb_raw,collected_at=started,mlb_pages=mlb_pages);calls=len(mlb_pages) if mlb_pages else 1;typed=result["changed"];disposition=result["disposition"];output={"configuration_id":config.identity,"provider_calls":calls,**result}
        elif command=="acquire-retrospective":
            if retrospective_runner is None:raise OperationsError("adapter-unavailable","bounded retrospective adapter is absent")
            created,calls=retrospective_runner(archive);typed=len(created);output={"configuration_id":config.identity,"namespace":config.namespace,"provider_calls":calls,"created_manifest_ids":created,"disposition":"completed"}
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
    parser.add_argument("command",choices=("initialize-activation","capture-prospective","refresh-supporting","refresh-retrospective-supporting","acquire-retrospective","reconcile-outcomes","reconcile-acquisitions","inspect","maintain","rebuild-index","sync-secondary","health-report","render-launchd"));parser.add_argument("--output",type=Path);parser.add_argument("--maximum-opportunities",type=int);parser.add_argument("--start-date");parser.add_argument("--end-date")
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
                    return live_mlb_material(purpose,at,histories=histories(at),public_get=public_get,clock=clock)
                def catalog_material(at):
                    pages=acquire_kalshi_catalog_pages(lambda cursor:public_get(config.provider_base_url,encoded_kalshi_catalog_path(cursor)),clock=clock,command_start=at)
                    return merge_kalshi_catalog_pages(pages),pages
                def supporting_material(at):
                    mlb,mlb_pages=mlb_material("schedule",at);catalog,catalog_pages=catalog_material(at);return mlb,catalog,catalog_pages,mlb_pages
                supporting_loader=supporting_material;outcome_loader=lambda at:mlb_material("outcomes",at)
                if args.command=="refresh-retrospective-supporting":
                    if not args.start_date or not args.end_date:raise OperationsError("configuration-error","retrospective supporting acquisition requires --start-date and --end-date")
                    try:start_day=date.fromisoformat(args.start_date);end_day=date.fromisoformat(args.end_date)
                    except ValueError as exc:raise OperationsError("configuration-error","retrospective date bounds must be canonical ISO dates") from exc
                    if start_day.isoformat()!=args.start_date or end_day.isoformat()!=args.end_date or end_day<start_day or (end_day-start_day).days>=31 or start_day<RETROSPECTIVE_WINDOW_START.date() or end_day>=APPROVED_EASTERN_DATE:raise OperationsError("retrospective-bound-invalid","retrospective supporting batch must contain 1 to 31 in-window dates")
                    def retrospective_supporting(at):
                        if end_day>=at.astimezone(ZoneInfo(APPROVED_TIMEZONE)).date():raise OperationsError("retrospective-bound-invalid","retrospective supporting dates must be complete at command start")
                        mlb_pages=[]
                        for offset in range((end_day-start_day).days+1):
                            day=start_day+timedelta(days=offset);path,endpoint=canonical_mlb_schedule_request(day);began=clock();raw=public_get("https://statsapi.mlb.com",path);completed=clock();mlb_pages.append(ProviderPageAcquisition(day.isoformat(),endpoint,raw,began,completed,len(mlb_pages),"mlb-stats-api",at.isoformat(),day.isoformat()))
                        catalog_pages=acquire_retrospective_catalog_pages(lambda path:public_get(config.provider_base_url,path),clock=clock,command_start=at)
                        return merge_mlb_schedule_responses(tuple(x.raw for x in mlb_pages)),merge_kalshi_catalog_pages(catalog_pages),catalog_pages,tuple(mlb_pages)
                    supporting_loader=retrospective_supporting
            retrospective_runner=None
            if args.command=="acquire-retrospective":
                if args.maximum_opportunities is None:raise OperationsError("configuration-error","--maximum-opportunities is required for bounded retrospective acquisition")
                if args.fixture:
                    retro_transport=FixtureTransport(args.fixture/"candles.json")
                else:
                    bounded=configured_kalshi_transport(config,clock);retro_transport=LiveRetrospectiveTransport(bounded,config.provider_base_url)
                def retrospective_runner(archive):
                    state=replay_pr17_archive(archive,analysis_boundary=clock())
                    if not any(x.design_tag.value=="retrospective" for x in state.bucket("protocols")):raise OperationsError("retrospective-authority-invalid","canonical retrospective Protocol is not initialized")
                    cutoff_started=clock();cutoff_raw=(args.fixture/"cutoff.json").read_bytes() if args.fixture else bounded.get("/historical/cutoff");cutoff_completed=clock()
                    try:cutoff=datetime.fromisoformat(json.loads(cutoff_raw)["market_settled_ts"].replace("Z","+00:00"))
                    except (KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:raise OperationsError("provider-data-invalid","Kalshi historical cutoff is malformed") from exc
                    if cutoff.tzinfo is None:raise OperationsError("provider-data-invalid","Kalshi historical cutoff is naive")
                    cutoff_digest=__import__('hashlib').sha256(cutoff_raw).hexdigest();normalized={"schema_version":"1","record_kind":"pr17c2-historical-cutoff","provider":"kalshi","endpoint":"/historical/cutoff","market_settled_at":cutoff,"raw_sha256":cutoff_digest,"started_at":cutoff_started,"completed_at":cutoff_completed}
                    values=_entry_values(archive=archive,command="acquire-retrospective-cutoff",request_id=request_identity({"raw_sha256":cutoff_digest,"started_at":cutoff_started}),invoked_at=cutoff_completed,endpoint=config.provider_base_url.rstrip("/")+"/historical/cutoff",disposition=Disposition.SUCCESS,protocol_id=None,design=DesignAuthority.SUPPORTING,diagnostics=("exact Kalshi historical partition cutoff",),provider_effective_at=cutoff);values["provider_id"]="kalshi"
                    with archive.mutation_lock():archive._commit_locked(raw_body=cutoff_raw,normalized=normalized,entry_values=values)
                    def request_builder(_opportunity,series,target):
                        values=tuple(x.split("=",1)[1] for x in series.settlement_evidence if x.startswith("settlement_ts="))
                        if len(values)!=1:raise OperationsError("retrospective-authority-invalid","provider settlement timestamp is absent or ambiguous")
                        try:settled_at=datetime.fromisoformat(values[0].replace("Z","+00:00"))
                        except ValueError as exc:raise OperationsError("retrospective-authority-invalid","provider settlement timestamp is malformed") from exc
                        path=canonical_kalshi_candle_path(series.provider_market_id,target,historical=settled_at<cutoff);return config.provider_base_url.rstrip("/")+path,{}
                    def adapter(value,_raw,_opportunity,series,target):return adapt_kalshi_candles(value,market_ticker=series.provider_market_id,target_at=target)
                    created=discover_and_acquire_retrospective(archive=archive,transport_factory=lambda _opportunity,_series:retro_transport,clock=clock,sleeper=time.sleep,request_builder=request_builder,response_adapter=adapter,maximum_opportunities=args.maximum_opportunities)
                    return created,retro_transport.calls+(0 if args.fixture else 1)
            result=execute(args.command,config,clock=clock,transport_factory=factory,supporting_loader=supporting_loader,outcome_loader=outcome_loader,retrospective_runner=retrospective_runner)
        print(json.dumps(result,sort_keys=True,separators=(",",":"),default=lambda x:x.isoformat()))
        return int(ExitCode.SUCCESS if result.get("disposition")!="not-ready" else ExitCode.NOT_READY)
    except OperationsError as exc:
        print(json.dumps({"code":exc.code,"detail":exc.detail,"state":"failed"},sort_keys=True,separators=(",",":")),file=sys.stderr)
        return int(ExitCode.INTEGRITY_FAILURE if any(x in exc.code for x in ("integrity","corrupt","archive")) else ExitCode.OPERATIONAL_FAILURE)
    except Exception as exc:
        print(json.dumps({"code":"internal-error","detail":f"unexpected internal failure ({type(exc).__name__})","state":"failed"},sort_keys=True,separators=(",",":")),file=sys.stderr);return int(ExitCode.OPERATIONAL_FAILURE)
if __name__=="__main__":raise SystemExit(main())
