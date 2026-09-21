"""Disposable, content-checked NFL reader snapshot. Never an evidence store."""
from copy import deepcopy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock

import nfl_forecast_import as base
from nfl_performance import Performance, RULE_FILE, PARTIAL_RULE_FILE, instant
from nfl_performance_sources import LEGACY_OUTCOME_RULE
from nfl_forecast_time import RULE_FILE as FILE_TIME_RULE_FILE


class Replay(Performance):
    """Memoize only inside a private immutable snapshot, including legacy replay."""
    def __init__(self, root):
        self.memo = {}
        super().__init__(root)

    def remembered(self, key, fn):
        if key not in self.memo:
            self.memo[key] = fn()
        return deepcopy(self.memo[key])

    def events(self):
        return self.remembered('events', lambda: super(Replay, self).events())

    def validate_starting_cohort(self):
        return self.remembered('cohort', lambda: super(Replay, self).validate_starting_cohort())

    def decode(self, event, **kwargs):
        kwargs.setdefault('outcome_rule', LEGACY_OUTCOME_RULE)
        key = ('decode', base.encode(event), base.encode(kwargs))
        return self.remembered(key, lambda: super(Replay, self).decode(event, **kwargs))

    def parsed(self, function, *args, **kwargs):
        parts=[hashlib.sha256(a).hexdigest() if isinstance(a,bytes) else a for a in args]
        key=('parsed',function.__module__,function.__name__,base.encode(parts),base.encode(kwargs))
        return self.remembered(key, lambda:function(*args,**kwargs))


class ReaderCache:
    # One snapshot per reader, not an unbounded collection of historical versions.
    MAX_BYTES = 512 * 1024 * 1024

    def __init__(self, root):
        self.root = Path(root)
        self.lock = RLock()
        self.identity = None
        self.temporary = None
        self.engine = None
        self.reports = {}

    def scan(self, retain=False):
        for p in (self.root,):
            if p.is_symlink():
                raise ValueError('Aliased performance evidence is not allowed')
        digest = hashlib.sha256()
        files = {}
        total = 0
        for p in sorted(self.root.rglob('*')):
            if p.is_symlink():
                raise ValueError('Aliased performance evidence is not allowed')
            if not p.is_file():
                continue
            name = str(p.relative_to(self.root))
            # The advisory lock has no scientific content.
            if name == '.lock':
                continue
            total += p.stat().st_size
            if total > self.MAX_BYTES:
                raise ValueError('Saved reader snapshot exceeds 512 MiB; inspect capacity')
            raw = p.read_bytes()
            digest.update(base.encode([name, hashlib.sha256(raw).hexdigest()]))
            if retain:
                files[name] = raw
        # Rule bytes are outside the archive and also govern replay acceptance.
        for p in (RULE_FILE, PARTIAL_RULE_FILE, FILE_TIME_RULE_FILE):
            digest.update(p.read_bytes())
        return digest.hexdigest(), files

    def prepare(self):
        identity, _ = self.scan()
        if identity != self.identity:
            self.clear()
            captured, files = self.scan(retain=True)
            if identity != captured:
                raise ValueError('Saved NFL data changed while reading; reopen the page')
            temporary = TemporaryDirectory(prefix='pops-nfl-reader-')
            try:
                root = Path(temporary.name)
                for name, raw in files.items():
                    target = root/name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                self.temporary = temporary
                self.identity = identity
                self.engine = Replay(root) if 'activation.json' in files else None
            except Exception:
                temporary.cleanup()
                self.clear()
                raise
        return self.engine

    def verify(self):
        if self.scan()[0] != self.identity:
            self.clear()
            raise ValueError('Saved NFL data changed while reading; reopen the page')

    def clear(self):
        self.identity = None
        self.engine = None
        self.reports = {}
        if self.temporary:
            self.temporary.cleanup()
            self.temporary = None

    def __del__(self):
        if self.temporary:
            self.temporary.cleanup()

    def report(self, report):
        identity = report['report_id']
        if self.engine is None:
            raise ValueError('Weekly performance is not initialized')
        if instant(report['boundary']) > instant(self.engine.clock()):
            raise ValueError('Analysis boundary is in the future')
        if identity not in self.reports:
            self.reports[identity] = self.engine.replay_report(self.engine.root/'reports'/(identity+'.json'))
        return deepcopy(self.reports[identity])
