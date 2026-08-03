import csv
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from event_contracts import ContractError
from market_contracts import MarketAdapterOutcome, MarketSide, MarketStatus
from market_valuation import ZeroFeeModel, value_market
from kalshi_activity_positions import read_activity_positions, write_position_summary
from opportunity_board import BoardEntry, OpportunityState, Position, analyze_liquidation, build_opportunity, render_opportunity_board, sorted_entries
from run_opportunity_board import BUNDLE_SCHEMA_VERSION, build_entries, notification_lines, read_positions, run, select_market_results, validate_bundle
from kalshi_mlb_adapter import adapt_market
from tests.test_market_analysis import START, adapted, bid_book, facts, forecast, market_payload

AT = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
ACTIVITY_FIXTURE = Path(__file__).parent / "fixtures" / "kalshi_activity_mlb_redacted.csv"


def position_for(result, side=MarketSide.YES, quantity=Decimal(0), cost=Decimal(0), captured_at=AT):
    return Position(result.series.series_id,result.series.proposition_id,result.observation.canonical_event_id,side,quantity,cost,captured_at)

def complete_opportunity(position=None, *, quantity=Decimal(2), result=None, side=MarketSide.YES):
    result = result or adapted(bid_book())
    position = position or Position.none(result.series.series_id,result.series.proposition_id,result.observation.canonical_event_id,side)
    valuation = value_market(forecast=forecast(), market=result.observation, proposition=result.proposition,
                             series=result.series, side=side, quantity=quantity,
                             fee_model=ZeroFeeModel(), event_scheduled_start=START)
    return build_opportunity(forecast=forecast(), observation=result.observation, series=result.series,
                             valuation=valuation, position=position, game="Away Club at Home Club", scheduled_start=START)


def entry_for(opportunity, entry_id="entry:1"):
    return BoardEntry(entry_id, opportunity.state, opportunity.game, opportunity.scheduled_start,
                      opportunity.proposition, "KXMLB", opportunity, opportunity.position, None,
                      opportunity.position_cost_basis, opportunity.forecast_captured_at,
                      opportunity.market_captured_at, opportunity.issues, opportunity.diagnostics)


class OpportunityTests(unittest.TestCase):
    def test_deterministic_construction_and_reference_only_boundary(self):
        first=complete_opportunity(); second=complete_opportunity()
        self.assertEqual(first,second); self.assertEqual(first.opportunity_id,f"opportunity:{first.valuation_id}")
        self.assertNotIn("forecast",first.__dataclass_fields__); self.assertNotIn("market",first.__dataclass_fields__)

    def test_incompatible_position_fails_closed(self):
        result=adapted(bid_book()); bad=Position("market-series:kalshi:OTHER",result.series.proposition_id,result.observation.canonical_event_id,MarketSide.YES,Decimal(1),Decimal("0.5"))
        with self.assertRaises(ContractError): complete_opportunity(bad,result=result)

    def test_position_proposition_event_and_complementary_side_mismatches_fail(self):
        result=adapted(bid_book())
        for bad in (
            Position(result.series.series_id,"winner:mlb:777:other",result.observation.canonical_event_id,MarketSide.YES,Decimal(1),Decimal("0.5")),
            Position(result.series.series_id,result.series.proposition_id,"mlb:other",MarketSide.YES,Decimal(1),Decimal("0.5")),
            position_for(result,side=MarketSide.NO,quantity=Decimal(1),cost=Decimal("0.5")),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ContractError): complete_opportunity(bad,result=result,side=MarketSide.YES)

    def test_no_side_opportunity_displays_the_complementary_claim(self):
        result=adapted(bid_book()); held=position_for(result,side=MarketSide.NO,quantity=Decimal(1),cost=Decimal("0.5"))
        opportunity=complete_opportunity(held,result=result,side=MarketSide.NO)
        self.assertEqual(opportunity.position.side,MarketSide.NO); self.assertEqual(opportunity.proposition,"Away Club wins"); self.assertEqual(opportunity.forecast_probability,Decimal("0.4"))

    def test_no_position_and_existing_position_metrics(self):
        result=adapted(bid_book()); no_position=complete_opportunity(result=result); held=complete_opportunity(position_for(result,quantity=Decimal(4),cost=Decimal("0.50")),result=result)
        self.assertFalse(no_position.position.exists); self.assertTrue(held.position.exists)
        self.assertEqual((held.position_cost_basis,held.executable_liquidation_proceeds,held.executable_position_profit_loss),(Decimal("2.00"),Decimal("2.16"),Decimal("0.16")))

    def test_attention_sort_prioritizes_positions_then_investigation_then_positive_value(self):
        result=adapted(bid_book()); held=complete_opportunity(position_for(result,quantity=Decimal(1),cost=Decimal("0.54")),result=result)
        complete=complete_opportunity()
        ambiguous=BoardEntry("ambiguous:1",OpportunityState.AMBIGUOUS,"Game",START,"Unknown",None,None,None,None,None,None,None,("needs reconciliation",),(('Input','{}'),))
        ordered=sorted_entries((entry_for(complete,"complete:1"),ambiguous,entry_for(held,"held:1")))
        self.assertEqual([item.entry_id for item in ordered],["ambiguous:1","held:1","complete:1"])

    def test_attention_sort_prioritizes_constrained_and_adverse_exposure_deterministically(self):
        result=adapted(bid_book())
        constrained=complete_opportunity(position_for(result,quantity=Decimal(6),cost=Decimal("0.50")),result=result)
        adverse=complete_opportunity(position_for(result,quantity=Decimal(1),cost=Decimal("0.70")),result=result)
        healthy=complete_opportunity(position_for(result,quantity=Decimal(1),cost=Decimal("0.50")),result=result)
        ambiguous=BoardEntry("ambiguous:1",OpportunityState.AMBIGUOUS,"Game",START,"Unknown",None,None,None,None,None,None,None,("investigate",),(('Input','{}'),))
        ordered=sorted_entries((entry_for(healthy,"healthy:1"),ambiguous,entry_for(adverse,"adverse:1"),entry_for(constrained,"constrained:1")))
        self.assertEqual([item.entry_id for item in ordered],["constrained:1","adverse:1","ambiguous:1","healthy:1"])


class PositionInputTests(unittest.TestCase):
    def write_positions(self,path,rows):
        with path.open("w",newline="",encoding="utf-8") as output:
            writer=csv.DictWriter(output,fieldnames=("Provider","Provider Market ID","Proposition ID","Canonical Event ID","Side","Open Quantity","Average Entry Cost","Captured At","Status")); writer.writeheader(); writer.writerows(rows)

    def test_position_reader_preserves_authoritative_quantity_cost_and_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"positions.csv"; self.write_positions(path,[{"Provider":"kalshi","Provider Market ID":"ABC","Proposition ID":"winner:mlb:1:team:a","Canonical Event ID":"mlb:1","Side":"yes","Open Quantity":"3","Average Entry Cost":"0.50","Captured At":AT.isoformat(),"Status":"Open"}])
            position=read_positions(path)[0]; self.assertEqual(position.quantity,Decimal(3)); self.assertEqual(position.average_cost,Decimal("0.5")); self.assertEqual(position.captured_at,AT)

    def test_position_reader_preserves_offsetting_sides_and_rejects_duplicate_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"positions.csv"; self.write_positions(path,[
                {"Provider":"kalshi","Provider Market ID":"ABC","Proposition ID":"winner:mlb:1:team:a","Canonical Event ID":"mlb:1","Side":"yes","Open Quantity":"1","Average Entry Cost":"0.4","Status":"Open"},
                {"Provider":"kalshi","Provider Market ID":"ABC","Proposition ID":"winner:mlb:1:team:a","Canonical Event ID":"mlb:1","Side":"no","Open Quantity":"1","Average Entry Cost":"0.6","Status":"Open"}])
            self.assertEqual({p.side for p in read_positions(path)},{MarketSide.YES,MarketSide.NO})
            self.write_positions(path,[
                {"Provider":"kalshi","Provider Market ID":"ABC","Proposition ID":"winner:mlb:1:team:a","Canonical Event ID":"mlb:1","Side":"yes","Open Quantity":"1","Average Entry Cost":"0.4","Status":"Open"},
                {"Provider":"kalshi","Provider Market ID":"ABC","Proposition ID":"winner:mlb:1:team:a","Canonical Event ID":"mlb:1","Side":"yes","Open Quantity":"2","Average Entry Cost":"0.5","Status":"Open"}])
            with self.assertRaises(ValueError): read_positions(path)

    def test_position_reader_rejects_malformed_side_and_unknown_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"positions.csv"
            for provider,side in (("kalshi","maybe"),("other","yes")):
                self.write_positions(path,[{"Provider":provider,"Provider Market ID":"ABC","Proposition ID":"winner:mlb:1:team:a","Canonical Event ID":"mlb:1","Side":side,"Open Quantity":"1","Average Entry Cost":"0.4","Status":"Open"}])
                with self.assertRaises(ValueError): read_positions(path)

    def test_missing_position_evidence_differs_from_explicit_empty_summary(self):
        with self.assertRaises(ValueError): read_positions(None)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"positions.csv"; self.write_positions(path,[])
            self.assertEqual(read_positions(path),())


class ActivityPositionTests(unittest.TestCase):
    ticker="KXMLBGAME-26AUG011610MINSEA-MIN"

    def market_result(self):
        return adapted(bid_book(),payload=market_payload(ticker=self.ticker))

    def rows(self):
        with ACTIVITY_FIXTURE.open(newline="",encoding="utf-8") as source: return list(csv.DictReader(source))

    def write_rows(self,path,rows):
        with ACTIVITY_FIXTURE.open(newline="",encoding="utf-8") as source: fields=csv.DictReader(source).fieldnames
        with path.open("w",newline="",encoding="utf-8") as output:
            writer=csv.DictWriter(output,fieldnames=fields); writer.writeheader(); writer.writerows(rows)

    def test_actual_activity_header_partial_close_fee_and_mapping_contract(self):
        result=self.market_result(); position=read_activity_positions(ACTIVITY_FIXTURE,(result,))[0]
        self.assertEqual((position.series_id,position.proposition_id,position.canonical_event_id),(result.series.series_id,result.series.proposition_id,result.observation.canonical_event_id))
        self.assertEqual((position.side,position.quantity,position.average_cost),(MarketSide.YES,Decimal(6),Decimal("0.49")))
        self.assertEqual((position.entry_fees,position.exit_fees),(Decimal("0.04"),Decimal("0.02")))
        self.assertEqual(position.captured_at,datetime.fromisoformat("2026-08-01T22:35:00+00:00")); self.assertEqual(len(position.evidence_sha256),64)

    def test_normalized_summary_round_trips_without_merging_fees_into_cost(self):
        position=read_activity_positions(ACTIVITY_FIXTURE,(self.market_result(),))[0]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"positions.csv"; write_position_summary(path,(position,)); restored=read_positions(path)[0]
        self.assertEqual(restored,position); self.assertEqual(restored.average_cost,Decimal("0.49")); self.assertEqual(restored.entry_fees,Decimal("0.04"))

    def test_no_position_zero_balance_and_settlement_are_excluded(self):
        rows=self.rows(); rows[1]["Amount_In_Dollars"]="10"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"activity.csv"; self.write_rows(path,rows); positions=read_activity_positions(path,(self.market_result(),))
        self.assertEqual(positions,())

    def test_no_side_is_preserved(self):
        rows=[self.rows()[0]]; rows[0]["Direction"]="No"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"activity.csv"; self.write_rows(path,rows); position=read_activity_positions(path,(self.market_result(),))[0]
        self.assertEqual(position.side,MarketSide.NO)

    def test_malformed_unknown_duplicate_and_overclosed_activity_fail_closed(self):
        variants=[]
        malformed=self.rows()[:1]; malformed[0]["Direction"]="Maybe"; variants.append(malformed)
        unknown=self.rows()[:1]; unknown[0]["Market_Ticker"]="UNKNOWN"; variants.append(unknown)
        duplicate=self.rows()[:1]*2; variants.append(duplicate)
        overclosed=self.rows()[:2]; overclosed[1]["Amount_In_Dollars"]="11"; variants.append(overclosed)
        with tempfile.TemporaryDirectory() as tmp:
            for index,rows in enumerate(variants):
                path=Path(tmp)/f"activity-{index}.csv"; self.write_rows(path,rows)
                with self.subTest(index=index):
                    with self.assertRaises(ValueError): read_activity_positions(path,(self.market_result(),))


class LiquidationTests(unittest.TestCase):
    def test_yes_and_no_single_level_liquidation(self):
        result=adapted(bid_book())
        yes=analyze_liquidation(position_for(result,MarketSide.YES,Decimal(2),Decimal("0.50")),result.observation)
        no=analyze_liquidation(position_for(result,MarketSide.NO,Decimal(2),Decimal("0.50")),result.observation)
        self.assertEqual((yes.gross_proceeds,yes.average_exit_price,yes.executable_profit_loss),(Decimal("1.0800"),Decimal("0.5400"),Decimal("0.0800")))
        self.assertEqual((no.gross_proceeds,no.average_exit_price,no.executable_profit_loss),(Decimal("0.8800"),Decimal("0.4400"),Decimal("-0.1200")))

    def test_multilevel_and_partial_liquidation_do_not_extrapolate(self):
        result=adapted(bid_book(yes=(("0.5400","2"),("0.5000","3"))))
        full=analyze_liquidation(position_for(result,MarketSide.YES,Decimal(5),Decimal("0.48")),result.observation)
        partial=analyze_liquidation(position_for(result,MarketSide.YES,Decimal(6),Decimal("0.48")),result.observation)
        self.assertEqual((full.gross_proceeds,full.average_exit_price,full.marginal_exit_price),(Decimal("2.5800"),Decimal("0.5160"),Decimal("0.5000")))
        self.assertEqual((partial.executable_quantity,partial.unpriced_quantity,partial.gross_proceeds),(Decimal(5),Decimal(1),Decimal("2.5800")))
        self.assertEqual(partial.executable_cost_basis,Decimal("2.40")); self.assertEqual(partial.executable_profit_loss,Decimal("0.1800")); self.assertIn("executable quantity",partial.limitation)

    def test_no_liquidity_and_closed_market_withhold_value_and_profit_loss(self):
        open_result=adapted(bid_book(yes=(),no=(("0.44","2"),)))
        unavailable=analyze_liquidation(position_for(open_result,MarketSide.YES,Decimal(1),Decimal("0.5")),open_result.observation)
        closed_result=adapted(bid_book(),payload=market_payload(status="closed"))
        closed=analyze_liquidation(position_for(closed_result,MarketSide.YES,Decimal(1),Decimal("0.5")),closed_result.observation)
        for analysis in (unavailable,closed):
            self.assertIsNone(analysis.gross_proceeds); self.assertIsNone(analysis.executable_profit_loss); self.assertEqual(analysis.unpriced_quantity,Decimal(1))


class BoardAndWorkflowTests(unittest.TestCase):
    def bundle_case(self, **changes):
        result=adapted(bid_book())
        case={"entry_id":"case:1","game":"Away Club at Home Club","scheduled_start":START.isoformat(),"proposition":"Home Club wins","side":"yes","quantity":"2","fee_per_contract":"0","forecast":forecast().to_dict(),"market_result":result.to_dict()}
        case.update(changes); return case

    def test_html_generation_is_deterministic_sortable_and_contains_positions_diagnostics(self):
        result=adapted(bid_book()); opportunity=complete_opportunity(position_for(result,quantity=Decimal(2),cost=Decimal("0.5")),result=result)
        with tempfile.TemporaryDirectory() as tmp:
            one=Path(tmp)/"one.html"; two=Path(tmp)/"two.html"
            first=render_opportunity_board((entry_for(opportunity),),generated_at=AT,output_path=one)
            second=render_opportunity_board((entry_for(opportunity),),generated_at=AT,output_path=two)
            self.assertEqual(first,second); self.assertIn("position-chip",first); self.assertIn("View details",first); self.assertIn("querySelectorAll('th')",first)
            self.assertIn("Forecast Capture",first); self.assertIn("August 1, 2026 7:00 AM CDT",first); self.assertIn("Fri Jul 31 6:00 PM",first)
        self.assertIn("Position Liquidation",first); self.assertIn("fully_liquidatable",first)
        self.assertIn("Gross Expected Profit",first); self.assertIn("Gross Return",first); self.assertIn("zero-fee-fixture-v1",first)
        self.assertIn("$1.08",first); self.assertIn("$0.08",first)

    def test_html_groups_two_propositions_into_one_operator_game_row(self):
        opportunity=complete_opportunity(); entries=(entry_for(opportunity,"entry:home"),entry_for(opportunity,"entry:away"))
        with tempfile.TemporaryDirectory() as tmp: document=render_opportunity_board(entries,generated_at=AT,output_path=Path(tmp)/"board.html")
        self.assertEqual(document.count('<tr class="game-row'),1)
        self.assertIn("Away Club @ Home Club",document)
        self.assertNotIn("Forecast Probability</th>",document)
        self.assertIn("<th>DRatings</th>",document); self.assertIn("<th>Kalshi</th>",document); self.assertIn("<th>Gross Edge</th>",document)
        self.assertIn("gross before Kalshi fees",document); self.assertIn("Production net EV is not yet available",document)

    def test_html_reports_market_book_capture_range(self):
        opportunity=complete_opportunity()
        first=entry_for(opportunity,"entry:one")
        entries=(first,replace(entry_for(opportunity,"entry:two"),market_captured_at=first.market_captured_at+timedelta(seconds=3)))
        with tempfile.TemporaryDirectory() as tmp: document=render_opportunity_board(entries,generated_at=AT,output_path=Path(tmp)/"board.html")
        self.assertIn("Market books captured",document)
        self.assertIn("July 31, 2026 10:00:00 AM–10:00:03 AM CDT",document)

    def test_html_escapes_hostile_display_and_diagnostic_content(self):
        hostile=BoardEntry("hostile:1",OpportunityState.REJECTED,"<script>alert(1)</script>",START,"<b>claim</b>",None,None,None,None,None,None,None,("<img src=x onerror=1>",),(("Provenance","</pre><script>evil()</script>"),))
        with tempfile.TemporaryDirectory() as tmp: document=render_opportunity_board((hostile,),generated_at=AT,output_path=Path(tmp)/"board.html")
        self.assertNotIn("<script>alert(1)</script>",document); self.assertNotIn("<script>evil()</script>",document); self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;",document)

    def test_build_entries_exposes_missing_forecast_and_missing_market(self):
        missing_forecast=build_entries({"cases":[self.bundle_case(forecast=None)]},())
        missing_market=build_entries({"cases":[self.bundle_case(market_result=None)]},())
        self.assertEqual(missing_forecast[0].state,OpportunityState.PARTIAL); self.assertIn("missing forecast",missing_forecast[0].issues[0]); self.assertEqual(missing_market[0].state,OpportunityState.PARTIAL)

    def test_build_entries_exposes_ambiguous_and_non_executable_market(self):
        ambiguous=adapted(payload=market_payload(yes_sub_title=None))
        ambiguous_entry=build_entries({"cases":[self.bundle_case(market_result=ambiguous.to_dict())]},())[0]
        closed=adapted(bid_book(),payload=market_payload(status="closed"))
        closed_entry=build_entries({"cases":[self.bundle_case(market_result=closed.to_dict())]},())[0]
        self.assertEqual(ambiguous_entry.state,OpportunityState.AMBIGUOUS); self.assertEqual(closed_entry.state,OpportunityState.NON_EXECUTABLE)

    def test_rejected_state_and_issue_render_without_authoritative_opportunity(self):
        rejected=adapted(payload={"ticker":"KXMLB-MALFORMED"})
        entry=build_entries({"cases":[self.bundle_case(market_result=rejected.to_dict())]},())[0]
        with tempfile.TemporaryDirectory() as tmp:
            document=render_opportunity_board((entry,),generated_at=AT,output_path=Path(tmp)/"board.html")
        self.assertEqual(entry.state,OpportunityState.REJECTED); self.assertIsNone(entry.opportunity); self.assertIn("rejected",document); self.assertIn("ticker and title are required",document)

    def test_partial_observation_and_notification_counts_are_visible(self):
        partial=adapted()
        entry=build_entries({"cases":[self.bundle_case(market_result=partial.to_dict())]},())[0]
        self.assertEqual(entry.state,OpportunityState.NON_EXECUTABLE); lines=notification_lines((entry,)); self.assertIn("1 analyses processed",lines); self.assertIn("0 existing positions",lines); self.assertIn("1 incomplete or non-executable analyses",lines)

    def test_manual_workflow_generates_single_primary_board_and_concise_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/"bundle.json"; output=Path(tmp)/"Opportunity_Board.html"; positions=Path(tmp)/"positions.csv"; PositionInputTests().write_positions(positions,[])
            bundle.write_text(json.dumps({"schema_version":BUNDLE_SCHEMA_VERSION,"generated_at":AT.isoformat(),"cases":[self.bundle_case()]},sort_keys=True),encoding="utf-8")
            entries=run(bundle,output,positions)
            self.assertEqual(len(entries),1); self.assertTrue(output.exists()); self.assertIn("Opportunity Board",output.read_text(encoding="utf-8"))

    def test_bundle_schema_validation_rejects_missing_unsupported_duplicate_and_credentials(self):
        valid={"schema_version":BUNDLE_SCHEMA_VERSION,"generated_at":AT.isoformat(),"cases":[self.bundle_case()]}
        self.assertEqual(validate_bundle(valid),valid); self.assertEqual(validate_bundle(json.loads(json.dumps(valid,sort_keys=True))),valid)
        invalids=(
            {"generated_at":AT.isoformat(),"cases":[]},
            {**valid,"schema_version":"future-v2"},
            {**valid,"cases":[self.bundle_case(),self.bundle_case()]},
            {**valid,"credentials":"secret"},
        )
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError): validate_bundle(invalid)

    def test_unknown_position_reference_and_incompatible_forecast_market_fail(self):
        result=adapted(bid_book()); unknown=Position("market-series:kalshi:UNKNOWN",result.series.proposition_id,result.observation.canonical_event_id,MarketSide.YES,Decimal(1),Decimal("0.5"))
        with self.assertRaises(ValueError): build_entries({"cases":[self.bundle_case()]},(unknown,))
        entry=build_entries({"cases":[self.bundle_case(forecast=forecast(event_id="mlb:999").to_dict())]},())[0]
        self.assertEqual(entry.state,OpportunityState.NON_EXECUTABLE); self.assertIn("mismatch",entry.issues[0])

    def test_non_open_market_still_rejects_incompatible_position_mapping(self):
        closed=adapted(bid_book(),payload=market_payload(status="closed")); bad=Position(closed.series.series_id,"winner:mlb:777:other",closed.observation.canonical_event_id,MarketSide.YES,Decimal(1),Decimal("0.5"))
        with self.assertRaises(ValueError): build_entries({"cases":[self.bundle_case(market_result=closed.to_dict())]},(bad,))

    def test_notifications_reconcile_exactly_with_rendered_states(self):
        complete=build_entries({"cases":[self.bundle_case()]},())[0]
        ambiguous_result=adapted(payload=market_payload(yes_sub_title=None))
        ambiguous=build_entries({"cases":[self.bundle_case(entry_id="case:2",market_result=ambiguous_result.to_dict())]},())[0]
        lines=notification_lines((complete,ambiguous))
        self.assertIn("2 analyses processed",lines); self.assertIn("1 positive gross-edge analyses",lines); self.assertIn("1 ambiguous reconciliations",lines); self.assertIn("0 incomplete or non-executable analyses",lines)

    def test_temporal_selection_is_strict_and_latest_market_still_liquidates_position(self):
        game,schedule=facts(); pregame=adapted(bid_book())
        inplay=adapt_market(market_payload(),games=(game,),schedules=(schedule,),collected_at=START+timedelta(seconds=1),orderbook_payload=bid_book(),orderbook_collected_at=START+timedelta(seconds=1))
        at_start=adapt_market(market_payload(),games=(game,),schedules=(schedule,),collected_at=START,orderbook_payload=bid_book(),orderbook_collected_at=START)
        comparison,latest=select_market_results((pregame,inplay),START)
        self.assertEqual(comparison.observation.observation_id,pregame.observation.observation_id); self.assertEqual(latest.observation.observation_id,inplay.observation.observation_id)
        self.assertIsNone(select_market_results((at_start,),START)[0])
        self.assertIsNone(select_market_results((pregame,),None)[0])
        case=self.bundle_case(market_result=None,market_results=[pregame.to_dict(),inplay.to_dict()])
        position=position_for(inplay,quantity=Decimal(2),cost=Decimal("0.50"))
        entry=build_entries({"cases":[case]},(position,))[0]
        self.assertIsNotNone(entry.opportunity); self.assertEqual(entry.opportunity.market_observation_id,pregame.observation.observation_id)
        self.assertEqual(entry.display_liquidation.gross_proceeds,Decimal("1.0800")); self.assertEqual(entry.market_captured_at,inplay.observation.collected_at)

    def test_inplay_only_suppresses_gross_edge_but_retains_liquidation_and_count(self):
        game,schedule=facts(); captured=START+timedelta(seconds=1)
        inplay=adapt_market(market_payload(),games=(game,),schedules=(schedule,),collected_at=captured,orderbook_payload=bid_book(),orderbook_collected_at=captured)
        position=position_for(inplay,quantity=Decimal(2),cost=Decimal("0.50"))
        entry=build_entries({"cases":[self.bundle_case(market_result=inplay.to_dict())]},(position,))[0]
        self.assertIsNone(entry.opportunity); self.assertEqual(entry.display_liquidation.gross_proceeds,Decimal("1.0800"))
        self.assertIn("temporally comparable",entry.issues[0]); self.assertIn("0 positive gross-edge analyses",notification_lines((entry,)))
        with tempfile.TemporaryDirectory() as tmp: document=render_opportunity_board((entry,),generated_at=captured,output_path=Path(tmp)/"board.html")
        self.assertIn("In Play",document); self.assertIn("<th>Gross Edge</th>",document)

    def test_lifecycle_status_precedes_missing_depth(self):
        settled=adapted(payload=market_payload(status="settled")); suspended=adapted(bid_book(),payload=market_payload(status="suspended"))
        entries=build_entries({"cases":[self.bundle_case(entry_id="settled",market_result=settled.to_dict()),self.bundle_case(entry_id="suspended",market_result=suspended.to_dict())]},())
        with tempfile.TemporaryDirectory() as tmp:
            settled_doc=render_opportunity_board((entries[0],),generated_at=AT,output_path=Path(tmp)/"settled.html")
            suspended_doc=render_opportunity_board((entries[1],),generated_at=AT,output_path=Path(tmp)/"suspended.html")
        self.assertIn("status-settled\">Settled",settled_doc); self.assertNotIn("status-missing-depth\">Missing Depth",settled_doc)
        self.assertIn("status-suspended\">Suspended",suspended_doc)
        self.assertIn(".status-in-play",settled_doc); self.assertIn(".status-settled",settled_doc); self.assertIn(".status-suspended",settled_doc)

    def test_rejected_side_keeps_both_canonical_lines_and_game_is_not_complete(self):
        complete=build_entries({"cases":[self.bundle_case(entry_id="home")]},())[0]
        rejected=adapted(bid_book(no=(("0.43","2"),)),payload=market_payload(yes="away",ticker="KXMLB-AWAY"))
        rejected_entry=build_entries({"cases":[self.bundle_case(entry_id="away",proposition="Away Club wins",market_result=rejected.to_dict())]},())[0]
        with tempfile.TemporaryDirectory() as tmp: document=render_opportunity_board((complete,rejected_entry),generated_at=AT,output_path=Path(tmp)/"board.html")
        body=document.split("<tbody>",1)[1]
        self.assertLess(body.find("Away Club</span>"),body.find("Home Club</span>"))
        self.assertIn("status-rejected\">Rejected",document); self.assertNotIn("status-complete\">Complete",document)

    def test_canonical_away_home_order_overrides_provider_orders_and_places_position(self):
        home=adapted(bid_book()); away=adapted(bid_book(),payload=market_payload(yes="away",ticker="KXMLB-20260731-AWYHME-AWY"))
        away_case=self.bundle_case(entry_id="away",proposition="Away Club wins",market_result=away.to_dict())
        home_case=self.bundle_case(entry_id="home",market_result=home.to_dict())
        position=position_for(away,quantity=Decimal(3),cost=Decimal("0.40"))
        entries=build_entries({"cases":[home_case,away_case]},(position,))
        with tempfile.TemporaryDirectory() as tmp: document=render_opportunity_board(entries,generated_at=AT,output_path=Path(tmp)/"board.html")
        body=document.split("<tbody>",1)[1]
        self.assertLess(body.find("Away Club</span>"),body.find("Home Club</span>"))
        self.assertIn("● Away Club YES",document)
        self.assertIn('&quot;semantic&quot;:&quot;participant-wins:team:home&quot;',document)

    def test_offsetting_position_components_attach_only_to_matching_side_rows(self):
        result=adapted(bid_book()); positions=(position_for(result,MarketSide.YES,Decimal(2),Decimal("0.5")),position_for(result,MarketSide.NO,Decimal(1),Decimal("0.6")))
        yes=self.bundle_case(entry_id="case:yes",side="yes"); no=self.bundle_case(entry_id="case:no",side="no")
        entries=build_entries({"cases":[yes,no]},positions)
        self.assertEqual([(entry.opportunity.position.side,entry.opportunity.position.quantity) for entry in entries],[(MarketSide.YES,Decimal(2)),(MarketSide.NO,Decimal(1))])


if __name__ == "__main__": unittest.main()
