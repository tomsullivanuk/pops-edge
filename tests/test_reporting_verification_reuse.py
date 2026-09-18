"""Invocation-local reuse; original source adversarial suite also runs scoped."""
from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import patch

import forecast_reporting_source as source
import forecast_reporting_delivery as delivery
import tests.test_forecast_reporting_source as source_tests
import tests.test_forecast_reporting_delivery as delivery_tests


class ScopedSourceTests(source_tests.ReportingSourceTests):
    def setUp(self):
        super().setUp()
        self.enterContext(source.reporting_verification_scope())

    def test_one_reconstruction_but_fresh_receipts(self):
        with patch.object(source, '_reconstruct_uncached', wraps=source._reconstruct_uncached) as replay:
            boundary = self.freeze()
            first, receipt = self.verify(boundary)
            second, later = self.verify(boundary, clock=lambda: self.at + timedelta(days=2))
            self.assertEqual(first, second)
            self.assertNotEqual(receipt.verified_at, later.verified_at)
            self.assertEqual(replay.call_count, 1)

    def test_new_cutoff_and_nested_invocation_do_not_share_trust(self):
        with patch.object(source, '_reconstruct_uncached', wraps=source._reconstruct_uncached) as replay:
            first = self.freeze()
            self.freeze(clock=lambda: self.at + timedelta(seconds=1))
            self.assertEqual(replay.call_count, 2)
            with source.reporting_verification_scope():
                self.verify(first)
                self.assertEqual(replay.call_count, 3)

    def test_failed_reconstruction_not_cached(self):
        with patch.object(source, '_reconstruct_uncached', side_effect=ValueError('synthetic failure')) as replay:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'synthetic failure'):
                    self.freeze()
            self.assertEqual(replay.call_count, 2)

    def test_scope_cleans_up_after_exception(self):
        outer = source._reconstruction_scope.get()
        with self.assertRaises(ValueError):
            with source.reporting_verification_scope():
                self.freeze()
                raise ValueError('stop')
        self.assertIs(source._reconstruction_scope.get(), outer)

    def test_selection_containers_cannot_poison_cache(self):
        boundary = self.freeze()
        _, selection = source._reconstruct(self.archive, boundary.manifest_inventory, boundary.evidence_cutoff_at)
        selection.clear()
        self.verify(boundary)


class DeliveryReuseTests(delivery_tests.DeliveryTests):
    # Existing delivery tests also exercise generation with the new scope.
    def test_generation_reconstructs_once_and_matches_uncached_bytes(self):
        started = self.now
        with patch.object(source, '_reconstruct_uncached', wraps=source._reconstruct_uncached) as replay:
            cached = self.generate()
            self.assertEqual(replay.call_count, 1)
        cached_bytes = {name: self.payload(cached, name) for name in
                        ('source.json', 'analysis.json', 'projections.json', 'report.html')}
        self.now = started
        with patch.object(delivery, 'reporting_verification_scope', nullcontext), \
             patch.object(source, '_reconstruct_uncached', wraps=source._reconstruct_uncached) as replay:
            uncached = self.generate()
            self.assertGreaterEqual(replay.call_count, 7)
        for name in ('source.json', 'analysis.json', 'projections.json'):
            self.assertEqual(cached_bytes[name], self.payload(uncached, name), name)
        self.assertIsNone(source._reconstruction_scope.get())
        # A separate explicit verification is independent, not a warmed trust hit.
        with patch.object(source, '_reconstruct_uncached', wraps=source._reconstruct_uncached) as replay:
            self.verify(cached)
            self.assertGreaterEqual(replay.call_count, 3)
