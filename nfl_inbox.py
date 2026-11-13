"""Automatic input choice is operational convenience, never publication evidence."""
import csv
import io
import sys
import stat
from nfl_activity import REQUIRED
from nfl_accounting import PNL_FIELDS

LABELS = {'forecast': 'ELWAY workbook', 'activity': 'Kalshi All Activity', 'pnl': 'Kalshi realized P&L'}


def is_dataless(info):
    """Darwin SF_DATALESS means content is not local; compressed is not dataless."""
    return sys.platform == 'darwin' and bool(getattr(info, 'st_flags', 0) & getattr(stat, 'SF_DATALESS', 0x40000000))


def filename_kind(name):
    lower = name.lower()
    return ('forecast' if lower.endswith('.xlsx') else
            'pnl' if 'kalshi' in lower and ('realized' in lower or 'pnl' in lower) else
            'activity' if 'kalshi' in lower and ('activity' in lower or 'all-activity' in lower) else None)


def classify(name, raw):
    """CSV contents determine type; familiar names retain visible invalid inputs."""
    lower = name.lower()
    if lower.endswith('.xlsx'):
        return 'forecast', None
    hint = filename_kind(name)
    try:
        fields = next(csv.reader(io.StringIO(raw.decode('utf-8-sig'))), [])
        kinds = [kind for kind, required in [('activity', REQUIRED), ('pnl', PNL_FIELDS)] if required.issubset(fields)]
        if len(kinds) != 1:
            return hint, 'CSV columns do not identify one supported Kalshi export.'
        kind = kinds[0]
        if len(fields) != len(set(fields)):
            return kind, 'CSV has duplicate column names.'
        if hint and hint != kind:
            return hint, 'CSV contents conflict with its export filename.'
        return kind, None
    except (UnicodeError, csv.Error):
        return hint, 'CSV cannot be read. Download the export again.'


def newest(files):
    selected = {}
    for kind, label in LABELS.items():
        candidates = [f for f in files if f.get('input_kind') == kind or kind in f.get('possible_kinds', ())]
        if not candidates:
            selected[kind] = dict(state='missing', message=f'No {label} found.')
            continue
        modified = max(f['modified_ns'] for f in candidates)
        latest = [f for f in candidates if f['modified_ns'] == modified]
        if len(latest) != 1:
            selected[kind] = dict(state='ambiguous', message=f'Multiple {label} files have the same newest saved time. Keep one latest copy in this folder.', names=[f['name'] for f in latest])
            continue
        item = latest[0]
        selected[kind] = dict(item, state='not_downloaded' if item.get('not_downloaded') else 'invalid' if item.get('input_error') else 'ready', message=item.get('input_error') or '')
    return selected
