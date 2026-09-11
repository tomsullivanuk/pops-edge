"""Explicitly initialized local weekly capture/scoring service. Not activated by import.

The existing UI does not call this service yet. All source acquisition uses the
existing bounded NFL transports. Reports replay saved evidence without network.
"""
from contextlib import contextmanager
from decimal import Decimal
from datetime import timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import fcntl
import json
import nfl_forecast_import as base
import nfl_excel_import as excel
import nfl_schedule as schedule
import nfl_comparison_board as board
import retrieve_kalshi_nfl as kalshi
import nfl_performance_sources as sources

PROTOCOL = 'nfl-weekly-contract-value-v1'
SCHEMA = 'nfl-weekly-measurement-v1'
RULE_FILE = Path(__file__).parent / 'docs/NFL_MODEL_PERFORMANCE_PROTOCOL.md'
D = Decimal


def instant(value):
    return kalshi.aware(value)


def canonical_time(value):
    return instant(value).astimezone(timezone.utc).isoformat()


class Performance:
    def __init__(self, root, clock=kalshi.utc):
        self.root = Path(root)
        self.clock = clock
        if not (self.root / 'activation.json').exists():
            raise ValueError('Weekly performance is not initialized')
        self.activation = json.loads((self.root / 'activation.json').read_text())
        if self.activation['protocol'] != PROTOCOL or self.activation['protocol_digest'] != base.digest(RULE_FILE.read_bytes()):
            raise ValueError('Protocol identity differs from initialized store')
        if self.activation['schema'] != SCHEMA:
            raise ValueError('Unsupported performance schema')
        instant(self.activation['effective_at'])

    @classmethod
    def initialize(cls, root, authorization, clock=kalshi.utc):
        """Called only as an explicit, separately authorized commissioning action."""
        if not isinstance(authorization, str) or not authorization.strip():
            raise ValueError('Explicit commissioning authorization reference required')
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        if list(root.iterdir()):
            raise ValueError('Initialize an empty store; never replace activation')
        base.write_once(root / 'activation.json', base.encode(dict(schema=SCHEMA, protocol=PROTOCOL,
            protocol_digest=base.digest(RULE_FILE.read_bytes()), effective_at=clock(), authorization=authorization)))
        return cls(root, clock)

    @contextmanager
    def locked(self):
        with (self.root / '.lock').open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError('A performance operation is already running') from exc
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def blob(self, raw):
        key = base.digest(raw)
        base.write_once(self.root / 'blobs' / key, raw)
        return key

    def raw(self, key):
        if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('Invalid blob identity')
        raw = (self.root / 'blobs' / key).read_bytes()
        if base.digest(raw) != key:
            raise ValueError('Source digest mismatch')
        return raw

    def events(self):
        events = []
        previous = base.digest(base.encode(self.activation))
        for index, path in enumerate(sorted((self.root / 'events').glob('*.json')), 1):
            event = json.loads(path.read_text())
            identity = event.pop('id')
            if path.name != f'{index:06d}.json' or event['previous'] != previous or base.digest(base.encode(event)) != identity:
                raise ValueError('Event history integrity failure')
            if instant(event['at']) < instant(events[-1]['at'] if events else self.activation['effective_at']):
                raise ValueError('Event chronology failure')
            events.append(dict(event, id=identity))
            previous = identity
        return events

    def append(self, kind, payload):
        events = self.events()
        at = self.clock()
        if instant(at) < instant(events[-1]['at'] if events else self.activation['effective_at']):
            raise ValueError('Clock moved backwards')
        event = dict(kind=kind, at=at, payload=payload,
                     previous=events[-1]['id'] if events else base.digest(base.encode(self.activation)))
        event['id'] = base.digest(base.encode(event))
        base.write_once(self.root / 'events' / f'{len(events)+1:06d}.json', base.encode(event))
        return event

    def archive(self, folder):
        return {p.name: self.blob(p.read_bytes()) for p in sorted(Path(folder).iterdir()) if p.is_file()}

    @contextmanager
    def bundle(self, refs):
        with TemporaryDirectory() as tmp:
            for name, key in refs.items():
                if Path(name).name != name:
                    raise ValueError('Invalid bundle filename')
                (Path(tmp) / name).write_bytes(self.raw(key))
            yield Path(tmp)

    def decode(self, event):
        p = event['payload']
        if event['kind'] == 'import':
            raw = self.raw(p['raw'])
            try:
                value = excel.parse(raw)
                rows = [{k: v for k, v in r.items() if k != 'excel_row'} for r in value['rows'] if r['week'] == p['week']]
                if value['season'] != p['season'] or not rows or any(r['conditional'] for r in rows):
                    raise ValueError('Missing, conditional or wrong-season target week')
                if instant(value['updated_at']) > instant(p['received_at']) or instant(p['received_at']) > instant(event['at']):
                    raise ValueError('Workbook chronology mismatch')
                rows.sort(key=lambda r: (r['home'], r['away']))
                material = dict(source='ELWAY', season=p['season'], week=p['week'],
                                updated_at=canonical_time(value['updated_at']), rows=rows)
                return dict(material, semantic=base.digest(base.encode(material)), error=None)
            except Exception as exc:
                return dict(error=type(exc).__name__ + ': ' + str(exc))
        if event['kind'] == 'schedule':
            with self.bundle(p['files']) as folder:
                r = json.loads((folder / 'receipt.json').read_text())
                raw = (folder / 'source.html').read_bytes()
                if base.digest(raw) != r['raw_sha256'] or r['season'] != p['season'] or r['week'] != p['week']:
                    raise ValueError('Schedule identity mismatch')
                if not instant(r['started_at']) <= instant(r['completed_at']) <= instant(event['at']):
                    raise ValueError('Schedule chronology mismatch')
                if r.get('error'):
                    return dict(error=r['error'])
                schedule.replay(folder)
                return dict(r, outcomes=sources.outcomes(raw, p['season'], p['week']))
        if event['kind'] == 'market':
            with self.bundle(p['files']) as folder:
                r = kalshi.replay(folder)
                if not instant(r['run_started_at']) <= instant(r['run_completed_at']) <= instant(event['at']):
                    raise ValueError('Market chronology mismatch')
                records = json.loads((folder / 'complete.json').read_text())['requests']
                markets = []
                for rec in records:
                    if rec['purpose'] == 'catalog' and rec['status'] == 200 and not rec['error']:
                        markets.extend(json.loads((folder / f"response-{rec['sequence']:03d}.body").read_text())['markets'])
                return dict(r, markets=markets)
        return p

    def _schedule(self, season, week, transport):
        with TemporaryDirectory() as tmp:
            folder, _ = schedule.capture(tmp, season, week, transport=transport, clock=self.clock)
            return self.append('schedule', dict(season=season, week=week, files=self.archive(folder)))

    def observe_results(self, season, week, transport=schedule.fetch):
        schedule.scope(season, week)
        with self.locked():
            return self._schedule(season, week, transport)

    def refresh(self, raw, name, season, week, *, retry=False,
                schedule_transport=schedule.fetch, market_transport=kalshi.public_get):
        """New import captures once; explicit retries never overwrite successes.

        No production caller is installed in this slice. Injectable transports
        allow the full lifecycle to be tested without provider access.
        """
        schedule.scope(season, week)
        with self.locked():
            received = self.clock()
            event = self.append('import', dict(raw=self.blob(raw), name=Path(name).name,
                received_at=received, season=season, week=week))
            forecast = self.decode(event)
            if forecast['error']:
                return self.append('rejected', dict(import_id=event['id'], season=season, week=week, error=forecast['error']))
            old = [e for e in self.events() if e['kind'] == 'import' and e['id'] != event['id'] and
                   e['payload']['season'] == season and e['payload']['week'] == week and
                   self.decode(e).get('semantic') == forecast['semantic']]
            if old and not retry:
                return self.append('duplicate', dict(import_id=event['id'], original_id=old[0]['id']))
            if retry and not old:
                raise ValueError('Retry requires an existing forecast import')
            # Record the attempt before IO; interrupted/failed attempts stay visible.
            attempt = self.append('attempt', dict(import_id=event['id'], retry=retry,
                semantic=forecast['semantic'], season=season, week=week))
            s_event = self._schedule(season, week, schedule_transport)
            s = self.decode(s_event)
            if s.get('error'):
                return self.append('failed', dict(attempt_id=attempt['id'], season=season, week=week, error=s['error']))
            current = self.report(season, week, self.clock())
            if current['cutoff'] is None or instant(self.clock()) >= instant(current['cutoff']):
                return self.append('failed', dict(attempt_id=attempt['id'], season=season, week=week, error='Weekly cutoff unknown or passed'))
            dates = [instant(g['kickoff']).astimezone(board.NY).date().isoformat() for g in s['rows']]
            with TemporaryDirectory() as tmp:
                folder, _ = kalshi.capture(tmp, min(dates), max(dates), transport=market_transport, clock=self.clock)
                return self.append('market', dict(attempt_id=attempt['id'], import_id=event['id'],
                    schedule_id=s_event['id'], retry=retry, season=season, week=week, files=self.archive(folder)))

    def report(self, season, week, boundary, *, source_boundary=None):
        """Pure saved-source replay. No writes, no network, no inferred holdings."""
        schedule.scope(season, week)
        at = instant(boundary)
        if at > instant(self.clock()):
            raise ValueError('Analysis boundary is in the future')
        if at < instant(self.activation['effective_at']):
            raise ValueError('Boundary precedes activation')
        all_events = self.events()
        if source_boundary == '':
            all_events = []
        elif source_boundary is not None:
            tips = [i for i, e in enumerate(all_events) if e['id'] == source_boundary]
            if len(tips) != 1:
                raise ValueError('Missing report source boundary')
            all_events = all_events[:tips[0]+1]
        events = [e for e in all_events if instant(e['at']) <= at]
        # Validate sources even when not selected; never trust persisted derivations.
        values = {e['id']: self.decode(e) for e in events}
        scoped = [e for e in events if e['payload'].get('season') == season and e['payload'].get('week') == week]
        schedules = [e for e in scoped if e['kind'] == 'schedule' and not values[e['id']].get('error')]
        cutoff = None
        games = {}
        outcomes = {}
        blocked = False
        active_ids = set()
        slots = {}
        conflicts = set()
        for e in schedules:
            s = values[e['id']]
            starts = [instant(g['kickoff']) for g in s['rows'] if g['kickoff']]
            unknown = len(starts) != len(s['rows'])
            proposed = min(starts) if starts else None
            # Only move an open window; once its deadline passes it never reopens.
            if cutoff is None:
                cutoff = proposed
            elif proposed is not None:
                cutoff = min(cutoff, proposed) if instant(e['at']) >= cutoff else proposed
            blocked = unknown
            active_ids = {g['game_id'] for g in s['rows']}
            for g in s['rows']:
                slot = (g['home'], g['away'])
                if slot in slots and slots[slot] != g['game_id']:
                    conflicts.update((slots[slot], g['game_id']))
                slots[slot] = g['game_id']
                previous = games.get(g['game_id'])
                if previous and (previous.get('identity_conflict') or (previous['home'], previous['away']) != (g['home'], g['away'])):
                    g = dict(g, identity_conflict=True)
                games[g['game_id']] = g
            for key, outcome in s['outcomes'].items():
                outcomes[key] = dict(outcome, observed_at=e['at'], source_id=e['id'])
                if outcome.get('start') and cutoff:
                    cutoff = min(cutoff, instant(outcome['start']))
        effective_cutoff = None if blocked else cutoff
        imports = []
        for e in scoped:
            if e['kind'] != 'import' or values[e['id']].get('error') or not effective_cutoff:
                continue
            if instant(e['at']) >= effective_cutoff or instant(self.activation['effective_at']) >= effective_cutoff:
                continue
            # A schedule observed before cutoff is required, never retrospectively supplied.
            known = [s for s in schedules if instant(s['at']) < effective_cutoff]
            if not known:
                continue
            imports.append(e)
        selected = None
        selection_issue = None
        if imports:
            newest = max(instant(values[e['id']]['updated_at']) for e in imports)
            candidates = [e for e in imports if instant(values[e['id']]['updated_at']) == newest]
            identities = {values[e['id']]['semantic'] for e in candidates}
            if len(identities) != 1:
                selection_issue = 'Conflicting forecasts at newest publication time'
            else:
                selected = candidates[0]
        selected_value = values[selected['id']] if selected else None
        captures = {}
        quote_issues = {}
        attempts = []
        if selected:
            family = {e['id'] for e in imports if values[e['id']]['semantic'] == selected_value['semantic']}
            valid_attempts = {e['id']: e for e in scoped if e['kind'] == 'attempt' and e['payload']['import_id'] in family}
            for attempt_event in valid_attempts.values():
                terminals = [e for e in scoped if e['kind'] in ('market', 'failed') and e['payload'].get('attempt_id') == attempt_event['id']]
                state = 'interrupted-or-in-progress'
                error = None
                if terminals:
                    terminal = terminals[-1]
                    error = values[terminal['id']].get('error') or values[terminal['id']].get('issue')
                    state = 'failed' if terminal['kind'] == 'failed' else values[terminal['id']]['state']
                attempts.append(dict(id=attempt_event['id'], at=attempt_event['at'],
                                     retry=attempt_event['payload']['retry'], state=state, error=error))
            for e in scoped:
                if e['kind'] != 'market' or e['payload']['attempt_id'] not in valid_attempts:
                    continue
                p, market = e['payload'], values[e['id']]
                attempt = valid_attempts[p['attempt_id']]
                if p['import_id'] != attempt['payload']['import_id'] or p['retry'] != attempt['payload']['retry']:
                    raise ValueError('Attempt linkage mismatch')
                s_event = next((s for s in schedules if s['id'] == p['schedule_id']), None)
                if not s_event or instant(s_event['at']) >= effective_cutoff:
                    continue
                if not instant(attempt['at']) <= instant(s_event['at']) <= instant(market['run_started_at']):
                    raise ValueError('Capture does not follow import and schedule')
                for g in values[s_event['id']]['rows']:
                    gid = g['game_id']
                    if gid in captures:
                        continue
                    try:
                        quote = sources.midpoint(g, market, market['markets'])
                        if not instant(market['run_started_at']) <= instant(quote['metadata_received_at']) <= instant(quote['started_at']) <= instant(quote['received_at']) < effective_cutoff:
                            raise ValueError('Quote outside weekly cutoff')
                        captures[gid] = dict(quote, source_id=e['id'], retry=p['retry'], game=g)
                    except (ValueError, KeyError, TypeError) as exc:
                        quote_issues.setdefault(gid, []).append(str(exc))
                        continue
        rows = []
        forecast_rows = {(r['home'], r['away']): r for r in selected_value['rows']} if selected else {}
        for gid, game in sorted(games.items()):
            row = dict(game_id=gid, home=game['home'], away=game['away'], state='missing-capture', issues=[],
                       elway=None, kalshi=None, outcome=outcomes.get(gid), scores=None)
            f, q = forecast_rows.get((game['home'], game['away'])), captures.get(gid)
            if not selected:
                row['issues'].append(selection_issue or 'No qualifying weekly baseline')
            if not f:
                row['issues'].append('Missing forecast')
            if not q:
                row['issues'].append('Missing qualifying home YES quote')
                row['issues'].extend(quote_issues.get(gid, []))
            if effective_cutoff is None:
                row['issues'].append('Unknown weekly cutoff')
            if f and q:
                row['elway'] = board.payout_range(f['home_win'], f['away_win'])
                row['kalshi'] = q
                if gid not in active_ids or gid in conflicts or game.get('identity_conflict') or f['neutral'] != game['neutral'] or q['game']['kickoff'] != game['kickoff'] or q['game']['neutral'] != game['neutral']:
                    row.update(state='excluded', issues=['Schedule identity, time or neutral-site changed'])
                elif game['status'] not in ('SCHEDULED', 'FINAL', 'FINAL_OVERTIME', 'COMPLETED'):
                    row.update(state='excluded', issues=['Unsupported schedule status'])
                elif at < effective_cutoff:
                    row['state'] = 'candidate'
                else:
                    outcome = outcomes.get(gid)
                    row['state'] = outcome['state'] if outcome else 'awaiting-outcome'
                    if outcome and outcome['state'] == 'final':
                        if instant(outcome['observed_at']) <= instant(game['kickoff']):
                            row.update(state='unresolved-outcome', issues=['Final observation before kickoff'])
                        else:
                            row['state'] = 'scored'
                            row['scores'] = sources.error_scores(row['elway']['central'], q['value'], outcome['payout'])
            rows.append(row)
        scored = [r['scores'] for r in rows if r['state'] == 'scored']
        means = {k: str(sum(D(r[k]) for r in scored)/len(scored)) if scored else None
                 for k in ('elway_error', 'kalshi_error', 'difference')}
        coverage = {s: sum(r['state'] == s for r in rows) for s in sorted({r['state'] for r in rows})}
        result = dict(schema=SCHEMA, protocol=PROTOCOL, activation=self.activation, season=season, week=week,
            boundary=boundary, source_boundary=events[-1]['id'] if events else None,
            cutoff=effective_cutoff.isoformat() if effective_cutoff else None,
            frozen=bool(effective_cutoff and at >= effective_cutoff), population=len(rows), paired_games=len(scored),
            population_status='unavailable' if not schedules else 'identity-conflict' if conflicts else 'observed',
            selected_imported_at=selected['payload']['received_at'] if selected else None,
            selected_validated_at=selected['at'] if selected else None,
            selected_import=selected['id'] if selected else None, selected_forecast=selected_value,
            selection_issue=selection_issue, attempts=attempts, coverage=coverage, means=means, games=rows,
            diagnostics=[dict(id=e['id'], kind=e['kind'], error=values[e['id']].get('error')) for e in scoped
                         if values[e['id']].get('error')])
        result['report_id'] = base.digest(base.encode(result))
        return result

    def save_report(self, season, week, boundary):
        with self.locked():
            result = self.report(season, week, boundary)
            base.write_once(self.root / 'reports' / (result['report_id'] + '.json'), base.encode(result))
            return result

    def replay_report(self, path):
        saved = json.loads(Path(path).read_text())
        derived = self.report(saved['season'], saved['week'], saved['boundary'], source_boundary=saved['source_boundary'] or '')
        if derived != saved:
            raise ValueError('Saved report differs from replay')
        return derived
