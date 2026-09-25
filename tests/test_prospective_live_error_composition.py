"""Actual live adapter + collector, with offline requester responses only."""
import unittest
from datetime import timedelta

from forecast_standalone_activation import BoundedLiveReadOnlyTransport
from forecast_standalone_operations import OperationsError, replay_pr17_archive
from forecast_prospective_projection import check_capture_persistence
from operate_forecast_standalone_activation import execute
from tests import test_forecast_prospective_market_selection as selection_tests


class LiveErrorCompositionTests(unittest.TestCase):
    def fixture(self):
        fixture = selection_tests.MarketSelectionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_known_failures_publish_once_and_allow_later_valid_capture(self):
        cases = (
            (429, b'{"error":"limited"}', 'AcquisitionFailed', True),
            (500, b'{"error":"unavailable"}', 'AcquisitionFailed', True),
            (302, b'{"redirect":"elsewhere"}', 'CapturedInvalid', True),
            (200, b'{', 'CapturedInvalid', True),
            (200, b'1', 'CapturedInvalid', True),
            (200, b'\xff', 'CapturedInvalid', True),
            (200, b'{"orderbook_fp":{}}', 'CapturedInvalid', True),
            (200, b'x' * 1025, 'AcquisitionFailed', False),
            (429, b'{"token":"must-not-persist"}', 'AcquisitionFailed', False),
            (200, b'{"token":"must-not-persist"}', 'AcquisitionFailed', False),
            (200, b'{"token":"must-not-persist"', 'AcquisitionFailed', False),
            (None, TimeoutError(), 'AcquisitionFailed', False),
            (None, ConnectionError(), 'AcquisitionFailed', False),
        )
        for status, body, result_type, preserve in cases:
            with self.subTest(status=status, body=repr(body)[:50]):
                f = self.fixture()
                calls = []
                def requester(url, headers, timeout, redirects):
                    calls.append((url, timeout, redirects))
                    if len(calls) > 1:
                        return 200, f.book, {}
                    if isinstance(body, Exception):
                        raise body
                    return status, body, {'Location': 'https://never-follow.invalid', 'Retry-After': '60'}
                transport = BoundedLiveReadOnlyTransport('https://fixture.invalid', requester,
                                                        timeout_seconds=1, maximum_bytes=1024)
                def capture(at):
                    return execute('capture-prospective', f.archive.config, clock=lambda: at,
                                   transport_factory=lambda *_: transport)
                result = capture(f.at)
                self.assertEqual(result['provider_calls'], 1)
                self.assertEqual(calls, [(f'https://fixture.invalid/markets/{f.market["ticker"]}/orderbook', 1, False)])
                entries = f.archive.entries()
                self.assertFalse(check_capture_persistence(f.archive, entries))
                state = replay_pr17_archive(f.archive, analysis_boundary=f.at)
                attempts = state.bucket('attempts')
                self.assertEqual(len(attempts), 1)
                self.assertEqual(type(attempts[0].result).__name__, result_type)
                self.assertTrue(attempts[0].provider_call_occurred)
                self.assertFalse(state.bucket('market_observations'))
                entry = next(x for x in entries if x['command'] == 'capture-prospective')
                if preserve:
                    self.assertEqual(f.archive.read_verified('raw', entry['raw_object_sha256']), body)
                else:
                    self.assertIsNone(entry['raw_object_sha256'])
                if isinstance(body, bytes) and b'must-not-persist' in body:
                    for path in f.archive.root.rglob('*'):
                        if path.is_file():
                            self.assertNotIn(b'must-not-persist', path.read_bytes())
                # Same slot cannot repeat the already accounted-for call.
                self.assertEqual(capture(f.at)['provider_calls'], 0)
                later = f.at + timedelta(minutes=1)
                self.assertEqual(capture(later)['provider_calls'], 1)
                self.assertEqual(len(calls), 2)
                later_state = replay_pr17_archive(f.archive, analysis_boundary=later)
                by_slot = {a.slot: a for a in later_state.bucket('attempts')}
                self.assertEqual(type(by_slot[1].result).__name__, 'CapturedValid')
                self.assertEqual(by_slot[0], attempts[0])
                self.assertFalse(check_capture_persistence(f.archive, f.archive.entries()))

    def test_unexpected_errors_leave_unknown_call_fenced(self):
        for failure in (OperationsError('archive-corrupt', 'fixture'), RuntimeError('fixture')):
            with self.subTest(failure=type(failure).__name__):
                f = self.fixture()
                calls = []
                def requester(*args):
                    calls.append(args)
                    raise failure
                transport = BoundedLiveReadOnlyTransport('https://fixture.invalid', requester, timeout_seconds=1)
                with self.assertRaises(type(failure)):
                    execute('capture-prospective', f.archive.config, clock=lambda: f.at,
                            transport_factory=lambda *_: transport)
                self.assertEqual(len(check_capture_persistence(f.archive, f.archive.entries())), 1)
                with self.assertRaisesRegex(OperationsError, 'prospective-publication-ambiguous'):
                    execute('capture-prospective', f.archive.config,
                            clock=lambda: f.at + timedelta(minutes=1), transport_factory=lambda *_: transport)
                self.assertEqual(len(calls), 1)

    def test_request_uses_signing_and_requested_timeout_without_predecoding(self):
        from types import SimpleNamespace
        calls, signed = [], []
        def headers(method, path, timestamp):
            signed.append((method, path, timestamp))
            return {'fixture-signature': 'signed'}
        def requester(*args):
            calls.append(args)
            return 500, b'{', {'Retry-After': '1'}
        transport = BoundedLiveReadOnlyTransport('https://fixture.invalid/api', requester,
            timeout_seconds=5, request_signer=SimpleNamespace(headers=headers), timestamp_ms=lambda: 42)
        response = transport.request('GET', 'ignored', params={'market_id': 'M'}, timeout=2, allow_redirects=False)
        self.assertEqual((response.status_code, response.body), (500, b'{'))
        self.assertEqual(signed, [('GET', '/api/markets/M/orderbook', 42)])
        self.assertEqual(calls[0][2:], (2, False))
        self.assertEqual(calls[0][1]['fixture-signature'], 'signed')
        for timeout in (0, 6):
            with self.assertRaisesRegex(OperationsError, 'transport-configuration'):
                transport.request('GET', 'ignored', params={'market_id': 'M'}, timeout=timeout, allow_redirects=False)
        self.assertEqual(len(calls), 1)

    def test_configured_requester_preserves_http_error_and_bounds_reads(self):
        import io
        import urllib.error
        from types import SimpleNamespace
        from unittest.mock import patch
        from operate_forecast_standalone_activation import configured_kalshi_transport
        f = self.fixture()
        reads, opens = [], []
        class ResponseBody(io.BytesIO):
            def read(self, size=-1):
                reads.append(size)
                return super().read(size)
        def open_error(request, timeout):
            opens.append((request.full_url, timeout))
            error = urllib.error.HTTPError(request.full_url, 429, 'limited',
                {'Retry-After': '60'}, ResponseBody(b'{"error":"limited"}'))
            self.addCleanup(error.close)
            raise error
        def build_opener(handler):
            self.assertIsNone(handler.redirect_request(None, None, 302, None, {}, 'https://never-follow.invalid'))
            return SimpleNamespace(open=open_error)
        with patch('urllib.request.build_opener', side_effect=build_opener):
            transport = configured_kalshi_transport(f.archive.config, lambda: f.at)
            result = execute('capture-prospective', f.archive.config, clock=lambda: f.at,
                             transport_factory=lambda *_: transport)
        self.assertEqual(result['provider_calls'], 1)
        self.assertEqual(len(opens), 1)
        self.assertEqual(reads, [2_000_001])
        self.assertFalse(check_capture_persistence(f.archive, f.archive.entries()))
