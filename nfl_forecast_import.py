"""Local ELWAY screenshot import. No network, market valuation, or policy authority."""
from __future__ import annotations
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

TEAMS = set('ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS'.split())
VERSION = 'elway-image-import-v1'
FIELDS = ('home', 'home_win', 'away', 'away_win', 'neutral')


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(data):
    return (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def write_once(path, data):
    """Publish complete bytes create-only; an interrupted temp is not a record."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Existing record differs: {path}')
        return
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ValueError(f'Concurrent record differs: {path}')
    finally:
        os.unlink(tmp)


def timestamp(value):
    t = datetime.fromisoformat(value)
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError('Update timestamp needs a timezone offset.')
    return t


def image_type(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    raise ValueError('Use a PNG or JPEG screenshot.')


def extract(image):
    tool = Path(__file__).parent / 'tools' / 'elway_ocr.swift'
    with tempfile.TemporaryDirectory(prefix='elway-ocr-') as cache:
        result = subprocess.run(['swift', '-module-cache-path', cache, str(tool), str(image)],
                                capture_output=True, text=True, timeout=180, check=True)
    return json.loads(result.stdout)


def candidates(ocr):
    """Group visible OCR lines by vertical centres; never assert extraction validity."""
    items = ocr['items']
    groups = []
    for item in sorted(items, key=lambda a: -(a['y'] + a['h']/2)):
        y = item['y'] + item['h']/2
        group = next((g for g in groups if abs(g[0]-y) < max(item['h']*.65, .002)), None)
        if group is None:
            groups.append([y, [item]])
        else:
            group[1].append(item)
    rows = []
    for _, group in groups:
        text = ' | '.join(i['text'] for i in sorted(group, key=lambda a:a['x']))
        percentages = re.findall(r'\d+(?:\.\d+)?\s*%', text)
        if len(percentages) != 2:
            continue
        parts = re.split(r'\d+(?:\.\d+)?\s*%', text)
        def code(part):
            codes = [s for s in re.findall(r'\b[A-Z]{2,3}\b', part) if s in TEAMS]
            return codes[0] if len(codes) == 1 else ''
        rows.append(dict(row_id=len(rows)+1, home=code(parts[0]),
                         home_win=percentages[0].replace(' ', ''),
                         away=code(parts[1]),
                         away_win=percentages[1].replace(' ', ''),
                         neutral=bool(re.search(r'\b(?:\d+\s*)?N\b', text)), reviewed=False, raw_text=text))
    return rows


def validate(review, receipt):
    if review.get('source_sha256') != receipt['source_sha256']:
        raise ValueError('Review belongs to a different image.')
    if review.get('metadata_reviewed') is not True:
        raise ValueError('Verify season, week, update time and complete image row count.')
    season, week, expected = review.get('season'), review.get('week'), review.get('expected_games')
    if type(season) is not int or not 2000 <= season <= 2100:
        raise ValueError('Invalid season.')
    if type(week) is not int or not 1 <= week <= 18:
        raise ValueError('Only regular-season weeks 1–18 are supported.')
    if type(expected) is not int or not 1 <= expected <= 16:
        raise ValueError('Expected visible game count must be 1–16.')
    updated = timestamp(review['updated_at'])
    if updated > timestamp(receipt['imported_at']):
        raise ValueError('Source update is after actual image import.')
    if updated.year not in (season, season+1):
        raise ValueError('Source update year conflicts with season.')
    rows = review.get('rows', [])
    if len(rows) != expected:
        raise ValueError('Row count differs from verified complete screenshot count.')
    seen = set()
    result = []
    for i, row in enumerate(rows, 1):
        if row.get('reviewed') is not True:
            raise ValueError(f'Row {i}: visual verification required.')
        home, away = row.get('home'), row.get('away')
        if home not in TEAMS or away not in TEAMS or home == away:
            raise ValueError(f'Row {i}: unknown or identical teams.')
        if home in seen or away in seen:
            raise ValueError(f'Row {i}: a team appears in more than one game this week.')
        seen.update((home, away))
        if type(row.get('neutral')) is not bool:
            raise ValueError(f'Row {i}: verify neutral-site marker.')
        probabilities = []
        for key in ('home_win', 'away_win'):
            value = row.get(key, '')
            if not isinstance(value, str) or not re.fullmatch(r'\d{1,3}(?:\.\d+)?%', value):
                raise ValueError(f'Row {i}: probability must preserve displayed percent, e.g. 68.4%.')
            p = Decimal(value[:-1]) / 100
            if not 0 <= p <= 1:
                raise ValueError(f'Row {i}: probability outside 0–100%.')
            probabilities.append(p)
        if sum(probabilities) > 1:
            raise ValueError(f'Row {i}: probabilities exceed 100%; correct rather than normalize.')
        result.append({**{k:row[k] for k in FIELDS},
                       'home_probability':str(probabilities[0]), 'away_probability':str(probabilities[1]),
                       'source_row':i, 'season':season, 'week':week,
                       'forecast_match_key':f'nfl:{season}:week-{week}:{home}:{away}'})
    return result


def render_review(review, image, mime, imported):
    payload = json.dumps(review).replace('<', '\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><title>ELWAY forecast review</title>
<style>body{font:16px system-ui;margin:28px;color:#172033;background:#f4f6fa}h1{margin-bottom:6px}.layout{display:grid;grid-template-columns:1fr 1fr;gap:24px}img{width:100%;position:sticky;top:10px}section{background:white;padding:20px;border-radius:12px}table{border-collapse:collapse;width:100%}td,th{padding:6px;border-bottom:1px solid #ddd;text-align:left}input{font:inherit;max-width:95px}input.wide{max-width:none;width:270px}button{padding:12px;margin-top:16px;background:#164e63;color:white;border:0;border-radius:6px}label{display:block;margin:12px 0}.note{color:#546174}#errors{color:#9c2d19} @media(max-width:1000px){.layout{grid-template-columns:1fr}}</style>
<h1>Check your ELWAY forecast</h1><p class="note">Unverified extraction · Check every row against the original. Changes affect the review only.</p>
<div class="layout"><section><img alt="Original forecast screenshot" src="data:''' + mime + ';base64,' + base64.b64encode(image).decode() + '''"></section><section>
<label>Season <input id="season" type="number"></label><label>Week <input id="week" type="number"></label>
<label>Published update (with timezone) <input class="wide" id="updated_at"></label>
<label>Games visible in complete image <input id="expected_games" type="number"></label>
<p class="note">Actually imported: ''' + html.escape(imported) + '''. Screenshot update time is separate from import time.</p>
<table><thead><tr><th>Home</th><th>Win %</th><th>Away</th><th>Win %</th><th>Neutral</th><th>Checked</th><th></th></tr></thead><tbody id="rows"></tbody></table>
<button id="add">Add missing row</button><label><input type="checkbox" id="metadata_reviewed"> I checked the season, week, update time and complete game count.</label>
<p id="errors"></p><button id="save">Save checked review</button>
<p class="note">Save the downloaded JSON, then use the verify command to validate and archive it. Saving this page does not activate a forecast.</p></section></div>
<script>const data=''' + payload + ''';
for(const k of ['season','week','updated_at','expected_games']) document.getElementById(k).value=data[k]??'';
function draw(){const body=document.getElementById('rows');body.replaceChildren();data.rows.forEach((r,i)=>{const tr=document.createElement('tr');for(const k of ['home','home_win','away','away_win','neutral','reviewed']){const td=document.createElement('td'),input=document.createElement('input');input.type=['neutral','reviewed'].includes(k)?'checkbox':'text';if(input.type==='checkbox')input.checked=r[k]===true;else input.value=r[k]??'';input.onchange=()=>{r[k]=input.type==='checkbox'?input.checked:input.value;if(k!=='reviewed'){r.reviewed=false;draw()}};td.append(input);tr.append(td)}const td=document.createElement('td'),b=document.createElement('button');b.textContent='Remove';b.onclick=()=>{data.rows.splice(i,1);draw()};td.append(b);tr.append(td);body.append(tr)})}draw();
document.getElementById('add').onclick=()=>{data.rows.push({home:'',home_win:'',away:'',away_win:'',neutral:false,reviewed:false});draw()};
document.getElementById('save').onclick=()=>{for(const k of ['season','week','expected_games'])data[k]=Number(document.getElementById(k).value);data.updated_at=document.getElementById('updated_at').value;data.metadata_reviewed=document.getElementById('metadata_reviewed').checked;if(!data.metadata_reviewed||data.rows.some(r=>!r.reviewed)||data.rows.length!==data.expected_games){document.getElementById('errors').textContent='Check every row and metadata; game count must match.';return}const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='elway-checked-review.json';a.click();URL.revokeObjectURL(a.href)};</script></html>'''


def load_source(root, source_id):
    if not re.fullmatch('[a-f0-9]{64}', source_id):
        raise ValueError('Invalid source digest.')
    folder = root / 'sources' / source_id
    receipt = json.loads((folder/'receipt.json').read_text())
    image = (folder/'image').read_bytes()
    if receipt['source_sha256'] != source_id or digest(image) != source_id:
        raise ValueError('Archived image or receipt identity mismatch.')
    return folder, receipt, image


def prepare(args):
    image = args.image
    if image is None:
        files = [p for p in args.inbox.iterdir() if p.suffix.lower() in ('.png','.jpg','.jpeg')]
        if len(files) != 1:
            raise ValueError('Specify an image path when the inbox does not contain exactly one image.')
        image = files[0]
    raw = image.read_bytes()
    mime = image_type(raw)
    source_id = digest(raw)
    folder = args.store/'sources'/source_id
    if (folder/'receipt.json').exists():
        _, receipt, _ = load_source(args.store, source_id)
    else:
        receipt = dict(schema=VERSION, source_sha256=source_id, original_name=image.name,
                       imported_at=now(), mime=mime)
        write_once(folder/'image', raw)
        write_once(folder/'receipt.json', encode(receipt))
    try:
        if (folder/'ocr.json').exists():
            ocr = json.loads((folder/'ocr.json').read_text())
        else:
            ocr = extract(folder/'image')
            write_once(folder/'ocr.json', encode(ocr))
        rows = candidates(ocr)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        failure = encode(dict(at=now(), error=str(exc)))
        write_once(folder/'failures'/f'{digest(failure)}.json', failure)
        raise ValueError('Local OCR failed; original retained. Retry with Swift/Vision available.') from exc
    texts = [a['text'] for a in ocr['items']]
    week = next((int(m.group(1)) for t in texts if (m:=re.fullmatch(r'Week (\d+)', t))), None)
    update_text = next((t for t in texts if t.startswith('Updated ')), '')
    updated = ''
    m = re.fullmatch(r'Updated (\w+ \d+, \d{4}) at (\d+:\d+ [AP]M) (EDT|EST)', update_text)
    if m:
        parsed = datetime.strptime(m[1]+' '+m[2], '%B %d, %Y %I:%M %p')
        updated = parsed.isoformat() + ('-04:00' if m[3]=='EDT' else '-05:00')
    expected = next((int(m.group(1)) for t in texts if (m:=re.fullmatch(r'(\d+) games', t))), None)
    review = dict(source_sha256=source_id, season=args.season, week=week,
                  updated_at=updated, source_update_text=update_text, expected_games=expected,
                  metadata_reviewed=False, rows=rows)
    review_dir = args.store/'reviews'/source_id
    write_once(review_dir/'candidate.json', encode(review))
    write_once(review_dir/'review.html', render_review(review,raw,mime,receipt['imported_at']).encode())
    print(f'Unverified: {len(rows)} candidate rows. Review: {(review_dir/"review.html").resolve()}')
    print(f'After saving the checked review: python3 nfl_forecast_import.py verify REVIEW.json --store "{args.store}" --reviewer YOUR_NAME')


def verify(args):
    review = json.loads(args.review.read_text())
    _, receipt, _ = load_source(args.store, review.get('source_sha256',''))
    rows = validate(review, receipt)
    if not args.reviewer.strip():
        raise ValueError('Reviewer identity is required.')
    supersedes = args.supersedes
    if supersedes:
        if not re.fullmatch('[a-f0-9]{64}', supersedes):
            raise ValueError('Invalid predecessor verification ID.')
        previous = json.loads((args.store/'verified'/f'{supersedes}.json').read_text())
        if previous['source']['source_sha256'] != receipt['source_sha256']:
            raise ValueError('Corrections must refer to the same source image.')
    key = digest(encode(dict(review=review, reviewer=args.reviewer, supersedes=supersedes)))
    path = args.store/'verified'/f'{key}.json'
    if path.exists():
        record = json.loads(path.read_text())
        if record['review'] != review or record['rows'] != rows or record['reviewer'] != args.reviewer or record['source'] != receipt:
            raise ValueError('Existing verification differs.')
        print(f'Already verified: {path.resolve()}')
        return
    record = dict(schema=VERSION, supersedes=supersedes, verification_id=key, verified_at=now(), reviewer=args.reviewer,
                  source=receipt, review=review, rows=rows,
                  scope='verified provider transcription; canonical game mapping and market eligibility pending')
    write_once(path, encode(record))
    print(f'Verified {len(rows)} rows: {path.resolve()}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    p = commands.add_parser('prepare')
    p.add_argument('image',type=Path,nargs='?')
    p.add_argument('--inbox',type=Path,default=Path.home()/'Downloads/PopsEdge/NFL')
    p.add_argument('--season',type=int,required=True)
    v = commands.add_parser('verify')
    v.add_argument('review',type=Path)
    v.add_argument('--reviewer',required=True)
    v.add_argument('--supersedes',help='Previous verification ID for a correction of the same source')
    for command in (p,v):
        command.add_argument('--store',type=Path,default=Path.home()/'PopsEdgeData/NFL')
    args = parser.parse_args()
    try:
        (prepare if args.command=='prepare' else verify)(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2,f'Import needs attention: {exc}\n')


if __name__ == '__main__':
    main()
