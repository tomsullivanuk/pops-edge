"""Explicit archive-only PR17C3 derivation/Measurement/Coverage publication.

No transport, acquisition, aggregate analysis, or automatic recovery lives here.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from forecast_standalone_operations import (
    DesignAuthority, Disposition, ManifestEntry, OperationsError, PR17_GRAPH_BUCKETS,
    _entry_values, _utc, canonical_bytes, pr17_contract_bundle, reconcile_archive,
    replay_pr17_archive, request_identity, sha256_bytes,
)

KIND = "pr17c3-retrospective-publication"
COMMAND = "publish-retrospective-analysis"
STAGE = "retrospective-publication-stage.json"


def _fail(detail):
    raise OperationsError("retrospective-publication-conflict", detail)


def publication_source(archive, boundary):
    """Verified scientific input only; indexes, logs and this output are excluded."""
    state = replay_pr17_archive(archive, analysis_boundary=boundary,
                               _exclude_retrospective_publications=True)
    material = {"namespace": archive.config.namespace, "mode": archive.config.mode.value,
                "source_manifest_ids": state.source_manifest_ids,
                "contracts": sorted(x.to_json() for x in state.objects)}
    return state, "scientific-input:" + sha256_bytes(canonical_bytes(material))


def _authority(state, protocol_id):
    from forecast_standalone_activation import canonical_retrospective_authority
    activation, protocol = canonical_retrospective_authority()
    if protocol_id != protocol.standalone_probability_source_protocol_id:
        _fail("noncanonical retrospective Protocol")
    if protocol not in state.bucket("protocols") or activation not in state.bucket("activation_boundaries"):
        _fail("exact archived Protocol and activation authority required")
    return activation, protocol


def _augmented(state, contracts, boundary):
    from forecast_standalone_research import deserialize_v3, validate_standalone_research_graph
    graph = {name: list(values) for name, values in state.graph}
    for contract in contracts:
        if deserialize_v3(contract.to_json()) != contract:
            _fail("candidate serialization does not round trip")
        graph[PR17_GRAPH_BUCKETS[type(contract).__name__]].append(contract)
    validate_standalone_research_graph(**graph, analysis_boundary=boundary)


def _candidate(state, protocol_id, snapshot, boundary, namespace):
    from forecast_research_contracts import ResearchContractProvenance
    from forecast_standalone_research import (
        create_historical_candle_probability_derivation,
        create_probability_source_measurement_v3, create_probability_source_coverage_v3,
        validate_manifest_lineage,
    )
    activation, protocol = _authority(state, protocol_id)
    for bucket in ("historical_derivations", "measurements", "coverages"):
        if any(x.protocol_id == protocol_id for x in state.bucket(bucket)):
            _fail("independent derived authority already exists for Protocol")
    provenance = ResearchContractProvenance(
        "pops-edge:archive-retrospective-publication", "1",
        additional_input_ids=(protocol_id, snapshot, "namespace:" + namespace),
        notes=("archive-derived Analysis; no new raw Evidence",), generated_at=boundary)
    opportunities = tuple(x for x in state.bucket("opportunities") if x.protocol_id == protocol_id)
    ids = {x.research_capture_opportunity_id for x in opportunities}
    contexts = tuple(x for x in state.bucket("eligibility_contexts") if x.research_capture_opportunity_id in ids)
    results = tuple(x for x in state.bucket("eligibility_results") if x.research_capture_opportunity_id in ids)
    histories = state.bucket("outcome_histories")
    manifests = tuple(x for x in state.bucket("manifests") if x.protocol_id == protocol_id)
    candles = state.bucket("candles")
    common = dict(protocol=protocol, activation=activation, analysis_boundary=boundary,
                  opportunities=opportunities, eligibility_contexts=contexts,
                  eligibility_results=results, schedule_histories=histories,
                  classifications=state.bucket("classifications"), manifests=manifests,
                  candles=candles, provenance=provenance)
    # Canonical Coverage, not caller categories or successful candles, owns selection.
    baseline = create_probability_source_coverage_v3(**common)
    targets = set(baseline.reconciliation.derivation_unavailable)
    terminal = validate_manifest_lineage(manifests, boundary)
    derivations, measurements = [], []
    for opportunity in opportunities:
        oid = opportunity.research_capture_opportunity_id
        if oid not in targets:
            continue
        context, = (x for x in contexts if x.research_capture_opportunity_id == oid)
        result, = (x for x in results if x.research_capture_opportunity_id == oid)
        history, = (x for x in histories if x.canonical_event_id == context.canonical_event_id)
        schedule, = (x for x in history.observations if x.observation_id == opportunity.schedule_observation_id)
        manifest, = (x for x in terminal if x.opportunity_id == oid)
        derivation = create_historical_candle_probability_derivation(
            protocol=protocol, activation=activation, opportunity=opportunity,
            eligibility_context=context, eligibility_result=result, schedule_history=history,
            analysis_boundary=boundary, manifest=manifest, manifests=manifests,
            candles=tuple(x for x in candles if x.manifest_id == manifest.historical_candle_query_manifest_id),
            home_participant_id=schedule.home_participant_id,
            complement_outcome_id=schedule.away_participant_id,
            effective_at=boundary, provenance=provenance, limitations=protocol.design.limitations)
        derivations.append(derivation)
        outcomes = tuple(x for x in history.observations if x.authoritative_final and x.collected_at <= boundary)
        if outcomes:
            measurements.append(create_probability_source_measurement_v3(
                protocol=protocol, activation=activation, opportunity=opportunity,
                eligibility_context=context, eligibility_result=result, schedule_history=history,
                derivations=(derivation,), outcome=outcomes[-1], outcome_histories=histories,
                effective_at=boundary, provenance=provenance, limitations=protocol.design.limitations))
    coverage = create_probability_source_coverage_v3(
        **common, historical_derivations=derivations, measurements=measurements)
    contracts = (*derivations, *measurements, coverage)
    _augmented(state, contracts, boundary)
    bundle = pr17_contract_bundle(*contracts)
    material = {"schema_version": "1", "record_kind": KIND, "protocol_id": protocol_id,
                "namespace": namespace, "source_snapshot": snapshot,
                "analysis_boundary": boundary.isoformat(), "provider_calls": 0,
                "bundle_sha256": sha256_bytes(canonical_bytes(bundle)), "bundle": bundle}
    material["publication_id"] = KIND + ":" + sha256_bytes(canonical_bytes(material))
    return material


def verify_publication(archive, value):
    """Exact source/digest and full graph gate shared by staging, replay and retry."""
    from forecast_standalone_research import deserialize_v3
    required = {"schema_version", "record_kind", "protocol_id", "namespace", "source_snapshot",
                "analysis_boundary", "provider_calls", "bundle_sha256", "bundle", "publication_id"}
    if set(value) != required or value["record_kind"] != KIND or value["schema_version"] != "1":
        _fail("unknown publication schema")
    if value["namespace"] != archive.config.namespace or value["provider_calls"] != 0:
        _fail("foreign namespace or provider-call authority")
    material = {k: v for k, v in value.items() if k != "publication_id"}
    if value["publication_id"] != KIND + ":" + sha256_bytes(canonical_bytes(material)):
        _fail("publication identity digest mismatch")
    boundary = datetime.fromisoformat(value["analysis_boundary"])
    _utc(boundary, "publication analysis boundary")
    state, snapshot = publication_source(archive, boundary)
    _authority(state, value["protocol_id"])
    if snapshot != value["source_snapshot"]:
        _fail("scientific source snapshot changed")
    bundle = value["bundle"]
    contracts = tuple(deserialize_v3(x) for x in bundle["contracts"])
    if canonical_bytes(pr17_contract_bundle(*contracts)) != canonical_bytes(bundle):
        _fail("bundle serialization conflict")
    if sha256_bytes(canonical_bytes(bundle)) != value["bundle_sha256"]:
        _fail("bundle digest mismatch")
    allowed = {"HistoricalCandleProbabilityDerivation", "ProbabilitySourceMeasurementV3", "ProbabilitySourceCoverageV3"}
    for item in contracts:
        if type(item).__name__ not in allowed or item.protocol_id != value["protocol_id"]:
            _fail("foreign contract in publication")
        if item.provenance.generated_at != boundary or item.provenance.producer_id != "pops-edge:archive-retrospective-publication":
            _fail("publication provenance conflict")
    coverage = tuple(x for x in contracts if type(x).__name__ == "ProbabilitySourceCoverageV3")
    if len(coverage) != 1 or coverage[0].coverage_scope != "cumulative" or coverage[0].analysis_boundary != boundary:
        _fail("exactly one matching cumulative Coverage required")
    reconciled = coverage[0].reconciliation
    if reconciled.derivation_unavailable:
        _fail("publication omits an available derivation")
    derived = {x.opportunity_id for x in contracts if type(x).__name__ == "HistoricalCandleProbabilityDerivation"}
    if derived != set(reconciled.measured) | set(reconciled.outcome_unresolved):
        _fail("publication derivation membership conflicts with Coverage")
    contexts = {x.research_capture_opportunity_id:x for x in state.bucket("eligibility_contexts")}
    histories = {x.canonical_event_id:x for x in state.bucket("outcome_histories")}
    for oid in reconciled.outcome_unresolved:
        if any(x.authoritative_final and x.collected_at<=boundary for x in histories[contexts[oid].canonical_event_id].observations):
            _fail("publication omits an available Measurement")
    expected_inputs = {value["protocol_id"], snapshot, "namespace:" + archive.config.namespace}
    for item in contracts:
        if set(item.provenance.additional_input_ids)!=expected_inputs or item.provenance.producer_version!="1":
            _fail("publication source provenance conflict")
    _augmented(state, contracts, boundary)
    return contracts


def _manifest_values(archive, value, completed):
    boundary = datetime.fromisoformat(value["analysis_boundary"])
    _utc(completed, "publication completion")
    if completed < boundary:
        _fail("trusted clock precedes frozen staging boundary")
    values = _entry_values(archive=archive, command=COMMAND,
        request_id=request_identity({"publication_id": value["publication_id"]}),
        invoked_at=boundary, endpoint="local://archive/retrospective-publication",
        disposition=Disposition.DERIVED, protocol_id=value["protocol_id"],
        design=DesignAuthority.RETROSPECTIVE,
        diagnostics=(value["publication_id"], value["source_snapshot"], "provider_calls:0"),
        provider_effective_at=boundary)
    values.update(provider_id="pops-edge-archive-analysis", acquired_at=completed,
                  invocation_id="operations-invocation:"+sha256_bytes(canonical_bytes({"publication_id":value["publication_id"]})))
    return values


def _published(archive):
    result = []
    for entry in archive.entries():
        if entry.get("command") != COMMAND:
            continue
        if entry.get("raw_object_sha256") or not entry.get("normalized_object_id"):
            _fail("publication must be normalized-only")
        value = json.loads(archive.read_verified("normalized", entry["normalized_object_id"]))
        if entry.get("protocol_id") != value.get("protocol_id") or entry.get("provider_id") != "pops-edge-archive-analysis":
            _fail("publication manifest provenance conflict")
        verify_publication(archive, value)
        expected = ManifestEntry.create(**_manifest_values(archive,value,datetime.fromisoformat(entry["acquired_at"]["datetime_utc"])),
            namespace=archive.config.namespace, operating_mode=archive.config.mode,
            raw_object_sha256=None, normalized_object_id="normalized:"+sha256_bytes(canonical_bytes(value)),
            normalized_schema_version="1")
        if canonical_bytes(expected)!=canonical_bytes(entry):
            _fail("publication manifest binding conflict")
        stage=archive.root/STAGE
        if stage.exists() and stage.read_bytes()!=canonical_bytes(value):
            _fail("staged bytes differ from publication")
        result.append((entry, value))
    if len(result) > 1:
        _fail("ambiguous publication manifests")
    return result


def publish_retrospective_analysis(*, archive, protocol_id, expected_source_snapshot,
                                   clock=lambda: datetime.now(timezone.utc), failpoint=None):
    """One explicit snapshot publication; exact stage resumption only, never acquisition."""
    with archive.mutation_lock():
        integrity = reconcile_archive(archive)
        if integrity.blocking:
            raise OperationsError("archive-integrity-failure", "publication requires verified source objects")
        existing = _published(archive)
        if existing:
            if integrity.orphaned:
                _fail("unrelated orphaned content conflicts with completed publication")
            entry, value = existing[0]
            if (value["protocol_id"], value["source_snapshot"]) != (protocol_id, expected_source_snapshot):
                _fail("existing publication differs from requested source authority")
            if publication_source(archive,clock())[1]!=value["source_snapshot"]:
                _fail("scientific source snapshot changed since publication")
            return _result(entry["manifest_entry_id"], value, "unchanged")
        stage = archive.root / STAGE
        if stage.exists():
            value = json.loads(stage.read_bytes())
            if (value.get("protocol_id"), value.get("source_snapshot")) != (protocol_id, expected_source_snapshot):
                _fail("staged publication differs from requested source authority")
            verify_publication(archive, value)
        else:
            if integrity.orphaned:
                _fail("unrelated orphaned content prevents new staging")
            boundary = clock()
            _utc(boundary, "trusted publication clock")
            state, snapshot = publication_source(archive, boundary)
            if snapshot != expected_source_snapshot:
                _fail("scientific source snapshot changed before staging")
            value = _candidate(state, protocol_id, snapshot, boundary, archive.config.namespace)
            verify_publication(archive, value)
            archive._publish(stage, canonical_bytes(value))
        normalized_id = "normalized:" + sha256_bytes(canonical_bytes(value))
        if set(integrity.orphaned) - {normalized_id}:
            _fail("unrelated orphaned content prevents stage resumption")
        verify_publication(archive, value)
        if publication_source(archive,clock())[1]!=value["source_snapshot"]:
            _fail("scientific source snapshot changed since staging")
        if failpoint == "before-normalized":
            raise OperationsError("injected-interruption", failpoint)
        archive._publish(archive._path("normalized", normalized_id), canonical_bytes(value))
        if failpoint in {"after-normalized", "before-manifest"}:
            raise OperationsError("injected-interruption", failpoint)
        completed = clock()
        values = _manifest_values(archive,value,completed)
        entry = archive._commit_normalized_locked(normalized=value, entry_values=values)
        if failpoint == "after-manifest":
            raise OperationsError("injected-interruption", failpoint)
        _published(archive)
        replay_pr17_archive(archive, analysis_boundary=completed)
        return _result(entry.manifest_entry_id, value, "published")


def _result(manifest_id, value, disposition):
    return {"disposition": disposition, "provider_calls": 0, "manifest_id": manifest_id,
            "publication_id": value["publication_id"], "source_snapshot": value["source_snapshot"],
            "analysis_boundary": value["analysis_boundary"], "bundle_sha256": value["bundle_sha256"],
            "normalized_bytes": len(canonical_bytes(value)), "contracts": len(value["bundle"]["contracts"])}
