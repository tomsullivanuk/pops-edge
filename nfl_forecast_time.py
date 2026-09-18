"""Bound file-birth observations; never manufacture publisher timestamps."""
from datetime import datetime, timezone
import os
from pathlib import Path
import nfl_forecast_import as base

RULE = 'nfl-file-creation-proxy-v1'
RULE_FILE = Path(__file__).parent / 'docs/NFL_FILE_CREATION_TIME_AMENDMENT.md'
LABEL = 'File creation time — publication-time proxy'


def evidence(raw, created_at, observed_at):
    value = dict(rule=RULE, rule_digest=base.digest(RULE_FILE.read_bytes()),
                 source_sha256=base.digest(raw), created_at=created_at, observed_at=observed_at)
    validate(value, raw, observed_at)
    return value


def validate(value, raw, boundary):
    if not isinstance(value, dict) or set(value) != {'rule', 'rule_digest', 'source_sha256', 'created_at', 'observed_at'}:
        raise ValueError('Invalid file creation evidence')
    if value['rule'] != RULE or value['rule_digest'] != base.digest(RULE_FILE.read_bytes()) or value['source_sha256'] != base.digest(raw):
        raise ValueError('File creation evidence identity differs')
    created, observed, end = (base.timestamp(t) for t in (value['created_at'], value['observed_at'], boundary))
    if not created <= observed <= end:
        raise ValueError('File creation evidence chronology differs')
    return created.astimezone(timezone.utc).isoformat()


def read_file(path):
    """Read bytes and birth metadata from one open file; detect concurrent edits."""
    with Path(path).open('rb') as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read()
        after = os.fstat(stream.fileno())
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('Workbook changed while being read; retry after saving')
    birth = getattr(before, 'st_birthtime', None)
    from nfl_excel_import import parse
    try:
        parse(raw)
    except ValueError:
        pass
    else:
        return raw, None
    # Published workbooks remain usable on filesystems without birth time.
    timing = None if birth is None else evidence(raw, datetime.fromtimestamp(birth, timezone.utc).isoformat(), base.now())
    return raw, timing
