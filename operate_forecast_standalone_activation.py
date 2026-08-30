#!/usr/bin/env python3
"""Typed PR17C1 deployment composition; inert until explicitly invoked."""
from __future__ import annotations
import argparse,json,shutil,sys,time
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from forecast_standalone_activation import APPROVED_EASTERN_DATE,APPROVED_TIMEZONE,RETROSPECTIVE_WINDOW_START,BoundedLiveReadOnlyTransport,KalshiCatalogPage,KalshiRequestSigner,MacOSKeychainCredentialProvider,OperationalHeartbeat,OperationalState,ProviderPageAcquisition,acquire_kalshi_catalog_pages,acquire_retrospective_catalog_pages,adapt_kalshi_candles,adapt_kalshi_orderbook,canonical_kalshi_candle_path,canonical_mlb_schedule_request,complete_supporting_session_from_archive,encoded_kalshi_catalog_path,encoded_kalshi_retrospective_catalog_path,health_from_operational_state,initialize_activation,invoke_activated_prospective,merge_kalshi_catalog_pages,merge_retrospective_catalog_pages,merge_mlb_schedule_responses,preserve_supporting_response,reconcile_outcomes_from_raw,refresh_supporting_from_raw,render_launchd_jobs,required_mlb_query_dates,rsa_pss_sha256_sign
from forecast_standalone_operations import RETROSPECTIVE_SUPPORTING_RETRY_POLICY,DeploymentConfig,DesignAuthority,Disposition,ExitCode,HTTPResponse,NamespaceArchive,OperatingMode,OperationsError,RetrospectiveAcquisitionError,SupportingAcquisitionError,_entry_values,acquire_prospective_once,acquire_typed_supporting_fixture,acquire_with_retries,discover_and_acquire_retrospective,index_health,inspect_archive,rebuild_index,reconcile_incomplete_acquisitions,replay_pr17_archive,request_identity,sync_secondary

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
    """Return bounded GET results so the acquisition layer owns disposition handling."""
    def __init__(self,bounded,base_url):self.bounded,self.base_url,self.calls=bounded,base_url.rstrip("/"),0
    def request(self,method,url,*,params,timeout,allow_redirects):
        if method!="GET" or params or allow_redirects or timeout>self.bounded.timeout_seconds or not url.startswith(self.base_url+"/"):raise OperationsError("transport-configuration","retrospective request is noncanonical")
        self.calls+=1
        status,body,headers=self.bounded.requester(url,{"Accept":"application/json"},timeout,False)
        if len(body)>self.bounded.maximum_bytes:return HTTPResponse(413,b"",{})
        return HTTPResponse(status,body,headers)

def adapt_kalshi_historical_cutoff(value):
    try:cutoff=datetime.fromisoformat(value["market_settled_ts"].replace("Z","+00:00"))
    except (KeyError,TypeError,ValueError) as exc:raise OperationsError("validation-failure","Kalshi historical cutoff is malformed") from exc
    if cutoff.tzinfo is None:raise OperationsError("validation-failure","Kalshi historical cutoff is naive")
    return {"market_settled_at":cutoff}


def acquire_retrospective_supporting_page(*,archive,session_id,provider,purpose,base,path,request_identity_value,transport,clock,sleeper=time.sleep,partition=None,partition_position=None,validator=lambda value:value):
    """Acquire and durably preserve one PR17C2 logical supporting page."""
    endpoint=base.rstrip("/")+path
    result=acquire_with_retries(transport=transport,endpoint=endpoint,request={},policy=RETROSPECTIVE_SUPPORTING_RETRY_POLICY,now=clock,sleeper=sleeper,validator=validator)
    terminal=result.attempts[-1]
    preserve_supporting_response(archive=archive,session_id=session_id,provider=provider,purpose=purpose,endpoint=endpoint,request_identity_value=request_identity_value,started_at=result.attempts[0].started_at,completed_at=terminal.completed_at,disposition=result.disposition,raw=result.raw_body,partition=partition,partition_position=partition_position,attempts=result.attempts,attempt_raw_bodies=result.attempt_raw_bodies)
    return result

def live_mlb_material(purpose,at,*,histories,public_get,clock):
    """Acquire obligation dates through the established MLB request contract."""
    dates=required_mlb_query_dates(trusted_at=at,histories=histories,purpose=purpose);pages=[]
    for day in dates:
        path,endpoint=canonical_mlb_schedule_request(day);started=clock();raw=public_get("https://statsapi.mlb.com",path);completed=clock();pages.append(ProviderPageAcquisition(day.isoformat(),endpoint,raw,started,completed,len(pages),"mlb-stats-api",at.isoformat(),day.isoformat()))
    pages=tuple(pages)
    return merge_mlb_schedule_responses(tuple(x.raw for x in pages)),pages

def execute(command,config,*,clock=lambda:datetime.now(timezone.utc),transport_factory=None,supporting_loader=None,outcome_loader=None,retrospective_runner=None,free_disk=None,session_completion_id=None,session_correction_reason=None):
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
            loaded=supporting_loader(started);mlb_raw,kalshi_raw=loaded[:2];pages=loaded[2] if len(loaded)>2 else ();mlb_pages=loaded[3] if len(loaded)>3 else ();cutoff_at=loaded[5] if len(loaded)>5 else None;session_id=loaded[6] if len(loaded)>6 else None;calls=loaded[4] if len(loaded)>4 else (len(mlb_pages) if mlb_pages else 1)+(len(pages) if pages else 1)
            requested_window=((mlb_pages[0].request_identity,mlb_pages[-1].request_identity) if command=="refresh-retrospective-supporting" and mlb_pages else None)
            try:result=refresh_supporting_from_raw(archive=archive,mlb_raw=mlb_raw,kalshi_raw=kalshi_raw,collected_at=started,catalog_pages=pages,mlb_pages=mlb_pages,acquisition_command=command,retrospective_cutoff_at=cutoff_at,supporting_session_id=session_id,supporting_provider_calls=calls,requested_date_window=requested_window)
            except OperationsError as exc:
                if not hasattr(exc,"provider_calls"):exc.provider_calls=calls
                raise
            typed=result["contracts"];disposition=result["disposition"];output={"configuration_id":config.identity,"provider_calls":calls,**result}
        elif command=="reconcile-outcomes":
            if outcome_loader is None:raise OperationsError("adapter-unavailable","configured MLB outcome adapter is absent")
            loaded=outcome_loader(started);mlb_raw,mlb_pages=(loaded if isinstance(loaded,tuple) and len(loaded)==2 else (loaded,()))
            result=reconcile_outcomes_from_raw(archive=archive,mlb_raw=mlb_raw,collected_at=started,mlb_pages=mlb_pages);calls=len(mlb_pages) if mlb_pages else 1;typed=result["changed"];disposition=result["disposition"];output={"configuration_id":config.identity,"provider_calls":calls,**result}
        elif command=="acquire-retrospective":
            if retrospective_runner is None:raise OperationsError("adapter-unavailable","bounded retrospective adapter is absent")
            created,calls=retrospective_runner(archive);typed=len(created);output={"configuration_id":config.identity,"namespace":config.namespace,"provider_calls":calls,"created_manifest_ids":created,"disposition":"completed"}
        elif command=="complete-retrospective-supporting-session":
            if not session_completion_id:raise OperationsError("configuration-error","explicit --session-id is required")
            result=complete_supporting_session_from_archive(archive=archive,session_id=session_completion_id);calls=0;typed=result.get("contracts",0);output={"configuration_id":config.identity,"namespace":config.namespace,**result};output.setdefault("disposition","completed")
        elif command=="correct-retrospective-supporting-session":
            if not session_completion_id or not session_correction_reason:raise OperationsError("configuration-error","explicit --session-id and --reason are required")
            result=complete_supporting_session_from_archive(archive=archive,session_id=session_completion_id,correction_reason=session_correction_reason);calls=0;typed=result.get("contracts",0);output={"configuration_id":config.identity,"namespace":config.namespace,**result};output.setdefault("disposition","corrected")
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
        calls=getattr(exc,"provider_calls",calls);failure=exc.code;disposition="failed";raise
    finally:
        completed=clock()
        try:state.append(OperationalHeartbeat("1",command,started,completed,disposition,calls,typed,due,failure))
        except OperationsError:
            if failure is None:raise

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--config",type=Path);parser.add_argument("--fixture",type=Path);parser.add_argument("--trusted-at")
    parser.add_argument("command",choices=("initialize-activation","capture-prospective","refresh-supporting","refresh-retrospective-supporting","complete-retrospective-supporting-session","correct-retrospective-supporting-session","acquire-retrospective","reconcile-outcomes","reconcile-acquisitions","inspect","maintain","rebuild-index","sync-secondary","health-report","render-launchd"));parser.add_argument("--output",type=Path);parser.add_argument("--maximum-opportunities",type=int);parser.add_argument("--start-date");parser.add_argument("--end-date");parser.add_argument("--session-id");parser.add_argument("--reason")
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
                        session="supporting-session:"+request_identity({"configuration_id":config.identity,"command_started_at":at,"start_date":start_day,"end_date":end_day}).split(":",1)[1];session_archive=NamespaceArchive(config);calls=0;mlb_pages=[];catalog_pages=[]
                        requester=configured_kalshi_transport(config,clock).requester
                        def bounded_get(provider,purpose,base,path,identity,*,partition=None,partition_position=None,validator=lambda value:value):
                            nonlocal calls
                            endpoint=base.rstrip("/")+path;transport=LiveRetrospectiveTransport(BoundedLiveReadOnlyTransport(base,requester,timeout_seconds=RETROSPECTIVE_SUPPORTING_RETRY_POLICY.request_timeout_seconds),base)
                            result=acquire_retrospective_supporting_page(archive=session_archive,session_id=session,provider=provider,purpose=purpose,base=base,path=path,request_identity_value=identity,transport=transport,clock=clock,partition=partition,partition_position=partition_position,validator=validator);calls+=len(result.attempts)
                            attempt=result.attempts[-1]
                            if result.disposition is not Disposition.SUCCESS or result.raw_body is None:raise SupportingAcquisitionError("supporting-acquisition-failed",f"{purpose} acquisition failed",calls)
                            return result.raw_body,result.attempts[0].started_at,attempt.completed_at,result.normalized
                        try:
                            for offset in range((end_day-start_day).days+1):
                                day=start_day+timedelta(days=offset);path,endpoint=canonical_mlb_schedule_request(day);raw,began,completed,_=bounded_get("mlb-stats-api","schedule","https://statsapi.mlb.com",path,day.isoformat());mlb_pages.append(ProviderPageAcquisition(day.isoformat(),endpoint,raw,began,completed,len(mlb_pages),"mlb-stats-api",at.isoformat(),day.isoformat()))
                            cutoff_path="/historical/cutoff";cutoff_raw,_,_,cutoff_value=bounded_get("kalshi","historical-cutoff",config.provider_base_url,cutoff_path,"historical-cutoff",validator=adapt_kalshi_historical_cutoff);cutoff=cutoff_value["market_settled_at"]
                            for historical,partition in ((True,"historical"),(False,"live")):
                                position=[0];timings={}
                                builder=lambda cursor,historical=historical:encoded_kalshi_retrospective_catalog_path(cursor,historical=historical)
                                def fetch_cursor(cursor,partition=partition,builder=builder):
                                    raw,began,completed,_=bounded_get("kalshi","catalog",config.provider_base_url,builder(cursor),cursor,partition=partition,partition_position=position[0]);timings[cursor]=(began,completed);position[0]+=1;return raw
                                acquired=acquire_kalshi_catalog_pages(fetch_cursor,clock=clock,command_start=at,path_builder=builder)
                                for page in acquired:catalog_pages.append(KalshiCatalogPage(len(catalog_pages),page.request_cursor,page.next_cursor,page.raw,page.markets,*timings[page.request_cursor],config.provider_base_url.rstrip("/")+(page.endpoint or builder(page.request_cursor)),partition,page.position))
                            return merge_mlb_schedule_responses(tuple(x.raw for x in mlb_pages)),merge_retrospective_catalog_pages(catalog_pages,cutoff),tuple(catalog_pages),tuple(mlb_pages),calls,cutoff,session
                        except SupportingAcquisitionError:raise
                        except OperationsError as exc:raise SupportingAcquisitionError(exc.code,"retrospective supporting validation failed",calls) from exc
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
                    cutoff_transport=FixtureTransport(args.fixture/"cutoff.json") if args.fixture else retro_transport
                    cutoff_endpoint=config.provider_base_url.rstrip("/")+"/historical/cutoff"
                    acquired_cutoff=acquire_prospective_once(transport=cutoff_transport,endpoint=cutoff_endpoint,request={},timeout_seconds=config.retry_policy.request_timeout_seconds,now=clock,validator=adapt_kalshi_historical_cutoff)
                    cutoff_started=acquired_cutoff.attempts[0].started_at;cutoff_completed=acquired_cutoff.attempts[-1].completed_at
                    if acquired_cutoff.disposition is not Disposition.SUCCESS or acquired_cutoff.raw_body is None or acquired_cutoff.normalized is None:
                        values=_entry_values(archive=archive,command="acquire-retrospective-cutoff",request_id=request_identity({"endpoint":cutoff_endpoint,"started_at":cutoff_started}),invoked_at=cutoff_completed,endpoint=cutoff_endpoint,disposition=acquired_cutoff.disposition,protocol_id=None,design=DesignAuthority.SUPPORTING,diagnostics=("historical-cutoff",f"attempt-1:{acquired_cutoff.disposition.value}"),provider_effective_at=None);values["provider_id"]="kalshi"
                        with archive.mutation_lock():archive._record_failure_locked(entry_values=values,raw_body=acquired_cutoff.raw_body)
                        raise RetrospectiveAcquisitionError("bounded historical cutoff acquisition failed",0 if args.fixture else 1)
                    cutoff_raw=acquired_cutoff.raw_body;cutoff=acquired_cutoff.normalized["market_settled_at"]
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
                    try:created=discover_and_acquire_retrospective(archive=archive,transport_factory=lambda _opportunity,_series:retro_transport,clock=clock,sleeper=time.sleep,request_builder=request_builder,response_adapter=adapter,maximum_opportunities=args.maximum_opportunities)
                    except OperationsError as exc:
                        if hasattr(exc,"provider_calls"):exc.provider_calls+=0 if args.fixture else 1
                        raise
                    return created,retro_transport.calls
            result=execute(args.command,config,clock=clock,transport_factory=factory,supporting_loader=supporting_loader,outcome_loader=outcome_loader,retrospective_runner=retrospective_runner,session_completion_id=args.session_id,session_correction_reason=args.reason)
        print(json.dumps(result,sort_keys=True,separators=(",",":"),default=lambda x:x.isoformat()))
        return int(ExitCode.SUCCESS if result.get("disposition")!="not-ready" else ExitCode.NOT_READY)
    except OperationsError as exc:
        failure={"code":exc.code,"detail":exc.detail,"state":"failed"}
        if hasattr(exc,"provider_calls"):failure["provider_calls"]=exc.provider_calls
        print(json.dumps(failure,sort_keys=True,separators=(",",":")),file=sys.stderr)
        return int(ExitCode.INTEGRITY_FAILURE if any(x in exc.code for x in ("integrity","corrupt","archive")) else ExitCode.OPERATIONAL_FAILURE)
    except Exception as exc:
        print(json.dumps({"code":"internal-error","detail":f"unexpected internal failure ({type(exc).__name__})","state":"failed"},sort_keys=True,separators=(",",":")),file=sys.stderr);return int(ExitCode.OPERATIONAL_FAILURE)
if __name__=="__main__":raise SystemExit(main())
