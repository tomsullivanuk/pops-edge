"""Offline empty-interval admission, immutable replay, and lifecycle regression tests."""
import copy
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import forecast_standalone_activation as a
from forecast_standalone_operations import OperationsError, canonical_bytes, replay_pr17_archive, _contracts_from_entry
from forecast_standalone_schedule_reconciliation import reconciliation_dates
from inspect_forecast_standalone_activation import fixtures
from operate_forecast_standalone_activation import execute
from tests import test_forecast_standalone_commissioning as commissioning


class EmptySupportingTests(unittest.TestCase):
    def setUp(self):
        f=commissioning.CommissioningTests();f.setUp();self.addCleanup(f.doCleanups)
        self.archive,self.config=f.archive,f.config
        self.at=datetime(2026,11,7,16,tzinfo=timezone.utc)

    def pages(self,at=None):
        at=at or self.at;state=replay_pr17_archive(self.archive,analysis_boundary=at)
        days=a.required_mlb_query_dates(trusted_at=at,histories=state.bucket('outcome_histories'))
        raw=Path(__file__).with_name('fixtures').joinpath('mlb_explicit_zero_schedule.json').read_bytes()
        pages=tuple(a.ProviderPageAcquisition(str(day),a.canonical_mlb_schedule_request(str(day))[1],raw,at,at,i,'mlb-stats-api') for i,day in enumerate(days))
        raw=b'{"cursor":"","markets":[]}'
        catalog=(a.KalshiCatalogPage(0,'','',raw,(),at,at,a.encoded_kalshi_catalog_path('')),)
        return pages,catalog

    def refresh(self,pages=None,catalog=None,at=None):
        at=at or self.at;defaults=self.pages(at)
        pages=defaults[0] if pages is None else pages;catalog=defaults[1] if catalog is None else catalog
        return a.refresh_supporting_from_raw(archive=self.archive,mlb_raw=a.merge_mlb_schedule_responses(tuple(p.raw for p in pages)),kalshi_raw=a.merge_kalshi_catalog_pages(catalog),collected_at=at,mlb_pages=pages,catalog_pages=catalog)

    def bundles(self):
        return [(e,self.archive.read_json_verified('normalized',e['normalized_object_id'])) for e in self.archive.entries() if e['command']=='refresh-supporting']

    def test_complete_empty_interval_retains_pages_replays_and_preserves_state(self):
        before=replay_pr17_archive(self.archive,analysis_boundary=self.at)
        result=self.refresh();self.assertEqual((result['events'],result['contracts'],result['disposition']),(0,0,'unchanged'))
        self.assertEqual(len(self.bundles()),2)
        for entry,value in self.bundles():
            self.assertEqual(value['derivation_rule'],a.EMPTY_SUPPORTING_DERIVATION_RULE_VERSION)
            self.assertEqual(value['contracts'],[]);a.verify_acquisition_bundle(self.archive,value)
            for page in value['pages']:
                raw=self.archive.read_verified('raw',page['raw_sha256'])
                if value['provider']=='mlb-stats-api':self.assertEqual(json.loads(raw)['totalGames'],0)
                self.assertEqual(page['started_at']['datetime_utc'],self.at.isoformat())
        self.assertEqual(before.objects,replay_pr17_archive(self.archive,analysis_boundary=self.at).objects)
        # Before-completion pages do not certify a day retrospectively.
        dates=reconciliation_dates(archive=self.archive,started=self.at+timedelta(days=3),start_date=self.at.date(),end_date=self.at.date()+timedelta(days=1))
        self.assertEqual(len(dates),2)
        old={p:p.read_bytes() for p in self.archive.root.glob('*/*/*') if p.is_file()}
        self.refresh(at=self.at+timedelta(hours=1));self.assertEqual(len(self.bundles()),4)
        self.assertTrue(all(p.read_bytes()==raw for p,raw in old.items()))

    def test_incomplete_or_invalid_empty_pages_fail_before_publication(self):
        before=self.archive.entries();pages,catalog=self.pages()
        cases=[pages[:1],pages+pages[:1],tuple(reversed(pages)),()]
        for raw in [b'{"dates":[]}',b'{"dates":[],"totalGames":1}',b'{"dates":[],"totalGames":false}',b'{"dates":[{"date":"2026-11-06","games":[]}],"totalGames":0}']:
            cases.append((replace(pages[0],raw=raw),)+pages[1:])
        cases.append((replace(pages[0],endpoint=a.canonical_mlb_schedule_request('2026-11-06')[1]),)+pages[1:])
        for items in cases:
            with self.subTest(items=items),self.assertRaises(OperationsError):self.refresh(items,catalog)
            self.assertEqual(self.archive.entries(),before)

    def test_complete_catalog_and_raw_agreement_still_required(self):
        before=self.archive.entries();pages,catalog=self.pages()
        bad=replace(catalog[0],next_cursor='more',raw=b'{"cursor":"more","markets":[]}')
        with self.assertRaisesRegex(OperationsError,'pagination-incomplete'):self.refresh(pages,(bad,))
        with self.assertRaisesRegex(OperationsError,'acquisition-page-conflict'):self.refresh(pages,(replace(catalog[0],raw=b'{"cursor":"","markets":[{"ticker":"x"}]}'),))
        with self.assertRaises(OperationsError):self.refresh(pages,())
        for altered in [replace(catalog[0],endpoint='/wrong'),replace(catalog[0],started_at=self.at-timedelta(seconds=1))]:
            with self.assertRaises(OperationsError):self.refresh(pages,(altered,))
        self.assertEqual(self.archive.entries(),before)

    def test_legacy_empty_rejection_unknown_rule_and_dependency_mismatch(self):
        self.refresh();entry,value=next((e,v) for e,v in self.bundles() if v['provider']=='mlb-stats-api')
        original=self.archive.read_json_verified
        for rule,code in [(None,'provider-data-invalid'),('future-rule','acquisition-incompatible')]:
            changed=copy.deepcopy(value)
            if rule is None:changed.pop('derivation_rule')
            else:changed['derivation_rule']=rule
            def read(family,identity):return changed if identity==entry['normalized_object_id'] else original(family,identity)
            with patch.object(self.archive,'read_json_verified',side_effect=read),self.assertRaisesRegex(OperationsError,code):_contracts_from_entry(self.archive,entry)
        changed=copy.deepcopy(value);changed['union_rule']='provider-pages-canonical-union-1'
        with self.assertRaisesRegex(OperationsError,'acquisition-incompatible'):a.verify_acquisition_bundle(self.archive,changed)
        entry,value=next((e,v) for e,v in self.bundles() if v['provider']=='kalshi');changed=copy.deepcopy(value);changed.pop('derivation_rule')
        def read(family,identity):return changed if identity==entry['normalized_object_id'] else original(family,identity)
        with patch.object(self.archive,'read_json_verified',side_effect=read),self.assertRaisesRegex(OperationsError,'acquisition-dependency-conflict'):_contracts_from_entry(self.archive,entry)

    def test_iterable_pages_and_changed_source_fence(self):
        pages,catalog=self.pages()
        result=a.refresh_supporting_from_raw(archive=self.archive,mlb_raw=b'{"dates":[]}',kalshi_raw=b'{"cursor":"","markets":[]}',
            collected_at=self.at,mlb_pages=iter(pages),catalog_pages=iter(catalog))
        self.assertEqual(result['disposition'],'unchanged')
        before=self.archive.entries()
        with patch('forecast_supporting_replay.SupportingReplayArchive.assert_current',side_effect=OperationsError('supporting-source-changed','fixture change')):
            with self.assertRaisesRegex(OperationsError,'supporting-source-changed'):self.refresh(at=self.at+timedelta(hours=1))
        self.assertEqual(self.archive.entries(),before)

    def test_empty_source_remains_compatible_with_frozen_source_verification(self):
        from forecast_reporting_source import freeze_reporting_source,verify_reporting_source
        self.refresh()
        boundary=freeze_reporting_source(archive=self.archive,clock=lambda:self.at+timedelta(seconds=1))
        trusted=boundary.boundary_id
        state,receipt=verify_reporting_source(archive=self.archive,boundary=boundary,expected_boundary_id=trusted,clock=lambda:self.at+timedelta(seconds=2))
        self.assertEqual(state.bucket('outcome_histories'),())
        self.assertEqual(state.bucket('opportunities'),())

    def test_empty_interval_does_not_clear_unresolved_historical_obligations(self):
        mlb,catalog,_=fixtures()
        a.refresh_supporting_from_raw(archive=self.archive,mlb_raw=mlb,kalshi_raw=catalog,collected_at=datetime(2026,9,5,4,tzinfo=timezone.utc))
        before=replay_pr17_archive(self.archive,analysis_boundary=self.at)
        pending=tuple(h for h in before.bucket('outcome_histories') if h.latest.unresolved);self.assertTrue(pending)
        self.refresh();after=replay_pr17_archive(self.archive,analysis_boundary=self.at)
        self.assertEqual(before.objects,after.objects)
        required=a.required_mlb_query_dates(trusted_at=self.at,histories=after.bucket('outcome_histories'),purpose='outcomes')
        self.assertTrue(all(h.latest.scheduled_start.date() in required for h in pending))
        before_midnight=datetime(2026,9,13,3,59,tzinfo=timezone.utc)
        after_midnight=before_midnight+timedelta(minutes=1)
        self.assertIn(datetime(2026,9,5).date(),a.required_mlb_query_dates(trusted_at=before_midnight,histories=pending))
        self.assertNotIn(datetime(2026,9,5).date(),a.required_mlb_query_dates(trusted_at=after_midnight,histories=pending))
        self.assertIn(datetime(2026,9,5).date(),a.required_mlb_query_dates(trusted_at=after_midnight,histories=pending,purpose='outcomes'))

    def test_mixed_interval_accepts_valid_empty_page_but_rejects_undeclared_emptiness(self):
        self.at=datetime(2026,9,5,4,tzinfo=timezone.utc)
        pages,catalog=self.pages();mlb,_,_=fixtures();mixed=(replace(pages[0],raw=mlb),pages[1])
        before=self.archive.entries()
        with self.assertRaisesRegex(OperationsError,'schedule-date-incomplete'):
            self.refresh((mixed[0],replace(mixed[1],raw=b'{"dates":[]}')),catalog)
        self.assertEqual(self.archive.entries(),before)
        state=replay_pr17_archive(self.archive,analysis_boundary=self.at)
        expected=a.refresh_supporting_from_raw(archive=None,mlb_raw=mlb,kalshi_raw=b'{"cursor":"","markets":[]}',collected_at=self.at,prior_state=state,derive_only=True)
        result=self.refresh(mixed,catalog)
        self.assertEqual(result['events'],2)
        after=replay_pr17_archive(self.archive,analysis_boundary=self.at)
        self.assertTrue(set(x.to_json() for x in expected)<=set(x.to_json() for x in after.objects))
        self.assertTrue(all('derivation_rule' not in v for e,v in self.bundles()))

    def test_real_fixture_lifecycle_runs_maintenance_after_empty_supporting(self):
        state=a.OperationalState(self.config.log_root/'operational-state')
        state.append(a.OperationalHeartbeat('1','capture-prospective',self.at,self.at,'no-due-work',0,0,0,None))
        pages,catalog=self.pages()
        def supporting(at):return b'{"dates":[]}',b'{"cursor":"","markets":[]}',catalog,pages,3
        def outcomes(at):return b'{"dates":[]}',pages,2
        result=execute('lifecycle-cycle',self.config,clock=lambda:self.at,supporting_loader=supporting,outcome_loader=outcomes,free_disk=lambda _:10**9)
        self.assertEqual(result['disposition'],'success',result)
        self.assertTrue(all(p['disposition']=='success' for p in result['phases']),result)
        self.assertEqual(len(result['phases']),6)

    def test_later_valid_attempt_preserves_failed_heartbeat(self):
        pages,catalog=self.pages()
        def bad(at):return b'{"dates":[]}',b'{"cursor":"","markets":[]}',catalog,pages[:1],2
        with self.assertRaises(OperationsError):execute('refresh-supporting',self.config,clock=lambda:self.at,supporting_loader=bad)
        later=self.at+timedelta(seconds=1);pages,catalog=self.pages(later)
        def good(at):return b'{"dates":[]}',b'{"cursor":"","markets":[]}',catalog,pages,3
        result=execute('refresh-supporting',self.config,clock=lambda:later,supporting_loader=good)
        self.assertEqual(result['disposition'],'unchanged')
        beats=a.OperationalState(self.config.log_root/'operational-state').entries()
        self.assertEqual([b.disposition for b in beats if b.command=='refresh-supporting'],['failed','unchanged'])


if __name__=='__main__':unittest.main()
