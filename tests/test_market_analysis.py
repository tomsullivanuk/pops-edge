import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from event_contracts import ContractError, Evidence, NativeIdentifier, Provenance, ReasonCode, ReconciliationResult, ValidationReason
from forecast_contracts import AssumptionDisclosure, ForecastDistribution, ForecastObservation, ForecastOutcome, ProbabilityScale, ProviderReportedAssumptions, PublishedProbability
from kalshi_mlb_adapter import adapt_market,adapt_markets
from collect_kalshi_mlb_orderbooks import collect_orderbooks
from market_contracts import ComponentEvidence, MarketAdapterOutcome, MarketProposition, MarketSide, MarketStatus, PriceEvidenceKind
from market_valuation import ExecutionStatus, FlatPerContractFeeModel, ZeroFeeModel, executable_acquisition, value_market
from mlb_contracts import MLBTeamRef, ScheduleObservation, make_mlb_game

UTC=timezone.utc; AT=datetime(2026,7,31,15,tzinfo=UTC); START=datetime(2026,7,31,23,tzinfo=UTC)

def facts(game_pk=777):
    away=MLBTeamRef("team:away",1,"Away Club","AWY"); home=MLBTeamRef("team:home",2,"Home Club","HME")
    game=make_mlb_game(game_pk=game_pk,away_team=away,home_team=home,season="2026")
    schedule=ScheduleObservation(f"schedule:{game_pk}",game.event.canonical_event_id,START,Provenance("mlb",f"schedule:{game_pk}",game.event.canonical_event_id,AT))
    return game,schedule

def market_payload(*,yes="home",ticker="KXMLB-20260731-AWYHME-HME",status="open",**changes):
    yes_label,no_label=("Home Club","Away Club") if yes=="home" else ("Away Club","Home Club")
    value={"ticker":ticker,"event_ticker":"KXMLB-20260731-AWYHME","title":"Away Club at Home Club winner?","yes_sub_title":yes_label,"no_sub_title":no_label,"status":status,"close_time":"2026-07-31T23:00:00Z","yes_bid_dollars":"0.54","yes_ask_dollars":"0.56","no_bid_dollars":"0.44","no_ask_dollars":"0.46","last_price_dollars":"0.55","volume_fp":"100","open_interest_fp":"50","rules_primary":f"Pays $1 if {yes_label} wins."}
    value.update(changes); return value

def bid_book(*,ticker=None,yes=(("0.5400","5.00"),),no=(("0.4400","2.00"),("0.4000","3.00"))):
    value={"orderbook_fp":{"yes_dollars":[list(x) for x in yes],"no_dollars":[list(x) for x in no]}}
    if ticker is not None: value["ticker"]=ticker
    return value

def adapted(book=None,book_at=None,payload=None):
    game,schedule=facts()
    return adapt_market(payload or market_payload(),games=(game,),schedules=(schedule,),collected_at=AT,orderbook_payload=book,orderbook_collected_at=book_at)

def forecast(*,include_away=True,event_id="mlb:777",observation_id="forecast:1"):
    game,_=facts(); event=game.event
    probabilities=[PublishedProbability(ForecastOutcome("team:home","participant-wins:team:home",event_id),Decimal("0.6"),"60%",0,ProbabilityScale.PERCENT)]
    if include_away: probabilities.append(PublishedProbability(ForecastOutcome("team:away","participant-wins:team:away",event_id),Decimal("0.4"),"40%",0,ProbabilityScale.PERCENT))
    # A missing acquired outcome is represented by a different complete outcome, not an invalid one-outcome distribution.
    if not include_away: probabilities.append(PublishedProbability(ForecastOutcome("team:other","participant-wins:team:other",event_id),Decimal("0.4"),"40%",0,ProbabilityScale.PERCENT))
    dist=ForecastDistribution(tuple(probabilities)); matched=event if event_id==event.canonical_event_id else replace(event,canonical_event_id=event_id)
    rec=ReconciliationResult.matched(NativeIdentifier("forecast-record",observation_id),matched,evidence=(Evidence("matchup","Away Club at Home Club"),))
    return ForecastObservation(observation_id,"version:1",rec,dist,ProviderReportedAssumptions(AssumptionDisclosure.UNKNOWN),AT,Provenance("forecast-provider",observation_id,event_id,AT))

def ambiguous_forecast():
    game,_=facts(); other=replace(game.event,canonical_event_id="mlb:778")
    dist=ForecastDistribution((PublishedProbability(ForecastOutcome("team:away","participant-wins:team:away",None),Decimal("0.4"),"40%",0,ProbabilityScale.PERCENT),PublishedProbability(ForecastOutcome("team:home","participant-wins:team:home",None),Decimal("0.6"),"60%",0,ProbabilityScale.PERCENT)))
    rec=ReconciliationResult.ambiguous(NativeIdentifier("forecast-record","forecast:ambiguous"),(game.event,other),evidence=(Evidence("matchup","Away Club at Home Club"),),reasons=(ValidationReason(ReasonCode.AMBIGUOUS_CANDIDATES,"two games remain"),))
    return ForecastObservation("forecast:ambiguous","version:1",rec,dist,ProviderReportedAssumptions(AssumptionDisclosure.UNKNOWN),AT,Provenance("forecast-provider","forecast:ambiguous",None,AT))

class MarketIdentityAndAdapterTests(unittest.TestCase):
    def test_winner_proposition_is_provider_neutral_and_deterministic(self):
        p=MarketProposition.winner("mlb:777","team:home"); self.assertEqual(p.proposition_id,"winner:mlb:777:team:home"); self.assertNotIn("ticker",p.__dataclass_fields__); self.assertEqual(p,p.from_json(p.to_json()))

    def test_distinct_relisted_contracts_share_proposition_but_not_series(self):
        a=adapted(bid_book()); b=adapted(bid_book(),payload=market_payload(ticker="KXMLB-RELIST-HME"))
        self.assertEqual(a.proposition,b.proposition); self.assertNotEqual(a.series.series_id,b.series.series_id)

    def test_mutable_status_and_quotes_do_not_change_series_identity(self):
        a=adapted(); b=adapted(payload=market_payload(status="closed",yes_bid_dollars="0.68",yes_ask_dollars="0.70",no_bid_dollars="0.28",no_ask_dollars="0.30"))
        self.assertEqual(a.series.series_id,b.series.series_id); self.assertNotIn("status",a.series.__dataclass_fields__); self.assertNotIn("quotes",a.series.__dataclass_fields__)

    def test_observation_is_immutable_and_round_trips(self):
        obs=adapted(bid_book()).observation
        with self.assertRaises(FrozenInstanceError): obs.status=MarketStatus.CLOSED
        self.assertEqual(obs,obs.from_json(obs.to_json()))

    def test_yes_home_and_yes_away_map_explicit_complementary_participants(self):
        home=adapted(bid_book()); away=adapted(bid_book(),payload=market_payload(yes="away"))
        self.assertEqual(home.series.yes_semantic.participant_id,"team:home"); self.assertEqual(home.series.no_semantic.participant_id,"team:away")
        self.assertEqual(away.series.yes_semantic.participant_id,"team:away"); self.assertEqual(away.series.no_semantic.participant_id,"team:home")

    def test_current_kalshi_mlb_binary_no_label_resolves_explicit_complement(self):
        payload=market_payload(ticker="KXMLBGAME-26JUL311905PHIBAL-PHI",title="Philadelphia vs Baltimore Winner?",yes_sub_title="Philadelphia",no_sub_title="Philadelphia",rules_primary="If Philadelphia wins, then the market resolves to Yes.",notional_value_dollars="1.0000")
        game,schedule=facts(); game=replace(game,away_team=replace(game.away_team,display_name="Philadelphia Phillies"),home_team=replace(game.home_team,display_name="Baltimore Orioles"))
        result=adapt_market(payload,games=(game,),schedules=(schedule,),collected_at=AT,orderbook_payload=bid_book(ticker=payload["ticker"]))
        self.assertEqual(result.outcome,MarketAdapterOutcome.COMPLETE);self.assertEqual(result.series.yes_semantic.provider_label,"Philadelphia");self.assertEqual(result.series.no_semantic.participant_id,"team:home")

    def test_missing_or_incompatible_side_evidence_emits_no_series(self):
        missing=adapted(payload=market_payload(yes_sub_title=None)); bad_no=adapted(payload=market_payload(no_sub_title="Another Club"))
        self.assertEqual(missing.outcome,MarketAdapterOutcome.AMBIGUOUS); self.assertIsNone(missing.series); self.assertEqual(bad_no.outcome,MarketAdapterOutcome.REJECTED); self.assertIsNone(bad_no.series)

    def test_settlement_disagreement_and_missing_rules_fail_closed(self):
        conflict=adapted(payload=market_payload(rules_primary="Pays $1 if Away Club wins.")); missing=adapted(payload=market_payload(rules_primary=None))
        self.assertEqual(conflict.outcome,MarketAdapterOutcome.REJECTED); self.assertEqual(missing.outcome,MarketAdapterOutcome.REJECTED)

    def test_ambiguous_doubleheader_preserves_candidates_without_series(self):
        game,schedule=facts(); other,other_schedule=facts(778); other_schedule=replace(other_schedule,scheduled_start=schedule.scheduled_start)
        result=adapt_market(market_payload(),games=(game,other),schedules=(schedule,other_schedule),collected_at=AT)
        self.assertEqual(result.outcome,MarketAdapterOutcome.AMBIGUOUS); self.assertIsNone(result.series); self.assertEqual(len(result.candidate_event_ids),2)

    def test_explicit_nonmatching_date_never_falls_back_to_participant(self):
        result=adapted(payload=market_payload(close_time="2026-08-01T23:00:00Z"));self.assertEqual(result.outcome,MarketAdapterOutcome.REJECTED);self.assertIsNone(result.series);self.assertEqual(result.issues[0].code,"no-matching-event")

    def test_both_structured_sides_and_aware_time_are_mandatory(self):
        missing_no=adapted(payload=market_payload(no_sub_title=None));foreign_no=adapted(payload=market_payload(no_sub_title="Third Club"));missing_time=adapted(payload=market_payload(close_time=None));malformed=adapted(payload=market_payload(close_time="not-a-time"))
        self.assertTrue(all(item.series is None for item in (missing_no,foreign_no,missing_time,malformed)));self.assertEqual([item.issues[0].code for item in (missing_no,foreign_no,missing_time,malformed)],["missing-no-side","no-matching-event","missing-market-time","malformed-market-time"])

    def test_schedule_instant_rule_is_timezone_safe_and_catalog_order_independent(self):
        game,schedule=facts();same_instant=market_payload(close_time="2026-07-31T19:00:00-04:00");other_date=market_payload(ticker="OTHER",close_time="2026-07-30T19:00:00-04:00")
        matched=adapt_market(same_instant,games=(game,),schedules=(schedule,),collected_at=AT);self.assertIsNotNone(matched.series)
        forward=adapt_markets((other_date,same_instant),games=(game,),schedules=(schedule,),collected_at=AT);reverse=adapt_markets((same_instant,other_date),games=(game,),schedules=(schedule,),collected_at=AT)
        self.assertEqual({item.provider_market_id:item.outcome for item in forward},{item.provider_market_id:item.outcome for item in reverse})

    def test_three_hour_expiration_rule_maps_exact_march_market_uniquely(self):
        game,schedule=facts();schedule=replace(schedule,scheduled_start=datetime(2026,3,26,0,5,tzinfo=UTC));payload=market_payload(ticker="KXMLBGAME-26MAR252005NYYSF-SF",close_time="2026-03-26T03:05:00Z",expected_expiration_time="2026-03-26T03:05:00Z")
        result=adapt_market(payload,games=(game,),schedules=(schedule,),collected_at=AT);self.assertIsNotNone(result.series);self.assertEqual(result.series.ticker,"KXMLBGAME-26MAR252005NYYSF-SF")

    def test_fixed_point_bids_preserve_raw_side_price_and_exact_derived_offer(self):
        obs=adapted(bid_book()).observation; yes=[x for x in obs.order_book if x.acquisition_side is MarketSide.YES]
        self.assertEqual([(x.provider_book_side,x.provider_price,x.acquisition_price,x.quantity) for x in yes],[(MarketSide.NO,Decimal("0.4400"),Decimal("0.5600"),Decimal("2.00")),(MarketSide.NO,Decimal("0.4000"),Decimal("0.6000"),Decimal("3.00"))])
        self.assertTrue(all(x.evidence_kind is PriceEvidenceKind.DERIVED_FROM_OPPOSITE_BID for x in yes)); self.assertTrue(all(x.transformation for x in yes))

    def test_asymmetric_book_proves_no_side_reversal_or_double_complement(self):
        payload=market_payload(yes_bid_dollars="0.17",yes_ask_dollars="0.38",no_bid_dollars="0.62",no_ask_dollars="0.83")
        obs=adapted(bid_book(yes=(("0.1700","7"),),no=(("0.6200","3"),("0.5100","4"))),payload=payload).observation
        yes=[x.acquisition_price for x in obs.order_book if x.acquisition_side is MarketSide.YES]; no=[x.acquisition_price for x in obs.order_book if x.acquisition_side is MarketSide.NO]
        self.assertEqual(yes,[Decimal("0.3800"),Decimal("0.4900")]); self.assertEqual(no,[Decimal("0.8300")])

    def test_matching_quote_book_is_complete_and_missing_or_empty_book_partial(self):
        self.assertEqual(adapted(bid_book()).outcome,MarketAdapterOutcome.COMPLETE)
        self.assertEqual(adapted().outcome,MarketAdapterOutcome.PARTIAL); self.assertEqual(adapted({"orderbook_fp":{"yes_dollars":[],"no_dollars":[]}}).outcome,MarketAdapterOutcome.PARTIAL)

    def test_contradictory_quote_book_and_malformed_fixed_point_reject(self):
        conflict=adapted(bid_book(no=(("0.4300","2"),))); malformed=adapted(bid_book(no=(("not-a-price","2"),)))
        self.assertEqual(conflict.outcome,MarketAdapterOutcome.REJECTED); self.assertEqual(malformed.outcome,MarketAdapterOutcome.REJECTED)

    def test_one_sided_book_is_partial_and_other_side_remains_unavailable(self):
        result=adapted(bid_book(yes=(),no=(("0.4400","2"),)))
        self.assertEqual(result.outcome,MarketAdapterOutcome.PARTIAL); self.assertEqual(executable_acquisition(result.observation,MarketSide.NO,Decimal(1)).status,ExecutionStatus.UNAVAILABLE)

    def test_separate_component_timing_digests_and_large_spread_are_preserved(self):
        later=AT+timedelta(hours=4); obs=adapted(bid_book(),later).observation
        self.assertEqual(obs.component_timing_spread_seconds,Decimal("14400.0")); self.assertEqual([x.collected_at for x in obs.component_evidence],[AT,later]); self.assertEqual(len({x.raw_response_sha256 for x in obs.component_evidence}),2)

    def test_book_before_metadata_preserves_actual_component_chronology(self):
        later=AT+timedelta(minutes=1); game,schedule=facts(); payload=market_payload()
        result=adapt_market(payload,games=(game,),schedules=(schedule,),collected_at=AT,metadata_collected_at=later,orderbook_payload=bid_book(),orderbook_collected_at=AT)
        self.assertEqual(result.observation.collected_at,AT)
        self.assertEqual([item.collected_at for item in result.observation.component_evidence],[later,AT])
        self.assertEqual(result.observation.component_timing_spread_seconds,Decimal("60.0"))

    def test_component_market_mismatch_and_impossible_chronology_reject(self):
        mismatch=adapted(bid_book(ticker="OTHER")); chronology=adapted(bid_book(),AT-timedelta(seconds=1))
        self.assertEqual(mismatch.outcome,MarketAdapterOutcome.REJECTED); self.assertEqual(chronology.outcome,MarketAdapterOutcome.REJECTED)

    def test_bounded_orderbook_collection_preserves_separate_times_and_digests(self):
        class Response:
            status_code=200
            def __init__(self,payload): self._payload=payload; self.content=json.dumps(payload,sort_keys=True).encode()
            def json(self): return self._payload
        class Client:
            def __init__(self): self.calls=[]
            def orderbook(self,ticker): self.calls.append(ticker); return Response(bid_book())
        times=iter((AT,AT+timedelta(seconds=1))); client=Client()
        captures=collect_orderbooks(("B","A"),client=client,clock=lambda:next(times))
        self.assertEqual(client.calls,["A","B"]); self.assertEqual([item.collected_at for item in captures],[AT,AT+timedelta(seconds=1)])
        self.assertTrue(all(len(item.raw_response_sha256)==64 and len(item.canonical_sha256)==64 for item in captures))
        self.assertEqual([item.payload["ticker"] for item in captures],["A","B"])

class ExecutionAndValuationTests(unittest.TestCase):
    def test_non_open_operational_states_are_not_executable(self):
        for status in ("closed","paused","settled","cancelled","mystery"):
            with self.subTest(status=status):
                obs=adapted(bid_book(),payload=market_payload(status=status)).observation; execution=executable_acquisition(obs,MarketSide.YES,Decimal(1)); self.assertEqual(execution.status,ExecutionStatus.UNAVAILABLE); self.assertEqual(execution.filled_quantity,0)

    def test_invalid_quantity_rejected_and_no_liquidity_unavailable(self):
        obs=adapted().observation
        for quantity in (Decimal(0),Decimal(-1)):
            with self.assertRaises(ContractError): executable_acquisition(obs,MarketSide.YES,quantity)
        self.assertEqual(executable_acquisition(obs,MarketSide.YES,Decimal(1)).status,ExecutionStatus.UNAVAILABLE)

    def test_one_level_exact_exhaustion_and_multilevel_partial_fill(self):
        obs=adapted(bid_book()).observation
        exact=executable_acquisition(obs,MarketSide.YES,Decimal(2)); self.assertEqual(exact.status,ExecutionStatus.FULL); self.assertEqual(exact.total_cost,Decimal("1.1200"))
        partial=executable_acquisition(obs,MarketSide.YES,Decimal(6)); self.assertEqual((partial.filled_quantity,partial.unfilled_quantity,partial.total_cost,partial.average_price,partial.worst_price),(Decimal(5),Decimal(1),Decimal("2.9200"),Decimal("0.5840"),Decimal("0.6000")))

    def test_yes_and_no_depth_consumption_use_their_own_executable_offers(self):
        obs=adapted(bid_book()).observation
        self.assertEqual(executable_acquisition(obs,MarketSide.YES,Decimal(1)).average_price,Decimal("0.5600")); self.assertEqual(executable_acquisition(obs,MarketSide.NO,Decimal(1)).average_price,Decimal("0.4600"))

    def valuation_kwargs(self,result=None,forecast_value=None,quantity=Decimal(2)):
        result=result or adapted(bid_book()); return dict(forecast=forecast_value or forecast(),market=result.observation,proposition=result.proposition,series=result.series,quantity=quantity,event_scheduled_start=START)

    def test_hand_calculated_yes_and_no_fee_valuations(self):
        kwargs=self.valuation_kwargs(); yes=value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**kwargs); no=value_market(side=MarketSide.NO,fee_model=FlatPerContractFeeModel(Decimal("0.01")),**kwargs)
        self.assertEqual((yes.gross_expected_payout,yes.gross_acquisition_cost,yes.expected_profit,yes.expected_return_on_capital),(Decimal("1.2"),Decimal("1.1200"),Decimal("0.0800"),Decimal("0.0800")/Decimal("1.1200")))
        self.assertEqual((no.forecast_probability,no.total_fees,no.effective_acquisition_cost,no.expected_profit),(Decimal("0.4"),Decimal("0.02"),Decimal("0.9400"),Decimal("-0.1400")))
        self.assertEqual((yes.monetary_unit,yes.payout_per_winning_contract),("USD",Decimal(1)))

    def test_partial_fill_valuation_uses_executed_quantity_denominators(self):
        value=value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**self.valuation_kwargs(quantity=Decimal(6)))
        self.assertEqual((value.executable_quantity,value.unfilled_quantity,value.gross_expected_payout,value.expected_profit),(Decimal(5),Decimal(1),Decimal("3.0"),Decimal("0.0800"))); self.assertEqual(value.expected_value_per_contract,Decimal("0.0160")); self.assertTrue(value.issues)

    def test_no_requires_explicit_complementary_forecast_outcome(self):
        with self.assertRaises(ContractError): value_market(side=MarketSide.NO,fee_model=ZeroFeeModel(),**self.valuation_kwargs(forecast_value=forecast(include_away=False)))

    def test_ambiguous_forecast_reconciliation_cannot_be_valued(self):
        with self.assertRaises(ContractError): value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**self.valuation_kwargs(forecast_value=ambiguous_forecast()))

    def test_event_participant_series_and_observation_mismatches_fail(self):
        result=adapted(bid_book()); kwargs=self.valuation_kwargs(result=result)
        with self.assertRaises(ContractError): value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**{**kwargs,"forecast":forecast(event_id="mlb:999")})
        with self.assertRaises(ContractError): value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**{**kwargs,"proposition":MarketProposition.winner("mlb:777","team:away")})
        with self.assertRaises(ContractError): value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**{**kwargs,"market":replace(result.observation,series_id="market-series:kalshi:OTHER")})

    def test_fee_metadata_and_material_inputs_change_analysis_identity(self):
        kwargs=self.valuation_kwargs(); zero=value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**kwargs); fee=value_market(side=MarketSide.YES,fee_model=FlatPerContractFeeModel(Decimal("0.01")),**kwargs); quantity=value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**{**kwargs,"quantity":Decimal(1)})
        self.assertNotEqual(zero.analysis_id,fee.analysis_id); self.assertNotEqual(zero.analysis_id,quantity.analysis_id); self.assertEqual(zero,value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**kwargs)); self.assertEqual((fee.fee_quantity_basis,fee.fee_price_basis,fee.fee_rounding_rule),("executed-contracts","gross-executable-acquisition-cost-dollars","exact-no-rounding"))

    def test_fee_exact_arithmetic_has_no_hidden_rounding(self):
        value=value_market(side=MarketSide.YES,fee_model=FlatPerContractFeeModel(Decimal("0.005")),**self.valuation_kwargs(quantity=Decimal(3)))
        self.assertEqual(value.total_fees,Decimal("0.015")); self.assertEqual(value.fee_rounding_rule,"exact-no-rounding")

    def test_analysis_is_derived_immutable_and_policy_free(self):
        result=adapted(bid_book()); original=result.observation; value=value_market(side=MarketSide.YES,fee_model=ZeroFeeModel(),**self.valuation_kwargs(result=result))
        self.assertEqual(original,result.observation)
        for deferred in ("recommendation","kelly","minimum_edge","bankroll","position"):
            self.assertNotIn(deferred,value.__dataclass_fields__)

if __name__=="__main__": unittest.main()
