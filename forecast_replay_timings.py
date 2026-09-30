"""Bounded operational timings, never scientific identity or freshness authority."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import time

_current = ContextVar('replay_timings', default=None)
STAGES = frozenset({'authority', 'date-selection', 'provider', 'derivation',
                    'publication', 'lock-wait', 'lock-held', 'source-check'})


@contextmanager
def timed(stage):
    values = _current.get()
    if values is None:
        yield
        return
    if stage not in STAGES:
        raise ValueError('unknown replay timing stage')
    started = time.monotonic()
    try:
        yield
    finally:
        row = values.setdefault(stage, {'seconds': 0.0, 'count': 0})
        row['seconds'] += time.monotonic() - started
        row['count'] += 1


def begin():
    return _current.set({})


def finish(token, root, command, started_at, completed_at, disposition):
    """A separate optional diagnostic receipt keeps old heartbeat readers valid.

    Nested durations overlap. In particular derivation may include publication,
    and publication includes its lock stages. They must not be summed as CPU time.
    Logging failure never turns a committed acquisition into an apparent failure.
    """
    stages = _current.get()
    _current.reset(token)
    value = {'schema_version': '1', 'command': command,
             'started_at': started_at.isoformat(), 'completed_at': completed_at.isoformat(),
             'disposition': disposition, 'stages': stages}
    body = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    path = root/'replay-timings'/f'{hashlib.sha256(body).hexdigest()}.json'
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(body)
    except FileExistsError:
        pass
    except OSError:
        import sys
        print('replay-timing-receipt-unavailable', file=sys.stderr)
