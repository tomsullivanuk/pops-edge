"""Offline observable bounds and authority checks for the collector projection."""
import json
import threading
import time
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from forecast_prospective_projection import (
    capture_boundary, collector_lock, load_projection, projection_path,
    projection_status, rebuild_projection, replay_boundary,
)
from forecast_standalone_operations import (
    DesignAuthority, Disposition, NamespaceArchive, OperationsError,
    _lock_available, canonical_bytes, discover_and_capture_prospective,
    replay_pr17_archive, sha256_bytes,
)
from tests import test_forecast_standalone_operations as fixtures
SequenceTransport = fixtures.SequenceTransport


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OperationsTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.g, self.at = self.fixture.seed_prospective()
        self.archive = self.fixture.archive

    def capture(self, clock=None, factory=None):
        return discover_and_capture_prospective(
            archive=self.archive, clock=clock or (lambda: self.at),
            transport_factory=factory or (lambda *_: SequenceTransport(TimeoutError())))

    def test_absent_omitted_altered_version_and_source_fail_without_calls(self):
        path = projection_path(self.archive)
        original = path.read_bytes()
        path.unlink()
        self.assertEqual(projection_status(self.archive, self.at), "absent")
        with self.assertRaisesRegex(OperationsError, "projection-absent"):
            self.capture(factory=lambda *_: self.fail("transport prepared"))
        for change in ("omitted", "version", "altered"):
            value = json.loads(original)
            if change == "omitted": value["projection"]["source_manifest_ids"].pop()
            elif change == "version":
                value["projection"]["builder_version"] = "unrecognized"
                value["sha256"] = sha256_bytes(canonical_bytes(value["projection"]))
            else: value["projection"]["scientific_assertion"] = "eligible"
            path.write_bytes(canonical_bytes(value))
            self.assertEqual(projection_status(self.archive, self.at), "invalid")
            with self.assertRaisesRegex(OperationsError, "projection-invalid"):
                self.capture(factory=lambda *_: self.fail("transport prepared"))
        path.write_bytes(original)
        entry = self.archive.entries()[0]
        source = self.archive._path("normalized", entry["normalized_object_id"])
        source.chmod(0o644)
        source.write_bytes(b"corrupt")
        self.assertEqual(projection_status(self.archive, self.at), "invalid")
        with self.assertRaises(OperationsError):
            self.capture(factory=lambda *_: self.fail("transport prepared"))

    def test_oversized_projection_fails_before_source_reconstruction(self):
        from forecast_prospective_projection import MAX_PROJECTION_BYTES
        projection_path(self.archive).write_bytes(b"x" * (MAX_PROJECTION_BYTES + 1))
        with patch("forecast_prospective_projection.capture_boundary", side_effect=AssertionError("source read")):
            with self.assertRaisesRegex(OperationsError, "projection-invalid"):
                self.capture(factory=lambda *_: self.fail("transport prepared"))

    def test_format_boundary_accepts_exact_limit_and_preserves_cache_on_overflow(self):
        from forecast_prospective_projection import _publish, _read
        boundary = capture_boundary(self.archive)
        replay_boundary(boundary, self.at)
        _publish(self.archive, boundary, self.at)
        path = projection_path(self.archive)
        original = path.read_bytes()
        with patch("forecast_prospective_projection.MAX_PROJECTION_BYTES", len(original)):
            _publish(self.archive, boundary, self.at)
            self.assertEqual(_read(self.archive)["lineage"], boundary._checkpoint_lineage)
        with patch("forecast_prospective_projection.MAX_PROJECTION_BYTES", len(original) - 1):
            with self.assertRaisesRegex(OperationsError, "checkpoint exceeds format bound"):
                _publish(self.archive, boundary, self.at)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaisesRegex(OperationsError, "projection-invalid"):
                _read(self.archive)
        self.assertEqual(list(self.archive.root.glob(".prospective-*.partial")), [])

    def test_checkpoint_above_former_limit_loads_within_emergency_limit(self):
        from forecast_prospective_projection import MAX_PROJECTION_BYTES, _read
        self.assertEqual(MAX_PROJECTION_BYTES, 128 * 1024 * 1024)
        path = projection_path(self.archive)
        original = path.read_bytes()
        # JSON whitespace exercises real read-size enforcement without changing
        # any scientific or checkpoint content or bypassing checksum validation.
        path.write_bytes(original + b" " * (64 * 1024 * 1024 + 1 - len(original)))
        self.assertEqual(_read(self.archive)["authority"], "non-authoritative-operations-checkpoint")
        _, state = load_projection(self.archive, self.at)
        self.assertEqual(state.graph, replay_pr17_archive(self.archive, analysis_boundary=self.at).graph)

    def test_attempt_append_refreshes_and_matches_canonical_replay(self):
        self.capture()
        self.assertEqual(projection_status(self.archive, self.at), "stale")
        boundary, state = load_projection(self.archive, self.at)
        canonical = replay_pr17_archive(self.archive, analysis_boundary=self.at)
        self.assertEqual(state.graph, canonical.graph)
        self.assertEqual(projection_status(self.archive, self.at), "current")
        self.assertEqual(len(boundary._bytes), len(set(boundary._bytes)))
        self.assertEqual(self.capture().provider_request_count, 0)

    def test_interrupted_publication_restart_never_repeats_request(self):
        from forecast_standalone_operations import reconcile_archive
        for stage in ("raw", "normalized"):
            with self.subTest(stage=stage):
                self.fixture.select_namespace("interrupted-" + stage)
                self.g, self.at = self.fixture.seed_prospective()
                self.archive = self.fixture.archive
                transport = SequenceTransport(self.fixture.prospective_response_at(self.g, self.at))
                original = self.archive._publish
                def interrupted(path, body):
                    result = original(path, body)
                    if path.parent.parent == getattr(self.archive, stage + "_root"):
                        raise RuntimeError("simulated process interruption")
                    return result
                with patch.object(self.archive, "_publish", side_effect=interrupted):
                    with self.assertRaisesRegex(RuntimeError, "simulated process interruption"):
                        self.capture(factory=lambda *_: transport)
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(replay_pr17_archive(self.archive, analysis_boundary=self.at).bucket("attempts"), ())
                orphaned = reconcile_archive(self.archive).orphaned
                self.assertTrue(any(x.startswith("raw:") for x in orphaned))
                self.assertEqual(any(x.startswith("normalized:") for x in orphaned), stage == "normalized")
                # A new archive instance has no process-local ownership or cache.
                self.archive = NamespaceArchive(self.archive.config)
                second = SequenceTransport(self.fixture.prospective_response_at(self.g, self.at))
                began = time.monotonic()
                def scoped_only(archive, **kwargs):
                    self.assertIn("_entries", kwargs, "unbounded audit")
                    return reconcile_archive(archive, **kwargs)
                with patch("forecast_prospective_projection.reconcile_archive", side_effect=scoped_only):
                    with self.assertRaisesRegex(OperationsError, "prospective-publication-ambiguous"):
                        self.capture(factory=lambda *_: second)
                self.assertLess(time.monotonic()-began, 30)
                self.assertEqual(len(second.calls), 0)
                self.assertEqual(reconcile_archive(self.archive).orphaned, orphaned)
                self.assertEqual(replay_pr17_archive(self.archive, analysis_boundary=self.at).bucket("attempts"), ())
                self.assertEqual(projection_status(self.archive, self.at), "invalid")
                print(f"interruption after {stage}: first calls=1; restart calls=0; no manifested attempt or orphan adoption")

    def test_completed_manifest_survives_interruption_before_return(self):
        transport = SequenceTransport(self.fixture.prospective_response_at(self.g, self.at))
        original = self.archive._publish
        def interrupted(path, body):
            result = original(path, body)
            if path.parent.parent == self.archive.manifest_root:
                raise RuntimeError("lost after manifest publication")
            return result
        with patch.object(self.archive, "_publish", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "lost after manifest"):
                self.capture(factory=lambda *_: transport)
        self.archive = NamespaceArchive(self.archive.config)
        self.assertEqual(self.capture().provider_request_count, 0)
        self.assertEqual(len(transport.calls), 1)
        attempts = replay_pr17_archive(self.archive, analysis_boundary=self.at).bucket("attempts")
        self.assertEqual(sum(item.provider_call_occurred for item in attempts), 1)

    def test_unresolved_other_opportunity_blocks_checkpoint_use(self):
        from forecast_prospective_projection import begin_request
        with self.archive.mutation_lock():
            begin_request(self.archive, "prior-protocol", "prior-opportunity")
        transport = SequenceTransport(self.fixture.prospective_response_at(self.g, self.at))
        with self.assertRaisesRegex(OperationsError, "prospective-publication-ambiguous"):
            self.capture(factory=lambda *_: transport)
        self.assertEqual(len(transport.calls), 0)
        self.assertEqual(projection_status(self.archive, self.at), "invalid")

    def test_request_fence_survives_interruption_before_response_publication(self):
        class InterruptedTransport:
            calls = 0
            def request(self, *args, **kwargs):
                self.calls += 1
                raise RuntimeError("process lost before publication")
        transport = InterruptedTransport()
        with self.assertRaisesRegex(RuntimeError, "process lost"):
            self.capture(factory=lambda *_: transport)
        self.archive = NamespaceArchive(self.archive.config)
        with self.assertRaisesRegex(OperationsError, "prospective-publication-ambiguous"):
            self.capture(factory=lambda *_: self.fail("ambiguous request repeated"))
        self.assertEqual(transport.calls, 1)

    def test_completed_capture_is_manifest_identical_idempotent_and_conflict_closed(self):
        from forecast_prospective_projection import publish_capture
        captured = []
        def recording(archive, **kwargs):
            captured.append(dict(kwargs))
            return publish_capture(archive, **kwargs)
        transport = SequenceTransport(self.fixture.prospective_response_at(self.g, self.at))
        with patch("forecast_prospective_projection.publish_capture", side_effect=recording):
            self.capture(factory=lambda *_: transport)
        material = captured[0]
        material.pop("request_fence")
        before = self.archive.entries()
        entry = publish_capture(self.archive, **material)
        self.assertEqual(self.archive.entries(), before)
        # The original canonical writer produces precisely the same immutable
        # raw, normalized and manifest identities for the completed material.
        expected = self.archive.commit(**material)
        self.assertEqual(entry, expected)
        self.assertEqual(self.archive.entries(), before)
        changed = {**material, "normalized": {**material["normalized"], "unexpected": True}}
        with self.assertRaisesRegex(OperationsError, "immutable-conflict"):
            publish_capture(self.archive, **changed)
        self.assertEqual(self.archive.entries(), before)
        self.archive = NamespaceArchive(self.archive.config)
        self.assertEqual(self.capture().provider_request_count, 0)

    def test_actual_supporting_tagged_cutoff_success_and_failure_are_independent(self):
        from forecast_standalone_operations import _entry_values, request_identity
        before = projection_path(self.archive).read_bytes()
        excluded = set()
        for disposition in (Disposition.SUCCESS, Disposition.TIMEOUT):
            raw = b'{"market_settled_ts":"2026-05-01T00:00:00Z"}' if disposition is Disposition.SUCCESS else b"cutoff failure"
            digest = sha256_bytes(raw)
            endpoint = self.archive.config.provider_base_url.rstrip("/") + "/historical/cutoff"
            values = _entry_values(archive=self.archive, command="acquire-retrospective-cutoff",
                request_id=request_identity({"raw_sha256": digest, "started_at": self.at}), invoked_at=self.at,
                endpoint=endpoint, disposition=disposition, protocol_id=None, design=DesignAuthority.SUPPORTING,
                diagnostics=("exact Kalshi historical partition cutoff",), provider_effective_at=None)
            values["provider_id"] = "kalshi"
            if disposition is Disposition.SUCCESS:
                normalized = {"schema_version": "1", "record_kind": "pr17c2-historical-cutoff", "provider": "kalshi",
                    "endpoint": "/historical/cutoff", "market_settled_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
                    "raw_sha256": digest, "started_at": self.at, "completed_at": self.at}
                entry = self.archive.commit(raw_body=raw, normalized=normalized, entry_values=values)
                excluded.add(("normalized", entry.normalized_object_id.split(":")[-1]))
            else:
                entry = self.archive.record_failure(entry_values=values, raw_body=raw)
            excluded.add(("raw", digest))
            self.assertNotIn(entry.manifest_entry_id, {x["manifest_entry_id"] for x in capture_boundary(self.archive).entries()})
            original = NamespaceArchive.read_verified
            def guarded(archive, family, identity):
                self.assertNotIn((family, identity.split(":")[-1]), excluded)
                return original(archive, family, identity)
            with patch.object(NamespaceArchive, "read_verified", guarded):
                self.assertEqual(projection_status(self.archive, self.at), "current")
                load_projection(self.archive, self.at)
            self.assertEqual(projection_path(self.archive).read_bytes(), before)

    def test_non_authoritative_outcome_failure_does_not_invalidate(self):
        before = projection_path(self.archive).read_bytes()
        values = self.fixture.entry_values(Disposition.TIMEOUT)
        values.update(command="reconcile-outcomes-failure", invocation_id="failed-outcome",
                      design_authority=DesignAuthority.SUPPORTING)
        self.archive.record_failure(entry_values=values, raw_body=b"failed response")
        self.assertEqual(projection_status(self.archive, self.at), "current")
        self.assertEqual(projection_path(self.archive).read_bytes(), before)

    def test_cross_activation_predecessors_and_classification_correction_match_replay(self):
        import forecast_standalone_research as research
        from forecast_standalone_operations import archive_pr17_authority
        from tests.test_forecast_standalone_research import classification_variant
        g = self.g
        activation = g["activation"].activation_at
        original = replace(g["retro_schedule"], observation_id="cross-original",
            canonical_event_id="cross-event", provider_event_id="cross-provider",
            scheduled_start=activation-timedelta(days=1), collected_at=activation-timedelta(days=2))
        moved = replace(original, observation_id="cross-moved", scheduled_start=activation+timedelta(days=1),
                        collected_at=activation+timedelta(hours=1))
        history = research.OutcomeHistory("cross-event", "mlb-stats-api", (original, moved))
        at = max(self.at, moved.collected_at)
        classification = classification_variant(g["retro_classification"], provider_event_id="cross-provider",
            canonical_event_id="cross-event", collected_at=original.collected_at, effective_at=original.collected_at)
        contracts = [g["retrospective"], history, classification]
        for protocol in (g["retrospective"], g["prospective"]):
            opportunities = research.expected_schedule_opportunities(protocol=protocol, activation=g["activation"],
                schedule_histories=(history,), analysis_boundary=at)
            for opportunity in opportunities:
                context, result = research.create_standalone_eligibility_authority(protocol=protocol,
                    opportunity=opportunity, outcome_history=history, classification=classification,
                    classifications=(classification,), analysis_boundary=at, provenance=g["provenance"])
                contracts.extend((opportunity, context, result))
        archive_pr17_authority(self.archive, contracts, recorded_at=at)
        _, projected = load_projection(self.archive, at)
        self.assertEqual(projected.graph, replay_pr17_archive(self.archive, analysis_boundary=at).graph)
        selected = next(x for x in projected.bucket("outcome_histories") if x.canonical_event_id == "cross-event")
        self.assertEqual(tuple(x.observation_id for x in selected.observations), ("cross-original", "cross-moved"))
        child = classification_variant(classification, effective_at=at+timedelta(seconds=1),
            supersedes_classification_id=classification.standalone_event_classification_evidence_id,
            correction_reason="fixture correction", game_type="R")
        archive_pr17_authority(self.archive, (child,), recorded_at=at+timedelta(seconds=1))
        _, projected = load_projection(self.archive, at+timedelta(seconds=1))
        self.assertEqual(projected.graph, replay_pr17_archive(self.archive, analysis_boundary=at+timedelta(seconds=1)).graph)

    def test_partial_acquisition_cannot_be_refreshed_into_authority(self):
        from forecast_standalone_activation import publish_verified_acquisition
        with self.archive.mutation_lock(), self.assertRaisesRegex(OperationsError, "injected-acquisition-interruption"):
            publish_verified_acquisition(archive=self.archive, provider="kalshi", union_raw=b'{"cursor":"","markets":[]}',
                pages=(("", "/markets?status=open&limit=1000", b'{"cursor":"","markets":[]}'),),
                contracts=(), collected_at=self.at, protocol_id=None, command="refresh-supporting", fail_after_pages=1)
        with self.assertRaises(OperationsError):
            self.capture(factory=lambda *_: self.fail("partial acquisition authorized transport"))

    def test_future_publication_and_missing_dependency_fail_before_transport(self):
        values = self.fixture.entry_values(Disposition.TIMEOUT)
        values.update(command="required-supporting-mutation", invocation_id="future-source",
                      acquired_at=self.at+timedelta(days=1), design_authority=DesignAuthority.SUPPORTING)
        self.archive.record_failure(entry_values=values)
        with self.assertRaisesRegex(OperationsError, "future-effective"):
            self.capture(factory=lambda *_: self.fail("future source authorized transport"))
        dependency = self.archive.entries()[0]
        self.archive._path("manifest", dependency["manifest_entry_id"]).unlink()
        with self.assertRaisesRegex(OperationsError, "projection-invalid"):
            self.capture(factory=lambda *_: self.fail("missing source authorized transport"))

    def test_supporting_cancellation_and_classification_correction_match_replay(self):
        from tests import test_forecast_standalone_commissioning as commissioning
        from forecast_standalone_activation import refresh_supporting_from_raw
        from inspect_forecast_standalone_activation import fixtures
        fixture = commissioning.CommissioningTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        archive = fixture.archive
        mlb, catalog, _ = fixtures()
        at = datetime(2026, 9, 5, 3, 59, tzinfo=timezone.utc)
        refresh_supporting_from_raw(archive=archive, mlb_raw=mlb, kalshi_raw=catalog, collected_at=at)
        load_projection(archive, at)
        changed = json.loads(mlb)
        game = changed["dates"][0]["games"][0]
        game["gameType"] = "P"
        game["status"] = {"abstractGameState": "Final", "detailedState": "Cancelled"}
        refresh_supporting_from_raw(archive=archive, mlb_raw=canonical_bytes(changed), kalshi_raw=catalog,
                                    collected_at=at+timedelta(seconds=1))
        self.assertEqual(projection_status(archive, at+timedelta(seconds=1)), "stale")
        _, projected = load_projection(archive, at+timedelta(seconds=1))
        self.assertEqual(projected.graph, replay_pr17_archive(archive, analysis_boundary=at+timedelta(seconds=1)).graph)
        self.assertTrue(any(x.supersedes_classification_id for x in projected.bucket("classifications")))

    def test_real_retrospective_publication_is_not_replayed(self):
        from tests import test_forecast_standalone_publication as publication
        fixture = publication.PublicationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.publish()
        canonical = replay_pr17_archive(fixture.archive, analysis_boundary=fixture.boundary)
        with patch("forecast_standalone_publication.verify_publication", side_effect=AssertionError("publication replay")):
            scoped = replay_boundary(capture_boundary(fixture.archive), fixture.boundary)
        for name in ("protocols", "activation_boundaries", "outcome_histories", "classifications", "opportunities"):
            self.assertEqual(scoped.bucket(name), canonical.bucket(name))

    def test_factory_preparation_crosses_slot_or_endpoint_truthfully(self):
        target = self.g["prospective_target"]
        for offset in (61, 301):
            with self.subTest(offset=offset):
                # Independent archive: the earlier iteration cannot consume a slot.
                self.fixture.select_namespace(f"cross-{offset}")
                self.g, self.at = self.fixture.seed_prospective()
                self.archive = self.fixture.archive
                now = [target + timedelta(seconds=59)]
                transport = SequenceTransport(TimeoutError())
                def factory(*_):
                    now[0] = target + timedelta(seconds=offset)
                    return transport
                result = self.capture(clock=lambda: now[0], factory=factory)
                state = replay_pr17_archive(self.archive, analysis_boundary=now[0])
                called = [x for x in state.bucket("attempts") if x.provider_call_occurred]
                self.assertEqual(result.provider_request_count, 1 if offset == 61 else 0)
                self.assertEqual([x.slot for x in called], [1] if offset == 61 else [])
                if offset == 301:
                    self.assertEqual(len(state.bucket("attempts")), 5)
                    self.assertEqual(len(state.bucket("snapshots")), 1)

    def test_verification_and_transport_release_global_lock_and_exclude_collectors(self):
        import forecast_standalone_operations as ops
        original = ops._contracts_from_entry
        def checked(*args, **kwargs):
            self.assertTrue(_lock_available(self.archive))
            return original(*args, **kwargs)
        test = self
        class Transport:
            def request(self, *args, **kwargs):
                test.assertTrue(_lock_available(test.archive))
                with test.assertRaisesRegex(OperationsError, "prospective-collector-busy"):
                    test.capture()
                raise TimeoutError()
        with patch.object(ops, "_contracts_from_entry", side_effect=checked):
            self.assertEqual(self.capture(factory=lambda *_: Transport()).provider_request_count, 1)
        self.assertEqual(self.capture().provider_request_count, 0)

    def test_changed_source_boundary_during_preparation_refuses_transport(self):
        def factory(*_):
            values = self.fixture.entry_values(Disposition.TIMEOUT)
            values.update(command="required-supporting-mutation", invocation_id="changed",
                          design_authority=DesignAuthority.SUPPORTING)
            self.archive.record_failure(entry_values=values)
            return SequenceTransport(TimeoutError())
        with self.assertRaisesRegex(OperationsError, "projection-stale"):
            self.capture(factory=factory)
        self.assertFalse(any(x["command"] == "capture-prospective" for x in self.archive.entries()))

    def test_source_corruption_after_verified_preparation_refuses_transport(self):
        transport = SequenceTransport(TimeoutError())
        def factory(*_):
            source = self.archive._path("normalized", self.archive.entries()[0]["normalized_object_id"])
            source.chmod(0o644)
            source.write_bytes(b"changed after verification")
            return transport
        with self.assertRaisesRegex(OperationsError, "projection-invalid"):
            self.capture(factory=factory)
        self.assertEqual(transport.calls, [])

    def test_unrelated_scale_has_zero_payload_reads_and_does_not_invalidate(self):
        baseline = projection_path(self.archive).read_bytes()
        # Independent manifest population at deployment scale; shared large raw
        # objects keep fixture construction cheap without reducing manifest count.
        raw = b"x" * 500_000
        raw_digest = sha256_bytes(raw)
        with self.archive.mutation_lock():
            self.archive._publish(self.archive._path("raw", raw_digest), raw)
            for index in range(2000):
                from forecast_standalone_operations import ManifestEntry
                normalized = {"schema_version": "1", "historical_fixture": index}
                body = canonical_bytes(normalized)
                digest = sha256_bytes(body)
                values = self.fixture.entry_values()
                values["invocation_id"] = f"unrelated:{index}"
                entry = ManifestEntry.create(**values, namespace=self.archive.config.namespace,
                    operating_mode=self.archive.config.mode, raw_object_sha256=raw_digest,
                    normalized_object_id=f"normalized:{digest}", normalized_schema_version="1")
                self.archive._publish(self.archive._path("normalized", digest), body)
                self.archive._publish(self.archive._path("manifest", entry.manifest_entry_id), canonical_bytes(entry))
            values = self.fixture.entry_values(Disposition.DERIVED)
            values.update(command="publish-retrospective-analysis", provider_id="pops-edge-archive-analysis",
                          invocation_id="publication-scale")
            self.archive._commit_normalized_locked(normalized={"schema_version": "1",
                "record_kind": "pr17c3-retrospective-publication", "payload": "x" * 12_000_000}, entry_values=values)
        selected = {x["normalized_object_id"] for x in capture_boundary(self.archive).entries()
                    if x.get("normalized_object_id")}
        original = NamespaceArchive.read_verified
        reads = []
        def guarded(archive, family, identity):
            if family == "normalized" and hasattr(archive, "prospective_entries"): self.assertIn(identity, selected)
            reads.append((family, identity.split(":")[-1]))
            return original(archive, family, identity)
        started = time.monotonic()
        with patch.object(NamespaceArchive, "read_verified", guarded), patch(
                "forecast_standalone_publication.verify_publication", side_effect=AssertionError("historical replay")):
            result = self.capture()
        elapsed = time.monotonic()-started
        self.assertLess(elapsed, 30)
        self.assertEqual(result.provider_request_count, 1)
        self.assertEqual(len(reads), len(set(reads)))
        self.assertEqual(projection_path(self.archive).read_bytes(), baseline)
        reads.clear()
        started = time.monotonic()
        with patch.object(NamespaceArchive, "read_verified", guarded), patch("forecast_standalone_publication.verify_publication", side_effect=AssertionError("historical replay")):
            selected.update(x["normalized_object_id"] for x in capture_boundary(self.archive).entries() if x.get("normalized_object_id"))
            self.assertEqual(self.capture().provider_request_count, 0)
        elapsed = time.monotonic()-started
        self.assertLess(elapsed, 30)
        self.assertEqual(len(reads), len(set(reads)))
        print(f"projection scale: 2000 historical manifests, 12MB publication; {len(reads)} object reads; {elapsed:.3f}s")
        # Interrupt a later slot in the same large archive, then prove the
        # durable restart guard remains metadata/source bounded.
        later = self.at + timedelta(minutes=1)
        transport = SequenceTransport(self.fixture.prospective_response_at(self.g, later))
        publish = self.archive._publish
        def interrupted(path, body):
            result = publish(path, body)
            if path.parent.parent == self.archive.raw_root:
                raise RuntimeError("scale interruption")
            return result
        with patch.object(self.archive, "_publish", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "scale interruption"):
                self.capture(clock=lambda: later, factory=lambda *_: transport)
        self.archive = NamespaceArchive(self.archive.config)
        reads.clear()
        started = time.monotonic()
        with patch.object(NamespaceArchive, "read_verified", guarded):
            with self.assertRaisesRegex(OperationsError, "prospective-publication-ambiguous"):
                self.capture(clock=lambda: later, factory=lambda *_: self.fail("repeated scale request"))
        elapsed = time.monotonic()-started
        self.assertLess(elapsed, 30)
        self.assertEqual(len(reads), len(set(reads)))
        self.assertNotIn(("raw", raw_digest), reads)
        print(f"interrupted scale restart: {len(reads)} source reads; {elapsed:.3f}s; zero provider requests")


    def test_supporting_page_envelope_publication_is_a_stable_boundary(self):
        from tests.test_forecast_standalone_commissioning import CommissioningTests
        from forecast_standalone_activation import refresh_supporting_from_raw
        from inspect_forecast_standalone_activation import fixtures
        fixture = CommissioningTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        archive = fixture.archive
        mlb, catalog, _ = fixtures()
        at = datetime(2026, 9, 5, 3, 59, tzinfo=timezone.utc)
        page_visible, release, reader_done = threading.Event(), threading.Event(), threading.Event()
        original = archive._publish
        errors = []
        result = []
        def paused(path, body):
            value = original(path, body)
            if path.parent.parent == archive.manifest_root and not page_visible.is_set():
                page_visible.set()
                if not release.wait(5): raise AssertionError("test publication release timed out")
            return value
        def writer():
            try:
                with patch.object(archive, "_publish", side_effect=paused):
                    refresh_supporting_from_raw(archive=archive, mlb_raw=mlb, kalshi_raw=catalog, collected_at=at)
            except Exception as exc: errors.append(exc)
        def reader():
            try: result.append(load_projection(archive, at)[1])
            except Exception as exc: errors.append(exc)
            finally: reader_done.set()
        worker = threading.Thread(target=writer)
        worker.start()
        self.assertTrue(page_visible.wait(5))
        observer = threading.Thread(target=reader)
        observer.start()
        self.assertFalse(reader_done.wait(.05))
        release.set()
        worker.join(10); observer.join(10)
        self.assertFalse(worker.is_alive() or observer.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result[0].graph, replay_pr17_archive(archive, analysis_boundary=at).graph)


if __name__ == "__main__":
    unittest.main()
