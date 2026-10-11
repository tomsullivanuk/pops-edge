"""Retained real catalog regressions; all acquisitions are injected/offline."""
import copy,json,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from kalshi_mlb_adapter import reconcile_market,adapt_markets,DATE_ONLY_RULE_VERSION
from mlb_stats_api import MLBStatsAPIAdapter,MLBStatsAPIResponse
from forecast_standalone_activation import initialize_activation,refresh_supporting_from_raw,canonical_postseason_authority,canonical_prospective_authority
from forecast_standalone_operations import DeploymentConfig,NamespaceArchive,OperatingMode,RetryPolicy,replay_pr17_archive,discover_and_capture_prospective
from forecast_prospective_projection import rebuild_projection,load_projection
from forecast_prospective_market_selection import load_prospective_catalog,select_prospective_market

FIXTURE=json.loads((Path(__file__).parent/'fixtures/kalshi_mlb_postseason_date_only.json').read_text())
def mlb_material():
 from forecast_standalone_activation import merge_mlb_schedule_responses
 pages=tuple(json.dumps({"dates":[day]}).encode() for day in FIXTURE["mlb"]["dates"])
 return merge_mlb_schedule_responses(pages),pages
AT=datetime(2026,10,11,17,9,14,tzinfo=timezone.utc)
def facts(payload=None):
 data=payload or FIXTURE['mlb'];raw=json.dumps(data).encode()
 return MLBStatsAPIAdapter().parse_response(MLBStatsAPIResponse('https://statsapi.mlb.com/api/v1/schedule',(),AT,200,'https://statsapi.mlb.com/api/v1/schedule',data,raw))
class DateIdentityTests(unittest.TestCase):
 def setUp(self):
  fs=facts();self.games=tuple(x.game for x in fs.games);self.schedules=tuple(x.schedule_observation for x in fs.games)
  self.market=next(m for m in FIXTURE['markets'] if m['ticker']=='KXMLBGAME-26OCT112000LADMIL-MIL')
 def match(self,m=None,g=None,s=None,**kw):return reconcile_market(m or self.market,g or self.games,s or self.schedules,allow_date_only=True,**kw)
 def test_all_real_home_and_away_markets_match_three_distinct_games(self):
  rows=adapt_markets(FIXTURE['markets'],games=self.games,schedules=self.schedules,collected_at=AT,allow_date_only=True)
  self.assertEqual(len(rows),6);self.assertTrue(all(x.series for x in rows))
  self.assertEqual({x.series.provenance.canonical_event_id for x in rows},{'mlb:849809','mlb:849812','mlb:849820'})
  self.assertTrue(all(x.series.provenance.collector_version==DATE_ONLY_RULE_VERSION for x in rows))
 def test_old_default_rejects_date_only(self):
  self.assertIsNone(reconcile_market(self.market,self.games,self.schedules)[0])
 def test_precise_time_path_preserved_with_regular_game(self):
  market=copy.deepcopy(self.market)
  for key in ('rules_primary','rules_secondary'):market[key]=market[key].replace('Oct 11, 2026','Oct 11, 2026 at 8:00 PM EDT')
  games=tuple(replace(g,game_type='R') for g in self.games)
  self.assertEqual(reconcile_market(market,games,self.schedules),reconcile_market(market,games,self.schedules,allow_date_only=True))
  self.assertEqual(reconcile_market(market,games,self.schedules)[0][0].game_pk,849809)
 def test_regular_date_only_excluded(self):self.assertIsNone(self.match(g=tuple(replace(g,game_type='R') for g in self.games))[0])
 def test_conflicting_rules_labels_and_missing_secondary_rejected(self):
  for field,value in [('rules_secondary','The following market refers to the Los Angeles D vs Milwaukee professional baseball game originally scheduled for Oct 12, 2026.'),('rules_secondary',self.market['rules_secondary'].replace('Los Angeles D vs Milwaukee','Milwaukee vs Los Angeles D')),('rules_secondary',''),('yes_sub_title','Los Angeles D'),('no_sub_title','Cleveland')]:
   with self.subTest(field=field):self.assertIsNone(self.match(m={**self.market,field:value})[0])
 def test_doubleheader_and_game_number_rejected(self):
  for updates in ({'doubleheader_designation':'Y','game_number':1},{'game_number':2,'doubleheader_designation':'Y'}):
   games=tuple(replace(g,**updates) if g.game_pk==849809 else g for g in self.games)
   with self.subTest(updates=updates):self.assertIsNone(self.match(g=games)[0])
 def test_two_same_day_matchups_are_ambiguous(self):
  game=self.games[0];duplicate=replace(game,event=replace(game.event,canonical_event_id='mlb:999999',native_identifiers=tuple(replace(x,value='999999') for x in game.event.native_identifiers)),game_pk=999999)
  sched=replace(self.schedules[0],canonical_event_id='mlb:999999',provenance=replace(self.schedules[0].provenance,canonical_event_id='mlb:999999'),scheduled_start=self.schedules[0].scheduled_start+timedelta(hours=1))
  self.assertIsNone(self.match(g=self.games+(duplicate,),s=self.schedules+(sched,))[0])
 def test_reschedule_and_multiple_schedule_instants_rejected(self):
  for evidence in [('rescheduledFromDate=2026-10-10',),('status=suspended',)]:
   schedules=tuple(replace(x,status_evidence=evidence) if x.canonical_event_id=='mlb:849809' else x for x in self.schedules)
   self.assertIsNone(self.match(s=schedules)[0])
  self.assertIsNone(self.match(blocked_event_ids=('mlb:849809',))[0])
  self.assertIsNone(self.match(s=self.schedules+(replace(self.schedules[0],scheduled_start=self.schedules[0].scheduled_start+timedelta(hours=1)),))[0])
 def test_ticker_expiration_and_occurrence_never_determine_identity(self):
  m={**self.market,'ticker':'UNTRUSTED-26OCT121200','occurrence_datetime':'1999-01-01T00:00:00Z','expected_expiration_time':'1999-01-01T00:00:00Z'}
  self.assertEqual(self.match(m=m)[0][0].game_pk,849809)
  self.assertIsNone(self.match(m={**m,'rules_primary':m['rules_primary'].replace('Oct 11','Oct 10'),'rules_secondary':m['rules_secondary'].replace('Oct 11','Oct 10')})[0])
 def test_calendar_and_raw_lineage_markers_are_blocked(self):
  from kalshi_mlb_adapter import blocked_date_only_events
  self.assertFalse(blocked_date_only_events(FIXTURE['mlb']))
  for changes in ({'officialDate':'2026-10-10'},{'rescheduleDate':'2026-10-12T00:00:00Z'},{'resumeDate':'2026-10-12T00:00:00Z'}):
   data=copy.deepcopy(FIXTURE['mlb']);data['dates'][0]['games'][0].update(changes)
   self.assertIn('mlb:849809',blocked_date_only_events(data))
 def test_bad_clock_never_falls_back_to_date_only(self):
  for clock in (' at 8:00 PM CDT',' at nonsense'):
   m=copy.deepcopy(self.market)
   for key in ('rules_primary','rules_secondary'):m[key]=m[key].replace('Oct 11, 2026','Oct 11, 2026'+clock)
   self.assertIsNone(self.match(m=m)[0])

class DateAcquisitionTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name);post=canonical_postseason_authority()[1]
  self.archive=NamespaceArchive(DeploymentConfig('date','date',OperatingMode.ACTIVATED,root/'activated/date/primary',root/'activated/date/secondary','https://fixture.invalid',RetryPolicy(1,1,1,(),0),1,root/'logs',research_protocol_ids=(post.standalone_probability_source_protocol_id,canonical_prospective_authority()[1].standalone_probability_source_protocol_id),activation_at=__import__('forecast_standalone_operations').APPROVED_ACTIVATION_AT))
  initialize_activation(self.archive,datetime(2026,10,9,23,tzinfo=timezone.utc))
 def publish(self):
  return refresh_supporting_from_raw(archive=self.archive,mlb_raw=mlb_material()[0],mlb_pages=mlb_material()[1],kalshi_raw=json.dumps({'markets':FIXTURE['markets'],'cursor':''}).encode(),collected_at=AT)
 def test_actual_catalog_maps_next_games_and_selects_only_home_yes(self):
  result=self.publish();self.assertEqual(result['mapped'],3)
  rebuild_projection(self.archive,AT);boundary,state=load_projection(self.archive,AT)
  for game_id,target in [('mlb:849809',datetime(2026,10,11,18,tzinfo=timezone.utc)),('mlb:849812',datetime(2026,10,12,15,tzinfo=timezone.utc)),('mlb:849820',datetime(2026,10,12,18,tzinfo=timezone.utc))]:
   schedule=next(x for x in state.bucket('outcome_histories') if x.canonical_event_id==game_id).observations[-1]
   series,reason=select_prospective_market(load_prospective_catalog(boundary),state.bucket('market_series'),schedule,target)
   self.assertIsNotNone(series);self.assertEqual(series.yes_semantic.participant_id,schedule.home_participant_id);self.assertEqual(reason,'current-schedule-open-market')
  self.assertEqual(state.graph,replay_pr17_archive(self.archive,analysis_boundary=AT).graph)
  self.assertEqual(canonical_prospective_authority()[1].standalone_probability_source_protocol_id,'standalone-probability-source-protocol:f5303a5af20a0478e6192c4e6bdc9d133c85700fae3a410b48c81d6c6f0af2ec')
 def test_legacy_bundle_remains_unmapped_on_replay(self):
  # Publish a version-3 bundle with no date-only series, using the established publisher.
  from forecast_standalone_activation import publish_verified_acquisition,KalshiCatalogPage
  mlb,pages=mlb_material();raw=json.dumps({'markets':FIXTURE['markets'],'cursor':''}).encode()
  import forecast_standalone_activation as a
  with patch.object(a,'ACQUISITION_UNION_RULE_VERSION','provider-pages-canonical-union-3'):
   result=refresh_supporting_from_raw(archive=self.archive,mlb_raw=mlb,mlb_pages=pages,kalshi_raw=raw,collected_at=AT,union_rule='provider-pages-canonical-union-3')
  self.assertEqual(result['mapped'],0)
  state=replay_pr17_archive(self.archive,analysis_boundary=AT);self.assertEqual(len(state.bucket('market_series')),0)
 def test_exact_target_capture_and_duplicate_calls_use_real_selected_home_market(self):
  from inspect_forecast_standalone_activation import FixtureOrderBook
  from operate_forecast_standalone_activation import execute
  self.publish();target=datetime(2026,10,11,18,tzinfo=timezone.utc);rebuild_projection(self.archive,target)
  book=FixtureOrderBook(b'{"orderbook_fp":{"yes_dollars":[["0.4900","3.00"]],"no_dollars":[["0.5000","3.00"]]}}')
  first=execute('capture-prospective',self.archive.config,clock=lambda:target,transport_factory=lambda *_:book)
  self.assertEqual(first['provider_calls'],1)
  execute('capture-prospective',self.archive.config,clock=lambda:target+timedelta(seconds=10),transport_factory=lambda *_:self.fail('duplicate provider call'))
  execute('capture-prospective',self.archive.config,clock=lambda:target+timedelta(minutes=6),transport_factory=lambda *_:self.fail('late provider call'))
  state=replay_pr17_archive(self.archive,analysis_boundary=target+timedelta(minutes=6));snapshot=state.bucket('snapshots')[0]
  self.assertEqual(snapshot.terminal_disposition.value,'captured-valid');self.assertEqual(snapshot.provider_market_id,'KXMLBGAME-26OCT112000LADMIL-MIL')
  self.assertEqual(snapshot.target_at,target);self.assertEqual(len(snapshot.attempt_ids),5)
  self.assertEqual(sum(x.provider_call_occurred for x in state.bucket('attempts')),1)
 def test_after_window_never_calls_provider_or_backfills(self):
  self.publish();after=datetime(2026,10,11,18,6,tzinfo=timezone.utc);rebuild_projection(self.archive,after)
  result=discover_and_capture_prospective(archive=self.archive,clock=lambda:after,transport_factory=lambda *_:self.fail('late quote call'))
  self.assertEqual(result.provider_request_count,0)
  state=replay_pr17_archive(self.archive,analysis_boundary=after);snapshot=state.bucket('snapshots')[0]
  self.assertEqual(snapshot.terminal_disposition.value,'missed-window');self.assertIsNone(snapshot.captured_at)
  self.assertNotIn('fixture-only inactive acquisition',snapshot.limitations)
