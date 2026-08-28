import json
import copy
import subprocess
import socket
import plistlib
from unittest.mock import patch
import tempfile
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs,urlparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from decimal import Decimal

from forecast_standalone_activation import *
from forecast_standalone_operations import DeploymentConfig, NamespaceArchive, OperatingMode, OperationsError, RetryPolicy, rebuild_index, sync_secondary
from inspect_forecast_standalone_activation import run
from operate_forecast_standalone_activation import execute


class ActivationTests(unittest.TestCase):
    def test_exact_authority_is_deterministic(self):
        self.assertEqual(APPROVED_ACTIVATION.activation_at.isoformat(), "2026-09-05T00:00:00-04:00")
        self.assertEqual(APPROVED_ACTIVATION.activation_utc.isoformat(), "2026-09-05T04:00:00+00:00")
        self.assertEqual(APPROVED_ACTIVATION.to_json(), ProspectiveActivationAuthority.approved().to_json())
        with self.assertRaises(OperationsError): replace(APPROVED_ACTIVATION, activation_at=datetime(2026, 9, 5))
        with self.assertRaises(OperationsError): replace(APPROVED_ACTIVATION, activation_at=APPROVED_ACTIVATION.activation_at.astimezone(timezone.utc))

    def test_activated_config_example_names_canonical_protocol(self):
        example=Path(__file__).resolve().parents[1]/"operations/pr17c1.activated.config.example.json"
        config=DeploymentConfig.from_json(example)
        _,protocol=canonical_prospective_authority()
        self.assertEqual(config.research_protocol_ids,(protocol.standalone_probability_source_protocol_id,))

    def test_credential_provider_is_injected_and_sanitized(self):
        seen = []
        def runner(command, **kwargs):
            seen.append(command); return subprocess.CompletedProcess(command, 0, b"fixture-secret\n", b"")
        provider = MacOSKeychainCredentialProvider("fixture-service", "fixture-account", runner)
        self.assertEqual(provider.credential(), b"fixture-secret")
        self.assertNotIn("fixture-secret", repr(seen))
        denied = replace(provider, runner=lambda *a, **k: subprocess.CompletedProcess(a, 44, b"", b"private failure"))
        with self.assertRaisesRegex(OperationsError, "credential-unavailable") as error: denied.credential()
        self.assertNotIn("private", str(error.exception))
        for value in (b"", b"a\x00b", b"x" * 16385):
            bad = replace(provider, runner=lambda *a, value=value, **k: subprocess.CompletedProcess(a, 0, value, b""))
            with self.assertRaises(OperationsError): bad.credential()

    def test_transport_bounds_and_no_implicit_network(self):
        calls = []
        def ok(url, headers, timeout, redirects):
            calls.append((url, timeout, redirects)); return 200, b'{"ok":true}', {}
        transport = BoundedLiveReadOnlyTransport("https://fixture.invalid", ok)
        self.assertEqual(json.loads(transport.get("/schedule")), {"ok": True})
        self.assertEqual(calls, [("https://fixture.invalid/schedule", 5, False)])
        with self.assertRaises(OperationsError): BoundedLiveReadOnlyTransport("http://fixture.invalid", ok)
        cases=((302,b"{}","transport-redirect"),(500,b"{}","transport-status"),(200,b"not-json","malformed-response"),(200,b"1","incomplete-response"),(200,b"x"*(MAX_RESPONSE_BYTES+1),"transport-oversized"))
        for status, body, code in cases:
            item=BoundedLiveReadOnlyTransport("https://fixture.invalid",lambda *a,status=status,body=body:(status,body,{}))
            with self.assertRaisesRegex(OperationsError,code): item.get("/x")

    def test_market_discovery_exactly_one_home_yes(self):
        at=datetime(2026,9,6,tzinfo=timezone.utc)
        valid=KalshiMarketCandidate("m","s","e","h","a",at,"winner:e:h","h","open")
        args=dict(canonical_event_id="e",home_participant_id="h",away_participant_id="a",scheduled_start=at,proposition_id="winner:e:h")
        self.assertEqual(discover_unique_home_yes_market(candidates=(valid,),**args),valid)
        for candidates in ((),(valid,replace(valid,market_id="m2")),(replace(valid,provider="foreign"),),(replace(valid,yes_participant_id="a"),),(replace(valid,state="closed"),),(replace(valid,scheduled_start=at+timedelta(seconds=1)),)):
            with self.assertRaisesRegex(OperationsError,"market-discovery-ambiguous"): discover_unique_home_yes_market(candidates=candidates,**args)

    def test_refresh_and_rehearsal_are_byte_deterministic(self):
        self.assertFalse(classify_refresh({"x":1},{"x":1}).changed)
        self.assertTrue(classify_refresh({"x":1},{"x":2}).changed)
        self.assertEqual(run().encode(),run().encode())

    def test_offline_rehearsal_cannot_open_a_network_socket(self):
        original = socket.create_connection
        socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network prohibited"))
        try: self.assertIn('"network":"fixture-injected-only"', run())
        finally: socket.create_connection = original

    def test_activated_namespace_requires_exact_boundary_and_is_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            values=dict(config_id="fixture",namespace="prospective",mode=OperatingMode.ACTIVATED,
                primary_root=root/"activated/prospective/primary",secondary_root=root/"activated/prospective/secondary",
                provider_base_url="https://fixture.invalid",retry_policy=RetryPolicy(1,1,1,(),0),lock_timeout_seconds=1,
                log_root=root/"logs",activation_at=APPROVED_ACTIVATION_AT)
            config=DeploymentConfig(**values); self.assertIn("operations-config:",config.identity)
            with self.assertRaises(OperationsError): replace(config,activation_at=None)
            dry=replace(config,mode=OperatingMode.DRY_RUN,primary_root=root/"dry-run/prospective/primary",secondary_root=root/"dry-run/prospective/secondary",activation_at=None)
            with self.assertRaisesRegex(OperationsError,"promotion-prohibited"): NamespaceArchive(config).reject_promotion(NamespaceArchive(dry))

    def test_official_kalshi_signing_shape_is_explicit_and_sanitized(self):
        captured=[]
        signer=KalshiRequestSigner("public-key-id",StaticCredentialProvider(b"fixture-private-key"),lambda key,message:(captured.append((key,message)) or b"fixture-signature"))
        headers=signer.headers("GET","/trade-api/v2/markets?limit=2",1700000000000)
        self.assertEqual(captured[0][1],b"1700000000000GET/trade-api/v2/markets")
        self.assertEqual(set(headers),{"KALSHI-ACCESS-KEY","KALSHI-ACCESS-TIMESTAMP","KALSHI-ACCESS-SIGNATURE"})
        self.assertNotIn("fixture-private-key",json.dumps(headers))
        with self.assertRaises(OperationsError):signer.headers("POST","/trade-api/v2/markets",1)

    def test_operational_state_health_absence_and_population(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=DeploymentConfig("fixture","health",OperatingMode.ACTIVATED,root/"activated/health/primary",root/"activated/health/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",activation_at=APPROVED_ACTIVATION_AT)
            archive=NamespaceArchive(config);rebuild_index(archive);sync_secondary(archive);state=OperationalState(root/"state");at=APPROVED_ACTIVATION_UTC+timedelta(minutes=1)
            absent=health_from_operational_state(archive=archive,state=state,trusted_at=at,free_disk=lambda _:1_000_000_000)
            self.assertFalse(absent.ready);self.assertIsNone(absent.provider_calls)
            state.append(OperationalHeartbeat("1","capture-prospective",at,at,"success",1,1,1,None));state.append(OperationalHeartbeat("1","sync-secondary",at,at,"success",0,0,0,None))
            for command in ("refresh-supporting","reconcile-outcomes","maintain"):state.append(OperationalHeartbeat("1",command,at,at,"success",0,0,0,None))
            populated=health_from_operational_state(archive=archive,state=state,trusted_at=at,free_disk=lambda _:1_000_000_000)
            self.assertTrue(populated.ready);self.assertEqual(populated.provider_calls,1)
            self.assertFalse(health_from_operational_state(archive=archive,state=state,trusted_at=at,free_disk=lambda _:1).ready)
            state.append(OperationalHeartbeat("1","health-report",at+timedelta(days=2),at+timedelta(days=2),"success",0,0,0,None))
            self.assertFalse(health_from_operational_state(archive=archive,state=state,trusted_at=at+timedelta(days=2),free_disk=lambda _:1_000_000_000).ready)
            with self.assertRaisesRegex(OperationsError,"future-dated"):health_from_operational_state(archive=archive,state=state,trusted_at=at,free_disk=lambda _:1_000_000_000)
            with self.assertRaisesRegex(OperationsError,"secret-material"):state.append(OperationalHeartbeat("1","x",at,at,"failed",0,0,0,"password-leak"))

    def test_maintenance_is_fail_closed_and_rebuilds_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=DeploymentConfig("maintain","maintain",OperatingMode.ACTIVATED,root/"activated/maintain/primary",root/"activated/maintain/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",activation_at=APPROVED_ACTIVATION_AT);at=APPROVED_ACTIVATION_UTC
            result=execute("maintain",config,clock=lambda:at);self.assertEqual((result["inspection"],result["index_state"]),("verified","healthy"))
            archive=NamespaceArchive(config);orphan=archive.raw_root/"ff"/"orphan";orphan.parent.mkdir(parents=True,exist_ok=True);orphan.write_bytes(b"x")
            with self.assertRaisesRegex(OperationsError,"integrity-unsafe"):execute("maintain",config,clock=lambda:at+timedelta(seconds=1))

    def test_malformed_or_tampered_heartbeat_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state=OperationalState(Path(directory));(Path(directory)/("20260905T000000.000000Z-"+"0"*64+".json")).write_text("{}")
            with self.assertRaisesRegex(OperationsError,"heartbeat-corrupt"):state.entries()

    def test_render_all_jobs_with_absolute_safe_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            from inspect_forecast_standalone_activation import fixtures
            root=Path(directory);config_path=root/"activated.json";repo=Path(__file__).resolve().parents[1];fixture=root/"fixtures";fixture.mkdir();mlb,catalog,book=fixtures();(fixture/"mlb.json").write_bytes(mlb);(fixture/"kalshi.json").write_bytes(catalog);(fixture/"orderbook.json").write_bytes(book);_,protocol=canonical_prospective_authority();trusted="2026-09-05T00:06:06-04:00"
            material={"activation_at":"2026-09-05T00:00:00-04:00","config_id":"render","fixture_response_path":str(fixture),"lock_timeout_seconds":1,"log_root":str(root/"logs"),"mode":"activated","namespace":"render","primary_root":str(root/"activated/render/primary"),"provider_base_url":"https://fixture.invalid","research_protocol_ids":[protocol.standalone_probability_source_protocol_id],"retry_policy":{"maximum_attempts":1,"request_timeout_seconds":1,"total_timeout_seconds":1,"backoff_seconds":[],"maximum_retry_after_seconds":0},"schedule_parameters":{"fixture_trusted_at":trusted},"secondary_root":str(root/"activated/render/secondary")}
            config_path.write_text(json.dumps(material));config=DeploymentConfig.from_json(config_path);execute("initialize-activation",config,clock=lambda:datetime(2026,8,28,tzinfo=timezone.utc));paths=render_launchd_jobs(repository_root=repo,python_executable=Path(__import__('sys').executable),config_path=config_path,output_root=root/"rendered")
            self.assertEqual(len(paths),6)
            for path in paths:
                value=plistlib.loads(Path(path).read_bytes());self.assertTrue(all(Path(x).is_absolute() for x in value["ProgramArguments"] if "/" in x));self.assertEqual(value["ProgramArguments"][3],str(config_path.resolve()))
                completed=subprocess.run(value["ProgramArguments"],cwd="/",capture_output=True,text=True,check=False)
                self.assertEqual(completed.returncode,0,(completed.stdout,completed.stderr));self.assertNotIn("fixture-private",completed.stdout+completed.stderr)
            with self.assertRaisesRegex(OperationsError,"absolute"):render_launchd_jobs(repository_root=Path("."),python_executable=Path(__import__('sys').executable),config_path=config_path,output_root=root/"other")

    def test_activation_precheck_does_not_freeze_downstream_clock(self):
        class Archive: config=type("Config",(),{"identity":"id","namespace":"n"})()
        values=iter((APPROVED_ACTIVATION_AT,APPROVED_ACTIVATION_AT,APPROVED_ACTIVATION_AT+timedelta(seconds=2),APPROVED_ACTIVATION_AT+timedelta(seconds=5)))
        seen=[]
        def downstream(*,archive,transport_factory,clock,observation_adapter=None):
            seen.extend((clock(),clock(),clock()))
            from forecast_standalone_operations import ProspectiveDiscoveryResult
            return ProspectiveDiscoveryResult("id","n",seen[0],(),0,(),(),"no-due-work")
        with patch("forecast_standalone_activation.resolve_activated_authority",return_value=(object(),object())),patch("forecast_standalone_activation.discover_and_capture_prospective",side_effect=downstream):
            invoke_activated_prospective(archive=Archive(),transport_factory=lambda *a:None,clock=lambda:next(values))
        self.assertEqual(seen,[APPROVED_ACTIVATION_AT,APPROVED_ACTIVATION_AT+timedelta(seconds=2),APPROVED_ACTIVATION_AT+timedelta(seconds=5)])
        early=iter((APPROVED_ACTIVATION_AT-timedelta(microseconds=1),APPROVED_ACTIVATION_AT+timedelta(seconds=1)))
        with patch("forecast_standalone_activation.resolve_activated_authority",return_value=(object(),object())),patch("forecast_standalone_activation.discover_and_capture_prospective") as capture:
            result=invoke_activated_prospective(archive=Archive(),transport_factory=lambda *a:None,clock=lambda:next(early))
        self.assertEqual(result.provider_request_count,0);capture.assert_not_called()

    def test_canonical_activation_initialization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);activation,protocol=canonical_prospective_authority();config=DeploymentConfig("init","init",OperatingMode.ACTIVATED,root/"activated/init/primary",root/"activated/init/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),activation_at=APPROVED_ACTIVATION_AT);archive=NamespaceArchive(config);at=datetime(2026,8,28,tzinfo=timezone.utc)
            one=initialize_activation(archive,at);two=initialize_activation(archive,at)
            self.assertEqual(one,two);self.assertEqual(len(archive.entries()),2)
            with self.assertRaisesRegex(OperationsError,"configuration does not name canonical"):initialize_activation(NamespaceArchive(replace(config,research_protocol_ids=("foreign",))),at)

    def test_live_shaped_orderbook_raw_to_canonical(self):
        from market_contracts import MarketSide,ProviderMarketSeries,SideSemantic
        from event_contracts import Provenance
        at=APPROVED_ACTIVATION_UTC;event="mlb:event";proposition=f"winner:{event}:home";prov=Provenance("kalshi","KX-M",event,at)
        series=ProviderMarketSeries("market-series:kalshi:KX-M","kalshi","KX-M","KX-M",proposition,SideSemantic(MarketSide.YES,proposition,"home",True,"Home"),SideSemantic(MarketSide.NO,proposition,"away",False,"Away"),"Home wins",None,"KX-E",at,at+timedelta(days=1),("Pays $1",),prov)
        schedule=type("Schedule",(),{"canonical_event_id":event})();raw=b'{"orderbook_fp":{"yes_dollars":[["0.4000","2.00"],["0.4000","3.00"]],"no_dollars":[["0.3000","4.00"]]}}';observation=adapt_kalshi_orderbook(payload=json.loads(raw),raw=raw,started_at=at,completed_at=at+timedelta(seconds=1),series=series,schedule=schedule)
        self.assertEqual((observation.quotes.yes_bid,observation.quotes.yes_ask),(Decimal("0.4000"),Decimal("0.7000")));self.assertEqual(len(observation.order_book),3);self.assertEqual({x.acquisition_side.value for x in observation.order_book},{"yes","no"});self.assertTrue(all(x.evidence_kind.value=="derived-from-opposite-bid" for x in observation.order_book));self.assertEqual(observation.component_evidence[0].raw_response_sha256,__import__('hashlib').sha256(raw).hexdigest())
        bad=(b'{"orderbook_fp":{"yes_dollars":[],"no_dollars":[["0.3","1.00"]]}}',b'{"orderbook_fp":{"yes_dollars":[["1.1000","1.00"]],"no_dollars":[["0.3000","1.00"]]}}',b'{"legacy":{}}')
        for body in bad:
            with self.assertRaises(OperationsError):adapt_kalshi_orderbook(payload=json.loads(body),raw=body,started_at=at,completed_at=at,series=series,schedule=schedule)

    def test_complete_catalog_pagination_and_conflicts(self):
        bodies={"":b'{"markets":[{"ticker":"B"}],"cursor":"next"}',"next":b'{"markets":[{"ticker":"A"}],"cursor":""}'};calls=[]
        pages=acquire_kalshi_catalog_pages(lambda cursor:(calls.append(cursor) or bodies[cursor]))
        self.assertEqual(calls,["","next"]);self.assertEqual([x.endpoint for x in pages],[encoded_kalshi_catalog_path(""),encoded_kalshi_catalog_path("next")]);self.assertEqual([x["ticker"] for x in json.loads(merge_kalshi_catalog_pages(reversed(pages)))["markets"]],["A","B"])
        with self.assertRaisesRegex(OperationsError,"loop"):acquire_kalshi_catalog_pages(lambda cursor:b'{"markets":[],"cursor":"x"}' if not cursor else b'{"markets":[],"cursor":"x"}')
        conflict=(KalshiCatalogPage(0,"","x",b"",({"ticker":"A","title":"one"},)),KalshiCatalogPage(1,"x","",b"",({"ticker":"A","title":"two"},)))
        with self.assertRaisesRegex(OperationsError,"conflict"):merge_kalshi_catalog_pages(conflict)

    def test_eastern_obligation_date_rule(self):
        instant=datetime(2026,9,6,2,tzinfo=timezone.utc) # September 5 in New York
        self.assertEqual(required_mlb_query_dates(trusted_at=instant,purpose="schedule"),(datetime(2026,9,5).date(),datetime(2026,9,6).date()))
        self.assertEqual(required_mlb_query_dates(trusted_at=instant,purpose="outcomes"),(datetime(2026,9,4).date(),datetime(2026,9,5).date()))

    def test_unresolved_outcomes_outlive_correction_lookback(self):
        from outcome_contracts import OutcomeStatus
        at=datetime(2026,9,20,16,tzinfo=timezone.utc)
        def history(day,unresolved,status=OutcomeStatus.SCHEDULED):return SimpleNamespace(latest=SimpleNamespace(scheduled_start=datetime(2026,9,day,23,tzinfo=timezone.utc),unresolved=unresolved,provider_status=status))
        dates=required_mlb_query_dates(trusted_at=at,histories=(history(1,True),history(1,True),history(2,True),history(3,False),history(18,False),history(4,True,OutcomeStatus.CANCELLED)),purpose="outcomes")
        self.assertIn(datetime(2026,9,1).date(),dates);self.assertIn(datetime(2026,9,2).date(),dates);self.assertNotIn(datetime(2026,9,3).date(),dates);self.assertIn(datetime(2026,9,18).date(),dates);self.assertNotIn(datetime(2026,9,4).date(),dates);self.assertEqual(dates,tuple(sorted(set(dates))))

    def test_opaque_cursor_is_encoded_without_query_injection(self):
        for cursor in ("a+b=c%&/ two","雪 +&="):
            path=encoded_kalshi_catalog_path(cursor);query=parse_qs(urlparse(path).query,keep_blank_values=True)
            self.assertEqual(query,{"series_ticker":[KALSHI_MLB_SERIES_TICKER],"status":["open"],"limit":[str(KALSHI_CATALOG_PAGE_LIMIT)],"cursor":[cursor]});self.assertEqual(path.count("series_ticker="),1);self.assertEqual(path.count("status="),1);self.assertEqual(path.count("limit="),1);self.assertEqual(path.count("cursor="),1)
        self.assertEqual((KALSHI_MLB_SERIES_TICKER,KALSHI_CATALOG_PAGE_LIMIT),("KXMLBGAME",100))
        self.assertEqual(parse_qs(urlparse(encoded_kalshi_catalog_path("")).query),{"series_ticker":[KALSHI_MLB_SERIES_TICKER],"status":["open"],"limit":[str(KALSHI_CATALOG_PAGE_LIMIT)]})

    def test_acquisition_manifest_replay_rejects_page_and_union_conflicts(self):
        from inspect_forecast_standalone_activation import fixtures
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);mlb,catalog,_=fixtures();market=json.loads(catalog)["markets"][0];raw1=json.dumps({"markets":[market],"cursor":"opaque"},sort_keys=True,separators=(",",":")).encode();raw2=b'{"cursor":"","markets":[]}'
            pages=(KalshiCatalogPage(0,"","opaque",raw1,(market,)),KalshiCatalogPage(1,"opaque","",raw2,()))
            _,protocol=canonical_prospective_authority();config=DeploymentConfig("manifest","manifest",OperatingMode.ACTIVATED,root/"activated/manifest/primary",root/"activated/manifest/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),activation_at=APPROVED_ACTIVATION_AT);archive=NamespaceArchive(config);initialize_activation(archive,datetime(2026,8,28,tzinfo=timezone.utc))
            refresh_supporting_from_raw(archive=archive,mlb_raw=mlb,kalshi_raw=catalog,catalog_pages=pages,mlb_pages=(mlb,),collected_at=datetime(2026,9,5,3,59,tzinfo=timezone.utc))
            bundles=[]
            for entry in archive.entries():
                value=json.loads(archive.read_verified("normalized",entry["normalized_object_id"]))
                if value.get("record_kind")=="pr17c1-acquisition-bundle" and value.get("provider")=="kalshi":bundles.append(value)
            self.assertEqual(len(bundles),1);bundle=bundles[0];self.assertTrue(verify_acquisition_bundle(archive,bundle))
            missing=copy.deepcopy(bundle);missing["pages"].pop()
            altered=copy.deepcopy(bundle);altered["normalized_union_sha256"]="0"*64
            foreign=copy.deepcopy(bundle);foreign["acquisition_id"]="provider-acquisition:foreign"
            duplicate=copy.deepcopy(bundle);duplicate["pages"].append(copy.deepcopy(duplicate["pages"][-1]))
            for value in (missing,altered,foreign,duplicate):
                with self.assertRaises(OperationsError):verify_acquisition_bundle(archive,value)

    def test_acquisition_replay_requires_canonical_kalshi_endpoint(self):
        from inspect_forecast_standalone_activation import fixtures
        variants=("/markets?status=open&limit=100","/markets?series_ticker=FOREIGN&status=open&limit=100","/markets?series_ticker=KXMLBGAME&status=open&limit=99","/markets?series_ticker=KXMLBGAME&status=closed&limit=100",encoded_kalshi_catalog_path("foreign"),encoded_kalshi_catalog_path("")+"&extra=1","/markets?status=open&series_ticker=KXMLBGAME&limit=100")
        for endpoint in variants:
            with self.subTest(endpoint=endpoint),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);catalog=fixtures()[1];at=datetime(2026,9,5,3,59,tzinfo=timezone.utc);config=DeploymentConfig("endpoint","endpoint",OperatingMode.ACTIVATED,root/"activated/endpoint/primary",root/"activated/endpoint/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",activation_at=APPROVED_ACTIVATION_AT);archive=NamespaceArchive(config);page=ProviderPageAcquisition("",endpoint,catalog,at,at,0,"kalshi")
                bundle_id=publish_verified_acquisition(archive=archive,provider="kalshi",union_raw=catalog,pages=(page,),contracts=(),collected_at=at,protocol_id=None,command="refresh-supporting")["manifest_entry_id"];bundle=json.loads(archive.read_verified("normalized",next(x["normalized_object_id"] for x in archive.entries() if x["manifest_entry_id"]==bundle_id)))
                with self.assertRaisesRegex(OperationsError,"canonical discovery authority"):verify_acquisition_bundle(archive,bundle)

    def test_execute_passes_one_trusted_start_to_loaders(self):
        from inspect_forecast_standalone_activation import fixtures
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);mlb,catalog,_=fixtures();_,protocol=canonical_prospective_authority();at=datetime(2026,9,5,3,59,59,tzinfo=timezone.utc)
            config=DeploymentConfig("clock","clock",OperatingMode.ACTIVATED,root/"activated/clock/primary",root/"activated/clock/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),activation_at=APPROVED_ACTIVATION_AT);initialize_activation(NamespaceArchive(config),datetime(2026,8,28,tzinfo=timezone.utc));seen=[]
            execute("refresh-supporting",config,clock=lambda:at,supporting_loader=lambda trusted:(seen.append(trusted) or (mlb,catalog)))
            execute("reconcile-outcomes",config,clock=lambda:at,outcome_loader=lambda trusted:(seen.append(trusted) or (mlb,(mlb,))))
            self.assertEqual(seen,[at,at]);entries=OperationalState(config.log_root/"operational-state").entries();self.assertTrue(all(x.started_at==at and x.completed_at==at for x in entries))

    def test_page_chronology_and_partial_group_recovery_fail_closed(self):
        from inspect_forecast_standalone_activation import fixtures
        from forecast_standalone_operations import reconcile_archive,replay_pr17_archive
        with tempfile.TemporaryDirectory() as directory:
            from forecast_standalone_activation import ProviderPageAcquisition
            root=Path(directory);mlb,catalog,_=fixtures();_,protocol=canonical_prospective_authority();start=datetime(2026,9,5,3,59,59,tzinfo=timezone.utc);end=start+timedelta(seconds=2)
            config=DeploymentConfig("crash","crash",OperatingMode.ACTIVATED,root/"activated/crash/primary",root/"activated/crash/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),activation_at=APPROVED_ACTIVATION_AT);archive=NamespaceArchive(config);initialize_activation(archive,datetime(2026,8,28,tzinfo=timezone.utc));page=ProviderPageAcquisition("",encoded_kalshi_catalog_path(""),catalog,start,end,0,"kalshi")
            with archive.mutation_lock():
                with self.assertRaisesRegex(OperationsError,"injected-acquisition-interruption"):publish_verified_acquisition(archive=archive,provider="kalshi",union_raw=catalog,pages=(page,),contracts=(),collected_at=start,protocol_id=protocol.standalone_probability_source_protocol_id,command="refresh-supporting",fail_after_pages=1)
            integrity=reconcile_archive(archive);self.assertFalse(integrity.healthy);self.assertTrue(integrity.partial)
            with self.assertRaisesRegex(OperationsError,"archive-integrity-failure"):replay_pr17_archive(archive,analysis_boundary=end)
            from forecast_standalone_operations import rebuild_index,reconcile_incomplete_acquisitions,sync_secondary
            with self.assertRaisesRegex(OperationsError,"archive-integrity-failure"):rebuild_index(archive)
            artifact_ids=reconcile_incomplete_acquisitions(archive,reconciled_at=end+timedelta(seconds=1));self.assertEqual(len(artifact_ids),1)
            self.assertTrue(reconcile_archive(archive).healthy);self.assertEqual(reconcile_incomplete_acquisitions(archive,reconciled_at=end+timedelta(seconds=2)),())
            later_start=end+timedelta(seconds=3);mlb_end=later_start+timedelta(seconds=1);later_end=mlb_end+timedelta(seconds=1);replacement=ProviderPageAcquisition("2026-09-05","https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-09-05",mlb,later_start,mlb_end);catalog_page=KalshiCatalogPage(0,"","",catalog,tuple(json.loads(catalog)["markets"]),mlb_end,later_end,encoded_kalshi_catalog_path(""))
            result=refresh_supporting_from_raw(archive=archive,mlb_raw=mlb,kalshi_raw=catalog,collected_at=later_start,mlb_pages=(replacement,),catalog_pages=(catalog_page,));self.assertNotEqual(result["mlb_manifest_id"],artifact_ids[0]);self.assertTrue(reconcile_archive(archive).healthy)
            state=replay_pr17_archive(archive,analysis_boundary=later_end);self.assertTrue(state.bucket("outcome_histories"));rebuild_index(archive);self.assertEqual(sync_secondary(archive)["conflicts"],0)
            with self.assertRaisesRegex(OperationsError,"chronology"):ProviderPageAcquisition("",encoded_kalshi_catalog_path(""),catalog,end,start)

    def test_prospective_scope_is_not_ordinary_game_gated(self):
        _,protocol=canonical_prospective_authority();scope=dict(protocol.scope_rule.parameters)
        self.assertEqual(scope["scheduled_state_population"],"complete");self.assertNotIn("ordinary_game",scope)

    def test_live_orderbook_reaches_complete_probability_derivation(self):
        from inspect_forecast_standalone_research import build_synthetic_bundle
        from forecast_standalone_research import CapturedValid,ProspectiveCaptureAttempt,SkippedAfterSuccess,create_standalone_market_probability_derivation,reconcile_prospective_snapshot
        g=build_synthetic_bundle();schedule=next(x for x in g["legacy"]["outcome_history"].observations if x.observation_id==g["opportunity"].schedule_observation_id);series=g["series"];started=g["attempts"][1].invocation_at
        raw=b'{"orderbook_fp":{"yes_dollars":[["0.4000","2.00"],["0.4000","3.00"]],"no_dollars":[["0.3000","4.00"]]}}'
        observation=adapt_kalshi_orderbook(payload=json.loads(raw),raw=raw,started_at=started,completed_at=started,series=series,schedule=schedule)
        old=g["attempts"][1];values={name:getattr(old,name) for name in old.__dataclass_fields__ if name not in ("prospective_capture_attempt_id","input_digest","schema_version","identity_algorithm_version","result")}
        success=ProspectiveCaptureAttempt.create(**values,result=CapturedValid("raw:fixture",__import__('hashlib').sha256(raw).hexdigest(),observation.observation_id))
        attempts=[g["attempts"][0],success]
        for old in g["attempts"][2:]:
            values={name:getattr(old,name) for name in old.__dataclass_fields__ if name not in ("prospective_capture_attempt_id","input_digest","schema_version","identity_algorithm_version","result")}
            attempts.append(ProspectiveCaptureAttempt.create(**values,result=SkippedAfterSuccess(success.prospective_capture_attempt_id)))
        snapshot=reconcile_prospective_snapshot(protocol=g["prospective"],opportunity=g["opportunity"],activation=g["activation"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],analysis_boundary=g["snapshot"].effective_at,attempts=attempts,window_closed_at=g["prospective_target"]+timedelta(minutes=5),provenance=g["provenance"])
        derivation=create_standalone_market_probability_derivation(protocol=g["prospective"],activation=g["activation"],opportunity=g["opportunity"],eligibility_context=g["prospective_context"],eligibility_result=g["prospective_eligibility"],schedule_history=g["legacy"]["outcome_history"],analysis_boundary=snapshot.effective_at,snapshot=snapshot,snapshots=(snapshot,),attempts=attempts,observation=observation,market_observations=(observation,),series=series,effective_at=snapshot.effective_at,provenance=g["provenance"])
        self.assertEqual((derivation.bid.canonical_price,derivation.offer.canonical_price,derivation.midpoint,derivation.complement_probability),(Decimal("0.4000"),Decimal("0.7000"),Decimal("0.5500"),Decimal("0.4500")))
        self.assertEqual(derivation.bid.quantity,Decimal("5.00"));self.assertEqual(derivation.offer.quantity,Decimal("4.00"))


if __name__ == "__main__": unittest.main()
