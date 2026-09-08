"""Offline supporting-session/correction topology and replay work bounds."""
import json
import tempfile
import time
import unittest
from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
from itertools import permutations
from tests import pr29_catalog_reference as reference
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import forecast_standalone_activation as activation
from forecast_prospective_projection import (
    ProspectiveSourceBoundary, capture_boundary, load_projection, projection_path,
    projection_status, rebuild_projection, replay_boundary,
)
from forecast_standalone_operations import (
    DeploymentConfig, DesignAuthority, Disposition, NamespaceArchive, OperatingMode,
    OperationsError, RetryPolicy, _entry_values, archive_pr17_authority,
    canonical_bytes, request_identity,
)
from inspect_forecast_standalone_activation import fixtures


class CanonicalBoundary(ProspectiveSourceBoundary):
    """The pre-correction replay path with the same fresh verified byte view."""
    memoized_supporting_verification = None


def supporting_fixture(root, *, sessions=2, markets=20):
    config = DeploymentConfig('supporting-shape', 'supporting-shape', OperatingMode.DRY_RUN,
        root/'dry-run/supporting-shape/primary', root/'dry-run/supporting-shape/secondary',
        'https://fixture.invalid', RetryPolicy(1, 1, 1, (), 0), 1, root/'logs')
    archive = NamespaceArchive(config)
    archive_pr17_authority(archive, activation.canonical_activation_authorities(),
                          recorded_at=datetime(2026, 8, 27, tzinfo=timezone.utc))
    mlb, catalog, _ = fixtures()
    actual = json.loads(catalog)['markets']
    # Unmapped catalog objects still require complete partition/byte validation.
    # Nested rule material makes repeated canonical serialization observable.
    noise = [{'ticker': f'UNRELATED-{i}', 'settlement_ts': '2026-07-01T00:00:00Z',
              'rules': {'text': 'synthetic catalog rule ' * 20,
                        'details': [{'name': f'field-{j}', 'value': str(i)} for j in range(8)]}}
             for i in range(markets)]
    for number in range(sessions):
        at = datetime(2026, 9, 6, tzinfo=timezone.utc) + timedelta(minutes=number)
        session = f'supporting-session:shape-{number}'
        def preserve(provider, purpose, identity, endpoint, raw, **kw):
            activation.preserve_supporting_response(archive=archive, session_id=session,
                provider=provider, purpose=purpose, request_identity_value=identity,
                endpoint=endpoint, raw=raw, started_at=at, completed_at=at,
                disposition=Disposition.SUCCESS, **kw)
        preserve('mlb-stats-api', 'schedule', '2026-09-05',
                 activation.canonical_mlb_schedule_request('2026-09-05')[1], mlb)
        preserve('kalshi', 'historical-cutoff', 'historical-cutoff',
                 'https://fixture.invalid/historical/cutoff',
                 b'{"market_settled_ts":"2026-08-01T00:00:00Z"}')
        for partition, records in (('historical', noise), ('live', actual)):
            chunks = [records[i:i+100] for i in range(0, len(records), 100)] or [[]]
            for position, chunk in enumerate(chunks):
                cursor = '' if position == 0 else f'page-{position}'
                next_cursor = '' if position == len(chunks)-1 else f'page-{position+1}'
                endpoint = 'https://fixture.invalid' + activation.encoded_kalshi_retrospective_catalog_path(
                    cursor, historical=partition == 'historical')
                preserve('kalshi', 'catalog', cursor, endpoint,
                    canonical_bytes({'markets': chunk, 'cursor': next_cursor}),
                    partition=partition, partition_position=position)
        # Reproduce preserved legacy envelopes using the ordinary fixture writer,
        # then use the real append-only correction command. No verifier is stubbed:
        # the root is independently checked under its supported legacy rule.
        complete = activation.publish_supporting_session_completion
        verify = activation.verify_supporting_session_completion
        with patch.object(activation, 'ACQUISITION_UNION_RULE_VERSION', 'provider-pages-canonical-union-1'), patch.object(
                activation, 'publish_supporting_session_completion',
                side_effect=lambda **kw: complete(**kw, derivation_rule=None)), patch.object(
                activation, 'verify_supporting_session_completion',
                side_effect=lambda *a, **kw: verify(*a, **{**kw, 'allow_legacy': True})):
            activation.complete_supporting_session_from_archive(archive=archive, session_id=session)
        activation.complete_supporting_session_from_archive(archive=archive, session_id=session,
            correction_reason=activation.APPROVED_SUPPORTING_CORRECTION_REASON)
    return archive, at + timedelta(minutes=1)


def replay_with_counts(archive, at, *, canonical=False, entries=None):
    selected = capture_boundary(archive).entries() if entries is None else entries
    view = (CanonicalBoundary if canonical else ProspectiveSourceBoundary)(archive, selected)
    counts = Counter()
    original = activation._verify_acquisition_bundle
    merge = activation.merge_retrospective_catalog_pages
    merges = []
    def counted_merge(*args, **kwargs):
        merges.append(1)
        return merge(*args, **kwargs)
    def counted(archive, value, **kw):
        counts[value['acquisition_id']] += 1
        return original(archive, value, **kw)
    started = time.monotonic()
    with ExitStack() as stack:
        stack.enter_context(patch.object(activation, '_verify_acquisition_bundle', side_effect=counted))
        stack.enter_context(patch.object(activation, 'merge_retrospective_catalog_pages',
            side_effect=reference.merge_retrospective_catalog_pages if canonical else counted_merge))
        if canonical:
            stack.enter_context(patch.object(activation, 'merge_kalshi_catalog_pages',
                side_effect=reference.merge_kalshi_catalog_pages))
        state = replay_boundary(view, at)
    view.test_catalog_merges = len(merges)
    return state, view, counts, time.monotonic()-started


class SupportingReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive, self.at = supporting_fixture(Path(self.temp.name))

    def test_corrections_permutations_and_successful_checks_are_replay_local(self):
        canonical, _, baseline, _ = replay_with_counts(self.archive, self.at, canonical=True)
        selected = capture_boundary(self.archive).entries()
        # Equal chronology is legal; reverse discovery order must preserve the
        # exact outcome of the corresponding canonical replay ordering.
        for entries in (selected, tuple(reversed(selected))):
            try:
                expected, _, _, _ = replay_with_counts(self.archive, self.at, canonical=True, entries=entries)
            except OperationsError as canonical_error:
                with self.assertRaises(OperationsError) as optimized_error:
                    replay_with_counts(self.archive, self.at, entries=entries)
                self.assertEqual(str(optimized_error.exception), str(canonical_error))
                continue
            actual, view, counts, _ = replay_with_counts(self.archive, self.at, entries=entries)
            self.assertEqual(actual, expected)
            self.assertTrue(actual.bucket('opportunities'))
            self.assertEqual(len(counts), 8)  # root/corrected MLB+Kalshi per session
            self.assertEqual(set(counts.values()), {1})
            self.assertIsNone(view._supporting_verification)
        self.assertGreater(sum(baseline.values()), 3*8)
        again, _, counts, _ = replay_with_counts(self.archive, self.at)
        self.assertEqual(again, canonical)
        self.assertEqual(sum(counts.values()), 8)

    def test_rebuild_current_stale_and_fresh_digest_verification(self):
        expected, _, _, _ = replay_with_counts(self.archive, self.at, canonical=True)
        rebuild_projection(self.archive, self.at)
        before = projection_path(self.archive).read_bytes()
        self.assertEqual(projection_status(self.archive, self.at), 'current')
        _, actual = load_projection(self.archive, self.at)
        self.assertEqual(actual, expected)
        self.assertEqual(projection_path(self.archive).read_bytes(), before)
        values = _entry_values(archive=self.archive, command='supporting-fixture-failure',
            request_id=request_identity({'fixture': 1}), invoked_at=self.at,
            endpoint='fixture://supporting', disposition=Disposition.TIMEOUT,
            protocol_id=None, design=DesignAuthority.SUPPORTING, diagnostics=('visible fixture failure',))
        self.archive.record_failure(entry_values=values)
        self.assertEqual(projection_status(self.archive, self.at), 'stale')
        _, refreshed = load_projection(self.archive, self.at)
        expected, _, _, _ = replay_with_counts(self.archive, self.at, canonical=True)
        self.assertEqual(refreshed, expected)
        self.assertEqual(projection_status(self.archive, self.at), 'current')
        # A later invocation must not inherit a successful check or verified bytes.
        raw = next(x['raw_object_sha256'] for x in self.archive.entries() if x.get('raw_object_sha256'))
        path = self.archive._path('raw', raw)
        path.chmod(0o644)
        path.write_bytes(b'corrupt source after prior successful replay')
        for canonical in (False, True):
            with self.assertRaises(OperationsError):
                replay_with_counts(self.archive, self.at, canonical=canonical)

    def test_missing_dependencies_and_duplicate_correction_fail_equivalently(self):
        entries = self.archive.entries()
        correction = next(x for x in entries if x['command'] == 'correct-retrospective-supporting-session')
        value = self.archive.read_json_verified('normalized', correction['normalized_object_id'])
        values = _entry_values(archive=self.archive, command='correct-retrospective-supporting-session',
            request_id=request_identity({'duplicate': 1}), invoked_at=self.at,
            endpoint='fixture://duplicate', disposition=Disposition.SUCCESS, protocol_id=None,
            design=DesignAuthority.SUPPORTING, diagnostics=('duplicate fixture correction',))
        self.archive.commit(raw_body=canonical_bytes(value), normalized=value, entry_values=values)
        errors = []
        for canonical in (False, True):
            with self.assertRaises(OperationsError) as caught:
                replay_with_counts(self.archive, self.at, canonical=canonical)
            errors.append(str(caught.exception))
        self.assertEqual(errors[0], errors[1])
        raw = next(x['raw_object_sha256'] for x in entries if x.get('raw_object_sha256'))
        self.archive._path('raw', raw).unlink()
        errors = []
        for canonical in (False, True):
            with self.assertRaises(OperationsError) as caught:
                replay_with_counts(self.archive, self.at, canonical=canonical)
            errors.append(caught.exception.code)
        self.assertEqual(errors[0], errors[1])

    def test_catalog_topology_scale_work_is_once_per_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, at = supporting_fixture(Path(directory), sessions=3, markets=1200)
            canonical, _, baseline, baseline_seconds = replay_with_counts(archive, at, canonical=True)
            actual, view, counts, seconds = replay_with_counts(archive, at)
            self.assertEqual(actual, canonical)
            self.assertEqual(len(counts), 12)
            self.assertEqual(set(counts.values()), {1})
            self.assertEqual(view.test_catalog_merges, 1)  # identical pages across root/corrections/sessions
            self.assertGreater(sum(baseline.values()), 3*sum(counts.values()))
            self.assertLess(seconds, 20)
            expected_reads = {('raw', x['raw_object_sha256']) for x in view.entries() if x.get('raw_object_sha256')}
            expected_reads.update(('normalized', x['normalized_object_id'].split(':')[-1]) for x in view.entries() if x.get('normalized_object_id'))
            self.assertEqual(set(view._bytes), expected_reads)
            print(json.dumps({'fixture': 'supporting-completions-and-corrections',
                'sessions': 3, 'catalog_markets_per_session': 1200, 'selected_manifests': len(view.entries()),
                'unique_object_reads': len(view._bytes), 'source_bytes': view.source_bytes,
                'canonical_bundle_checks': sum(baseline.values()), 'optimized_bundle_checks': sum(counts.values()),
                'optimized_catalog_unions': view.test_catalog_merges,
                'canonical_seconds': baseline_seconds, 'optimized_seconds': seconds}))


class CatalogByteEquivalenceTests(unittest.TestCase):
    def test_original_and_optimized_union_bytes_and_failures(self):
        cutoff = datetime(2026, 8, 1, tzinfo=timezone.utc)
        past = {'ticker': 'A', 'settlement_ts': '2026-07-01T00:00:00Z',
                'nested': {'unicode': '雪', 'values': [None, True, 7, 'quoted " text']}}
        current = {'ticker': 'B', 'settlement_ts': '2026-08-01T00:00:00Z'}
        def page(position, partition, markets, cursor='', next_cursor=''):
            raw = canonical_bytes({'markets': markets, 'cursor': next_cursor})
            return activation.KalshiCatalogPage(position, cursor, next_cursor, raw,
                tuple(markets), partition=partition, partition_position=0)
        pages = (page(0, 'historical', [past]), page(1, 'live', [current]))
        cases = list(permutations(pages))
        cases.extend([
            (pages[0], page(1, 'live', [past, current])),  # identical cross-partition duplicate
            (pages[0], page(1, 'live', [{**past, 'nested': {'changed': True}}, current])),
            (replace(pages[0], next_cursor='missing'), pages[1]),
            (replace(pages[0], request_cursor='foreign'), pages[1]),
            (replace(pages[0], partition='foreign'), pages[1]),
            (replace(pages[0], partition_position=2), pages[1]),
            (page(0, 'historical', [{**past, 'settlement_ts': None}]), pages[1]),
            (pages[0], page(1, 'live', [{**current, 'settlement_ts': 'naive'}])),
            (page(0, 'historical', [past, {**past, 'extra': 'conflict'}]), pages[1]),
            (page(0, 'historical', [{**past, 'settlement_ts': '2026-08-02T00:00:00Z'}]), pages[1]),
        ])
        for case in cases:
            with self.subTest(case=cases.index(case)):
                try:
                    expected = reference.merge_retrospective_catalog_pages(case, cutoff)
                except OperationsError as error:
                    with self.assertRaises(OperationsError) as actual:
                        activation.merge_retrospective_catalog_pages(case, cutoff)
                    self.assertEqual(str(actual.exception), str(error))
                else:
                    actual = activation.merge_retrospective_catalog_pages(case, cutoff)
                    self.assertEqual(actual, expected)
                    self.assertEqual(actual, canonical_bytes(json.loads(actual)))
                    self.assertEqual(activation._canonical_json_digest(actual),
                                     __import__('hashlib').sha256(actual).hexdigest())
        # Ordinary cursor union uses the same optimized encoded-market boundary.
        chain = (page(0, None, [past], next_cursor='next'),
                 page(1, None, [current], cursor='next'))
        for case in permutations(chain):
            self.assertEqual(activation.merge_kalshi_catalog_pages(case),
                             reference.merge_kalshi_catalog_pages(case))
