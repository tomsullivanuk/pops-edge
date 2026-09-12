"""Explicit local NFL weekly capture/scoring commands; never run on import."""
import argparse
import json
from pathlib import Path
import nfl_performance as performance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True, help='Dedicated performance evidence directory')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('initialize', help='Commission only with separate owner authorization')
    init.add_argument('--authorization', required=True)
    init.add_argument('--partial-week1', action='store_true', help='Pin the owner-approved 14-game 2026 Week 1 starting cohort from a fresh official schedule')
    capture = sub.add_parser('capture', help='Import a new weekly workbook and capture associated prices')
    capture.add_argument('workbook', type=Path)
    capture.add_argument('--retry-missing', action='store_true')
    outcome = sub.add_parser('outcomes', help='Capture official weekly schedule/result evidence')
    report = sub.add_parser('report', help='Replay and save a report; no network')
    report.add_argument('--boundary', required=True)
    for command in (capture, outcome, report):
        command.add_argument('--season', type=int, required=True)
        command.add_argument('--week', type=int, required=True)
    replay = sub.add_parser('replay', help='Verify a saved report; no network')
    replay.add_argument('report', type=Path)
    args = parser.parse_args()
    if args.command == 'initialize':
        if args.partial_week1:
            from tempfile import TemporaryDirectory
            with TemporaryDirectory() as tmp:
                folder, _ = performance.schedule.capture(tmp, 2026, 1)
                obj = performance.Performance.initialize(args.store, args.authorization, partial_week1_schedule=folder)
        else:
            obj = performance.Performance.initialize(args.store, args.authorization)
        result = obj.activation
    else:
        obj = performance.Performance(args.store)
        if args.command == 'capture':
            result = obj.refresh(args.workbook.read_bytes(), args.workbook.name, args.season, args.week, retry=args.retry_missing)
        elif args.command == 'outcomes':
            result = obj.observe_results(args.season, args.week)
        elif args.command == 'report':
            result = obj.save_report(args.season, args.week, args.boundary)
        else:
            result = obj.replay_report(args.report)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
