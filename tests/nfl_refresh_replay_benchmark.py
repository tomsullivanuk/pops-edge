"""Offline report-work benchmark on a disposable copy; never calls providers.

Run with --store PATH to an existing NFL performance store. Only reads PATH.
The same six report calculations run with and without refresh-local parse reuse.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import socket
import tempfile
import time

from nfl_performance import Performance
from nfl_refresh_replay import RefreshPerformance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--season', type=int, default=2026)
    args = parser.parse_args()
    def denied(*a, **kw):
        raise RuntimeError('Network disabled for offline benchmark')
    socket.socket.connect = denied
    socket.create_connection = denied
    with tempfile.TemporaryDirectory(prefix='pops-refresh-benchmark-') as tmp:
        root = Path(tmp)/'performance'
        shutil.copytree(args.store, root)
        boundary = datetime.now(timezone.utc).isoformat()
        results = []
        for cls in (Performance, RefreshPerformance):
            engine = cls(root, clock=lambda: boundary)
            start = time.monotonic()
            reports = [engine.report(args.season, week, boundary) for week in (1, 2, 3, 1, 2, 3)]
            elapsed = time.monotonic()-start
            print(json.dumps(dict(engine=cls.__name__, seconds=elapsed,
                retained_bytes=getattr(engine, 'retained_bytes', 0),
                entries=len(getattr(engine, '_parses', {})))), flush=True)
            results.append(reports)
        if results[0] != results[1]:
            raise AssertionError('Report semantics changed')
        print('All six report outputs identical; zero provider calls.', flush=True)


if __name__ == '__main__':
    main()
