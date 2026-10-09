"""Offline acceptance of phase authority, collection and reporting boundaries."""
import json
import unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from forecast_standalone_activation import canonical_prospective_authority, canonical_postseason_authority, POSTSEASON_GAME_START
from forecast_standalone_research import EventPhase, validate_population_side, create_standalone_eligibility_authority
from forecast_standalone_operations import archive_pr17_authority
from forecast_reporting_delivery import generate_report, read_entry
from performance_reader import MLBReader
from tests.reporting_fixtures import event_sources, archive_events, at, _classification
from tests import test_forecast_reporting_delivery as fixture_module
REVISION=fixture_module.REVISION


def postseason_event(legacy=False,**kw):
    def classified(schedule, provenance):
        original=_classification(schedule,provenance)
        values={k:getattr(original,k) for k in original.__dataclass_fields__ if k not in {'standalone_event_classification_evidence_id','input_digest'}}
        values.update(event_phase=EventPhase.POSTSEASON,game_type='L',ordinary_game=False)
        return type(original).create(**values)
    with patch('tests.reporting_fixtures.canonical_prospective_authority',return_value=canonical_prospective_authority() if legacy else canonical_postseason_authority()), patch('tests.reporting_fixtures._classification',side_effect=classified):
        return event_sources(design='prospective',**kw)


class PhaseAuthority(unittest.TestCase):
    def test_original_identity_and_disjoint_lineage(self):
        old=canonical_prospective_authority()[1];new=canonical_postseason_authority()[1]
        self.assertEqual(old.standalone_probability_source_protocol_id,'standalone-probability-source-protocol:f5303a5af20a0478e6192c4e6bdc9d133c85700fae3a410b48c81d6c6f0af2ec')
        self.assertNotEqual(old.standalone_probability_source_protocol_id,new.standalone_probability_source_protocol_id)
        self.assertEqual(dict(new.scope_rule.parameters)['predecessor_protocol_id'],old.standalone_probability_source_protocol_id)
        self.assertEqual(new.scoring_rule,old.scoring_rule)
        self.assertEqual(POSTSEASON_GAME_START,at('2026-10-11T05:00:00Z'))
    def test_inclusive_game_start_and_capture_before_day_boundary(self):
        activation,protocol=canonical_postseason_authority()
        validate_population_side(protocol,activation,POSTSEASON_GAME_START)
        with self.assertRaises(ValueError):validate_population_side(protocol,activation,POSTSEASON_GAME_START-timedelta(microseconds=1))
        self.assertEqual(POSTSEASON_GAME_START-timedelta(hours=6),at('2026-10-10T23:00:00Z'))
    def test_wrong_phase_cannot_enter_postseason(self):
        sources,old,history=event_sources(design='prospective',start='2026-10-11T19:00:00-05:00',acquired='2026-10-10T12:00:00Z',capture=False)
        new=canonical_postseason_authority()[1]
        from forecast_standalone_research import ResearchCaptureOpportunity
        opportunity=ResearchCaptureOpportunity.create(new.standalone_probability_source_protocol_id,history.observations[0].observation_id,'winner')
        classification=next(x for x in sources if type(x).__name__=='StandaloneEventClassificationEvidence')
        _,result=create_standalone_eligibility_authority(protocol=new,opportunity=opportunity,outcome_history=history,classification=classification,classifications=(classification,),analysis_boundary=history.observations[-1].collected_at,provenance=classification.provenance)
        self.assertEqual(result.disposition.value,'excluded')


class PhaseReports(unittest.TestCase):
    def test_postseason_report_scores_only_new_cohort_and_preserves_regular(self):
        fixture=fixture_module.DeliveryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        old=fixture.generate(prepare_matches=True)
        old_bytes=fixture.inventory(fixture.output/'packages'/old['package_id'])
        fixture.now=at('2026-10-12T12:00:00Z')
        post=postseason_event(name='postseason',start='2026-10-11T19:00:00-05:00',acquired='2026-10-10T12:00:00Z')
        legacy=postseason_event(legacy=True,name="postseason",start="2026-10-11T19:00:00-05:00",acquired="2026-10-10T12:00:00Z",capture=False)
        archive_events(fixture.archive,(post[0],legacy[0]),fixture.now-timedelta(seconds=1))
        before=fixture.inventory(fixture.archive.root)
        with patch('socket.socket',side_effect=AssertionError('no provider access')):
            ref=generate_report(archive=fixture.archive,output=fixture.output/'postseason',study='live',expected_revision=REVISION,clock=fixture.clock,synthetic_validation=True,update_live=True,prepare_matches=True,phase='postseason')
            analysis=json.loads((fixture.output/'postseason/packages'/ref['package_id']/'analysis.json').read_text())
            self.assertEqual(analysis['context']['computation']['domain'][1],['event_phase','postseason'])
            self.assertEqual(len(analysis['coverages'][0]['measurement_ids']),1)
            html=MLBReader(fixture.output).render({'phase':['postseason']}).decode()
            self.assertIn('Postseason',html);self.assertIn('October 11',html);self.assertIn('1 of 1 opportunities shown',html)
            self.assertIn('name="phase" value="postseason"',html)
            self.assertNotIn('regular-season study origin',html.lower())
        self.assertEqual(read_entry(fixture.output)['live'],old)
        self.assertEqual(fixture.inventory(fixture.output/'packages'/old['package_id']),old_bytes)
        self.assertEqual(fixture.inventory(fixture.archive.root),before)
    def test_before_start_report_is_empty_and_displays_future_origin(self):
        fixture=fixture_module.DeliveryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.now=at('2026-10-09T12:00:00Z')
        archive_pr17_authority(fixture.archive,(canonical_postseason_authority()[1],),recorded_at=fixture.now)
        ref=generate_report(archive=fixture.archive,output=fixture.output/'postseason',study='live',expected_revision=REVISION,clock=fixture.clock,synthetic_validation=True,update_live=True,prepare_matches=True,phase='postseason')
        html=MLBReader(fixture.output).render({'phase':['postseason']}).decode()
        self.assertIn('Cohort begins Oct 11, 2026',html)
        self.assertIn('No scored results are available',html)

    def test_phase_missing_package_is_visible_and_inert(self):
        fixture=fixture_module.DeliveryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.generate();before=fixture.inventory(fixture.output)
        html=MLBReader(fixture.output).render({'phase':['postseason']}).decode()
        self.assertIn('unavailable',html)
        self.assertEqual(before,fixture.inventory(fixture.output))


class PhaseCollection(unittest.TestCase):
    def test_initialize_upgrade_admits_existing_schedule_without_quotes(self):
        import tempfile
        from pathlib import Path
        from forecast_standalone_activation import initialize_activation, APPROVED_ACTIVATION_AT
        from forecast_standalone_operations import DeploymentConfig,OperatingMode,RetryPolicy,NamespaceArchive,replay_pr17_archive
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);regular=canonical_prospective_authority()[1];post=canonical_postseason_authority()[1]
            config=DeploymentConfig('phase','phase',OperatingMode.ACTIVATED,root/'activated/phase/primary',root/'activated/phase/secondary','https://fixture.invalid',RetryPolicy(1,1,1,(),0),1,root/'logs',research_protocol_ids=(regular.standalone_probability_source_protocol_id,),activation_at=APPROVED_ACTIVATION_AT)
            archive=NamespaceArchive(config);now=at('2026-10-09T12:00:00Z')
            sources=postseason_event(legacy=True,name='scheduled',start='2026-10-11T19:00:00-05:00',acquired='2026-10-09T11:00:00Z',final=False,capture=False)[0]
            archive_events(archive,(sources,),now)
            before=tuple(archive.entries())
            upgraded=NamespaceArchive(replace(config,research_protocol_ids=(regular.standalone_probability_source_protocol_id,post.standalone_probability_source_protocol_id)))
            initialize_activation(upgraded,now)
            state=replay_pr17_archive(upgraded,analysis_boundary=now)
            self.assertEqual(len(state.bucket('protocols')),2)
            self.assertEqual(len(state.bucket('opportunities')),2)
            self.assertEqual(state.bucket('attempts'),())
            self.assertTrue(all(entry in upgraded.entries() for entry in before))
            count=len(upgraded.entries());initialize_activation(upgraded,now)
            self.assertEqual(count,len(upgraded.entries()))

    def test_dual_cohorts_capture_once_and_repeat_is_idempotent(self):
        from forecast_standalone_operations import NamespaceArchive,discover_and_capture_prospective,HTTPResponse,replay_pr17_archive
        from tests.test_forecast_standalone_operations import SequenceTransport
        fixture=fixture_module.DeliveryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        regular=canonical_prospective_authority()[1];post=canonical_postseason_authority()[1]
        fixture.archive=NamespaceArchive(replace(fixture.archive.config,research_protocol_ids=(regular.standalone_probability_source_protocol_id,post.standalone_probability_source_protocol_id)))
        kwargs=dict(name='capture',start='2026-10-11T19:00:00-05:00',acquired='2026-10-09T11:00:00Z',final=False)
        post_sources=postseason_event(**kwargs)[0]
        legacy_sources=postseason_event(legacy=True,capture=False,**kwargs)[0]
        # Seed authority and market identity, but no prior quote or capture attempt.
        seed=[x for x in post_sources if type(x).__name__ not in {'MarketObservation','ProspectiveCaptureAttempt','ProspectiveStandaloneSnapshot'}]
        now=at('2026-10-11T18:01:00Z')
        archive_events(fixture.archive,(seed,legacy_sources),now)
        from forecast_prospective_projection import rebuild_projection
        rebuild_projection(fixture.archive,now)
        series=next(x for x in post_sources if type(x).__name__=='ProviderMarketSeries')
        observation=next(x for x in post_sources if type(x).__name__=='MarketObservation')
        transport=SequenceTransport(HTTPResponse(200,json.dumps({'contract_json':observation.to_json()}).encode(),{}))
        with patch('forecast_prospective_market_selection.load_prospective_catalog',return_value=((),(),'fixture')),patch('forecast_prospective_market_selection.prepare_prospective_markets',return_value=()),patch('forecast_prospective_market_selection.select_prepared_market',return_value=(series,'fixture')):
            first=discover_and_capture_prospective(archive=fixture.archive,transport_factory=lambda *_:transport,clock=lambda:now)
            second=discover_and_capture_prospective(archive=fixture.archive,transport_factory=lambda *_:transport,clock=lambda:now)
        self.assertEqual(first.provider_request_count,1)
        self.assertEqual(second.provider_request_count,0)
        self.assertEqual(len(transport.calls),1)
        rollback=NamespaceArchive(replace(fixture.archive.config,research_protocol_ids=(regular.standalone_probability_source_protocol_id,)))
        stopped=discover_and_capture_prospective(archive=rollback,transport_factory=lambda *_:transport,clock=lambda:now)
        self.assertEqual(stopped.provider_request_count,0)
        self.assertEqual(len(transport.calls),1)
        attempts=replay_pr17_archive(fixture.archive,analysis_boundary=now).bucket('attempts')
        self.assertTrue(attempts)
        new_attempts=[x for x in attempts if x.canonical_event_id=='synthetic-event:capture']
        self.assertTrue(new_attempts)
        self.assertTrue(all(x.protocol_id==post.standalone_probability_source_protocol_id for x in new_attempts))


class PhaseOdds(unittest.TestCase):
    def test_saved_schedule_phase_and_inclusive_postseason_start(self):
        import mlb_odds
        from tests.test_mlb_odds import game
        record=game();record.update(gameType='L',gameDate='2026-10-11T05:00:00Z')
        raw=mlb_odds.encode({'totalGames':1,'dates':[{'date':'2026-10-11','totalGames':1,'games':[record]}]})
        rows=mlb_odds.schedule_games(raw,'2026-10-11','2026-10-09T12:00:00Z')
        row=rows[0]
        self.assertEqual(row['phase'],'postseason')
        self.assertFalse(any('scope' in reason.lower() for reason in row['reasons']))
        record['gameDate']='2026-10-11T04:59:59Z'
        raw=mlb_odds.encode({'totalGames':1,'dates':[{'date':'2026-10-11','totalGames':1,'games':[record]}]})
        self.assertTrue(any('Before October 11' in reason for reason in mlb_odds.schedule_games(raw,'2026-10-11','2026-10-09T12:00:00Z')[0]['reasons']))


class PhaseUpdate(unittest.TestCase):
    def fixture(self):
        from tests.test_mlb_performance_update import UpdateTests
        from forecast_standalone_operations import NamespaceArchive
        test=UpdateTests();test.setUp();self.addCleanup(test.doCleanups)
        test.fixture.now=at('2026-10-09T12:00:00Z')
        regular=canonical_prospective_authority()[1];post=canonical_postseason_authority()[1]
        test.fixture.archive=NamespaceArchive(replace(test.fixture.archive.config,research_protocol_ids=(regular.standalone_probability_source_protocol_id,post.standalone_probability_source_protocol_id)))
        archive_pr17_authority(test.fixture.archive,(post,),recorded_at=test.fixture.now)
        return test

    def test_manual_update_prepares_both_cohorts(self):
        test=self.fixture();before=test.fixture.inventory(test.fixture.archive.root)
        self.assertEqual(test.run_worker(),0)
        state=test.controller.status()
        self.assertEqual(state['status'],'succeeded')
        self.assertEqual(read_entry(test.root/'postseason')['live'],state['postseason_package'])
        self.assertEqual(before,test.fixture.inventory(test.fixture.archive.root))

    def test_postseason_failure_remains_visible_and_regular_report_survives(self):
        import forecast_reporting_delivery as delivery
        test=self.fixture();real=delivery.generate_report
        def fail_post(**kwargs):
            if kwargs.get('phase')=='postseason':raise ValueError('synthetic postseason failure')
            return real(**kwargs)
        with patch.object(delivery,'generate_report',side_effect=fail_post):
            self.assertEqual(test.run_worker(),0)
        state=test.controller.status()
        self.assertEqual(state['status'],'succeeded')
        self.assertIn('Postseason report update failed',state['message'])
        self.assertEqual(state['postseason_error'],'synthetic postseason failure')
        self.assertEqual(read_entry(test.root)['live'],state['package'])
