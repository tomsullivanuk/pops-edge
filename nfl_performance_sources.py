"""Versioned NFL payout-evaluation adapters; no network or storage side effects."""
import json
import re
from decimal import Decimal
import nfl_schedule as schedule
import nfl_comparison_board as board
import retrieve_kalshi_nfl as kalshi

D = Decimal


def weekly_games(raw, season, week):
    """Resolve the same explicit query as legacy schedule parsing, retaining summaries."""
    schedule.parse(raw, season, week)  # Preserve identity/scope validation.
    chunks = []
    for match in re.finditer(r'self\.__next_f\.push\((\[.*?\])\)</script>', raw.decode('utf-8')):
        value = json.loads(match[1])
        if len(value) == 2 and value[0] == 1 and isinstance(value[1], str):
            chunks.append(value[1])
    found = []

    def walk(value):
        if isinstance(value, dict):
            key = value.get('queryKey')
            if isinstance(key, list) and len(key) == 2 and key[0] == 'useFetchFootballWeeklyGameDetails':
                arg = key[1]
                if str(arg.get('season')) == str(season) and str(arg.get('week')) == str(week) and arg.get('seasonType') == 'REG':
                    found.append(value['state']['data'])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for line in ''.join(chunks).splitlines():
        try:
            value = json.loads(line.split(':', 1)[1])
        except (ValueError, IndexError):
            continue
        walk(value)
    if len(found) != 1:
        raise ValueError('Ambiguous weekly summary query')
    return found[0]


def outcomes(raw, season, week):
    result = {}
    for game in weekly_games(raw, season, week):
        row = dict(state='awaiting-outcome', payout=None, issues=[], start=None)
        result[game['id']] = row
        try:
            summary = game.get('summary')
            if not summary:
                continue
            if summary['gameId'] != game['id']:
                raise ValueError('Summary game identity mismatch')
            for side in ('home', 'away'):
                if summary[side + 'Team']['teamId'] != game[side + 'Team']['id']:
                    raise ValueError('Summary team identity mismatch')
            if summary.get('startTime'):
                kalshi.aware(summary['startTime'])
                row['start'] = summary['startTime']
            phase, quarter = summary.get('phase'), summary.get('quarter')
            if phase != 'FINAL' or quarter != 'END_OF_GAME':
                if phase == 'FINAL' or quarter == 'END_OF_GAME' or game['status'] in ('FINAL', 'FINAL_OVERTIME', 'COMPLETED'):
                    raise ValueError('Conflicting final markers')
                continue
            if game['status'] not in ('SCHEDULED', 'FINAL', 'FINAL_OVERTIME', 'COMPLETED'):
                raise ValueError('Unsupported outer result status')
            scores = []
            for side in ('home', 'away'):
                score = summary[side + 'Team']['score']
                total = score['total']
                if type(total) is not int or total < 0:
                    raise ValueError('Invalid final score')
                periods = [score[k] for k in ('q1', 'q2', 'q3', 'q4', 'ot') if k in score]
                if any(type(v) is not int or v < 0 for v in periods):
                    raise ValueError('Invalid period score')
                if all(k in score for k in ('q1', 'q2', 'q3', 'q4', 'ot')) and sum(periods) != total:
                    raise ValueError('Final score does not reconcile')
                scores.append(total)
            row.update(state='final', home_score=scores[0], away_score=scores[1],
                       payout='1' if scores[0] > scores[1] else '0' if scores[0] < scores[1] else '0.5')
            if game['status'] == 'SCHEDULED':
                row['issues'].append('Outer SCHEDULED; validated summary FINAL')
        except (ValueError, KeyError, TypeError) as exc:
            row.update(state='unresolved-outcome', payout=None)
            row['issues'].append(str(exc))
    return result


def midpoint(game, summary, markets):
    """Match only the designated home YES market; price/cost never selects a route."""
    if summary.get('state') not in ('complete', 'partial') or not summary.get('catalog_complete'):
        raise ValueError('Incomplete market catalog/capture')
    if not game['kickoff']:
        raise ValueError('Unknown kickoff')
    day = kalshi.aware(game['kickoff']).astimezone(board.NY).date().isoformat()
    candidates = []
    for market in markets:
        try:
            teams, yes_team, market_day = board.strict_market(market)
        except (ValueError, KeyError, TypeError):
            continue
        if teams == {game['home'], game['away']} and yes_team == game['home'] and market_day == day:
            candidates.append(market)
    if len(candidates) != 1:
        raise ValueError('Missing or ambiguous home YES market')
    market = candidates[0]
    if market.get('status') not in ('open', 'active'):
        raise ValueError('Market is not open')
    rows = [r for r in summary['rows'] if r['ticker'] == market['ticker']]
    if len(rows) != 1 or rows[0]['state'] != 'captured':
        raise ValueError('Missing valid two-sided book')
    row = rows[0]
    ask = kalshi.number(row['offers']['yes']['offer_price'], True)
    bid = 1 - kalshi.number(row['offers']['no']['offer_price'], True)
    if bid > ask:
        raise ValueError('Crossed book')
    return dict(ticker=market['ticker'], bid=str(bid), ask=str(ask), value=str((bid + ask) / 2),
                started_at=row['book_started_at'], received_at=row['book_received_at'],
                metadata_received_at=row['metadata_received_at'])


def error_scores(elway, kalshi_value, payout):
    e, k, y = (kalshi.number(str(v), True) for v in (elway, kalshi_value, payout))
    if y not in (D(0), D('.5'), D(1)):
        raise ValueError('Unsupported payout')
    a, b = (e-y)**2, (k-y)**2
    return dict(elway_error=str(a), kalshi_error=str(b), difference=str(b-a))
