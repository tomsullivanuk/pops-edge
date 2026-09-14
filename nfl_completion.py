"""Read-only official completion display v1; independent of research replay."""
import json
from pathlib import Path
import nfl_schedule as schedule
from nfl_performance_sources import weekly_games

VERSION = 'nfl-completion-display-v1'
FINAL_PHASES = ('FINAL', 'FINAL_OVERTIME')


def summaries(raw, season, week):
    """Validate sporting finality, never infer it from an account settlement."""
    rows = {}
    for game in weekly_games(raw, season, week):
        result = dict(state='awaiting', issues=[], phase=None)
        rows[game['id']] = result
        try:
            summary = game.get('summary')
            if not summary:
                if game['status'] != 'SCHEDULED':
                    raise ValueError('Schedule status without a supported summary')
                continue
            if summary['gameId'] != game['id']:
                raise ValueError('Summary game identity mismatch')
            for side in ('home', 'away'):
                if summary[side+'Team']['teamId'] != game[side+'Team']['id']:
                    raise ValueError('Summary team identity mismatch')
            phase, quarter = summary.get('phase'), summary.get('quarter')
            result['phase'] = phase
            if phase not in FINAL_PHASES or quarter != 'END_OF_GAME':
                if phase in FINAL_PHASES or quarter == 'END_OF_GAME' or game['status'] in (*FINAL_PHASES, 'COMPLETED'):
                    raise ValueError('Conflicting final markers')
                if phase not in (None, 'PREGAME', 'IN_PROGRESS'):
                    raise ValueError('Unsupported game phase')
                continue
            if game['status'] not in ('SCHEDULED', *FINAL_PHASES, 'COMPLETED'):
                raise ValueError('Unsupported outer result status')
            scores = {}
            for side in ('home', 'away'):
                score = summary[side+'Team']['score']
                total = score['total']
                if type(total) is not int or total < 0:
                    raise ValueError('Invalid final score')
                periods = [score[k] for k in ('q1', 'q2', 'q3', 'q4', 'ot') if k in score]
                if any(type(v) is not int or v < 0 for v in periods):
                    raise ValueError('Invalid period score')
                if sum(periods) > total or (all(k in score for k in ('q1', 'q2', 'q3', 'q4', 'ot')) and sum(periods) != total):
                    raise ValueError('Final score does not reconcile')
                scores[side+'_score'] = total
            result.update(state='final', overtime=phase == 'FINAL_OVERTIME', **scores)
            if game['status'] == 'SCHEDULED':
                result['issues'].append('Outer SCHEDULED; validated summary '+phase)
        except (ValueError, KeyError, TypeError) as exc:
            result.update(state='unresolved', issues=[str(exc)])
    return rows


def latest(root, season, now):
    """Select newest observed weekly receipt, including failures; never backfill."""
    candidates = {}
    diagnostics = []
    for path in sorted(Path(root).glob('schedules/*/receipt.json')):
        try:
            receipt = json.loads(path.read_text())
            if receipt['season'] != season:
                continue
            at = schedule.aware(receipt['completed_at'])
            if at > schedule.aware(now):
                continue
            week = receipt['week']
            schedule.scope(season, week)
            candidates.setdefault(week, []).append((at, path))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            diagnostics.append(dict(completion='Unreadable official receipt: '+str(path)+': '+str(exc)))
    selected = {}
    for week, options in candidates.items():
        newest = max(at for at, _ in options)
        paths = [p for at, p in options if at == newest]
        decoded = []
        try:
            for path in paths:
                receipt = schedule.replay(path.parent)
                decoded.append(dict(games=receipt['rows'], outcomes=summaries((path.parent/'source.html').read_bytes(), season, week),
                                    observed_at=receipt['completed_at'], url=receipt['url'], source=str(path.parent),
                                    raw_sha256=receipt['raw_sha256'], schema=VERSION))
            if any((x['games'], x['outcomes']) != (decoded[0]['games'], decoded[0]['outcomes']) for x in decoded[1:]):
                raise ValueError('Conflicting official observations at the same time')
            selected[week] = decoded[0]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            selected[week] = dict(error=str(exc), observed_at=newest.isoformat(), source=str(paths[0].parent))
    if diagnostics:
        # An unreadable receipt cannot safely be placed before another observation.
        for week in candidates:
            selected[week] = dict(error='Official receipt could not be verified; see calculation notes')
    return selected, diagnostics


def apply(games, observations, now):
    for game in games:
        game['completed'] = False
        observation = observations.get(game['week'])
        if not observation:
            continue
        info = {k: v for k, v in observation.items() if k not in ('games', 'outcomes')}
        game['official_result'] = info
        if observation.get('error'):
            info.update(state='unresolved', issues=[observation['error']])
        else:
            matches = [r for r in observation['games'] if (r['home'], r['away']) == (game['home'], game['away'])]
            official = matches[0] if len(matches) == 1 else None
            preview = game['game_id'].startswith('forecast-')
            if official is None or official['neutral'] != game['neutral'] or (not preview and official['game_id'] != game['game_id']):
                info.update(state='unresolved', issues=['Official game identity mismatch or game absent from latest schedule'])
            else:
                if preview:
                    game.update(official)
                info.update(observation['outcomes'][official['game_id']])
                info['outer_status'] = official['status']
        if info['state'] == 'final':
            game['completed'] = True
            game['display_status'] = 'Final'
        elif info['state'] == 'unresolved':
            game['display_status'] = 'Result needs review'
        elif info.get('phase') == 'IN_PROGRESS' or (game['kickoff'] and schedule.aware(game['kickoff']) <= schedule.aware(now)):
            game['display_status'] = 'Started'
        else:
            game['display_status'] = 'Scheduled' if game['kickoff'] else 'Date/time TBD'
        if game['completed'] or info['state'] == 'unresolved' or game['display_status'] == 'Started':
            for outcome in game['outcomes']:
                for route in outcome['routes']:
                    route['usable'] = False
