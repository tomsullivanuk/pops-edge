"""Local NFL refresh application. Fixed actions, explicit files, no order execution."""
import argparse
import base64
import csv
import io
import json
import os
from pathlib import Path
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
import uuid
import webbrowser
import nfl_excel_import as excel
import nfl_forecast_import as source
import nfl_schedule as schedule
import nfl_comparison_board as board
import retrieve_kalshi_nfl as kalshi

MAX_REQUEST=24*1024*1024


class Workflow:
    def __init__(self,root):
        self.root=Path(root).resolve();self.inbox=self.root/'Downloads/NFL';self.data=self.root/'Data/NFL'
        self.inbox.mkdir(parents=True,exist_ok=True);self.data.mkdir(parents=True,exist_ok=True)
        self.lock=threading.Lock();self.status=dict(state='inputs',message='Select an ELWAY workbook and activity export.')
        self.files={};self.candidate=None;self.activity=None;self.review_id=None;self.boards={}
        for path in sorted((self.data/'boards').glob('*/comparison.json')):
            if not (path.parent/'complete.json').exists():continue
            try:
                value=json.loads(path.read_text());key=f"{value['season']}-{value['week']}"
                if key not in self.boards or path.stat().st_mtime>self.boards[key].stat().st_mtime:self.boards[key]=path.parent
            except (OSError,ValueError,KeyError):continue

    def catalog(self):
        self.files={};listing=[]
        for p in sorted(self.inbox.glob('*')):
            if p.is_symlink() or not p.is_file() or p.suffix.lower() not in ('.xlsx','.csv'):continue
            identity=source.digest(str(p).encode());self.files[identity]=p
            listing.append(dict(id=identity,name=p.name,kind=p.suffix.lower()))
        return dict(files=listing,inbox=str(self.inbox),status=self.status,boards=sorted(self.boards))

    def file_bytes(self,spec,kind):
        if not isinstance(spec,dict) or set(spec)!={'id'}:raise ValueError('Select a file from the NFL inbox')
        path=self.files.get(spec['id'])
        if not path or path.is_symlink() or path.resolve().parent!=self.inbox or path.suffix.lower()!=kind:raise ValueError('Selected inbox file is unavailable')
        if not 0<path.stat().st_size<=excel.MAX_BYTES:raise ValueError('Use a nonempty file up to 8 MB')
        return path.read_bytes(),path.name

    def generate(self,payload):
        if not self.lock.acquire(False):raise ValueError('A generation is already running')
        try:
            raw,name=self.file_bytes(payload.get('forecast'),'.xlsx')
            activity,activity_name=self.file_bytes(payload.get('activity'),'.csv')
            attempt=self.data/'refreshes'/uuid.uuid4().hex
            source.write_once(attempt/'started.json',source.encode(dict(at=kalshi.utc(),forecast_sha256=source.digest(raw),activity_sha256=source.digest(activity),scope='all workbook weeks')))
            self.status=dict(state='running',message='Checking the selected files…')
            threading.Thread(target=self.run,args=(raw,name,activity,attempt),daemon=True).start()
            return self.status
        except Exception:self.lock.release();raise

    def run(self,raw,name,activity,attempt):
        try:
            candidate=excel.prepare(raw,name,self.data/'forecasts')
            from nfl_activity import REQUIRED
            reader=csv.DictReader(io.StringIO(activity.decode('utf-8-sig')))
            if not REQUIRED.issubset(reader.fieldnames or []):raise ValueError('Activity export missing required columns')
            for row in reader:
                if row.get('Market_Ticker','').startswith('KXNFLGAME-') and row.get('type') in ('Trade','Settlement'):
                    if kalshi.aware(row['Original_Date'])>kalshi.aware(kalshi.utc()):raise ValueError('Activity has a future timestamp')
            if any(r['conditional'] for r in candidate['rows']):raise ValueError('Workbook contains marked conditional projections; use the main forecast table')
            verified={week:excel.validate_automatically(candidate,week,self.data/'forecasts') for week in candidate['weeks']}
            activity_path=self.data/'activity'/source.digest(activity)/'activity.csv';source.write_once(activity_path,activity)
            source.write_once(activity_path.parent/('import-'+uuid.uuid4().hex+'.json'),source.encode(dict(imported_at=kalshi.utc(),source_sha256=source.digest(activity))))
            self.candidate=candidate;self.activity=activity_path
            season=candidate['season'];failures=[];completed=[];pending_dates=[]
            for index,week in enumerate(candidate['weeks'],1):
                try:
                    self.status=dict(state='running',message=f'Refreshing week {week} ({index} of {len(verified)}): schedule…')
                    sf,s=schedule.capture(self.data/'schedules',season,week)
                    if s['error']:raise ValueError(s['error'])
                    dates=[kalshi.aware(g['kickoff']).astimezone(board.NY).date().isoformat() for g in s['rows'] if g['kickoff']]
                    if not dates:
                        pending_dates.append(dict(week=week,schedule=str(sf),games=len(s['rows'])))
                        continue
                    self.status=dict(state='running',message=f'Refreshing week {week} ({index} of {len(verified)}): prices…')
                    kf,k=kalshi.capture(self.data/'kalshi',min(dates),max(dates))
                    if k['state']!='complete':raise ValueError('Kalshi capture incomplete')
                    folder,data=board.build(self.data/'boards',verified[week],self.data/'forecasts',sf,kf,activity_path)
                    board.replay(folder)
                    self.boards[f'{season}-{week}']=folder;completed.append(dict(week=week,board=folder.name))
                except Exception as exc:failures.append(dict(week=week,error=str(exc)))
            result=dict(at=kalshi.utc(),completed=completed,failures=failures,pending_dates=pending_dates)
            source.write_once(attempt/('complete.json' if not failures else 'partial.json'),source.encode(result))
            if failures:
                self.status=dict(state='attention',message=f"Updated {len(completed)} of {len(verified)} weeks. Needs attention: "+'; '.join(f"Week {x['week']}: {x['error']}" for x in failures)+'. Older captures remain labeled with their original times.',updated=bool(completed))
            else:
                note=(' '+', '.join(f"Week {x['week']}" for x in pending_dates)+': date/time TBD. Games remain listed in their weeks.') if pending_dates else ''
                self.status=dict(state='complete',message=f"Bet Sheet refreshed: {candidate['game_count']} games. {len(completed)} weeks updated."+note,updated=True)
        except Exception as exc:
            self.status=dict(state='attention',message=str(exc)+'. Previous sheets remain available.')
            source.write_once(attempt/'failed.json',source.encode(dict(at=kalshi.utc(),error=str(exc))))
        finally:self.lock.release()


def handler(workflow,token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,data,kind='application/json'):
            body=source.encode(data) if kind=='application/json' else data
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers();self.wfile.write(body)
        def trusted(self,write=False):
            origin=f'http://127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':return False
            if self.headers.get('Sec-Fetch-Site')=='cross-site':return False
            if write:return self.headers.get('Origin')==origin and secrets.compare_digest(self.headers.get('X-Pops-Token',''),token) and self.headers.get('Content-Type')=='application/json'
            return True
        def do_GET(self):
            if not self.trusted():return self.send(403,dict(error='Local access only'))
            path=urlsplit(self.path).path
            try:
                if path=='/':
                    html=(Path(__file__).with_name('nfl_refresh.html')).read_text().replace('__TOKEN__',token).replace('__VERSION__',Path(__file__).with_name('VERSION').read_text().strip())
                    return self.send(200,html.encode(),'text/html; charset=utf-8')
                if path=='/season':
                    from nfl_season_board import assemble,render
                    return self.send(200,render(assemble(workflow.data,list(workflow.boards.values()),workflow.candidate)).encode(),'text/html; charset=utf-8')
                if path=='/api/state':return self.send(200,workflow.catalog())
                m=re.fullmatch(r'/board/(board-[a-f0-9]{32}|activity-[a-f0-9]{32})/(board.html|comparison.json|complete.json)',path)
                if m:
                    folder=workflow.data/'boards'/m[1]
                    if folder.is_symlink() or folder not in workflow.boards.values():raise ValueError('Board unavailable')
                    target=folder/m[2]
                    if target.is_symlink():raise ValueError('Invalid saved board')
                    board.replay(folder,check_html=False)
                    if m[2]=='board.html':
                        from nfl_board_view import render
                        return self.send(200,render(json.loads((folder/'comparison.json').read_text())).encode(),'text/html; charset=utf-8')
                    return self.send(200,target.read_bytes(),'application/octet-stream')
                if path=='/api/boards':return self.send(200,{k:v.name for k,v in workflow.boards.items()})
                return self.send(404,dict(error='Not found'))
            except (ValueError,OSError,KeyError) as exc:return self.send(400,dict(error=str(exc)))
        def do_POST(self):
            if not self.trusted(True):return self.send(403,dict(error='Refresh request must come from this local app'))
            try:
                self.connection.settimeout(15)
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=MAX_REQUEST:raise ValueError('Request exceeds limit')
                payload=json.loads(self.rfile.read(length))
                if not isinstance(payload,dict):raise ValueError('Invalid request')
                if self.path=='/api/generate':return self.send(200,workflow.generate(payload))
                return self.send(404,dict(error='Unknown action'))
            except Exception as exc:return self.send(400,dict(error=str(exc)))
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path.home()/'PopsEdge');p.add_argument('--port',type=int,default=8766);p.add_argument('--no-browser',action='store_true');args=p.parse_args()
    workflow=Workflow(args.root);server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(workflow,secrets.token_hex(32)))
    url=f'http://127.0.0.1:{server.server_port}/';print('NFL Bet Sheet: '+url,flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
