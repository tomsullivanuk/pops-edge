"""Offline provider-page and capture regressions for current market selection."""
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from forecast_prospective_market_selection import load_prospective_catalog, select_prospective_market
from forecast_prospective_projection import rebuild_projection, load_projection
from forecast_standalone_activation import initialize_activation, refresh_supporting_from_raw, canonical_prospective_authority
from forecast_standalone_operations import DeploymentConfig, NamespaceArchive, OperatingMode, RetryPolicy, discover_and_capture_prospective, replay_pr17_archive, OperationsError, APPROVED_ACTIVATION_AT
from inspect_forecast_standalone_activation import fixtures
from inspect_forecast_standalone_activation import FixtureOrderBook
from operate_forecast_standalone_activation import execute


class MarketSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);_,protocol=canonical_prospective_authority()
        self.at=datetime(2026,9,5,4,tzinfo=timezone.utc)
        self.archive=NamespaceArchive(DeploymentConfig("selection","selection",OperatingMode.ACTIVATED,root/"activated/selection/primary",root/"activated/selection/secondary","https://fixture.invalid",RetryPolicy(1,1,1,(),0),1,root/"logs",research_protocol_ids=(protocol.standalone_probability_source_protocol_id,),activation_at=APPROVED_ACTIVATION_AT))
        initialize_activation(self.archive,datetime(2026,8,28,tzinfo=timezone.utc))
        self.mlb,self.raw,self.book=fixtures()
        self.market=json.loads(self.raw)["markets"][0]
        self.publish([self.market],self.at-timedelta(minutes=1))

    def publish(self,markets,at,mlb=None):
        refresh_supporting_from_raw(archive=self.archive,mlb_raw=mlb or self.mlb,kalshi_raw=json.dumps({"markets":markets,"cursor":""}).encode(),collected_at=at)
        rebuild_projection(self.archive,at)

    def selection(self,at=None,schedule=None):
        at=at or self.at
        boundary,state=load_projection(self.archive,at)
        schedule=schedule or state.bucket("outcome_histories")[0].observations[-1]
        return select_prospective_market(load_prospective_catalog(boundary),state.bucket("market_series"),schedule,at)

    def test_ordinary_current_market_and_replay(self):
        series,reason=self.selection()
        self.assertEqual((series.provider_market_id,reason),(self.market["ticker"],"current-schedule-open-market"))
        _,state=load_projection(self.archive,self.at)
        self.assertEqual(state.graph,replay_pr17_archive(self.archive,analysis_boundary=self.at).graph)

    def test_latest_empty_catalog_does_not_fall_back(self):
        self.publish([],self.at)
        self.assertEqual(self.selection(),(None,"market-unavailable"))
        result=discover_and_capture_prospective(archive=self.archive,clock=lambda:self.at,transport_factory=lambda *_:self.fail("unavailable market queried"))
        self.assertEqual(result.provider_request_count,0)
        state=replay_pr17_archive(self.archive,analysis_boundary=self.at)
        self.assertIn("market-unavailable",state.bucket("attempts")[0].diagnostics)

    def test_postponed_occurrence_rejects_old_market_even_if_open(self):
        boundary,state=load_projection(self.archive,self.at)
        original=state.bucket("outcome_histories")[0].observations[-1]
        makeup=replace(original,scheduled_start=original.scheduled_start+timedelta(days=1))
        self.assertEqual(self.selection(schedule=makeup),(None,"market-unavailable"))

    def test_replacement_selected_with_old_series_still_archived(self):
        replacement=copy.deepcopy(self.market)
        replacement.update(ticker="KXMLBGAME-REPLACEMENT")
        later=self.at+timedelta(seconds=1)
        self.publish([replacement],later)
        series,_=self.selection(at=later)
        self.assertEqual(series.provider_market_id,replacement["ticker"])
        _,state=load_projection(self.archive,later)
        self.assertEqual(len(state.bucket("market_series")),2)

    def test_ambiguous_current_candidates_never_choose_by_order(self):
        other={**self.market,"ticker":"KXMLBGAME-OTHER"}
        self.publish([self.market,other],self.at)
        self.assertEqual(self.selection(),(None,"ambiguous-market"))

    def test_catalog_change_midwindow_preserves_attempt_identity_and_closes(self):
        empty=FixtureOrderBook(b'{"orderbook_fp":{"yes_dollars":[],"no_dollars":[]}}')
        execute("capture-prospective",self.archive.config,clock=lambda:self.at,transport_factory=lambda *_:empty)
        self.assertEqual(empty.calls,1)
        self.publish([{**self.market,"ticker":"KXMLBGAME-REPLACEMENT"}],self.at+timedelta(seconds=20))
        result=execute("capture-prospective",self.archive.config,clock=lambda:self.at+timedelta(minutes=1),transport_factory=lambda *_:self.fail("switched market queried"))
        self.assertEqual(result["provider_calls"],0)
        execute("capture-prospective",self.archive.config,clock=lambda:self.at+timedelta(minutes=6),transport_factory=lambda *_:self.fail("closed window queried"))
        state=replay_pr17_archive(self.archive,analysis_boundary=self.at+timedelta(minutes=6))
        self.assertEqual({x.provider_market_id for x in state.bucket("attempts")},{self.market["ticker"]})
        self.assertTrue(any("market-selection-changed" in x.diagnostics for x in state.bucket("attempts")))
        self.assertEqual(state.bucket("snapshots")[0].terminal_disposition.value,"missed-window")

    def test_market_closing_during_preparation_cancels_unissued_fence(self):
        self.publish([{**self.market,"ticker":"KXMLBGAME-SHORT","close_time":(self.at+timedelta(seconds=30)).isoformat()}],self.at)
        current=[self.at]
        def factory(*_):
            current[0]=self.at+timedelta(seconds=40)
            return FixtureOrderBook(self.book)
        result=execute("capture-prospective",self.archive.config,clock=lambda:current[0],transport_factory=factory)
        self.assertEqual(result["provider_calls"],0)
        # No issued-request marker remains to obstruct the next invocation.
        result=execute("capture-prospective",self.archive.config,clock=lambda:self.at+timedelta(minutes=1),transport_factory=lambda *_:self.fail("closed market queried"))
        self.assertEqual(result["provider_calls"],0)

    def test_identity_matching_delay_uses_fresh_request_time(self):
        from forecast_prospective_market_selection import prepare_prospective_markets
        self.publish([{**self.market,"ticker":"KXMLBGAME-SHORT","close_time":(self.at+timedelta(seconds=30)).isoformat()}],self.at)
        current=[self.at];transport=FixtureOrderBook(self.book)
        def slow_prepare(*args):
            result=prepare_prospective_markets(*args)
            current[0]=self.at+timedelta(seconds=40)
            return result
        with patch("forecast_prospective_market_selection.prepare_prospective_markets",side_effect=slow_prepare):
            result=execute("capture-prospective",self.archive.config,clock=lambda:current[0],transport_factory=lambda *_:transport)
        self.assertEqual((result["provider_calls"],transport.calls),(0,0))
        _,state=load_projection(self.archive,current[0])
        self.assertEqual(state.bucket("attempts")[0].invocation_at,current[0])

    def test_candidate_opening_during_matching_makes_selection_ambiguous(self):
        from forecast_prospective_market_selection import prepare_prospective_markets
        self.publish([self.market,{**self.market,"ticker":"KXMLBGAME-OPENING","open_time":(self.at+timedelta(seconds=30)).isoformat()}],self.at)
        current=[self.at];transport=FixtureOrderBook(self.book)
        def slow_prepare(*args):
            result=prepare_prospective_markets(*args)
            current[0]=self.at+timedelta(seconds=40)
            return result
        with patch("forecast_prospective_market_selection.prepare_prospective_markets",side_effect=slow_prepare):
            result=execute("capture-prospective",self.archive.config,clock=lambda:current[0],transport_factory=lambda *_:transport)
        self.assertEqual((result["provider_calls"],transport.calls),(0,0))
        _,state=load_projection(self.archive,current[0])
        self.assertIn("ambiguous-market",state.bucket("attempts")[0].diagnostics)

    def test_matching_delay_crosses_slot_without_backdated_calls(self):
        from forecast_prospective_market_selection import prepare_prospective_markets
        current=[self.at];transport=FixtureOrderBook(self.book)
        def slow_prepare(*args):
            result=prepare_prospective_markets(*args)
            current[0]=self.at+timedelta(minutes=1,seconds=1)
            return result
        with patch("forecast_prospective_market_selection.prepare_prospective_markets",side_effect=slow_prepare):
            result=execute("capture-prospective",self.archive.config,clock=lambda:current[0],transport_factory=lambda *_:transport)
        self.assertEqual((result["provider_calls"],transport.calls),(1,1))
        _,state=load_projection(self.archive,current[0])
        attempt=next(x for x in state.bucket("attempts") if x.provider_call_occurred)
        self.assertEqual((attempt.slot,attempt.invocation_at),(1,current[0]))

    def test_matching_delay_crosses_window_without_provider_call(self):
        from forecast_prospective_market_selection import prepare_prospective_markets
        current=[self.at];transport=FixtureOrderBook(self.book)
        def slow_prepare(*args):
            result=prepare_prospective_markets(*args)
            current[0]=self.at+timedelta(minutes=5,microseconds=1)
            return result
        with patch("forecast_prospective_market_selection.prepare_prospective_markets",side_effect=slow_prepare):
            result=execute("capture-prospective",self.archive.config,clock=lambda:current[0],transport_factory=lambda *_:transport)
        self.assertEqual((result["provider_calls"],transport.calls),(0,0))
        _,state=load_projection(self.archive,current[0])
        self.assertEqual(state.bucket("snapshots")[0].terminal_disposition.value,"missed-window")

    def test_matching_failure_leaves_no_unissued_marker(self):
        with patch("forecast_prospective_market_selection.prepare_prospective_markets",side_effect=OperationsError("fixture-preparation-failed","before request intent")):
            with self.assertRaises(OperationsError):
                execute("capture-prospective",self.archive.config,clock=lambda:self.at,transport_factory=lambda *_:self.fail("failed preparation queried"))
        transport=FixtureOrderBook(self.book)
        result=execute("capture-prospective",self.archive.config,clock=lambda:self.at,transport_factory=lambda *_:transport)
        self.assertEqual((result["provider_calls"],transport.calls),(1,1))

    def test_status_interval_and_home_yes_checks(self):
        boundary,state=load_projection(self.archive,self.at)
        markets,games,reason=load_prospective_catalog(boundary)
        schedule=state.bucket("outcome_histories")[0].observations[-1]
        for changes in ({"status":"settled"},{"status":"paused"},{"open_time":None},{"close_time":None},{"close_time":self.at.isoformat()},{"open_time":(self.at+timedelta(seconds=1)).isoformat()},{"close_time":"invalid"},{"close_time":"2026-09-06T00:00:00"},{"yes_sub_title":"Away Club"}):
            with self.subTest(changes=changes):
                result=select_prospective_market((({**markets[0],**changes},),games,reason),state.bucket("market_series"),schedule,self.at)
                self.assertEqual(result,(None,"market-unavailable"))

    def test_absent_catalog_and_corrupt_selected_page_fail_closed(self):
        boundary,_=load_projection(self.archive,self.at)
        with patch.object(boundary,"entries",return_value=()):
            self.assertEqual(load_prospective_catalog(boundary),((),(),"market-catalog-unavailable"))
        with patch.object(boundary,"read_verified",side_effect=OperationsError("archive-integrity-failure","corrupt selected page")):
            with self.assertRaises(OperationsError):load_prospective_catalog(boundary)

    def test_empty_orderbook_remains_invalid(self):
        raw=b'{"orderbook_fp":{"yes_dollars":[],"no_dollars":[]}}'
        transport=FixtureOrderBook(raw)
        execute("capture-prospective",self.archive.config,clock=lambda:self.at,transport_factory=lambda *_:transport)
        execute("capture-prospective",self.archive.config,clock=lambda:self.at,transport_factory=lambda *_:transport)
        self.assertEqual(transport.calls,1)
        state=replay_pr17_archive(self.archive,analysis_boundary=self.at)
        self.assertEqual(type(state.bucket("attempts")[0].result).__name__,"CapturedInvalid")
        self.assertEqual(state.bucket("market_observations"),())

    def test_no_due_work_does_not_read_catalog(self):
        with patch("forecast_prospective_market_selection.load_prospective_catalog",side_effect=AssertionError("unnecessary catalog read")):
            result=execute("capture-prospective",self.archive.config,clock=lambda:self.at-timedelta(seconds=30),transport_factory=lambda *_:self.fail("not due"))
        self.assertEqual(result["provider_calls"],0)


if __name__=="__main__":unittest.main()
