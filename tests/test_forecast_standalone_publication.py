"""Only temporary synthetic archives; never configured deployed material."""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from forecast_standalone_operations import (
    DeploymentConfig, NamespaceArchive, OperatingMode, RetryPolicy, OperationsError,
    archive_pr17_authority, inspect_archive, rebuild_index, sync_secondary,
    replay_pr17_archive, canonical_bytes,
)
from forecast_standalone_publication import (
    STAGE, publication_source, publish_retrospective_analysis, verify_publication,
)
from inspect_forecast_standalone_research import build_synthetic_bundle
from tests.test_forecast_standalone_research import graph_args


def sized_candidate(count):
    """A valid independent-event synthetic population, not repeated identities."""
    from forecast_standalone_operations import ScientificArchiveState,PR17_GRAPH_BUCKETS
    from forecast_standalone_publication import _candidate
    from forecast_standalone_research import (ResearchCaptureOpportunity,HistoricalMarketCandleObservation,
        HistoricalCandleQueryManifest,create_standalone_eligibility_authority)
    from outcome_contracts import OutcomeHistory
    from tests.test_forecast_standalone_research import classification_variant
    g=build_synthetic_bundle();protocol=g["retrospective"];pid=protocol.standalone_probability_source_protocol_id
    boundary=g["retro_coverage"].analysis_boundary+timedelta(days=1)
    graph={name:[] for name in set(PR17_GRAPH_BUCKETS.values())}
    graph["activation_boundaries"]=[g["activation"]];graph["protocols"]=[protocol]
    for index in range(count):
        event=f"synthetic-event:size-{index}";provider_event=f"synthetic-game:size-{index}"
        observations=tuple(replace(x,canonical_event_id=event,provider_event_id=provider_event,observation_id=f"{x.observation_id}:size-{index}") for x in g["retro_history"].observations)
        history=OutcomeHistory(event,"mlb-stats-api",observations)
        opportunity=ResearchCaptureOpportunity.create(pid,observations[0].observation_id,"winner")
        classification=classification_variant(g["retro_classification"],canonical_event_id=event,provider_event_id=provider_event)
        context,result=create_standalone_eligibility_authority(protocol=protocol,opportunity=opportunity,
            outcome_history=history,classification=classification,classifications=(classification,),
            analysis_boundary=g["retro_eligibility"].analysis_boundary,provenance=g["provenance"])
        seed={key:getattr(g["candle"],key) for key in g["candle"].__dataclass_fields__
              if key not in {"historical_market_candle_observation_id","input_digest"}}
        seed.update(canonical_event_id=event,proposition_id=f"winner:{event}:{g['candle'].home_participant_id}",provider_market_id=f"synthetic-market:size-{index}",manifest_id="pending")
        provisional=HistoricalMarketCandleObservation.create(**seed)
        old=g["manifest"];values={key:getattr(old,key) for key in old.__dataclass_fields__ if key not in {"historical_candle_query_manifest_id","input_digest"}}
        values.update(canonical_event_id=event,proposition_id=seed["proposition_id"],provider_market_id=seed["provider_market_id"],
            opportunity_id=opportunity.research_capture_opportunity_id,
            pages=tuple(replace(x,returned_candle_evidence_ids=(provisional.historical_market_candle_observation_id,)) for x in old.pages),
            returned_candle_evidence_ids=(provisional.historical_market_candle_observation_id,))
        manifest=HistoricalCandleQueryManifest.create(**values)
        candle=HistoricalMarketCandleObservation.create(**{**seed,"manifest_id":manifest.historical_candle_query_manifest_id})
        for name,item in (("outcome_histories",history),("opportunities",opportunity),("classifications",classification),
                          ("eligibility_contexts",context),("eligibility_results",result),("manifests",manifest),("candles",candle)):
            graph[name].append(item)
    state=ScientificArchiveState(boundary,tuple(x for values in graph.values() for x in values),tuple((k,tuple(v)) for k,v in sorted(graph.items())),())
    with patch("forecast_standalone_activation.canonical_retrospective_authority",return_value=(g["activation"],protocol)):
        return _candidate(state,pid,"scientific-input:synthetic-sizing",boundary,"synthetic-sizing")


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.archive = NamespaceArchive(DeploymentConfig(
            "publication-test", "publication-test", OperatingMode.DRY_RUN,
            root / "dry-run/publication-test/primary", root / "dry-run/publication-test/secondary",
            "https://fixture.invalid", RetryPolicy(1, 1, 1, (), 0), 1, root / "logs"))
        self.g = build_synthetic_bundle()
        args = graph_args(self.g, path="retro", reports=False)
        self.boundary = args.pop("analysis_boundary") + timedelta(days=1)
        for key in ("historical_derivations", "measurements", "coverages", "performances", "reports"):
            args.pop(key)
        sources = tuple(x for values in args.values() for x in values)
        archive_pr17_authority(self.archive, sources, recorded_at=self.boundary-timedelta(seconds=1))
        self.authority = patch("forecast_standalone_activation.canonical_retrospective_authority",
                               return_value=(self.g["activation"], self.g["retrospective"]))
        self.authority.start()
        self.addCleanup(self.authority.stop)
        self.pid = self.g["retrospective"].standalone_probability_source_protocol_id
        self.snapshot = publication_source(self.archive, self.boundary)[1]

    def publish(self, **overrides):
        args = dict(archive=self.archive, protocol_id=self.pid,
                    expected_source_snapshot=self.snapshot, clock=lambda: self.boundary)
        args.update(overrides)
        return publish_retrospective_analysis(**args)

    def inventory(self):
        return {str(p.relative_to(self.archive.root)): p.read_bytes()
                for folder in (self.archive.raw_root, self.archive.normalized_root, self.archive.manifest_root)
                for p in folder.rglob("*") if p.is_file()}

    def test_whole_bundle_and_unchanged_repeat(self):
        raw = tuple(self.archive.raw_root.rglob("*"))
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            result = self.publish()
        self.assertEqual((result["provider_calls"], result["contracts"]), (0, 3))
        state = replay_pr17_archive(self.archive, analysis_boundary=self.boundary)
        coverage, = state.bucket("coverages")
        self.assertEqual(len(coverage.reconciliation.measured), 1)
        self.assertEqual(len(coverage.reconciliation.archive_unavailable), 1)
        self.assertEqual(set(coverage.coverage_universe_ids),
                         set(coverage.reconciliation.measured + coverage.reconciliation.archive_unavailable))
        self.assertEqual(tuple(self.archive.raw_root.rglob("*")), raw)
        before = self.inventory()
        with patch("forecast_standalone_publication._candidate", side_effect=AssertionError("must not derive again")):
            repeated = self.publish(clock=lambda: self.boundary+timedelta(days=10))
        self.assertEqual(repeated, {**result, "disposition": "unchanged"})
        self.assertEqual(before, self.inventory())
        self.assertTrue(inspect_archive(self.archive).ready)
        rebuild_index(self.archive)
        self.assertEqual(sync_secondary(self.archive)["conflicts"], 0)
        copy=NamespaceArchive(replace(self.archive.config,primary_root=self.archive.config.secondary_root,secondary_root=self.archive.config.primary_root))
        self.assertEqual(replay_pr17_archive(copy,analysis_boundary=self.boundary).bucket("coverages"),state.bucket("coverages"))
        self.assertEqual(publication_source(self.archive, self.boundary)[1], self.snapshot)
        self.assertEqual(self.publish()["publication_id"], result["publication_id"])

    def test_interruptions_resume_exact_frozen_payload(self):
        for failpoint in ("before-normalized", "after-normalized", "before-manifest", "after-manifest"):
            with self.subTest(failpoint=failpoint):
                # A separate namespace for each interruption, keeping prior objects intact.
                child = PublicationTests("test_whole_bundle_and_unchanged_repeat")
                child.setUp()
                try:
                    with self.assertRaisesRegex(OperationsError, "injected-interruption"):
                        child.publish(failpoint=failpoint)
                    stage = (child.archive.root/STAGE).read_bytes()
                    before = replay_pr17_archive(child.archive, analysis_boundary=child.boundary)
                    self.assertEqual(len(before.bucket("coverages")), int(failpoint=="after-manifest"))
                    result = child.publish(clock=lambda: child.boundary+timedelta(seconds=20))
                    self.assertEqual(result["analysis_boundary"], child.boundary.isoformat())
                    self.assertEqual((child.archive.root/STAGE).read_bytes(), stage)
                    self.assertEqual(child.publish()["disposition"], "unchanged")
                finally:
                    child.doCleanups()

    def test_wrong_protocol_and_changed_snapshot_fail_before_staging(self):
        for values in ({"protocol_id": "foreign"}, {"expected_source_snapshot": "foreign"}):
            with self.subTest(values=values), self.assertRaises(OperationsError):
                self.publish(**values)
        self.assertFalse((self.archive.root/STAGE).exists())

    def test_malformed_candidate_and_conflicting_stage_fail_closed(self):
        with patch("forecast_standalone_publication._candidate", return_value={"malformed": True}):
            with self.assertRaises(OperationsError): self.publish()
        self.assertFalse((self.archive.root/STAGE).exists())
        with self.assertRaises(OperationsError): self.publish(failpoint="before-normalized")
        with self.assertRaises(OperationsError): self.publish(expected_source_snapshot="changed")
        value = json.loads((self.archive.root/STAGE).read_bytes())
        value["bundle"]["contracts"].append(value["bundle"]["contracts"][0])
        with self.assertRaises(OperationsError): verify_publication(self.archive, value)

    def test_integrity_and_programming_failures_propagate(self):
        for error in (OperationsError("archive-integrity-failure", "test"), RuntimeError("test")):
            with patch("forecast_standalone_publication.publication_source", side_effect=error):
                with self.assertRaises(type(error)): self.publish()
        path = next(self.archive.raw_root.glob("*/*"))
        path.chmod(0o600)
        path.write_bytes(b"corrupt synthetic fixture")
        with self.assertRaisesRegex(OperationsError, "archive-integrity-failure"): self.publish()

    def test_source_change_after_stage_or_publication_is_rejected(self):
        self.publish()
        archive_pr17_authority(self.archive, (self.g["prospective"],), recorded_at=self.boundary)
        with self.assertRaisesRegex(OperationsError, "snapshot changed"): self.publish()

    def test_later_inputs_do_not_invalidate_frozen_historical_replay(self):
        self.publish()
        archive_pr17_authority(self.archive,(self.g["prospective"],),recorded_at=self.boundary+timedelta(seconds=1))
        self.assertTrue(replay_pr17_archive(self.archive,analysis_boundary=self.boundary+timedelta(seconds=2)).bucket("coverages"))
        with self.assertRaisesRegex(OperationsError,"snapshot changed"):
            self.publish(clock=lambda:self.boundary+timedelta(seconds=2))

    def test_source_change_after_staging_is_rejected_without_new_writes(self):
        with self.assertRaises(OperationsError): self.publish(failpoint="before-normalized")
        archive_pr17_authority(self.archive, (self.g["prospective"],), recorded_at=self.boundary)
        before = self.inventory()
        with self.assertRaisesRegex(OperationsError, "snapshot changed"): self.publish()
        self.assertEqual(before, self.inventory())

    def test_missing_and_corrupt_objects_block_globally(self):
        for family in ("raw", "normalized", "manifest"):
            for damage in ("missing", "corrupt"):
                with self.subTest(family=family, damage=damage):
                    child = PublicationTests("test_whole_bundle_and_unchanged_repeat")
                    child.setUp()
                    try:
                        path = next(getattr(child.archive, family+"_root").glob("*/*"))
                        if damage=="missing": path.unlink()
                        else:
                            path.chmod(0o600)
                            path.write_bytes(b"damaged synthetic object")
                        with self.assertRaises(OperationsError): child.publish()
                        self.assertFalse((child.archive.root/STAGE).exists())
                    finally: child.doCleanups()

    def test_publication_not_visible_before_actual_manifest_time(self):
        with self.assertRaises(OperationsError): self.publish(failpoint="before-manifest")
        self.publish(clock=lambda:self.boundary+timedelta(seconds=10))
        self.assertFalse(replay_pr17_archive(self.archive,analysis_boundary=self.boundary).bucket("coverages"))
        self.assertTrue(replay_pr17_archive(self.archive,analysis_boundary=self.boundary+timedelta(seconds=10)).bucket("coverages"))

    def test_cli_publication_never_constructs_provider_or_credentials(self):
        from operate_forecast_standalone_activation import main
        with patch("operate_forecast_standalone_activation.DeploymentConfig.from_json",return_value=self.archive.config), \
             patch("operate_forecast_standalone_activation.configured_kalshi_transport",side_effect=AssertionError("credentials forbidden")), \
             patch("operate_forecast_standalone_activation.execute",return_value={"provider_calls":0}) as execute:
            self.assertEqual(main(["--config","unused-fixture-config","publish-retrospective-analysis",
                                   "--protocol-id",self.pid,"--source-snapshot",self.snapshot]),0)
            self.assertEqual(execute.call_args.kwargs["publication_protocol_id"],self.pid)
            self.assertEqual(execute.call_args.kwargs["expected_source_snapshot"],self.snapshot)

    def test_exclusion_and_empty_candle_window_remain_coverage_dispositions(self):
        from forecast_standalone_research import HistoricalCandleQueryManifest, create_standalone_eligibility_authority
        from tests.test_forecast_standalone_research import classification_variant
        args = graph_args(self.g,path="retro",reports=False)
        for key in ("analysis_boundary","historical_derivations","measurements","coverages","performances","reports"):
            args.pop(key)
        old = self.g["manifest"]
        values = {name:getattr(old,name) for name in old.__dataclass_fields__
                  if name not in {"historical_candle_query_manifest_id","input_digest"}}
        values.update(pages=tuple(replace(page,returned_candle_evidence_ids=()) for page in old.pages),
                      returned_candle_evidence_ids=())
        args["manifests"] = (HistoricalCandleQueryManifest.create(**values),)
        args["candles"] = ()
        classification = classification_variant(self.g["retro_failure_classification"],ordinary_game=False)
        context,result = create_standalone_eligibility_authority(
            protocol=self.g["retrospective"],opportunity=self.g["retro_failure"],
            outcome_history=self.g["retro_failure_history"],classification=classification,
            classifications=(classification,),analysis_boundary=self.g["retro_failure_eligibility"].analysis_boundary,
            provenance=self.g["provenance"])
        args["classifications"]=(self.g["retro_classification"],classification)
        args["eligibility_contexts"]=(self.g["retro_context"],context)
        args["eligibility_results"]=(self.g["retro_eligibility"],result)
        root=Path(self.temporary.name)
        self.archive=NamespaceArchive(replace(self.archive.config,namespace="gaps",primary_root=root/"dry-run/gaps/primary",secondary_root=root/"dry-run/gaps/secondary"))
        archive_pr17_authority(self.archive,tuple(x for values in args.values() for x in values),recorded_at=self.boundary)
        self.snapshot=publication_source(self.archive,self.boundary)[1]
        result=self.publish()
        self.assertEqual(result["contracts"],1)
        coverage,=replay_pr17_archive(self.archive,analysis_boundary=self.boundary).bucket("coverages")
        self.assertEqual((len(coverage.reconciliation.protocol_ineligible),len(coverage.reconciliation.candle_unavailable)),(1,1))
        self.assertFalse(coverage.reconciliation.measured)

    def test_scaled_synthetic_fixture_has_distinct_valid_objects(self):
        value=sized_candidate(3)
        self.assertEqual(len(value["bundle"]["contracts"]),7)
        self.assertEqual(len(set(value["bundle"]["contracts"])),7)

    def test_duplicate_publication_manifests_fail_closed(self):
        from forecast_standalone_publication import _manifest_values
        self.publish()
        value=json.loads((self.archive.root/STAGE).read_bytes())
        with self.archive.mutation_lock():
            self.archive._commit_normalized_locked(normalized=value,entry_values=_manifest_values(self.archive,value,self.boundary+timedelta(seconds=1)))
        with self.assertRaisesRegex(OperationsError,"ambiguous publication"):self.publish()
        with self.assertRaisesRegex(OperationsError,"ambiguous publication"):replay_pr17_archive(self.archive,analysis_boundary=self.boundary+timedelta(seconds=2))


if __name__ == "__main__":
    unittest.main()
