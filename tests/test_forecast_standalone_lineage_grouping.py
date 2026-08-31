"""Differential and deterministic work-count checks; synthetic material only.

The two reference functions are frozen from main d7d1b38cb1bff717cb4f03f09f40544827660586.
Keep them independent of the optimized implementations, including rejection order.
"""
import copy
import itertools
import unittest
from collections import Counter
from datetime import timedelta
from unittest.mock import patch

import forecast_standalone_research as fsr
from event_contracts import ContractError, _require_aware
from forecast_standalone_research import _fail
from forecast_standalone_operations import canonical_bytes
from inspect_forecast_standalone_research import build_synthetic_bundle
from tests.test_forecast_standalone_publication import sized_candidate


def reference_classifications(classifications, boundary):
    _require_aware(boundary,"classification boundary");values=tuple(classifications);by_id={x.standalone_event_classification_evidence_id:x for x in values}
    if len(by_id)!=len(values):_fail("classification registry contains duplicate or conflicting identity")
    groups={(x.authoritative_provider_id,x.provider_event_id,x.canonical_event_id) for x in values};selected=[]
    for group in groups:
        members=tuple(x for x in values if (x.authoritative_provider_id,x.provider_event_id,x.canonical_event_id)==group)
        for item in members:
            if item.supersedes_classification_id:
                parent=by_id.get(item.supersedes_classification_id)
                if parent is None or parent not in members:_fail("orphaned or cross-event classification correction")
                if item.effective_at<=parent.effective_at:_fail("reversed classification correction chronology")
                if len(tuple(x for x in members if x.supersedes_classification_id==parent.standalone_event_classification_evidence_id))>1:_fail("branched classification correction")
        visible=tuple(x for x in members if x.effective_at<=boundary)
        if not visible:continue
        roots=tuple(x for x in visible if x.supersedes_classification_id is None)
        if len(roots)!=1:_fail("classification lineage requires one root")
        current=roots[0];seen={current.standalone_event_classification_evidence_id}
        while True:
            children=tuple(x for x in visible if x.supersedes_classification_id==current.standalone_event_classification_evidence_id)
            if len(children)>1:_fail("branched classification correction")
            if not children:break
            current=children[0];seen.add(current.standalone_event_classification_evidence_id)
        if len(seen)!=len(visible):_fail("disconnected classification correction lineage")
        selected.append(current)
    return tuple(sorted(selected,key=lambda x:(x.canonical_event_id,x.provider_event_id)))


def reference_manifests(manifests, boundary):
    _require_aware(boundary,"manifest analysis boundary");values=tuple(manifests);by_id={x.historical_candle_query_manifest_id:x for x in values}
    if len(by_id)!=len(values):_fail("duplicate or conflicting manifest identity")
    children={key:[] for key in by_id}
    for item in values:
        if item.supersedes_manifest_id:
            parent=by_id.get(item.supersedes_manifest_id)
            if parent is None:_fail("orphaned manifest correction")
            if (parent.protocol_id,parent.opportunity_id,parent.canonical_event_id,parent.proposition_id,parent.provider_market_id)!=(item.protocol_id,item.opportunity_id,item.canonical_event_id,item.proposition_id,item.provider_market_id):_fail("cross-authority manifest correction")
            if item.effective_at<=parent.effective_at:_fail("cyclic or reversed manifest correction")
            children[parent.historical_candle_query_manifest_id].append(item)
            if len(children[parent.historical_candle_query_manifest_id])>1:_fail("branched manifest correction")
    selected=[]
    groups={(x.protocol_id,x.opportunity_id,x.provider_market_id) for x in values}
    for group in groups:
        visible=[x for x in values if (x.protocol_id,x.opportunity_id,x.provider_market_id)==group and x.effective_at<=boundary]
        roots=[x for x in visible if x.supersedes_manifest_id is None]
        if len(roots)!=1:_fail("manifest lineage requires one unambiguous root")
        current=roots[0];seen={current.historical_candle_query_manifest_id}
        while True:
            nxt=[x for x in visible if x.supersedes_manifest_id==current.historical_candle_query_manifest_id]
            if len(nxt)>1:_fail("branched manifest correction")
            if not nxt:break
            current=nxt[0]
            if current.historical_candle_query_manifest_id in seen:_fail("cyclic manifest correction")
            seen.add(current.historical_candle_query_manifest_id)
        if len(seen)!=len(visible):_fail("ambiguous or disconnected manifest lineage")
        selected.append(current)
    return tuple(sorted(selected,key=lambda x:(x.protocol_id,x.opportunity_id,x.provider_market_id)))


def variant(record, **changes):
    excluded = {"input_digest", "standalone_event_classification_evidence_id", "historical_candle_query_manifest_id"}
    values = {name: getattr(record, name) for name in record.__dataclass_fields__ if name not in excluded}
    return type(record).create(**{**values, **changes})


def malformed(record, **changes):
    """Deliberately bypass construction ONLY to probe invalid registry graphs/IDs."""
    result = copy.copy(record)
    for name, value in changes.items():
        object.__setattr__(result, name, value)
    return result


class CountedRecord:
    """Count validator attribute work without wall-clock CI thresholds."""
    def __init__(self, record, counts):
        self.record = record
        self.counts = counts

    def __getattr__(self, name):
        self.counts[name] += 1
        return getattr(self.record, name)


class LineageGroupingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = build_synthetic_bundle()

    def compare(self, current, reference, values, boundary, accepted):
        def outcome(function, supplied):
            try:
                return ("accepted", function(supplied, boundary))
            except ContractError as error:
                return ("rejected", error.code, error.detail)
        for order in itertools.permutations(values):
            with self.subTest(order=tuple(x.input_digest for x in order), boundary=boundary):
                expected = outcome(reference, order)
                self.assertEqual(expected[0], "accepted" if accepted else "rejected")
                self.assertEqual(outcome(current, iter(order)), expected)

    def scenarios(self, root, id_field, parent_field, foreign_fields):
        at = root.effective_at
        child = variant(root, **{parent_field: getattr(root, id_field)},
                        correction_reason="synthetic correction", effective_at=at+timedelta(seconds=1))
        grandchild = variant(child, **{parent_field: getattr(child, id_field)}, effective_at=at+timedelta(seconds=2))
        other_root = variant(root, limitations=("distinct synthetic root",))
        branch = variant(child, limitations=("synthetic branch",))
        cases = [
            ("empty", (), at, True),
            ("root at equality", (root,), at, True),
            ("chain at root", (root, child, grandchild), at, True),
            ("chain at child", (root, child, grandchild), child.effective_at, True),
            ("chain at terminal", (root, child, grandchild), grandchild.effective_at, True),
            ("duplicate identity", (root, root), at, False),
            ("conflicting identity", (root, malformed(other_root, **{id_field: getattr(root, id_field)})), at, False),
            ("duplicate roots", (root, other_root), at, False),
            ("missing predecessor", (child,), child.effective_at, False),
            ("future orphan", (root, variant(child, **{parent_field: "absent"})), at, False),
            ("equal correction chronology", (root, variant(child, effective_at=at)), at, False),
            ("reversed correction chronology", (root, malformed(child, effective_at=at-timedelta(seconds=1))), at, False),
            ("future branch", (root, child, branch), at, False),
            ("visible branch", (root, child, branch), child.effective_at, False),
            ("self cycle", (malformed(child, **{parent_field: getattr(child, id_field)}),), at, False),
            ("disconnected cycle", (other_root, malformed(root, **{parent_field: getattr(child, id_field)}), child), child.effective_at, False),
        ]
        for field in foreign_fields:
            # The parent is present, but belongs to incompatible authority.
            cases.append(("foreign "+field, (root, variant(child, **{field: "foreign-authority"})), at, False))
        return cases

    def test_classification_differential(self):
        root = self.g["retro_classification"]
        for name, values, boundary, accepted in self.scenarios(root,
                "standalone_event_classification_evidence_id", "supersedes_classification_id",
                ("authoritative_provider_id", "provider_event_id", "canonical_event_id")):
            with self.subTest(case=name):
                self.compare(fsr.select_authoritative_event_classifications, reference_classifications,
                             values, boundary, accepted)
        # Existing asymmetry: a well-formed future-only classification group is invisible.
        self.compare(fsr.select_authoritative_event_classifications, reference_classifications,
                     (root,), root.effective_at-timedelta(microseconds=1), True)

    def test_manifest_differential(self):
        root = self.g["manifest"]
        for name, values, boundary, accepted in self.scenarios(root,
                "historical_candle_query_manifest_id", "supersedes_manifest_id",
                ("protocol_id", "opportunity_id", "canonical_event_id", "proposition_id", "provider_market_id")):
            with self.subTest(case=name):
                self.compare(fsr.validate_manifest_lineage, reference_manifests, values, boundary, accepted)
        # Do not silently discard future-only manifest groups: legacy validation rejects them.
        self.compare(fsr.validate_manifest_lineage, reference_manifests,
                     (root,), root.effective_at-timedelta(microseconds=1), False)

    def test_multiple_groups_and_boundary_ordering(self):
        for root, current, reference, group_field in (
                (self.g["retro_classification"], fsr.select_authoritative_event_classifications,
                 reference_classifications, "canonical_event_id"),
                (self.g["manifest"], fsr.validate_manifest_lineage, reference_manifests, "opportunity_id")):
            records = tuple(variant(root, **{group_field: "synthetic-group:"+str(i)}) for i in range(3))
            self.compare(current, reference, records, root.effective_at, True)
            self.compare(current, reference, records, root.effective_at.replace(tzinfo=None), False)

    def test_canonical_candidate_bytes_and_identities_unchanged(self):
        for size in (1, 8, 32):
            with self.subTest(events=size):
                with patch.object(fsr, "select_authoritative_event_classifications", reference_classifications), \
                     patch.object(fsr, "validate_manifest_lineage", reference_manifests):
                    before = sized_candidate(size)
                after = sized_candidate(size)
                self.assertEqual(canonical_bytes(after), canonical_bytes(before))
                self.assertEqual(after["publication_id"], before["publication_id"])

    def test_grouping_work_is_linear_per_invocation(self):
        for root, function, group_field, id_field, parent_field in (
                (self.g["retro_classification"], fsr.select_authoritative_event_classifications,
                 "canonical_event_id", "standalone_event_classification_evidence_id", "supersedes_classification_id"),
                (self.g["manifest"], fsr.validate_manifest_lineage,
                 "opportunity_id", "historical_candle_query_manifest_id", "supersedes_manifest_id")):
            for layout in ("independent", "chain"):
                totals = []
                for size in (16, 64, 128):
                    counts = Counter(); records = []
                    for index in range(size):
                        fields = {group_field: f"group:{index}"} if layout == "independent" else {}
                        if layout == "chain" and records:
                            fields.update({parent_field: getattr(records[-1], id_field), "correction_reason": "synthetic chain"})
                        record = variant(root, effective_at=root.effective_at+timedelta(seconds=index), **fields)
                        records.append(record)
                    values = tuple(CountedRecord(x, counts) for x in records)
                    selected = function(values, records[-1].effective_at)
                    self.assertEqual(len(selected), size if layout == "independent" else 1)
                    with self.subTest(function=function.__name__, layout=layout, size=size):
                        self.assertLess(sum(counts.values()), 45*size)
                    totals.append(sum(counts.values()))
                self.assertLessEqual(totals[-1], 9*totals[0])


if __name__ == "__main__":
    unittest.main()
