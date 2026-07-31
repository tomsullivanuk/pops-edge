"""Explicit, read-only MLB Stats API smoke test. Never imported by workflows."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Sequence

from mlb_stats_api import (
    AdapterOutcome,
    MLBStatsAPIAdapter,
    MLBStatsAPIClient,
    MLBStatsAPIError,
)


def run(argv: Sequence[str] | None = None, *, client=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("date", type=date.fromisoformat, help="schedule date (YYYY-MM-DD)")
    parser.add_argument("--game-pk", type=int, help="optional single MLB gamePk")
    args = parser.parse_args(argv)
    try:
        response = (client or MLBStatsAPIClient()).fetch_schedule(
            args.date, game_pk=args.game_pk
        )
        result = MLBStatsAPIAdapter().parse_response(response)
        for item in result.games:
            game_pk = item.game.game_pk if item.game is not None else "unavailable"
            issue_codes = ",".join(issue.code.value for issue in item.issues) or "none"
            print(
                f"record={item.source_record_id} gamePk={game_pk} "
                f"outcome={item.outcome.value} issues={issue_codes}"
            )
        for issue in result.issues:
            print(f"source_issue={issue.code.value} severity={issue.severity.value}")
        unsafe = bool(result.issues) or any(
            item.outcome is AdapterOutcome.REJECTED for item in result.games
        )
        return 1 if unsafe else 0
    except (MLBStatsAPIError, ValueError, TypeError) as error:
        print(f"smoke_failed={error}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
