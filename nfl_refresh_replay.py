"""Refresh-local reuse of pure parsing, never of evidence or report selection."""
from collections import OrderedDict
from copy import deepcopy
import sys

import nfl_forecast_import as source
from nfl_performance import Performance


def retained_size(value):
    """Conservative recursive Python size for the parser's built-in containers."""
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(retained_size(k) + retained_size(v) for k, v in value.items())
    elif isinstance(value, (tuple, list)):
        size += sum(retained_size(v) for v in value)
    return size


class RefreshPerformance(Performance):
    # Optional acceleration only: oversized entries are parsed normally.
    MAX_BYTES = 32 * 1024 * 1024
    MAX_ENTRIES = 2048

    def __init__(self, *args, **kwargs):
        self._parses = OrderedDict()
        self.retained_bytes = 0
        super().__init__(*args, **kwargs)

    def parsed(self, function, *args, **kwargs):
        # Callers still reread and hash blobs, validate receipts/event history,
        # and recompute selection at each current report boundary.
        parts = [('bytes', source.digest(a)) if isinstance(a, bytes) else ('value', a) for a in args]
        key = (function, source.encode(parts), source.encode(kwargs))
        if key in self._parses:
            value, size = self._parses.pop(key)
            self._parses[key] = value, size
            return deepcopy(value)
        value = function(*args, **kwargs)
        size = retained_size(key) + retained_size(value) + 256
        if size <= self.MAX_BYTES and self.MAX_ENTRIES > 0:
            while self._parses and (self.retained_bytes + size > self.MAX_BYTES
                                    or len(self._parses) >= self.MAX_ENTRIES):
                _, (_, removed) = self._parses.popitem(last=False)
                self.retained_bytes -= removed
            self._parses[key] = deepcopy(value), size
            self.retained_bytes += size
        return value
