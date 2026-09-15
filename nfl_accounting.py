"""Paired immutable activity/P&L imports, independent of quote and research capture."""
import csv
import io
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from datetime import timezone
import nfl_forecast_import as source
from retrieve_kalshi_nfl import aware

D = Decimal
PNL_FIELDS = {'subtrader_id', 'type', 'quantity_fp', 'market_ticker', 'side',
              'entry_price_dollars', 'exit_price_dollars', 'open_fees_dollars',
              'close_fees_dollars', 'realized_pnl_without_fees_dollars',
              'realized_pnl_with_fees_dollars', 'open_timestamp', 'close_timestamp'}


def rows(raw, required):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])) or not required.issubset(reader.fieldnames or []):
        raise ValueError('Incorrect CSV columns; select All Activity and realized P&L exports')
    result = list(reader)
    if any(None in r or None in r.values() for r in result):
        raise ValueError('Incomplete CSV row')
    return result


def number(value, signed=False):
    n = D(value)
    if not n.is_finite() or (not signed and n < 0):
        raise ValueError('Invalid accounting amount')
    return n


def second(value):
    return aware(value).astimezone(timezone.utc).replace(microsecond=0).isoformat()


def reconcile(activity_raw, pnl_raw, at):
    """Accept only complete, uniquely corroborated closed ticker histories.

    Partial or ambiguous histories remain review items, never inferred holdings.
    P&L lots may share an execution, but must partition its complete quantity.
    """
    from nfl_activity import REQUIRED
    activity = rows(activity_raw, REQUIRED)
    pnl = rows(pnl_raw, PNL_FIELDS)
    groups = defaultdict(list)
    for i, r in enumerate(pnl, 2):
        if r['market_ticker'].startswith('KXNFLGAME-'):
            groups[r['market_ticker']].append((i, r))
    accounts = {r['subtrader_id'] for _, rs in groups.items() for _, r in rs}
    if len(accounts) > 1:
        raise ValueError('Use a realized P&L export for one account')
    accepted, issues = [], []
    for ticker, records in sorted(groups.items()):
        try:
            trades = [r for r in activity if r['Market_Ticker'] == ticker and r['type'] == 'Trade']
            settlements = [r for r in activity if r['Market_Ticker'] == ticker and r['type'] == 'Settlement']
            if any(aware(r['Original_Date']) > aware(at) for r in trades + settlements):
                raise ValueError('Future activity timestamp')
            if len(settlements) > 1:
                raise ValueError('Duplicate or conflicting settlement records')
            if len({json.dumps(r, sort_keys=True) for r in trades}) != len(trades):
                raise ValueError('Duplicate activity trades')
            if len({json.dumps(r, sort_keys=True) for _, r in records}) != len(records):
                raise ValueError('Duplicate P&L lots without unique identifiers')
            used = defaultdict(lambda: dict(quantity=D(0), fees=D(0)))
            lots = []
            for rownum, r in records:
                if r['type'] != 'trade' or r['side'] not in ('yes', 'no') or not r['subtrader_id']:
                    raise ValueError('Unsupported P&L record')
                q, entry, exit_price, opening_fee, closing_fee = [number(r[k]) for k in
                    ('quantity_fp', 'entry_price_dollars', 'exit_price_dollars', 'open_fees_dollars', 'close_fees_dollars')]
                if q <= 0 or entry > 1 or exit_price > 1:
                    raise ValueError('Invalid quantity or contract price')
                opened, closed = second(r['open_timestamp']), second(r['close_timestamp'])
                if aware(opened) > aware(closed) or aware(closed) > aware(at):
                    raise ValueError('Invalid or future position timestamps')
                gross = q * (exit_price - entry)
                net = gross - opening_fee - closing_fee
                if gross != number(r['realized_pnl_without_fees_dollars'], True) or net != number(r['realized_pnl_with_fees_dollars'], True):
                    raise ValueError('Reported realized profit does not reconcile')
                def execution(timestamp, direction, price, fee, role):
                    matches = [(i, t) for i, t in enumerate(trades)
                               if second(t['Original_Date']) == timestamp and t['Direction'].lower() == direction]
                    if len(matches) != 1:
                        raise ValueError('Missing or ambiguous ' + role + ' execution')
                    index, trade = matches[0]
                    # This activity format quotes the YES leg for both directions.
                    yes_price = number(trade['Price_In_Cents']) / 100
                    expected = yes_price if r['side'] == 'yes' else 1 - yes_price
                    if price != expected:
                        raise ValueError('Activity and P&L execution prices differ')
                    used[index]['quantity'] += q
                    used[index]['fees'] += fee
                execution(opened, r['side'], entry, opening_fee, 'opening')
                matching_settlement = [s for s in settlements if second(s['Original_Date']) == closed]
                if matching_settlement:
                    s = matching_settlement[0]
                    if s['Result'].lower() not in ('yes', 'no'):
                        raise ValueError('Unsupported settlement result')
                    if exit_price != (D(1) if s['Result'].lower() == r['side'] else D(0)) or closing_fee != 0:
                        raise ValueError('Settlement price or fee does not reconcile')
                    kind = 'settlement'
                else:
                    execution(closed, 'no' if r['side'] == 'yes' else 'yes', exit_price, closing_fee, 'closing')
                    kind = 'sale'
                lots.append(dict(row=rownum, side=r['side'], quantity=str(q), entry=str(entry), exit=str(exit_price),
                                 opened=opened, closed=closed, kind=kind, cost=str(q*entry),
                                 opening_fee=str(opening_fee), closing_fee=str(closing_fee),
                                 proceeds=str(q*exit_price), profit=str(net)))
            if set(used) != set(range(len(trades))):
                raise ValueError('Trade history includes unpaired or still-open executions')
            for i, t in enumerate(trades):
                if used[i]['quantity'] != number(t['Amount_In_Dollars']):
                    raise ValueError('Partial or overlapping position quantities need review')
                # Recent Activity truncates fee precision; P&L retains allocation precision.
                fee = number(t['Fee_In_Dollars'])
                if not fee <= used[i]['fees'] < fee + D('.01'):
                    raise ValueError('Activity and P&L fees do not reconcile')
            settlement_proceeds = sum((D(l['proceeds']) for l in lots if l['kind'] == 'settlement'), D(0))
            if settlements and number(settlements[0]['Profit_In_Dollars']) != settlement_proceeds:
                raise ValueError('Settlement amount differs from reconciled positions')
            if settlements and any(aware(l['closed']) > aware(settlements[0]['Original_Date']) for l in lots):
                raise ValueError('Position closes after market settlement')
            accepted.append(dict(ticker=ticker, account=next(iter(accounts)), lots=lots))
        except (ValueError, ArithmeticError, KeyError) as exc:
            issues.append(dict(ticker=ticker, reason=str(exc)))
    activity_tickers = {r['Market_Ticker'] for r in activity if r['Market_Ticker'].startswith('KXNFLGAME-') and r['type'] in ('Trade', 'Settlement')}
    for ticker in sorted(activity_tickers - groups.keys()):
        issues.append(dict(ticker=ticker, reason='No closed position in selected P&L window; open balance unconfirmed'))
    return accepted, issues


def save(root, activity, pnl, at):
    accepted, issues = reconcile(activity, pnl, at)
    identity = source.digest(activity + b'\0' + pnl)
    folder = Path(root) / 'accounting' / identity
    receipt = dict(schema='nfl-accounting-v1', imported_at=at,
                   activity_sha256=source.digest(activity), pnl_sha256=source.digest(pnl))
    source.write_once(folder/'activity.csv', activity)
    source.write_once(folder/'pnl.csv', pnl)
    if not (folder/'complete.json').exists():
        source.write_once(folder/'complete.json', source.encode(receipt))
    return dict(positions=sum(len(r['lots']) for r in accepted), issues=issues)


def load(root, games, now):
    """Union closed lots across windows; conflicting observations never win by order."""
    variants = defaultdict(dict)
    capacities = defaultdict(lambda: D(0))
    issues, pending = [], {}
    for path in sorted((Path(root)/'accounting').glob('*/complete.json')):
        try:
            receipt = json.loads(path.read_text())
            if receipt['schema'] != 'nfl-accounting-v1':
                raise ValueError('Unknown accounting schema')
            if aware(receipt['imported_at']) > aware(now):
                continue
            a = (path.parent/'activity.csv').read_bytes()
            p = (path.parent/'pnl.csv').read_bytes()
            if source.digest(a) != receipt['activity_sha256'] or source.digest(p) != receipt['pnl_sha256']:
                raise ValueError('Accounting source fingerprint mismatch')
            records, warnings = reconcile(a, p, receipt['imported_at'])
            for warning in warnings:
                old = pending.get(warning['ticker'])
                if old is None or old['reason'].startswith('No closed position'):
                    pending[warning['ticker']] = warning
            for record in records:
                ticker = record['ticker']
                grouped = defaultdict(list)
                openings = defaultdict(lambda: D(0))
                for lot in record['lots']:
                    key = (record['account'], ticker, lot['side'], lot['opened'], lot['closed'])
                    grouped[key].append({k:v for k,v in lot.items() if k != 'row'})
                    openings[key[:4]] += D(lot['quantity'])
                for key, quantity in openings.items():
                    capacities[key] = max(capacities[key], quantity)
                for key, lots in grouped.items():
                    signature = json.dumps(sorted(lots, key=lambda l:json.dumps(l, sort_keys=True)), sort_keys=True)
                    variants[key][signature] = dict(ticker=ticker, lots=lots, source=str(path.parent),
                        imported_at=receipt['imported_at'], account=record['account'])
        except (OSError, ValueError, KeyError, ArithmeticError) as exc:
            # An unreadable snapshot could contradict an older financial result.
            return [], [dict(reason='Accounting history unavailable: '+str(exc), source=str(path))]
    conflicts = {key[1] for key, values in variants.items() if len(values) != 1}
    allocated = defaultdict(lambda: D(0))
    for key, values in variants.items():
        if len(values) == 1:
            allocated[key[:4]] += sum((D(l['quantity']) for l in next(iter(values.values()))['lots']), D(0))
    conflicts.update(key[1] for key, q in allocated.items() if q > capacities[key])
    # A discrepant observation must not silently expose an older accepted amount.
    conflicts.update(t for t,w in pending.items() if not w['reason'].startswith('No closed position'))
    if len({key[0] for key in variants}) > 1:
        return [], [dict(reason='Accounting history contains multiple accounts')]
    result = []
    for key, values in sorted(variants.items()):
        if key[1] in conflicts:
            continue
        record = next(iter(values.values()))
        # Exact ticker/team/date identity; never relax quote matching.
        matches = []
        for g in games:
            if not g.get('kickoff'):
                continue
            from zoneinfo import ZoneInfo
            date = aware(g['kickoff']).astimezone(ZoneInfo('America/New_York'))
            stamp = date.strftime('%y%b%d').upper()
            for yes in (g['home'], g['away']):
                if record['ticker'] == f"KXNFLGAME-{stamp}{g['away']}{g['home']}-{yes}":
                    matches.append((g, yes))
        if len(matches) != 1:
            issues.append(dict(ticker=record['ticker'], reason='Accounting has no unique game match'))
            continue
        g, yes = matches[0]
        for lot in record['lots']:
            result.append(dict(**lot, ticker=record['ticker'], game_id=g['game_id'], yes_team=yes,
                               team=yes if lot['side']=='yes' else next(t for t in (g['home'],g['away']) if t!=yes),
                               source=record['source'], imported_at=record['imported_at']))
    for ticker in sorted(conflicts):
        issues.append(dict(ticker=ticker, reason='Conflicting overlapping P&L lots; accounting needs review'))
    known = {r['ticker'] for r in result}
    issues.extend(w for ticker,w in pending.items() if ticker not in known and ticker not in conflicts)
    return result, issues


def latest_activity(root, now):
    """Return the most recent verified paired activity, for unpaired trade visibility."""
    candidates = []
    for path in (Path(root)/'accounting').glob('*/complete.json'):
        receipt = json.loads(path.read_text())
        if aware(receipt['imported_at']) <= aware(now):
            raw = (path.parent/'activity.csv').read_bytes()
            if source.digest(raw) != receipt['activity_sha256']:
                raise ValueError('Accounting activity fingerprint mismatch')
            candidates.append((receipt['imported_at'], receipt['activity_sha256'], raw))
    if not candidates:
        return None
    at = max(aware(c[0]) for c in candidates)
    newest = [c for c in candidates if aware(c[0]) == at]
    if len({c[1] for c in newest}) != 1:
        raise ValueError('Conflicting activity imports at the same timestamp')
    return newest[0][0], newest[0][2]
