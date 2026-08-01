#!/usr/bin/env python3
"""Inspect a local DRatings HTML snapshot; never access the network."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dratings_adapter import DRatingsAdapter, DRatingsSnapshotError, load_mlb_reconciliation_candidates


DEFAULT_CAPTURED_AT = "2026-07-31T17:53:55-05:00"


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", help="path to a manually captured DRatings HTML snapshot")
    parser.add_argument("--captured-at", default=DEFAULT_CAPTURED_AT, help="Pops' Edge capture timestamp (ISO-8601 with timezone)")
    parser.add_argument("--mlb-fixture", help="optional local MLB Stats API schedule fixture")
    parser.add_argument("--output", help="optional path for deterministic result JSON")
    args = parser.parse_args(argv)
    try:
        captured_at = datetime.fromisoformat(args.captured_at.replace("Z", "+00:00"))
        snapshot = DRatingsAdapter().parse_snapshot(args.snapshot, captured_at=captured_at)
        results = ()
        if args.mlb_fixture:
            candidates = load_mlb_reconciliation_candidates(args.mlb_fixture, collected_at=captured_at)
            results = DRatingsAdapter().transform(snapshot, canonical_events=candidates)
    except (OSError, ValueError, json.JSONDecodeError, DRatingsSnapshotError) as error:
        print(f"snapshot inspection failed: {error}", file=sys.stderr)
        return 1

    counts = {name: 0 for name in ("complete", "partial", "ambiguous", "rejected")}
    for result in results:
        counts[result.outcome.value] += 1
    print(f"parsed={len(snapshot.rows)} matched={counts['complete'] + counts['partial']} partial={counts['partial']} ambiguous={counts['ambiguous']} rejected={counts['rejected']}")
    for result in results:
        for issue in result.issues:
            print(f"{result.source_locator}: {issue.code}: {issue.detail}")
    if args.output:
        payload = [result.to_dict() for result in results] if results else {
            "raw_evidence": snapshot.raw.to_dict(),
            "row_count": len(snapshot.rows),
        }
        Path(args.output).write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
