"""Offline deterministic inspector for the synthetic PR15 reporting fixture."""
from __future__ import annotations

import sys
from pathlib import Path

from forecast_comparative_reporting import (
    ComparativeDriftAnalysis, ComparativePerformanceReport,
    TimeBoundedComparativePerformance, create_comparative_drift_analysis,
    create_comparative_performance_report, create_time_bounded_comparative_performance,
    validate_comparative_reporting_contracts,
)
from forecast_research_contracts import ProtocolClaimSet
from inspect_forecast_comparative_research import load_fixture as load_pr14_fixture


def load_fixture(path: Path) -> dict[str, object]:
    graph = load_pr14_fixture(path)
    protocol = graph["protocols"][0]
    current_boundary = graph["after"]
    claim_set = ProtocolClaimSet.create(
        protocol_id=protocol.research_protocol_id, effective_at=protocol.effective_at,
        edge_claim_ids=tuple(item.edge_claim_id for item in graph["claims"]),
        provenance=graph["provenance"])
    bounded, drift = [], []
    for claim in graph["claims"]:
        domain = next(item for item in protocol.research_domains
                      if item.research_domain_id == claim.research_domain_id)
        current = create_time_bounded_comparative_performance(
            protocol=protocol, edge_claim=claim, research_domain=domain,
            analysis_boundary=current_boundary, opportunities=graph["opportunities"],
            eligibility_contexts=graph["eligibility_contexts"],
            eligibility_results=graph["eligibility_results"], snapshots=graph["snapshots"],
            measurements=graph["measurements"], outcome_histories=graph["outcome_histories"],
            provenance=graph["provenance"], limitations=("synthetic output; not an empirical conclusion",))
        historical = next(item for item in graph["performances"]
                          if item.edge_claim_id == claim.edge_claim_id and item.analysis_boundary == graph["before"])
        analysis = create_comparative_drift_analysis(
            protocol=protocol, historical=historical, current=current,
            measurements=graph["measurements"], provenance=graph["provenance"],
            limitations=("synthetic Drift output",))
        bounded.append(current)
        drift.append(analysis)
    report = create_comparative_performance_report(
        protocol=protocol, claims=graph["claims"], protocol_claim_sets=(claim_set,),
        cumulative_performances=graph["performances"], bounded_performances=bounded,
        drift_analyses=drift, provenance=graph["provenance"],
        analysis_boundary=current_boundary, limitations=("synthetic report; no Research Review conclusion",))
    graph.update(protocol_claim_sets=(claim_set,), bounded_performances=tuple(bounded),
                 drift_analyses=tuple(drift), reports=(report,))
    for name, contract_type in (("protocol_claim_sets", ProtocolClaimSet),
                                ("bounded_performances", TimeBoundedComparativePerformance),
                                ("drift_analyses", ComparativeDriftAnalysis),
                                ("reports", ComparativePerformanceReport)):
        graph[name] = tuple(contract_type.from_json(item.to_json()) for item in graph[name])
    return graph


def run(path: Path) -> tuple[str, ...]:
    graph = load_fixture(path)
    validate_comparative_reporting_contracts(
        protocols=graph["protocols"], claims=graph["claims"],
        protocol_claim_sets=graph["protocol_claim_sets"],
        cumulative_performances=graph["performances"],
        bounded_performances=graph["bounded_performances"],
        drift_analyses=graph["drift_analyses"], reports=graph["reports"],
        opportunities=graph["opportunities"], eligibility_contexts=graph["eligibility_contexts"],
        eligibility_results=graph["eligibility_results"], snapshots=graph["snapshots"],
        measurements=graph["measurements"], outcome_histories=graph["outcome_histories"])
    report = graph["reports"][0]
    return (
        "PR15 Comparative Performance Reporting: VALID",
        f"Covered Edge Claims: {len(report.claim_findings)}",
        f"Analysis boundary: {report.analysis_boundary.isoformat()}",
        f"Report ID: {report.comparative_performance_report_id}",
        "Scientific conclusion: deferred to Research Review",
        "Current Scientific Applicability: deferred to PR16",
        "Policy Recommendation: deferred to PR16",
    )


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/forecast_comparative_reporting_cases.json")
    print("\n".join(run(path)))


if __name__ == "__main__":
    main()
