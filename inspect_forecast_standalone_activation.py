#!/usr/bin/env python3
"""Deterministic activated, offline PR17C1 deployment rehearsal."""
from __future__ import annotations
import hashlib,json,plistlib,subprocess,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
from forecast_standalone_activation import APPROVED_ACTIVATION_AT,KalshiCatalogPage,OperationalState,ProviderPageAcquisition,canonical_prospective_authority,merge_kalshi_catalog_pages,publish_verified_acquisition,render_launchd_jobs
from forecast_standalone_operations import DeploymentConfig,HTTPResponse,NamespaceArchive,OperationsError,index_health,inspect_archive,rebuild_index,reconcile_incomplete_acquisitions,replay_pr17_archive,sync_secondary
from operate_forecast_standalone_activation import execute

PRE=datetime.fromisoformat("2026-09-04T23:59:59-04:00");BOUNDARY=APPROVED_ACTIVATION_AT;TARGET=BOUNDARY

class FixtureOrderBook:
    def __init__(self,body):self.body=body;self.calls=0
    def request(self,*args,**kwargs):self.calls+=1;return HTTPResponse(200,self.body,{})

def fixtures():
    game={"gamePk":990001,"season":"2026","gameType":"R","gameDate":"2026-09-05T10:00:00Z","officialDate":"2026-09-05","lastUpdated":"2026-09-05T03:50:00Z","doubleHeader":"N","gameNumber":1,"status":{"abstractGameState":"Preview","detailedState":"Scheduled"},"venue":{"id":1,"name":"Fixture Park"},"teams":{"away":{"team":{"id":113,"name":"Away Club","abbreviation":"AWY"}},"home":{"team":{"id":114,"name":"Home Club","abbreviation":"HME"}}}}
    second={"gamePk":990002,"season":"2026","gameType":"R","gameDate":"2026-09-05T12:00:00Z","officialDate":"2026-09-05","lastUpdated":"2026-09-05T03:51:00Z","doubleHeader":"Y","gameNumber":2,"status":{"abstractGameState":"Preview","detailedState":"Scheduled"},"venue":{"id":2,"name":"Second Park"},"teams":{"away":{"team":{"id":115,"name":"Second Away","abbreviation":"SAY"}},"home":{"team":{"id":116,"name":"Second Home","abbreviation":"SHM"}}}}
    mlb=json.dumps({"dates":[{"date":"2026-09-05","games":[game,second]}]},sort_keys=True,separators=(",",":")).encode()
    market={"ticker":"KXMLB-20260905-AWYHME-HME","event_ticker":"KXMLB-20260905-AWYHME","market_type":"binary","title":"Away Club at Home Club winner?","yes_sub_title":"Home Club","no_sub_title":"Away Club","status":"open","open_time":"2026-09-04T00:00:00Z","close_time":"2026-09-05T10:00:00Z","expected_expiration_time":"2026-09-05T10:00:00Z","yes_bid_dollars":"0.4000","yes_ask_dollars":"0.7000","no_bid_dollars":"0.3000","no_ask_dollars":"0.6000","notional_value_dollars":"1.0000","rules_primary":"If Home Club wins the Away Club vs Home Club professional baseball game originally scheduled for Sep 5, 2026 at 6:00 AM EDT, then the market resolves to Yes.","rules_secondary":"The following market refers to the Away Club vs Home Club professional baseball game originally scheduled for Sep 5, 2026 at 6:00 AM EDT. If this game is postponed, the market remains open."}
    first=json.dumps({"markets":[market],"cursor":"terminal"},sort_keys=True,separators=(",",":")).encode();last=b'{"cursor":"","markets":[]}'
    pages=(KalshiCatalogPage(0,"","terminal",first,(market,)),KalshiCatalogPage(1,"terminal","",last,()))
    catalog=merge_kalshi_catalog_pages(pages);book=b'{"orderbook_fp":{"yes_dollars":[["0.4000","2.00"]],"no_dollars":[["0.3000","3.00"]]}}'
    return mlb,catalog,book

def run()->str:
    mlb,catalog,book=fixtures();activation,protocol=canonical_prospective_authority()
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);repo=Path(__file__).resolve().parent;config_path=root/"activated.json";fixture_root=root/"fixtures";fixture_root.mkdir();(fixture_root/"mlb.json").write_bytes(mlb);(fixture_root/"kalshi.json").write_bytes(catalog);(fixture_root/"orderbook.json").write_bytes(book)
        trusted=(TARGET+timedelta(minutes=6,seconds=6)).isoformat();material={"activation_at":APPROVED_ACTIVATION_AT.isoformat(),"config_id":"activated-rehearsal","fixture_response_path":str(fixture_root),"lock_timeout_seconds":1,"log_root":str(root/"logs"),"mode":"activated","namespace":"rehearsal","primary_root":str(root/"activated/rehearsal/primary"),"provider_base_url":"https://external-api.kalshi.com/trade-api/v2","research_protocol_ids":[protocol.standalone_probability_source_protocol_id],"retry_policy":{"backoff_seconds":[],"maximum_attempts":1,"maximum_retry_after_seconds":0,"request_timeout_seconds":5,"total_timeout_seconds":5},"schedule_parameters":{"fixture_trusted_at":trusted},"secondary_root":str(root/"activated/rehearsal/secondary"),"timezone_name":"America/New_York"}
        config_path.write_text(json.dumps(material));config=DeploymentConfig.from_json(config_path);archive=NamespaceArchive(config)
        market=json.loads(catalog)["markets"][0];page_raw=(json.dumps({"markets":[market],"cursor":"terminal"},sort_keys=True,separators=(",",":")).encode(),b'{"cursor":"","markets":[]}');pages=(KalshiCatalogPage(0,"","terminal",page_raw[0],(market,)),KalshiCatalogPage(1,"terminal","",page_raw[1],()))
        initialized=execute("initialize-activation",config,clock=lambda:datetime(2026,8,28,tzinfo=timezone.utc))
        pre_transport=FixtureOrderBook(book);pre=execute("capture-prospective",config,clock=lambda:PRE,transport_factory=lambda *_:pre_transport)
        supporting=execute("refresh-supporting",config,clock=lambda:BOUNDARY,supporting_loader=lambda _at:(mlb,catalog,pages,(mlb,)))
        live_transport=FixtureOrderBook(book);capture=execute("capture-prospective",config,clock=lambda:BOUNDARY,transport_factory=lambda *_:live_transport)
        closure=execute("capture-prospective",config,clock=lambda:TARGET+timedelta(minutes=6),transport_factory=lambda *_:live_transport);duplicate=execute("capture-prospective",config,clock=lambda:TARGET+timedelta(minutes=6,seconds=1),transport_factory=lambda *_:live_transport)
        graph=replay_pr17_archive(archive,analysis_boundary=TARGET+timedelta(minutes=7));inspection=inspect_archive(archive);execute("reconcile-outcomes",config,clock=lambda:TARGET+timedelta(minutes=6,seconds=2),outcome_loader=lambda _at:(mlb,(mlb,)))
        crash_start=TARGET+timedelta(minutes=6,seconds=2,microseconds=100000);crash_end=crash_start+timedelta(microseconds=100000);crash_page=ProviderPageAcquisition("","/markets?status=open&limit=1000",catalog,crash_start,crash_end,0,"kalshi")
        try:
            with archive.mutation_lock():publish_verified_acquisition(archive=archive,provider="kalshi",union_raw=catalog,pages=(crash_page,),contracts=(),collected_at=crash_start,protocol_id=protocol.standalone_probability_source_protocol_id,command="refresh-supporting",fail_after_pages=1)
        except OperationsError as exc:
            if exc.code!="injected-acquisition-interruption":raise
        unresolved=inspect_archive(archive);reconciliations=reconcile_incomplete_acquisitions(archive,reconciled_at=TARGET+timedelta(minutes=6,seconds=2,microseconds=300000));reconciled=inspect_archive(archive)
        # Add a genuine recent supporting heartbeat after the simulated six-minute capture window.
        execute("refresh-supporting",config,clock=lambda:TARGET+timedelta(minutes=6,seconds=3),supporting_loader=lambda _at:(mlb,catalog));maintenance=execute("maintain",config,clock=lambda:TARGET+timedelta(minutes=6,seconds=4));secondary=execute("sync-secondary",config,clock=lambda:TARGET+timedelta(minutes=6,seconds=5))
        health=execute("health-report",config,clock=lambda:TARGET+timedelta(minutes=6,seconds=6),free_disk=lambda _:1_000_000_000)
        rendered=render_launchd_jobs(repository_root=repo,python_executable=Path(__import__('sys').executable),config_path=config_path,output_root=root/"rendered");jobs=tuple(plistlib.loads(Path(x).read_bytes()) for x in rendered);runs=tuple((x["Label"],subprocess.run(x["ProgramArguments"],cwd="/",capture_output=True,text=True,check=False)) for x in jobs);job_statuses=tuple((label,result.returncode) for label,result in runs)
        if any(code!=0 for _,code in job_statuses):raise RuntimeError(f"rendered job rehearsal failed: {tuple((x,r.returncode,r.stderr) for x,r in runs)}")
        raw_digest=hashlib.sha256(book).hexdigest();raw_present=any(x.get("raw_object_sha256")==raw_digest for x in archive.entries())
        payload={"activation_id":initialized["activation_id"],"archive_ready":inspection.ready,"attempts":len(graph.bucket("attempts")),"boundary_calls":capture["provider_calls"],"catalog_pages":supporting["catalog_pages"],"duplicate_calls":duplicate["provider_calls"],"health_ready":health["ready"],"index_state":index_health(archive)[0],"mapped":supporting["mapped"],"market_observations":len(graph.bucket("market_observations")),"missing":supporting["missing"],"network":"fixture-injected-only","partial_ready":unresolved.ready,"reconciled_ready":reconciled.ready,"reconciliation_artifacts":len(reconciliations),"pre_activation_calls":pre_transport.calls,"protocol_id":initialized["protocol_id"],"raw_orderbook_preserved":raw_present,"rendered_job_statuses":job_statuses,"secondary_conflicts":secondary["conflicts"],"snapshots":len(graph.bucket("snapshots")),"supporting_events":supporting["events"],"total_orderbook_calls":live_transport.calls}
    return json.dumps(payload,sort_keys=True,separators=(",",":"))

if __name__=="__main__":print(run())
