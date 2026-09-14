"""Disposable archive-to-report acceptance; no production or provider interfaces."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext, ROUND_UP
from pathlib import Path
from unittest.mock import patch

import forecast_reporting_analysis as analysis
import forecast_reporting_delivery as delivery
import forecast_reporting_projections as projections
import forecast_standalone_research as legacy
from forecast_reporting_source import freeze_reporting_source
from forecast_standalone_operations import DeploymentConfig, NamespaceArchive, OperatingMode, RetryPolicy, canonical_bytes, sha256_bytes, archive_pr17_authority
from tests.reporting_fixtures import at, event_sources, archive_events

REVISION = '3001ee9cd4d95519567e0e4567ff71be0465a6a0'


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.output = self.root/'reports'
        self.archive = NamespaceArchive(DeploymentConfig('delivery','delivery',OperatingMode.DRY_RUN,
            self.root/'dry-run/delivery/primary',self.root/'dry-run/delivery/secondary',
            'https://fixture.invalid',RetryPolicy(1,1,1,(),0),1,self.root/'logs'))
        self.now = at('2026-09-12T19:00:00Z')
        self.events = [event_sources(), event_sources(design='prospective',name='live',
            start='2026-09-10T20:00:00-04:00', acquired='2026-09-09T12:00:00Z')]
        archive_events(self.archive,tuple(x[0] for x in self.events),self.now-timedelta(seconds=1))

    def clock(self):
        self.now += timedelta(microseconds=1)
        return self.now

    def generate(self, study='live', **kw):
        return delivery.generate_report(archive=self.archive,output=self.output,study=study,
            expected_revision=REVISION, clock=self.clock, synthetic_validation=True,
            update_live=study=='live', **kw)

    def verify(self, ref):
        return delivery.verify_package(archive=self.archive,output=self.output,
            package_id=ref['package_id'],anchor_key=ref['anchor_key'],clock=self.clock)

    def payload(self, ref, name):
        return (self.output/'packages'/ref['package_id']/name).read_bytes()

    def inventory(self, path):
        return {str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()}

    def test_both_studies_source_immutable_and_independent_selection(self):
        before=self.inventory(self.archive.root)
        with patch('socket.socket',side_effect=AssertionError('network forbidden')), \
             patch.object(self.archive,'commit',side_effect=AssertionError('Evidence write')), \
             patch.object(self.archive,'mutation_lock',side_effect=AssertionError('collector lock')):
            historical=self.generate('historical')
            self.assertIsNone(delivery.read_entry(self.output)['historical'])
            delivery.select_historical(output=self.output,package_id=historical['package_id'],
                anchor_key=historical['anchor_key'],archive=self.archive,clock=self.clock)
            historical_bytes=self.inventory(self.output/'packages'/historical['package_id'])
            for _ in range(2):
                live=self.generate(); self.verify(live)
                self.assertEqual(delivery.read_entry(self.output)['historical'],historical)
            self.verify(historical)
            self.assertEqual(historical_bytes,self.inventory(self.output/'packages'/historical['package_id']))
        self.assertEqual(before,self.inventory(self.archive.root))
        report=analysis.deserialize_reporting_analysis(self.payload(historical,'analysis.json').decode())
        self.assertEqual(report.context.computation.bounded_scopes[0].end,at('2026-09-05T04:00:00Z'))
        self.assertEqual(report.performances[0].sample_size,1)

    def test_capture_unresolved_missing_and_future_obligations(self):
        due,_,_=event_sources(design='prospective',name='due',start='2026-09-12T20:00:00-04:00',
            acquired='2026-09-11T12:00:00Z',final=False)
        future,_,_=event_sources(design='prospective',name='future',start='2026-09-13T20:00:00-04:00',
            acquired='2026-09-11T12:00:00Z',final=False,capture=False)
        missed,_,_=event_sources(design='prospective',name='missed',start='2026-09-10T20:00:00-04:00',
            acquired='2026-09-09T12:00:00Z',missed=True)
        archive_events(self.archive,(due,future,missed),self.now)
        ref=self.generate();p=json.loads(self.payload(ref,'projections.json'))['scopes'][0]
        self.assertEqual([len(p[k]) for k in ('eligible_ids','captured_ids','valid_probability_ids','scored_ids')],[3,2,2,1])
        self.assertEqual(len(p['reconciliation']['capture_not_yet_due']),1)
        self.assertEqual(len(p['reconciliation']['missed_window']),1)
        self.assertEqual(len(p['reconciliation']['outcome_unresolved']),1)
        self.verify(ref)

    def test_failed_derivation_does_not_remove_valid_capture(self):
        # Historical Coverage treats an invalid earlier candidate as candle_invalid,
        # while the rule-selected latest candle still satisfies capture validation.
        # This exercises separate original capture/derivation stages without a score.
        event,protocol,_=event_sources(name='stage')
        candle=next(x for x in event if type(x) is legacy.HistoricalMarketCandleObservation)
        manifest=next(x for x in event if type(x) is legacy.HistoricalCandleQueryManifest)
        seed={k:getattr(candle,k) for k in candle.__dataclass_fields__ if k not in {'historical_market_candle_observation_id','input_digest'}}
        early=legacy.HistoricalMarketCandleObservation.create(**{**seed,'manifest_id':'pending','candle_end_at':candle.candle_end_at-timedelta(minutes=1),'close_yes_bid':None})
        mids=tuple(sorted((candle.historical_market_candle_observation_id,early.historical_market_candle_observation_id)))
        vals={k:getattr(manifest,k) for k in manifest.__dataclass_fields__ if k not in {'historical_candle_query_manifest_id','input_digest'}}
        new=legacy.HistoricalCandleQueryManifest.create(**{**vals,'pages':(replace(manifest.pages[0],returned_candle_evidence_ids=mids),),'returned_candle_evidence_ids':mids})
        latest=legacy.HistoricalMarketCandleObservation.create(**{**seed,'manifest_id':new.historical_candle_query_manifest_id})
        early=legacy.HistoricalMarketCandleObservation.create(**{**seed,'manifest_id':new.historical_candle_query_manifest_id,'candle_end_at':early.candle_end_at,'close_yes_bid':None})
        archive_events(self.archive,(tuple(x for x in event if x is not candle and x is not manifest)+(new,latest,early),),self.now)
        ref=self.generate('historical'); p=json.loads(self.payload(ref,'projections.json'))['scopes'][0]
        self.assertEqual(len(p['captured_ids']),2)
        self.assertEqual(len(p['valid_probability_ids']),1)
        self.assertEqual(len(p['scored_ids']),1)
        self.verify(ref)

    def test_empty_singleton_constant_infinite_and_bin_endpoints(self):
        for values in ((),('0.5',),('0.5','0.5'),('0','0.1','0.9','1')):
            with self.subTest(values=values), tempfile.TemporaryDirectory() as directory:
                previous=self.archive; self.archive=NamespaceArchive(replace(previous.config,
                    primary_root=Path(directory)/'dry-run/delivery/primary',secondary_root=Path(directory)/'dry-run/delivery/secondary'))
                from forecast_standalone_activation import canonical_retrospective_authority
                events=[event_sources(name='p'+str(i),probability=Decimal(p))[0] for i,p in enumerate(values)]
                archive_events(self.archive,events or (canonical_retrospective_authority(),),self.now-timedelta(seconds=1))
                ref=self.generate('historical'); p=json.loads(self.payload(ref,'projections.json'))['scopes'][0]
                r=p['reference']; self.assertEqual(r['sample_size'],len(values))
                self.assertEqual(r['mean_brier_score'],'0.25' if values else None)
                self.assertEqual(r['measurement_ids'],p['calibration']['measurement_ids'])
                bins=p['calibration']['bins'];self.assertEqual(sum(x['count'] for x in bins),len(values))
                self.assertTrue(all(x['mean_home_probability'] is None for x in bins if not x['count']))
                if len(values)==4:
                    self.assertEqual([x['count'] for x in bins],[1,1,0,0,0,0,0,0,0,2])
                    self.assertEqual(bins[-1]['mean_home_probability'],'0.95')
                    self.assertIn(b'Infinity',self.payload(ref,'report.html'))
                self.verify(ref);self.archive=previous

    def test_projection_replay_under_precision_and_input_permutation(self):
        ref=self.generate('historical'); before=self.inventory(self.output/'packages'/ref['package_id'])
        entries=self.archive.entries()
        with localcontext() as ctx, patch.object(self.archive,'entries',return_value=tuple(reversed(entries))):
            ctx.prec=6;ctx.rounding=ROUND_UP;receipt=self.verify(ref)
        self.assertEqual(before,self.inventory(self.output/'packages'/ref['package_id']))
        self.assertEqual(receipt['package_id'],ref['package_id'])
        self.assertEqual(len(list((self.output/'receipts').iterdir())),2)

    def rehash(self,path):
        manifest=json.loads((path/'package.json').read_bytes())
        manifest['inventory']={x.name:sha256_bytes(x.read_bytes()) for x in path.iterdir() if x.name!='package.json'}
        manifest['package_id']=sha256_bytes(canonical_bytes({k:v for k,v in manifest.items() if k!='package_id'}))
        (path/'package.json').write_bytes(canonical_bytes(manifest))

    def test_rehashed_projection_html_inventory_and_mixed_study_tampering(self):
        ref=self.generate('historical');live=self.generate()
        original=self.output/'packages'/ref['package_id']
        mutations=['capture','baseline','calibration','html','omission','extra','mixed','source']
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                path=self.root/('forged-'+mutation);shutil.copytree(original,path)
                path.chmod(0o755)
                for x in path.iterdir():x.chmod(0o644)
                if mutation in ('capture','baseline','calibration'):
                    p=json.loads((path/'projections.json').read_bytes());sc=p['scopes'][0]
                    if mutation=='capture':sc['captured_ids']=[]
                    elif mutation=='baseline':sc['reference']['mean_brier_score']='0'
                    else:sc['calibration']['bins'][5]['home_win_frequency']='0'
                    (path/'projections.json').write_bytes(canonical_bytes(p))
                elif mutation=='html':(path/'report.html').write_text('forged')
                elif mutation=='omission':(path/'protocol.json').unlink()
                elif mutation=='extra':(path/'extra.json').write_text('{}')
                elif mutation=='mixed':(path/'analysis.json').write_bytes(self.payload(live,'analysis.json'))
                else:(path/'source.json').write_bytes(self.payload(live,'source.json'))
                self.rehash(path)
                with self.assertRaises(Exception):delivery._verify(path,self.output,ref['anchor_key'],self.archive,self.clock)
        self.verify(ref)

    def test_missing_and_candidate_derived_anchor_rejected(self):
        ref=self.generate();path=self.output/'anchors'/(ref['anchor_key']+'.json');saved=path.read_bytes();path.unlink()
        with self.assertRaisesRegex(Exception,'anchor is missing'):self.verify(ref)
        path.symlink_to(self.output/'packages'/ref['package_id']/'source.json')
        with self.assertRaisesRegex(Exception,'not a package alias'):self.verify(ref)
        path.unlink();path.write_bytes(saved)
        other=self.generate()
        with self.assertRaises(Exception):delivery.verify_package(output=self.output,archive=self.archive,
            package_id=ref['package_id'],anchor_key=other['anchor_key'],clock=self.clock)
        self.verify(ref)

    def test_failure_stages_preserve_current_and_old_package(self):
        ref=self.generate();old=self.inventory(self.output/'packages'/ref['package_id'])
        for stage in ('freeze','analysis','projections','write','verify','reference'):
            with self.subTest(stage=stage):
                name={'freeze':'freeze_reporting_source','analysis':None,'projections':'create_reporting_projections',
                      'write':'_create','verify':'_verify','reference':'_replace_entry'}[stage]
                if stage=='analysis':ctx=patch.object(analysis,'create_standalone_report_analysis',side_effect=RuntimeError(stage))
                elif stage=='reference':
                    original=delivery._replace_entry
                    def replacement(output,state):
                        if state['last_attempt']['status']=='succeeded':raise OSError('reference replacement failed')
                        return original(output,state)
                    ctx=patch.object(delivery,name,side_effect=replacement)
                elif stage=='write':
                    original_create=delivery._create
                    def create(path,body):
                        if path.name=='analysis.json':raise OSError('candidate write failed')
                        return original_create(path,body)
                    ctx=patch.object(delivery,name,side_effect=create)
                else:ctx=patch.object(delivery,name,side_effect=RuntimeError(stage))
                with ctx,self.assertRaises(Exception):self.generate()
                state=delivery.read_entry(self.output)
                self.assertEqual(state['live'],ref);self.assertEqual(state['last_attempt']['status'],'failed')
                self.assertEqual(old,self.inventory(self.output/'packages'/ref['package_id']))
        self.assertTrue(list((self.output/'candidates').iterdir()))

    def test_no_prior_failure_and_attempt_persistence_failure(self):
        with patch.object(delivery,'freeze_reporting_source',side_effect=RuntimeError('source failure')):
            with self.assertRaises(RuntimeError):self.generate()
        self.assertIn('No validated report available.',(self.output/'entry.html').read_text())
        self.assertIn('source failure',(self.output/'entry.html').read_text())
        with patch.object(delivery,'_replace_entry',side_effect=OSError('disk full')):
            with self.assertRaisesRegex(Exception,'ATTEMPT STATUS COULD NOT BE SAVED'):self.generate()

    def test_missing_historical_does_not_block_live_update(self):
        historical=self.generate('historical')
        delivery.select_historical(output=self.output,archive=self.archive,package_id=historical['package_id'],anchor_key=historical['anchor_key'],clock=self.clock)
        path=self.output/'packages'/historical['package_id'];path.chmod(0o755);path.rename(self.root/'unavailable-historical')
        live=self.generate();self.verify(live)
        self.assertEqual(delivery.read_entry(self.output)['historical'],historical)
        self.assertIn('Selected package unavailable',(self.output/'entry.html').read_text())

    def test_open_without_archive_network_or_analysis(self):
        ref=self.generate();before=self.inventory(self.output)
        self.archive.root.rename(self.root/'archive-offline')
        with patch('socket.socket',side_effect=AssertionError('network')), \
             patch.object(delivery,'_verify',side_effect=AssertionError('verification')), \
             patch.object(analysis,'create_standalone_report_analysis',side_effect=AssertionError('scoring')):
            opened=[]
            delivery.open_saved(output=self.output,package_id=ref['package_id'],opener=opened.append)
            delivery.open_saved(output=self.output,opener=opened.append)
        self.assertEqual(len(opened),2);self.assertEqual(before,self.inventory(self.output))

    def test_output_overlap_aliases_and_managed_symlinks_rejected(self):
        for output in (self.archive.root/'reports',self.archive.root.parent,delivery.REPOSITORY/'reports',delivery.REPOSITORY.parent,self.archive.config.secondary_root/'reports'):
            with self.subTest(output=output),self.assertRaises(Exception):delivery.generate_report(archive=self.archive,
                output=output,study='live',expected_revision=REVISION,synthetic_validation=True,clock=self.clock)
        alias=self.root/'alias';alias.symlink_to(self.archive.root,target_is_directory=True)
        with self.assertRaises(Exception):delivery.validate_output_root(alias/'reports',self.archive)
        self.output.mkdir();(self.output/'anchors').symlink_to(self.archive.root)
        with self.assertRaises(Exception):self.generate()

    def test_dirty_operational_generation_and_final_requests_rejected(self):
        with self.assertRaisesRegex(Exception,'clean reproducible'):delivery.generate_report(
            archive=self.archive,output=self.output,study='live',expected_revision=REVISION)
        for status in ('final','correction'):
            with self.assertRaisesRegex(Exception,'outside this workflow'):self.generate(report_status=status)
        with self.assertRaisesRegex(Exception,'actual wall time'):delivery.generate_report(
            archive=self.archive,output=self.output,study='live',expected_revision=REVISION,clock=self.clock)

    def test_fresh_process_verifies_independent_anchor(self):
        ref=self.generate()
        script='''from pathlib import Path
from datetime import datetime,timezone
from forecast_standalone_operations import *
from forecast_reporting_delivery import verify_package
import sys
root=Path(sys.argv[1]); config=DeploymentConfig('delivery','delivery',OperatingMode.DRY_RUN,root/'dry-run/delivery/primary',root/'dry-run/delivery/secondary','https://fixture.invalid',RetryPolicy(1,1,1,(),0),1,root/'logs')
print(verify_package(output=root/'reports',archive=NamespaceArchive(config),package_id=sys.argv[2],anchor_key=sys.argv[3],clock=lambda:datetime(2026,9,14,tzinfo=timezone.utc))['package_id'])
'''
        result=subprocess.run([os.sys.executable,'-c',script,str(self.root),ref['package_id'],ref['anchor_key']],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn(ref['package_id'],result.stdout)

    def test_later_outcome_correction_preserves_package_and_selection(self):
        ref=self.generate('historical');old=self.inventory(self.output/'packages'/ref['package_id'])
        history=self.events[0][2]; final=history.observations[-1];self.now+=timedelta(days=1)
        correction=replace(final,observation_id=final.observation_id+':corrected',winning_participant_id=final.away_participant_id,
            losing_participant_id=final.home_participant_id,collected_at=self.now)
        archive_pr17_authority(self.archive,(replace(history,observations=history.observations+(correction,)),),recorded_at=self.now)
        self.verify(ref);new=self.generate('historical');self.verify(new)
        self.assertNotEqual(ref['package_id'],new['package_id']);self.assertEqual(old,self.inventory(self.output/'packages'/ref['package_id']))

    def test_historical_offered_rates_mapping_unknown_and_ambiguity(self):
        history=self.events[0][2];schedule=history.observations[0]
        template=next(x for x in self.events[1][0] if type(x) is legacy.ProviderMarketSeries)
        def mapping(series_id, market):
            proposition=f'winner:{schedule.canonical_event_id}:{schedule.home_participant_id}'
            return replace(template,series_id='market-series:kalshi:'+market,provider_market_id=market,proposition_id=proposition,
                yes_semantic=replace(template.yes_semantic,proposition_id=proposition,participant_id=schedule.home_participant_id),
                no_semantic=replace(template.no_semantic,proposition_id=proposition,participant_id=schedule.away_participant_id),
                provenance=replace(template.provenance,canonical_event_id=schedule.canonical_event_id,
                    source_record_id=market,collected_at=schedule.collected_at))
        unknown=self.generate('historical')
        old=json.loads(self.payload(unknown,'projections.json'))['scopes'][0]['historical_markets']
        self.assertIsNone(old['offered_over_eligible']);self.assertEqual(len(old['unknown_membership_ids']),1)
        series=mapping('synthetic-mapping:historical','synthetic-native:game')
        archive_pr17_authority(self.archive,(series,),recorded_at=self.now)
        offered=self.generate('historical');self.verify(offered)
        new=json.loads(self.payload(offered,'projections.json'))['scopes'][0]['historical_markets']
        self.assertEqual(new['offered_over_eligible'],'1');self.assertEqual(new['scored_over_offered'],'1')
        self.verify(unknown)
        archive_pr17_authority(self.archive,(mapping('synthetic-mapping:ambiguous','another-market'),),recorded_at=self.now)
        with self.assertRaisesRegex(Exception,'ambiguous historical market mapping'):self.generate('historical')

    def test_late_session_completion_and_empty_calendar_are_package_frozen(self):
        from tests.test_forecast_standalone_publication import PinnedSupportingAuthorityTests
        fixture=PinnedSupportingAuthorityTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.archive=fixture.archive;self.now=fixture.boundary
        old=self.generate('historical');saved=self.inventory(self.output/'packages'/old['package_id'])
        old_source=json.loads(self.payload(old,'source.json'))
        self.assertTrue(old_source['session_dispositions'][0][1].startswith('excluded:'))
        fixture.complete();self.now+=timedelta(days=2)
        from forecast_standalone_activation import canonical_mlb_schedule_request, merge_mlb_schedule_responses, reconcile_outcomes_from_raw
        raw=b'{"dates":[],"totalGames":0}'
        reconcile_outcomes_from_raw(archive=self.archive,mlb_raw=merge_mlb_schedule_responses((raw,)),
            collected_at=self.now,mlb_pages=(('2026-08-21',canonical_mlb_schedule_request('2026-08-21')[1],raw),))
        self.verify(old);fresh=self.generate('historical');self.verify(fresh)
        fresh_source=json.loads(self.payload(fresh,'source.json'))
        self.assertEqual(fresh_source['session_dispositions'][0][1],'verified-complete')
        self.assertEqual(saved,self.inventory(self.output/'packages'/old['package_id']))
        report=analysis.deserialize_reporting_analysis(self.payload(fresh,'analysis.json').decode())
        self.assertTrue(report.coverages[0].verified_calendar_dates)
        self.assertTrue(report.coverages[0].unknown_calendar_dates)

    def test_package_collision_preserves_existing_bytes(self):
        original_rename=delivery.os.rename
        collisions=[]
        def collide(source,target):
            if source.parent.name=='candidates':
                target.mkdir();(target/'sentinel').write_bytes(b'existing unrelated bytes')
                collisions.append(target)
            return original_rename(source,target)
        with patch.object(delivery.os,'rename',side_effect=collide),self.assertRaises(OSError):self.generate()
        self.assertEqual((collisions[0]/'sentinel').read_bytes(),b'existing unrelated bytes')
        self.assertIsNone(delivery.read_entry(self.output)['live'])

    def test_failed_reference_replace_system_call_and_receipt_write(self):
        ref=self.generate();old=delivery.os.replace
        calls=0
        def fail_once(source,target):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('entry replace failed')
            return old(source,target)
        with patch.object(delivery.os,'replace',side_effect=fail_once),self.assertRaises(OSError):self.generate()
        self.assertEqual(delivery.read_entry(self.output)['live'],ref)
        self.assertEqual(delivery.read_entry(self.output)['last_attempt']['status'],'failed')
        old_create=delivery._create
        def fail_receipt(path,body):
            if path.parent.name=='receipts':raise OSError('receipt storage failed')
            return old_create(path,body)
        with patch.object(delivery,'_create',side_effect=fail_receipt),self.assertRaises(OSError):self.generate()
        self.assertEqual(delivery.read_entry(self.output)['live'],ref)

    def test_package_payload_digest_tampering_fails_before_replay(self):
        ref=self.generate();path=self.output/'packages'/ref['package_id']/'report.html'
        path.chmod(0o644);path.write_bytes(path.read_bytes()+b'altered')
        with self.assertRaisesRegex(Exception,'digest conflict'):self.verify(ref)


    def principal_text(self, body):
        from html.parser import HTMLParser
        class Visible(HTMLParser):
            def __init__(self):super().__init__();self.hidden=0;self.detail=0;self.parts=[]
            def handle_starttag(self,tag,attrs):
                if tag in {'style','script','head'}:self.hidden+=1
                if tag=='details':self.detail+=1
            def handle_endtag(self,tag):
                if tag in {'style','script','head'}:self.hidden-=1
                if tag=='details':self.detail-=1
            def handle_data(self,value):
                if not self.hidden and not self.detail:self.parts.append(value)
        parser=Visible();parser.feed(body.decode());return ' '.join(parser.parts)

    def test_simple_principal_hides_technical_evidence_and_retains_exact_details(self):
        ref=self.generate();raw=self.payload(ref,'report.html');visible=self.principal_text(raw)
        self.assertIn('0.202',visible);self.assertIn('0.250',visible)
        self.assertIn('Only one scored observation',visible)
        self.assertIn('Study in progress',visible);self.assertIn('EDT',visible)
        self.assertIn('synthetic data',visible)
        for technical in (ref['report_id'],'Mean log loss','Fixed-bin calibration','time-bounded','Computation started','Protocol','sha256'):
            self.assertNotIn(technical,visible)
        self.assertIn(ref['report_id'].encode(),raw)
        self.assertIn(b'<summary>Details</summary>',raw)
        self.assertIn(b'0.2025',raw)
        self.assertIn(b'Mean log loss',raw)
        self.assertIn(b'href="analysis.json"',raw)
        entry=(self.output/'entry.html').read_bytes();main=self.principal_text(entry)
        self.assertIn('Prediction error',main);self.assertIn('0.202',main)
        self.assertNotIn(ref['package_id'],main)
        self.assertIn('Historical candle report',main)
        self.verify(ref)

    def test_display_rounding_is_fixed_and_only_presentation(self):
        from forecast_reporting_presentation import rounded
        with localcontext() as ctx:
            ctx.prec=3;ctx.rounding=ROUND_UP
            self.assertEqual(rounded(Decimal('0.2025')),'0.202')
            self.assertEqual(rounded(Decimal('0.12345')),'0.123')
            self.assertEqual(rounded(Decimal('0.3333333333333333333'),1,True),'33.3%')
            self.assertEqual(rounded(None),'Unavailable')
            self.assertEqual(rounded(Decimal('Infinity')),'Infinite')
        ref=self.generate()
        report=analysis.deserialize_reporting_analysis(self.payload(ref,'analysis.json').decode())
        self.assertEqual(report.performances[0].mean_brier_score,Decimal('0.2025'))
        self.verify(ref)

    def test_failure_principal_is_plain_language_with_retained_date(self):
        ref=self.generate()
        with patch.object(delivery,'freeze_reporting_source',side_effect=RuntimeError('technical diagnostic: 123abc')):
            with self.assertRaises(RuntimeError):self.generate()
        raw=(self.output/'entry.html').read_bytes();visible=self.principal_text(raw)
        self.assertIn('last report attempt failed',visible)
        self.assertIn('saved report from',visible)
        self.assertIn('0.202',visible)
        self.assertNotIn('123abc',visible);self.assertNotIn(ref['report_id'],visible)
        self.assertIn(b'123abc',raw);self.assertEqual(delivery.read_entry(self.output)['live'],ref)

    def test_version_one_package_replays_without_rewriting_html(self):
        with patch.object(delivery,'RENDERER','mlb-reporting-html-1'):
            old=self.generate('historical')
        before=self.inventory(self.output/'packages'/old['package_id'])
        self.assertIn('Report identity',self.principal_text(self.payload(old,'report.html')))
        self.verify(old)
        fresh=self.generate('historical');self.verify(fresh)
        self.assertNotIn('Report identity',self.principal_text(self.payload(fresh,'report.html')))
        self.assertEqual(before,self.inventory(self.output/'packages'/old['package_id']))

    def test_empty_and_infinite_simple_results_remain_honest(self):
        empty_events,_,_=event_sources(design='prospective',name='unresolved',start='2026-09-12T20:00:00-04:00',
            acquired='2026-09-11T12:00:00Z',final=False)
        # A separate namespace with only an unresolved capture has no scored results.
        self.archive=NamespaceArchive(replace(self.archive.config,
            primary_root=self.root/'empty/dry-run/delivery/primary',secondary_root=self.root/'empty/dry-run/delivery/secondary'))
        archive_events(self.archive,(empty_events,),self.now)
        ref=self.generate();visible=self.principal_text(self.payload(ref,'report.html'))
        self.assertIn('No scored results are available',visible)
        self.assertIn('No uncertainty interval',visible)
        self.assertIn('Awaiting a usable game result',visible)
        self.assertIn('Calendar coverage is unverified',visible)
        self.verify(ref)
        event,_,_=event_sources(name='impossible',probability=Decimal('0'))
        archive_events(self.archive,(event,),self.now)
        historical=self.generate('historical');raw=self.payload(historical,'report.html');visible=self.principal_text(raw)
        self.assertIn('assigned a zero probability',visible)
        self.assertNotIn('Mean log loss',visible);self.assertIn(b'Infinity',raw)
        self.verify(historical)


    def test_new_principal_read_failure_cannot_select_unreadable_package(self):
        prior=self.generate();original=delivery._inspect
        def inspect(path,expected_id=None):
            if path.parent.name=='packages' and path.name!=prior['package_id']:
                raise OSError('new saved package unavailable during entry construction')
            return original(path,expected_id)
        with patch.object(delivery,'_inspect',side_effect=inspect),self.assertRaises(OSError):
            self.generate()
        state=delivery.read_entry(self.output)
        self.assertEqual(state['live'],prior);self.assertEqual(state['last_attempt']['status'],'failed')
        self.assertIn('0.202',self.principal_text((self.output/'entry.html').read_bytes()))


if __name__=='__main__':unittest.main()
