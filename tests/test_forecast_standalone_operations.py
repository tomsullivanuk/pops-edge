import json
import multiprocessing
import os
import plistlib
import sqlite3
import subprocess
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from forecast_standalone_operations import (
    APPROVED_ACTIVATION_AT, COMMAND_CAPABILITIES, DesignAuthority, DeploymentConfig, Disposition,
    HTTPResponse, NamespaceArchive, OperatingMode, OperationsError, RetryPolicy,
    acquire_prospective_once, acquire_with_retries, capture_prospective,
    archive_pr17_authority,discover_and_capture_prospective,discover_and_acquire_retrospective,
    authoritative_entries,index_health, inspect_archive, preflight, rebuild_index,reconcile_archive,replay_pr17_archive,request_identity,
    run_supporting_acquisition, secondary_status, status, sync_secondary,
    validate_kalshi_payload, validate_pagination,
)

UTC=timezone.utc
NOW=datetime(2026,8,27,12,tzinfo=UTC)


class SequenceTransport:
    def __init__(self,*items):self.items=list(items);self.calls=[]
    def request(self,method,url,*,params,timeout,allow_redirects):
        self.calls.append((method,url,dict(params),timeout,allow_redirects))
        item=self.items.pop(0)
        if isinstance(item,BaseException):raise item
        return item


class SequenceClock:
    def __init__(self,*values):self.values=list(values);self.calls=[]
    def __call__(self):
        value=self.values.pop(0);self.calls.append(value);return value


def payload(kind="order-book",**changes):
    content={"yes":[{"price":45,"quantity":2}],"no":[{"price":54,"quantity":3}]}
    provider="kalshi"
    if kind=="historical-candles":content={"pages":[{"position":0,"cursor":"initial","next_cursor":None,"terminal":True,"candle_ids":["c1"]}]}
    elif kind=="schedule":provider="mlb-stats-api";content={"participant_ids":["away","home"],"status":"scheduled"}
    elif kind=="classification":provider="mlb-stats-api";content={"ordinary_game":True,"native_event_id":"1","event_phase":"regular-season","game_type":"regular","home_participant_id":"home","away_participant_id":"away"}
    elif kind=="outcome":provider="mlb-stats-api";content={"status":"final","winner_participant_id":"home"}
    value={"provider":"kalshi","kind":kind,"canonical_event_id":"mlb:1","provider_market_id":"KX-1",
           "scheduled_start":"2026-08-27T18:00:00Z","effective_at":"2026-08-27T12:00:00Z",
           "payload":content}
    value["provider"]=provider
    value.update(changes);return value


def response(kind="order-book",status_code=200,headers=None,**changes):
    return HTTPResponse(status_code,json.dumps(payload(kind,**changes),sort_keys=True).encode(),headers or {})


def validator(kind="order-book"):
    return lambda value:validate_kalshi_payload(value,expected_kind=kind,expected={"canonical_event_id":"mlb:1","provider_market_id":"KX-1"})


def hold_lock(config,ready):
    archive=NamespaceArchive(config)
    with archive.mutation_lock():ready.set();__import__("time").sleep(30)


class OperationsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)
        self.config=DeploymentConfig("fixture-config","fixture",OperatingMode.DRY_RUN,root/"dry-run"/"fixture"/"primary",
            root/"dry-run"/"fixture"/"secondary","https://fixture.invalid",RetryPolicy(3,2,10,(1,2),4),.05,
            root/"logs",schedule_parameters=(("prospective_interval_seconds","60"),))
        self.archive=NamespaceArchive(self.config)
    def tearDown(self):self.temp.cleanup()

    def entry_values(self,disposition=Disposition.SUCCESS):
        return dict(command="acquire-retrospective",invocation_id="invocation:1",provider_id="kalshi",endpoint="fixture://candles",
            sanitized_request_id="request:1",acquired_at=NOW,provider_effective_at=NOW,predecessor_id=None,correction_reason=None,
            disposition=disposition,protocol_id="protocol:retro",design_authority=DesignAuthority.RETROSPECTIVE,diagnostics=())

    def commit(self,body=b'{"fixture":true}'):
        return self.archive.commit(raw_body=body,normalized={"schema_version":"1","value":"fixture"},entry_values=self.entry_values())

    def seed_prospective(self):
        from forecast_standalone_research import create_standalone_eligibility_authority
        from inspect_forecast_standalone_research import build_synthetic_bundle
        g=build_synthetic_bundle();at=g["observation"].collected_at
        context,result=create_standalone_eligibility_authority(protocol=g["prospective"],opportunity=g["opportunity"],outcome_history=g["legacy"]["outcome_history"],classification=g["prospective_classification"],classifications=(g["prospective_classification"],),analysis_boundary=g["prospective_target"],provenance=g["provenance"])
        self.config=replace(self.config,research_protocol_ids=(g["prospective"].standalone_probability_source_protocol_id,));self.archive=NamespaceArchive(self.config)
        archive_pr17_authority(self.archive,(g["activation"],g["prospective"],g["opportunity"],g["prospective_classification"],context,result,g["legacy"]["outcome_history"],g["series"]),recorded_at=at)
        return g,at

    def prospective_response_at(self,g,at):
        provenance=replace(g["observation"].provenance,collected_at=at)
        components=tuple(replace(item,collected_at=at) for item in g["observation"].component_evidence)
        observation=replace(g["observation"],collected_at=at,component_evidence=components,provenance=provenance)
        return HTTPResponse(200,json.dumps({"contract_json":observation.to_json()}).encode(),{})

    def select_namespace(self,label):
        root=Path(self.temp.name);self.config=replace(self.config,namespace=label,primary_root=root/"dry-run"/label/"primary",secondary_root=root/"dry-run"/label/"secondary")

    def test_01_config_identity_and_namespace_isolation(self):
        self.assertEqual(self.config.identity,self.config.identity)
        bad=Path(self.temp.name)/"shared"
        with self.assertRaises(OperationsError):replace(self.config,primary_root=bad,secondary_root=bad)
        with self.assertRaises(OperationsError):replace(self.config,primary_root=Path(self.temp.name)/"primary")

    def test_02_activated_configuration_requires_approved_boundary(self):
        root=Path(self.temp.name)
        with self.assertRaisesRegex(OperationsError,"activation-authority-invalid"):
            replace(self.config,mode=OperatingMode.ACTIVATED,primary_root=root/"activated"/"fixture"/"primary",secondary_root=root/"activated"/"fixture"/"secondary")
        active=replace(self.config,mode=OperatingMode.ACTIVATED,primary_root=root/"activated"/"fixture"/"primary",secondary_root=root/"activated"/"fixture"/"secondary",activation_at=APPROVED_ACTIVATION_AT)
        self.assertEqual(active.activation_at,APPROVED_ACTIVATION_AT)

    def test_03_promotion_and_cross_namespace_rejected(self):
        other=replace(self.config,namespace="other",primary_root=Path(self.temp.name)/"dry-run"/"other"/"primary",secondary_root=Path(self.temp.name)/"dry-run"/"other"/"secondary")
        with self.assertRaisesRegex(OperationsError,"promotion-prohibited"):NamespaceArchive(other).reject_promotion(self.archive)
        with self.assertRaisesRegex(OperationsError,"promotion-prohibited"):self.archive.reject_promotion(self.archive)

    def test_04_create_only_idempotent_and_conflict(self):
        one=self.commit();two=self.commit();self.assertEqual(one,two);self.assertEqual(len(self.archive.entries()),1)
        path=self.archive._path("raw",f"raw:{one.raw_object_sha256}");path.chmod(0o644);path.write_bytes(b"corrupt")
        with self.assertRaisesRegex(OperationsError,"immutable-conflict"):self.commit()

    def test_05_raw_normalized_and_manifest_verify(self):
        item=self.commit();self.assertEqual(self.archive.read_verified("raw",f"raw:{item.raw_object_sha256}"),b'{"fixture":true}')
        self.assertEqual(self.archive.entries()[0]["manifest_entry_id"],item.manifest_entry_id)

    def test_06_partial_files_ignored_and_reported(self):
        self.archive._ensure_mutable();(self.archive.temporary_root/"dead.partial").write_bytes(b"partial")
        self.assertEqual(self.archive.entries(),());self.assertIn(".partial/dead.partial",self.archive.temporary_files())

    def test_07_manifest_corruption_detected(self):
        item=self.commit();path=self.archive._path("manifest",item.manifest_entry_id);path.chmod(0o644);path.write_text("{}")
        with self.assertRaisesRegex(OperationsError,"manifest-corrupt"):self.archive.entries()

    def test_08_prospective_exactly_one_request_success(self):
        transport=SequenceTransport(response())
        result=acquire_prospective_once(transport=transport,endpoint="fixture://book",request={},timeout_seconds=2,now=lambda:NOW,validator=validator())
        self.assertEqual(result.disposition,Disposition.SUCCESS);self.assertEqual(len(transport.calls),1);self.assertFalse(transport.calls[0][-1])

    def test_09_prospective_failure_categories_never_retry(self):
        cases=((TimeoutError(),Disposition.TIMEOUT),(ConnectionError(),Disposition.CONNECTION_FAILURE),(HTTPResponse(429,b"x",{}),Disposition.RATE_LIMITED),(HTTPResponse(503,b"x",{}),Disposition.PROVIDER_ERROR),(HTTPResponse(200,b"{",{}),Disposition.MALFORMED_RESPONSE))
        for item,wanted in cases:
            with self.subTest(wanted=wanted):
                transport=SequenceTransport(item,response());result=acquire_prospective_once(transport=transport,endpoint="x",request={},timeout_seconds=1,now=lambda:NOW,validator=validator())
                self.assertEqual(result.disposition,wanted);self.assertEqual(len(transport.calls),1)

    def test_10_incomplete_and_wrong_authority_rejected(self):
        for value in ({"provider":"kalshi"},payload(provider="other"),payload(provider_market_id="wrong"),payload(payload={"yes":[],"no":[]})):
            with self.subTest(value=value):
                with self.assertRaises(OperationsError):validator()(value)

    def test_10b_all_provider_contract_shapes_validate(self):
        for kind in ("schedule","classification","historical-candles","order-book","outcome"):
            with self.subTest(kind=kind):self.assertEqual(validator(kind)(payload(kind))["kind"],kind)

    def test_11_supporting_retry_chronology_and_retry_after_bound(self):
        clock=[NOW]
        def now():clock[0]+=timedelta(seconds=1);return clock[0]
        delays=[];transport=SequenceTransport(HTTPResponse(429,b"x",{"Retry-After":"99"}),response(status_code=503),response())
        result=acquire_with_retries(transport=transport,endpoint="x",request={},policy=self.config.retry_policy,now=now,sleeper=delays.append,validator=validator())
        self.assertEqual(result.disposition,Disposition.SUCCESS);self.assertEqual([x.attempt for x in result.attempts],[1,2,3]);self.assertEqual(delays,[4,2])

    def test_12_nonretryable_supporting_failure_stops(self):
        transport=SequenceTransport(HTTPResponse(404,b"x",{}),response());result=acquire_with_retries(transport=transport,endpoint="x",request={},policy=self.config.retry_policy,now=lambda:NOW,sleeper=lambda _:None,validator=validator())
        self.assertEqual(len(transport.calls),1);self.assertEqual(result.disposition,Disposition.VALIDATION_FAILURE)

    def test_13_pagination_success_and_input_order_authority(self):
        pages=({"position":0,"cursor":"initial","next_cursor":"b","terminal":False,"candle_ids":["c1"]},{"position":1,"cursor":"b","next_cursor":None,"terminal":True,"candle_ids":["c2"]})
        self.assertEqual(validate_pagination(pages),pages)
        with self.assertRaises(OperationsError):validate_pagination(reversed(pages))

    def test_14_pagination_gaps_cycles_duplicates_and_incomplete(self):
        bad=({"position":0,"cursor":"initial","next_cursor":"initial","terminal":False,"candle_ids":["c1"]},{"position":1,"cursor":"initial","next_cursor":None,"terminal":True,"candle_ids":["c1"]})
        with self.assertRaises(OperationsError):validate_pagination(bad)
        with self.assertRaises(OperationsError):validate_pagination(({"position":0,"cursor":"initial","next_cursor":"x","terminal":False,"candle_ids":[]},))

    def test_15_prospective_authority_discovery_one_request_and_direct_bypass_rejected(self):
        g,at=self.seed_prospective();transport=SequenceTransport(HTTPResponse(200,json.dumps({"contract_json":g["observation"].to_json()}).encode(),{}))
        result=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        self.assertEqual(result.provider_request_count,1);self.assertEqual(len(transport.calls),1);self.assertEqual(result.due_opportunity_ids,(g["opportunity"].research_capture_opportunity_id,))
        repeat=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        self.assertEqual(repeat.provider_request_count,0);self.assertEqual(len(transport.calls),1)
        with self.assertRaisesRegex(OperationsError,"direct-capture-prohibited"):capture_prospective(archive=self.archive,transport=transport,endpoint="x",request={},invoked_at=at,target_at=at,opportunity_id="invented",protocol_id="foreign",now=lambda:at,validator=validator())

    def test_16_failed_then_later_valid_authority_derived_slot(self):
        g,at=self.seed_prospective();transport=SequenceTransport(TimeoutError(),HTTPResponse(200,json.dumps({"contract_json":g["observation"].to_json()}).encode(),{}))
        first=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at-timedelta(minutes=1))
        second=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        self.assertEqual((first.provider_request_count,second.provider_request_count),(1,1));self.assertEqual(len(transport.calls),2)

    def test_17_rebuild_delete_rebuild_equivalence(self):
        self.commit();one=rebuild_index(self.archive);self.assertEqual(index_health(self.archive),("healthy",()))
        self.archive.index_path.unlink();self.assertEqual(index_health(self.archive)[0],"missing")
        two=rebuild_index(self.archive);self.assertEqual(one,two)

    def test_18_index_corruption_stale_and_disagreement(self):
        self.commit();rebuild_index(self.archive);self.archive.index_path.write_bytes(b"bad")
        self.assertEqual(index_health(self.archive)[0],"corrupt")
        rebuild_index(self.archive);db=sqlite3.connect(self.archive.index_path);db.execute("UPDATE metadata SET value='old' WHERE key='builder_version'");db.commit();db.close()
        self.assertEqual(index_health(self.archive)[0],"stale")
        rebuild_index(self.archive);db=sqlite3.connect(self.archive.index_path);db.execute("DELETE FROM manifest");db.commit();db.close()
        self.assertEqual(index_health(self.archive)[0],"disagreement")

    def test_19_secondary_copy_idempotency_lag_conflict_and_unexplained(self):
        self.commit();self.assertGreater(secondary_status(self.archive)["lag"],0);one=sync_secondary(self.archive);self.assertGreater(one["copied"],0)
        two=sync_secondary(self.archive);self.assertGreater(two["identical"],0);self.assertEqual(secondary_status(self.archive)["lag"],0)
        target=next(self.config.secondary_root.glob("raw/*/*"));target.chmod(0o644);target.write_bytes(b"bad")
        self.assertGreater(sync_secondary(self.archive)["conflicts"],0)
        extra=self.config.secondary_root/"raw"/"ff"/"extra";extra.parent.mkdir(parents=True,exist_ok=True);extra.write_bytes(b"x")
        self.assertEqual(secondary_status(self.archive)["unexplained"],1)

    def test_20_lock_is_bounded_and_termination_recovers(self):
        ready=multiprocessing.Event();process=multiprocessing.Process(target=hold_lock,args=(self.config,ready));process.start();self.assertTrue(ready.wait(5))
        with self.assertRaisesRegex(OperationsError,"lock-timeout"):self.commit()
        process.terminate();process.join(5);self.commit()

    def test_21_supporting_command_commits_attempt_chronology(self):
        result,entry=run_supporting_acquisition(archive=self.archive,command="acquire-retrospective",design=DesignAuthority.RETROSPECTIVE,
            transport=SequenceTransport(response("historical-candles")),endpoint="x",request={},invoked_at=NOW,now=lambda:NOW,sleeper=lambda _:None,validator=validator("historical-candles"),protocol_id="protocol:retro")
        self.assertEqual(result.disposition,Disposition.SUCCESS);self.assertTrue(any(item.startswith("attempt:1:") and ":success:" in item for item in entry.diagnostics))

    def test_22_status_preflight_inspection_are_typed_and_read_only(self):
        before=set(Path(self.temp.name).rglob("*"));diagnostic=status(self.archive);after=set(Path(self.temp.name).rglob("*"));self.assertEqual(before,after)
        self.assertFalse(diagnostic.ready);self.assertIn('"schema_version":"1"',diagnostic.to_json())
        self.commit();rebuild_index(self.archive);sync_secondary(self.archive);self.assertTrue(status(self.archive).ready);self.assertTrue(inspect_archive(self.archive).ready)
        self.assertFalse(preflight(self.archive,requested_mode=OperatingMode.ACTIVATED,credentials_configured=False).ready)

    def test_23_secret_structural_exclusion(self):
        for request in ({"Authorization":"x"},{"nested":{"api-key":"x"}},{"credential_value":"x"}):
            with self.assertRaisesRegex(OperationsError,"secret-material"):request_identity(request)
        body=json.dumps(payload(payload={"yes":[{"quantity":1}],"no":[{"quantity":1}],"authorization":"never-store"})).encode()
        result=acquire_prospective_once(transport=SequenceTransport(HTTPResponse(200,body,{})),endpoint="x",request={},timeout_seconds=1,now=lambda:NOW,validator=validator())
        self.assertIsNone(result.raw_body)

    def test_24_cli_capabilities_are_explicit(self):
        self.assertEqual(set(COMMAND_CAPABILITIES),{"acquire-schedule","acquire-classification","acquire-retrospective","capture-prospective","reconcile-outcomes","reconcile-acquisitions","sync-secondary","rebuild-index","status","preflight","inspect"})
        self.assertEqual(COMMAND_CAPABILITIES["status"],"read-only")

    def test_25_launchd_and_shell_templates_parse(self):
        operations=Path(__file__).parents[1]/"operations";root=operations/"launchd"
        example=DeploymentConfig.from_json(operations/"pr17b2.dry-run.config.example.json")
        self.assertEqual((example.mode,example.namespace),(OperatingMode.DRY_RUN,"fixture"))
        for path in root.glob("*.plist"):
            with path.open("rb") as handle:self.assertIsInstance(plistlib.load(handle),dict)
        for path in root.glob("*.sh"):
            self.assertEqual(subprocess.run(["sh","-n",str(path)],check=False).returncode,0)

    def test_26_archive_reconstructs_actual_pr17b1_graph_without_unrelated_bundle(self):
        g,at=self.seed_prospective();state=replay_pr17_archive(self.archive,analysis_boundary=at)
        self.assertEqual(state.bucket("protocols"),(g["prospective"],));self.assertEqual(state.bucket("opportunities"),(g["opportunity"],))
        entry=next(item for item in authoritative_entries(self.archive) if item["normalized_object_id"])
        path=self.archive._path("normalized",entry["normalized_object_id"]);path.chmod(0o644);path.write_bytes(b"{}")
        with self.assertRaises(OperationsError):replay_pr17_archive(self.archive,analysis_boundary=at)

    def test_27_retrospective_archive_acquisition_reconstructs_manifest_and_candle(self):
        from inspect_forecast_standalone_research import build_synthetic_bundle
        from market_contracts import ProviderMarketSeries,SideSemantic,MarketSide
        g=build_synthetic_bundle();at=g["retro_eligibility"].analysis_boundary;proposition=g["retro_schedule"].canonical_event_id
        prop=f"winner:{proposition}:{g['retro_schedule'].home_participant_id}";market_id="synthetic-retro-market"
        series=ProviderMarketSeries(f"market-series:kalshi:{market_id}","kalshi",market_id,market_id,prop,
            SideSemantic(MarketSide.YES,prop,g["retro_schedule"].home_participant_id,True,"home"),SideSemantic(MarketSide.NO,prop,g["retro_schedule"].away_participant_id,False,"away"),"fixture",None,None,None,None,(),g["series"].provenance)
        self.config=replace(self.config,research_protocol_ids=(g["retrospective"].standalone_probability_source_protocol_id,));self.archive=NamespaceArchive(self.config)
        archive_pr17_authority(self.archive,(g["activation"],g["retrospective"],g["retro_opportunity"],g["retro_classification"],g["retro_context"],g["retro_eligibility"],g["retro_history"],series),recorded_at=at)
        body=json.dumps({"pages":[{"position":0,"cursor":"initial","next_cursor":None,"terminal":True,"candles":[{"candle_end_at":g["candle"].candle_end_at.isoformat(),"close_yes_bid":"0.48","close_yes_ask":"0.52"}]}]},sort_keys=True).encode();transport=SequenceTransport(HTTPResponse(200,body,{}))
        created=discover_and_acquire_retrospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at,sleeper=lambda _:None)
        state=replay_pr17_archive(self.archive,analysis_boundary=at);self.assertEqual(len(created),1);self.assertEqual(len(state.bucket("manifests")),1);self.assertEqual(len(state.bucket("candles")),1)
        candle=state.bucket("candles")[0];entry=next(item for item in authoritative_entries(self.archive) if item["command"]=="acquire-retrospective")
        self.assertEqual((candle.raw_archive_sha256,candle.raw_archive_reference),(entry["raw_object_sha256"],f"raw:{entry['raw_object_sha256']}"))

    def test_28_prospective_archive_response_creates_attempt_and_terminal_snapshot(self):
        g,at=self.seed_prospective();transport=SequenceTransport(HTTPResponse(200,json.dumps({"contract_json":g["observation"].to_json()}).encode(),{}))
        discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        terminal=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:g["prospective_target"]+timedelta(minutes=5))
        state=replay_pr17_archive(self.archive,analysis_boundary=g["prospective_target"]+timedelta(minutes=5));self.assertEqual(len(state.bucket("attempts")),5);self.assertEqual(len(state.bucket("snapshots")),1);self.assertEqual(terminal.provider_request_count,0)
        self.assertEqual(state.bucket("snapshots")[0].market_observation_id,g["observation"].observation_id)

    def test_29_deterministic_publication_failpoints_reconcile_and_recover(self):
        stages={"before-raw":0,"after-raw":1,"after-normalized":2,"before-manifest":2,"after-manifest":0}
        for stage,orphan_count in stages.items():
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);config=replace(self.config,primary_root=root/"dry-run"/"fixture"/"primary",secondary_root=root/"dry-run"/"fixture"/"secondary",log_root=root/"logs");archive=NamespaceArchive(config)
                with self.assertRaisesRegex(OperationsError,"injected-interruption"):archive.commit(raw_body=b"same",normalized={"schema_version":"1","value":"same"},entry_values=self.entry_values(),failpoint=stage)
                one=reconcile_archive(archive);two=reconcile_archive(archive);self.assertEqual(one,two);self.assertEqual(len(one.orphaned),orphan_count)
                self.assertEqual(len(one.authoritative_manifest_ids),1 if stage=="after-manifest" else 0)
                self.assertEqual(inspect_archive(archive).ready,orphan_count==0)
                rebuild_index(archive);sync=sync_secondary(archive)
                self.assertEqual(sync["copied"],3 if stage=="after-manifest" else 0)
                if orphan_count:
                    with self.assertRaisesRegex(OperationsError,"orphan-conflict"):archive.commit(raw_body=b"different",normalized={"schema_version":"1","value":"different"},entry_values=self.entry_values())
                archive.commit(raw_body=b"same",normalized={"schema_version":"1","value":"same"},entry_values=self.entry_values())
                self.assertTrue(reconcile_archive(archive).healthy);self.assertEqual(len(authoritative_entries(archive)),1)

    def test_30_prospective_scientific_authority_cannot_be_selected_or_backdated(self):
        g,at=self.seed_prospective();transport=SequenceTransport()
        foreign=replace(self.config,research_protocol_ids=("foreign-protocol",));self.archive=NamespaceArchive(foreign)
        with self.assertRaisesRegex(OperationsError,"prospective-authority-invalid"):discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        self.assertEqual(len(transport.calls),0)
        with self.assertRaisesRegex(OperationsError,"direct-capture-prohibited"):capture_prospective(archive=self.archive,transport=transport,endpoint="x",request={},invoked_at=at-timedelta(days=1),target_at=at-timedelta(days=1),opportunity_id="invented",protocol_id="foreign",now=lambda:at-timedelta(days=1),validator=validator())
        command=["python3","operate_forecast_standalone_research.py","--config","missing.json","capture-prospective","--at",at.isoformat(),"--target-at",at.isoformat(),"--opportunity-id","invented"]
        rejected=subprocess.run(command,capture_output=True,text=True,check=False);self.assertEqual(rejected.returncode,2);self.assertIn("unrecognized arguments",rejected.stderr)
        wrapper=(Path(__file__).parents[1]/"operations/launchd/run_prospective_capture.sh").read_text()
        for prohibited in ("EVENT_ID","MARKET_ID","OPPORTUNITY_ID","PROTOCOL_ID","TARGET_AT","--at"):self.assertNotIn(prohibited,wrapper)

    def test_31_foreign_response_and_elapsed_window_never_create_provider_authority(self):
        from dataclasses import replace as dc_replace
        g,at=self.seed_prospective();foreign_provenance=dc_replace(g["observation"].provenance,canonical_event_id="mlb:foreign")
        foreign_observation=dc_replace(g["observation"],canonical_event_id="mlb:foreign",proposition_id="winner:mlb:foreign:home",provenance=foreign_provenance)
        transport=SequenceTransport(HTTPResponse(200,json.dumps({"contract_json":foreign_observation.to_json()}).encode(),{}))
        outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        self.assertEqual(outcome.provider_request_count,1);state=replay_pr17_archive(self.archive,analysis_boundary=at);self.assertEqual(state.bucket("market_observations"),())
        late=SequenceTransport();closed=g["prospective_target"]+timedelta(minutes=6)
        terminal=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:late,clock=lambda:closed)
        self.assertEqual(terminal.provider_request_count,0);self.assertEqual(len(late.calls),0);state=replay_pr17_archive(self.archive,analysis_boundary=closed);self.assertEqual(len(state.bucket("attempts")),5)

    def test_32_future_or_incompatible_authority_fails_before_provider_call(self):
        from forecast_standalone_research import create_standalone_eligibility_authority
        from inspect_forecast_standalone_research import build_synthetic_bundle
        g=build_synthetic_bundle();at=g["observation"].collected_at;transport=SequenceTransport()
        self.config=replace(self.config,research_protocol_ids=(g["prospective"].standalone_probability_source_protocol_id,));self.archive=NamespaceArchive(self.config)
        future_context,future_result=create_standalone_eligibility_authority(protocol=g["prospective"],opportunity=g["opportunity"],outcome_history=g["legacy"]["outcome_history"],classification=g["prospective_classification"],classifications=(g["prospective_classification"],),analysis_boundary=at+timedelta(seconds=1),provenance=g["provenance"])
        archive_pr17_authority(self.archive,(g["activation"],g["prospective"],g["opportunity"],g["prospective_classification"],future_context,future_result,g["legacy"]["outcome_history"],g["series"]),recorded_at=at)
        with self.assertRaises((OperationsError,ValueError)):discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        self.assertEqual(len(transport.calls),0)
        root=Path(self.temp.name);incompatible=replace(self.config,primary_root=root/"dry-run"/"incompatible"/"primary",secondary_root=root/"dry-run"/"incompatible"/"secondary",namespace="incompatible")
        self.archive=NamespaceArchive(incompatible)
        archive_pr17_authority(self.archive,(g["activation"],g["prospective"],g["opportunity"],g["retro_classification"],g["prospective_context"],g["prospective_eligibility"],g["legacy"]["outcome_history"],g["series"]),recorded_at=at)
        with self.assertRaises((OperationsError,ValueError)):discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=lambda:at)
        self.assertEqual(len(transport.calls),0)

    def test_33_same_and_next_slot_completion_preserve_request_start_chronology(self):
        for label,start_offset,completion_offset in (("same",timedelta(seconds=10),timedelta(seconds=20)),("next",timedelta(seconds=59),timedelta(seconds=61))):
            with self.subTest(completion_offset=completion_offset):
                self.select_namespace(label);g,_=self.seed_prospective();target=g["prospective_target"];start=target+start_offset;completed=target+completion_offset
                transport=SequenceTransport(self.prospective_response_at(g,start));clock=SequenceClock(start,start,completed)
                outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=clock)
                state=replay_pr17_archive(self.archive,analysis_boundary=completed);attempt=next(x for x in state.bucket("attempts") if x.provider_call_occurred)
                entry=next(x for x in authoritative_entries(self.archive) if f"slot:{attempt.slot}" in x["diagnostics"] and x["disposition"]==Disposition.SUCCESS.value)
                self.assertEqual((outcome.provider_request_count,len(transport.calls),attempt.slot),(1,1,0));self.assertEqual((attempt.invocation_at,attempt.effective_at),(start,completed));self.assertEqual(datetime.fromisoformat(entry["acquired_at"]["datetime_utc"]),completed)
                repeated=SequenceTransport();repeat_clock=SequenceClock(completed,completed)
                discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:repeated,clock=repeat_clock)
                self.assertEqual(len(repeated.calls),0)

    def test_34_multi_slot_and_post_window_completion_are_failure_inclusive(self):
        cases=((0,timedelta(minutes=3,seconds=5),False),(4,timedelta(minutes=5,seconds=10),True))
        for slot,completion_offset,terminal in cases:
            with self.subTest(slot=slot):
                self.select_namespace(f"cross-{slot}");g,_=self.seed_prospective();target=g["prospective_target"];start=target+timedelta(minutes=slot,seconds=30);completed=target+completion_offset
                transport=SequenceTransport(TimeoutError());clock=SequenceClock(start,start,completed)
                outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=clock)
                state=replay_pr17_archive(self.archive,analysis_boundary=completed);called=[x for x in state.bucket("attempts") if x.provider_call_occurred]
                self.assertEqual((outcome.provider_request_count,len(transport.calls),len(called)),(1,1,1));self.assertEqual((called[0].slot,called[0].invocation_at,called[0].effective_at),(slot,start,completed))
                self.assertEqual(len(state.bucket("attempts")),4 if slot==0 else 5)
                self.assertEqual(len(state.bucket("snapshots")),1 if terminal else 0)

    def test_35_fresh_authorization_advances_slot_or_closes_window_without_stale_call(self):
        g,_=self.seed_prospective();target=g["prospective_target"];transport=SequenceTransport(self.prospective_response_at(g,target+timedelta(minutes=1,seconds=1)))
        clock=SequenceClock(target+timedelta(seconds=59),target+timedelta(minutes=1,seconds=1),target+timedelta(minutes=1,seconds=2))
        outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=clock)
        state=replay_pr17_archive(self.archive,analysis_boundary=clock.calls[-1]);self.assertEqual((outcome.provider_request_count,len(transport.calls)),(1,1))
        self.assertFalse(next(x for x in state.bucket("attempts") if x.slot==0).provider_call_occurred);self.assertEqual(next(x for x in state.bucket("attempts") if x.provider_call_occurred).slot,1)

        self.select_namespace("closed");g,_=self.seed_prospective();target=g["prospective_target"];closed=SequenceTransport();clock=SequenceClock(target+timedelta(minutes=4,seconds=59),target+timedelta(minutes=5,microseconds=1))
        outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:closed,clock=clock);state=replay_pr17_archive(self.archive,analysis_boundary=clock.calls[-1])
        self.assertEqual((outcome.provider_request_count,len(closed.calls),len(state.bucket("attempts")),len(state.bucket("snapshots"))),(0,0,5,1))

    def test_36_invalid_cross_boundary_and_clock_reversal_never_lose_or_duplicate_calls(self):
        g,_=self.seed_prospective();target=g["prospective_target"];start=target+timedelta(seconds=59);completed=target+timedelta(minutes=1,seconds=1)
        transport=SequenceTransport(HTTPResponse(200,b"{}",{}));outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=SequenceClock(start,start,completed))
        state=replay_pr17_archive(self.archive,analysis_boundary=completed);called=[x for x in state.bucket("attempts") if x.provider_call_occurred]
        self.assertEqual((outcome.provider_request_count,len(transport.calls),called[0].slot,type(called[0].result).__name__),(1,1,0,"CapturedInvalid"));self.assertEqual(state.bucket("market_observations"),())

        self.select_namespace("reversal");g,_=self.seed_prospective();target=g["prospective_target"];transport=SequenceTransport(self.prospective_response_at(g,target))
        with self.assertRaisesRegex(OperationsError,"trusted-clock-reversed"):discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=SequenceClock(target,target,target-timedelta(seconds=1)))
        self.assertEqual(len(transport.calls),1);self.assertEqual(replay_pr17_archive(self.archive,analysis_boundary=target).bucket("attempts"),())

    def test_37_observation_interval_validation_is_persisted_and_boundary_inclusive(self):
        cases=(("predates",29,False),("at-start",30,True),("interior",35,True),("at-completion",40,True),("postdates",41,False))
        for label,observation_second,valid in cases:
            with self.subTest(label=label):
                self.select_namespace(f"chronology-{label}");g,_=self.seed_prospective();target=g["prospective_target"]
                started=target+timedelta(seconds=30);completed=target+timedelta(seconds=40);response=self.prospective_response_at(g,target+timedelta(seconds=observation_second));transport=SequenceTransport(response)
                outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=SequenceClock(started,started,completed))
                state=replay_pr17_archive(self.archive,analysis_boundary=completed);called=[x for x in state.bucket("attempts") if x.provider_call_occurred]
                self.assertEqual((outcome.provider_request_count,len(transport.calls),len(called)),(1,1,1));attempt=called[0]
                self.assertEqual((attempt.slot,attempt.invocation_at,attempt.effective_at),(0,started,completed));self.assertEqual(type(attempt.result).__name__,"CapturedValid" if valid else "CapturedInvalid")
                self.assertEqual(len(state.bucket("market_observations")),1 if valid else 0)
                entry=next(x for x in authoritative_entries(self.archive) if f"slot:{attempt.slot}" in x["diagnostics"] and x["raw_object_sha256"])
                self.assertEqual(datetime.fromisoformat(entry["acquired_at"]["datetime_utc"]),completed);self.assertEqual(self.archive.read_verified("raw",f"raw:{entry['raw_object_sha256']}"),response.body)
                if not valid:
                    self.assertEqual((attempt.result.raw_acquisition_reference,attempt.result.raw_sha256),(f"raw:{entry['raw_object_sha256']}",entry["raw_object_sha256"]));self.assertEqual(entry["disposition"],Disposition.VALIDATION_FAILURE.value)
                    self.assertTrue(any("outside the inclusive trusted request interval" in item for item in attempt.diagnostics))
                repeated=SequenceTransport();discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:repeated,clock=SequenceClock(completed,completed))
                self.assertEqual(len(repeated.calls),0)

    def test_38_provider_contract_decode_failures_are_typed_persisted_and_replayable(self):
        from forecast_standalone_research import AttemptValidationFailure
        g0,_=self.seed_prospective();target=g0["prospective_target"];valid=json.loads(self.prospective_response_at(g0,target+timedelta(seconds=30)).body)["contract_json"]
        def changed(mutator):
            value=json.loads(valid);mutator(value);return json.dumps(value,sort_keys=True,separators=(",",":"))
        cases=[
            ("malformed","{",AttemptValidationFailure.MALFORMED),
            ("top-scalar","5",AttemptValidationFailure.INCOMPLETE),
            ("top-list","[]",AttemptValidationFailure.INCOMPLETE),
            ("top-empty","{}",AttemptValidationFailure.INCOMPLETE),
            ("missing-type",changed(lambda x:x.pop("__type__")),AttemptValidationFailure.INCOMPLETE),
            ("type-integer",changed(lambda x:x.__setitem__("__type__",5)),AttemptValidationFailure.MAPPING),
            ("type-empty",changed(lambda x:x.__setitem__("__type__","")),AttemptValidationFailure.MAPPING),
            ("unknown-type",changed(lambda x:x.__setitem__("__type__","UnknownProviderContract")),AttemptValidationFailure.MAPPING),
            ("conflicting-top-markers",changed(lambda x:x.__setitem__("__enum__","MarketStatus:open")),AttemptValidationFailure.MAPPING),
            ("duplicate-type",'{"__type__":"MarketObservation","__type__":"MarketObservation"}',AttemptValidationFailure.MAPPING),
            ("reproduced-enum-shape",'{"__type__":"MarketObservation","status":{"__enum__":5}}',AttemptValidationFailure.MAPPING),
            ("reproduced-decimal-shape",'{"__type__":"MarketObservation","price":{"__decimal__":"not-a-decimal"}}',AttemptValidationFailure.MAPPING),
            ("missing-field",changed(lambda x:x.pop("provider_market_id")),AttemptValidationFailure.INCOMPLETE),
            ("invalid-enum",changed(lambda x:x.__setitem__("status",{"__enum__":"MarketStatus:not-a-status"})),AttemptValidationFailure.MAPPING),
            ("semantic-conflict",changed(lambda x:x["provenance"].__setitem__("canonical_event_id","mlb:foreign")),AttemptValidationFailure.MAPPING),
            ("wrong-contract",g0["prospective"].to_json(),AttemptValidationFailure.MAPPING),
        ]
        for label,item in (("integer",5),("null",None),("object",{}),("list",[])):
            cases.append((f"enum-{label}",changed(lambda x,item=item:x.__setitem__("status",{"__enum__":item})),AttemptValidationFailure.MAPPING))
        cases.extend((
            ("enum-no-separator",changed(lambda x:x.__setitem__("status",{"__enum__":"MarketStatus"})),AttemptValidationFailure.MAPPING),
            ("enum-empty-type",changed(lambda x:x.__setitem__("status",{"__enum__":":open"})),AttemptValidationFailure.MAPPING),
            ("enum-empty-value",changed(lambda x:x.__setitem__("status",{"__enum__":"MarketStatus:"})),AttemptValidationFailure.MAPPING),
            ("enum-unknown-type",changed(lambda x:x.__setitem__("status",{"__enum__":"UnknownEnum:open"})),AttemptValidationFailure.MAPPING),
            ("enum-extra-key",changed(lambda x:x.__setitem__("status",{"__enum__":"MarketStatus:open","extra":1})),AttemptValidationFailure.MAPPING),
            ("enum-nested-invalid",changed(lambda x:x["quotes"].__setitem__("yes_bid",{"nested":{"__enum__":5}})),AttemptValidationFailure.MAPPING),
        ))
        for label,item in (("integer",5),("null",None),("object",{}),("list",[])):
            cases.append((f"decimal-{label}",changed(lambda x,item=item:x["quotes"].__setitem__("yes_bid",{"__decimal__":item})),AttemptValidationFailure.MAPPING))
        for label,item in (("empty",""),("nonnumeric","not-a-decimal"),("exponent","1e+"),("nan","NaN"),("positive-infinity","Infinity"),("negative-infinity","-Infinity")):
            cases.append((f"decimal-{label}",changed(lambda x,item=item:x["quotes"].__setitem__("yes_bid",{"__decimal__":item})),AttemptValidationFailure.MAPPING))
        cases.extend((
            ("decimal-extra-key",changed(lambda x:x["quotes"].__setitem__("yes_bid",{"__decimal__":"0.5","extra":1})),AttemptValidationFailure.MAPPING),
            ("decimal-nested-invalid",changed(lambda x:x["quotes"].__setitem__("yes_bid",{"nested":{"__decimal__":"not-a-decimal"}})),AttemptValidationFailure.MAPPING),
        ))
        for label,item in (("integer",5),("unsupported","Infinity"),("ordinary-spelling","infinity")):
            cases.append((f"nonfinite-{label}",changed(lambda x,item=item:x["quotes"].__setitem__("yes_bid",{"__non_finite_decimal__":item})),AttemptValidationFailure.MAPPING))
        cases.extend((
            ("nonfinite-extra-key",changed(lambda x:x["quotes"].__setitem__("yes_bid",{"__non_finite_decimal__":"positive-infinity","extra":1})),AttemptValidationFailure.MAPPING),
            ("nonfinite-nested-invalid",changed(lambda x:x["quotes"].__setitem__("yes_bid",{"nested":{"__non_finite_decimal__":"unsupported"}})),AttemptValidationFailure.MAPPING),
            ("nonfinite-positive-control",changed(lambda x:x["quotes"].__setitem__("yes_bid",{"__non_finite_decimal__":"positive-infinity"})),AttemptValidationFailure.MAPPING),
            ("nonfinite-negative-control",changed(lambda x:x["quotes"].__setitem__("yes_bid",{"__non_finite_decimal__":"negative-infinity"})),AttemptValidationFailure.MAPPING),
        ))
        for marker in ("__date__","__datetime__"):
            cases.append((f"{marker}-integer",changed(lambda x,marker=marker:x.__setitem__("collected_at",{marker:5})),AttemptValidationFailure.MAPPING))
            cases.append((f"{marker}-extra-key",changed(lambda x,marker=marker:x.__setitem__("collected_at",{marker:"2026-06-01" if marker=="__date__" else "2026-06-01T19:00:00+00:00","extra":1})),AttemptValidationFailure.MAPPING))
        cases.extend((
            ("date-malformed",changed(lambda x:x.__setitem__("collected_at",{"__date__":"not-a-date"})),AttemptValidationFailure.MAPPING),
            ("date-impossible",changed(lambda x:x.__setitem__("collected_at",{"__date__":"2026-02-30"})),AttemptValidationFailure.MAPPING),
            ("date-nested-invalid",changed(lambda x:x["provenance"].__setitem__("collected_at",{"nested":{"__date__":"invalid"}})),AttemptValidationFailure.MAPPING),
            ("datetime-malformed",changed(lambda x:x.__setitem__("collected_at",{"__datetime__":"not-a-datetime"})),AttemptValidationFailure.MAPPING),
            ("datetime-bad-offset",changed(lambda x:x.__setitem__("collected_at",{"__datetime__":"2026-06-01T19:00:00+99:00"})),AttemptValidationFailure.MAPPING),
            ("datetime-naive",changed(lambda x:x.__setitem__("collected_at",{"__datetime__":"2026-06-01T19:00:00"})),AttemptValidationFailure.MAPPING),
            ("datetime-nested-invalid",changed(lambda x:x["provenance"].__setitem__("collected_at",{"nested":{"__datetime__":5}})),AttemptValidationFailure.MAPPING),
        ))
        deep={"__decimal__":"0.5"}
        for _ in range(66):deep={"nested":deep}
        cases.append(("excessive-nesting",changed(lambda x:x["quotes"].__setitem__("yes_bid",deep)),AttemptValidationFailure.MAPPING))
        for label,contract_json,category in cases:
            with self.subTest(label=label):
                self.select_namespace(f"decode-{label}");g,_=self.seed_prospective();started=target+timedelta(seconds=20);completed=target+timedelta(seconds=40)
                body=json.dumps({"contract_json":contract_json},sort_keys=True).encode();transport=SequenceTransport(HTTPResponse(200,body,{}))
                outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=SequenceClock(started,started,completed));state=replay_pr17_archive(self.archive,analysis_boundary=completed)
                called=[x for x in state.bucket("attempts") if x.provider_call_occurred];self.assertEqual((outcome.provider_request_count,len(transport.calls),len(called)),(1,1,1));attempt=called[0]
                self.assertEqual((attempt.slot,attempt.invocation_at,attempt.effective_at,type(attempt.result).__name__),(0,started,completed,"CapturedInvalid"));self.assertEqual(attempt.result.validation_failures,(category,));self.assertEqual(state.bucket("market_observations"),())
                entry=next(x for x in authoritative_entries(self.archive) if x["raw_object_sha256"]);self.assertEqual((entry["disposition"],datetime.fromisoformat(entry["acquired_at"]["datetime_utc"])),(Disposition.MALFORMED_RESPONSE.value if category is AttemptValidationFailure.MALFORMED else (Disposition.INCOMPLETE_RESPONSE.value if category is AttemptValidationFailure.INCOMPLETE else Disposition.VALIDATION_FAILURE.value),completed))
                self.assertEqual(self.archive.read_verified("raw",f"raw:{entry['raw_object_sha256']}"),body);self.assertEqual((attempt.result.raw_acquisition_reference,attempt.result.raw_sha256),(f"raw:{entry['raw_object_sha256']}",entry["raw_object_sha256"]))
                repeated=SequenceTransport();discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:repeated,clock=SequenceClock(completed,completed));self.assertEqual(len(repeated.calls),0)

        from forecast_standalone_operations import _validate_provider_serialization
        for marker in ({"__date__":"2026-06-01"},{"__datetime__":"2026-06-01T19:00:00+00:00"},{"__decimal__":"0.5"},{"__non_finite_decimal__":"positive-infinity"},{"__non_finite_decimal__":"negative-infinity"},{"__enum__":"MarketStatus:open"}):
            _validate_provider_serialization(marker)

        self.select_namespace("decode-secret");g,_=self.seed_prospective();secret_contract=changed(lambda x:x.__setitem__("authorization","must-not-persist"));body=json.dumps({"contract_json":secret_contract},sort_keys=True).encode();transport=SequenceTransport(HTTPResponse(200,body,{}));started=target+timedelta(seconds=20);completed=target+timedelta(seconds=40);raw_before=tuple(sorted(self.archive.raw_root.glob("*/*")))
        outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=SequenceClock(started,started,completed));state=replay_pr17_archive(self.archive,analysis_boundary=completed);called=[x for x in state.bucket("attempts") if x.provider_call_occurred]
        self.assertEqual((outcome.provider_request_count,len(transport.calls),len(called),type(called[0].result).__name__),(1,1,1,"AcquisitionFailed"));entry=next(x for x in authoritative_entries(self.archive) if f"slot:{called[0].slot}" in x["diagnostics"]);self.assertIsNone(entry["raw_object_sha256"]);self.assertEqual(tuple(sorted(self.archive.raw_root.glob("*/*"))),raw_before)

        transport=SequenceTransport(HTTPResponse(200,b"{}",{}))
        with self.assertRaisesRegex(RuntimeError,"programmer-defect"):acquire_prospective_once(transport=transport,endpoint="fixture://unexpected",request={},timeout_seconds=1,now=SequenceClock(target,target),validator=lambda _value:(_ for _ in ()).throw(RuntimeError("programmer-defect")))
        self.assertEqual(len(transport.calls),1)

    def test_39_market_observation_schema_field_mutations_are_failure_inclusive(self):
        from forecast_standalone_research import AttemptValidationFailure
        g0,_=self.seed_prospective();target=g0["prospective_target"];valid=json.loads(json.loads(self.prospective_response_at(g0,target+timedelta(seconds=30)).body)["contract_json"])
        def mutation(path,value,remove=False):
            result=json.loads(json.dumps(valid));cursor=result
            for item in path[:-1]:cursor=cursor[item]
            if remove:cursor.pop(path[-1])
            else:cursor[path[-1]]=value
            return json.dumps(result,sort_keys=True,separators=(",",":"))
        wrong_contract=valid["quotes"]
        mutations=[]
        for field in ("observation_id","series_id","provider_market_id","canonical_event_id","proposition_id","capture_session_id"):
            mutations.append((f"top-{field}",(field,),None))
        mutations.extend((
            ("top-collected-at",("collected_at",),5),("top-status",("status",),{"__enum__":"MarketSide:yes"}),("top-quotes",("quotes",),5),
            ("top-order-book",("order_book",),{}),("top-component-evidence",("component_evidence",),"bad"),("reproduced-provenance",("provenance",),5),
            ("top-volume",("volume",),"0.5"),("top-open-interest",("open_interest",),[]),("top-issues",("issues",),{}),
            ("quotes-wrong-tag",("quotes",),valid["provenance"]),("quotes-decimal-shape",("quotes","yes_bid"),"0.5"),("quotes-price-scale",("quotes","price_scale"),False),
            ("order-book-member",("order_book",0),"bad"),("order-book-enum",("order_book",0,"acquisition_side"),{"__enum__":"MarketStatus:open"}),
            ("order-book-level-bool",("order_book",0,"level"),True),("order-book-datetime",("order_book",0,"collected_at"),{"__date__":"2026-06-01"}),
            ("component-wrong-tag",("component_evidence",0),wrong_contract),("component-id",("component_evidence",0,"component"),5),
            ("component-datetime",("component_evidence",0,"collected_at"),"2026-06-01T19:00:00+00:00"),
            ("provenance-provider",("provenance","provider"),5),("provenance-transform-member",("provenance","transformations"),[5]),
            ("provenance-enum",("provenance","validation_status"),{"__enum__":"MarketStatus:open"}),
            ("provenance-reason-member",("provenance","validation_reasons"),["bad"]),("issue-member",("issues",),["bad"]),
            ("issue-field",("issues",),[{"__type__":"MarketIssue","code":5,"detail":"bad"}]),
            ("identifier-wrong-marker",("observation_id",),{"__decimal__":"1"}),
        ))
        mutations.append(("unknown-field",("unexpected",),5))
        for index,(label,path,value) in enumerate(mutations):
            with self.subTest(label=label):
                self.select_namespace(f"schema-{index}");g,_=self.seed_prospective();contract_json=mutation(path,value);body=json.dumps({"contract_json":contract_json},sort_keys=True).encode();transport=SequenceTransport(HTTPResponse(200,body,{}));started=target+timedelta(seconds=20);completed=target+timedelta(seconds=40)
                outcome=discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=SequenceClock(started,started,completed));state=replay_pr17_archive(self.archive,analysis_boundary=completed);called=[x for x in state.bucket("attempts") if x.provider_call_occurred]
                self.assertEqual((outcome.provider_request_count,len(transport.calls),len(called)),(1,1,1));attempt=called[0];self.assertEqual((attempt.slot,attempt.invocation_at,attempt.effective_at,type(attempt.result).__name__),(0,started,completed,"CapturedInvalid"));self.assertEqual(attempt.result.validation_failures,(AttemptValidationFailure.MAPPING,));self.assertEqual(state.bucket("market_observations"),())
                entry=next(x for x in authoritative_entries(self.archive) if x["raw_object_sha256"]);self.assertEqual((entry["disposition"],datetime.fromisoformat(entry["acquired_at"]["datetime_utc"])),(Disposition.VALIDATION_FAILURE.value,completed));self.assertEqual(self.archive.read_verified("raw",f"raw:{entry['raw_object_sha256']}"),body);self.assertEqual(attempt.result.raw_acquisition_reference,f"raw:{entry['raw_object_sha256']}")
                repeated=SequenceTransport();discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:repeated,clock=SequenceClock(completed,completed));self.assertEqual(len(repeated.calls),0)

        self.select_namespace("schema-missing");g,_=self.seed_prospective();contract_json=mutation(("provenance",),None,remove=True);transport=SequenceTransport(HTTPResponse(200,json.dumps({"contract_json":contract_json}).encode(),{}));started=target+timedelta(seconds=20);completed=target+timedelta(seconds=40)
        discover_and_capture_prospective(archive=self.archive,transport_factory=lambda _o,_s:transport,clock=SequenceClock(started,started,completed));entry=next(x for x in authoritative_entries(self.archive) if x["command"]=="capture-prospective");self.assertEqual((len(transport.calls),entry["disposition"]),(1,Disposition.INCOMPLETE_RESPONSE.value))


if __name__=="__main__":unittest.main()
