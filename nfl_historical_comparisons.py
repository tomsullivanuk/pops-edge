"""Read-only historical comparisons for the season display, never quote eligibility."""
from copy import deepcopy
import json
from pathlib import Path

import nfl_comparison_board as board
from nfl_board_view import sheet_rows


def identity(game, outcome):
    return (game['game_id'], game.get('season'), game['week'], game['home'], game['away'], game.get('neutral'),
            game.get('kickoff'), outcome['team'])


def attach_history(root, games, selected, now):
    """Fill display-only history from verified bundles; leave active inputs untouched.

    Selected snapshots also supply history when merely aging on reload. Other
    bundles are inspected only for the requested identities and replayed before
    use. A bad historical bundle is disclosed and never supplies values.
    """
    needed = {identity(g, o): o for g in games for o in g['outcomes']
              if o.get('team') and not any(r['usable'] for r in o['routes'])}
    if not needed:
        return []
    issues = []
    candidates = [(Path(p), snap, True) for p, snap in selected]
    known = {p.resolve() for p, _, _ in candidates}
    for path in sorted((Path(root) / 'boards').glob('*/comparison.json')):
        if path.parent.resolve() in known or not (path.parent / 'complete.json').is_file():
            continue
        try:
            snap = json.loads(path.read_text())
            # Only discovery uses unvalidated metadata; replay admits the source.
            if any(identity(g, o) in needed for g in snap['games'] for o in g['outcomes']):
                candidates.append((path.parent, snap, False))
        except (OSError, ValueError, KeyError, TypeError):
            issues.append(dict(history='Saved comparison could not be inspected', bundle=path.parent.name))

    def chronology(item):
        try:
            return board.kalshi.aware(item[1]['generated_at'])
        except (ValueError, KeyError, TypeError):
            return board.kalshi.aware('1970-01-01T00:00:00Z')

    # Same-generation activity overlays do not change comparison values. Compare
    # tied values below so directory order cannot choose conflicting economics.
    found = {}
    for folder, snap, verified in sorted(candidates, key=chronology, reverse=True):
        try:
            at = board.kalshi.aware(snap['generated_at'])
            if at > board.kalshi.aware(now):
                continue
            relevant = [g for g in snap['games'] if any(
                identity(g, o) in needed and (identity(g, o) not in found or at >= found[identity(g, o)][0])
                and any(r.get('usable') for r in o['routes']) for o in g['outcomes'])]
            if not relevant:
                continue
            if not verified:
                snap = board.replay(folder, check_html=False)
            # Later activity overlays cannot invalidate an originally eligible
            # pregame quote for historical display. They still govern the current
            # season view's completion/accounting independently.
            for row in sheet_rows({**snap, 'activity': {}}):
                g, o, route = row['game'], row['outcome'], row['route']
                key = identity(g, o)
                if key not in needed or route is None:
                    continue
                if key in found and at < found[key][0]:
                    continue
                value = dict(outcome=deepcopy(o), route=deepcopy(route),
                             forecast_updated_at=snap['forecast_updated_at'],
                             forecast_verified_at=snap['forecast_verified_at'],
                             fee_model=snap['fee_model'], generated_at=snap['generated_at'])
                if snap.get('forecast_time_basis'):value['forecast_time_basis']=snap['forecast_time_basis']
                if key in found and found[key][1] != value:
                    found[key] = (at, None, None)
                else:
                    found[key] = (at, value, folder.name)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(dict(history='Saved comparison failed validation', bundle=folder.name, reason=str(exc)))
    for key, (_, value, bundle) in found.items():
        if value is None:
            issues.append(dict(history='Conflicting saved comparisons at the same time', game=key[0], team=key[-1]))
        else:
            needed[key]['historical'] = dict(value, source_bundle=bundle)
    return issues
