"""Exercise the real local application boundary with an offline provider transport."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import requests
import nfl_refresh
from mlb_odds_store import OddsStore
from tests.test_mlb_odds import Clock, Feed, DAY, schedule


class LocalHTTP(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='/private/tmp',prefix='mlb-http-')
        self.feed,self.clock=Feed(),Clock()
        self.root=Path(self.temp.name)/'Data/MLB/odds'
        self.store=OddsStore(self.root,fetch=self.feed,clock=self.clock.now,monotonic=self.clock.mono)
        with patch('mlb_odds_store.OddsStore',return_value=self.store):
            handler=nfl_refresh.handler(nfl_refresh.Workflow(self.temp.name),'test-token')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.headers={'Origin':self.url,'X-Pops-Token':'test-token'}
    def tearDown(self):
        if self.store.thread:self.store.thread.join(3)
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def get(self,path):return requests.get(self.url+path,timeout=3)
    def post(self,body,headers=None):return requests.post(self.url+'/api/mlb/refresh',json=body,headers=headers or self.headers,timeout=3)

    def test_navigation_is_inert_and_local_only(self):
        self.assertIn('href="/mlb"',self.get('/').text)
        page=self.get('/mlb');self.assertEqual(page.status_code,200)
        self.assertIn('Refresh MLB odds',page.text);self.assertNotIn('__TOKEN__',page.text)
        self.assertIsNone(self.get('/api/mlb/day?date='+DAY).json()['result'])
        self.assertFalse(self.root.exists());self.assertFalse(self.feed.calls)
        self.assertEqual(requests.get(self.url+'/mlb',headers={'Host':'evil.example'},timeout=3).status_code,403)
        for query in ['date='+DAY+'&date='+DAY,'path=/anything','date=../anything']:
            self.assertEqual(self.get('/api/mlb/day?'+query).status_code,400)

    def test_refresh_requires_local_authority_and_fixed_scope(self):
        for headers in [{'Origin':'https://evil.example','X-Pops-Token':'test-token'}, {'Origin':self.url,'X-Pops-Token':'wrong'}]:
            self.assertEqual(self.post({'date':DAY},headers).status_code,403)
        for body in [{'date':DAY,'tickers':['arbitrary']},{'date':'../file'},{'date':False}]:
            self.assertEqual(self.post(body).status_code,400)
        self.assertFalse(self.feed.calls)
        self.assertEqual(self.post({'date':DAY}).status_code,200)
        self.store.thread.join(3);self.assertFalse(self.store.thread.is_alive())
        state=self.get('/api/mlb/day?date='+DAY).json()
        self.assertEqual(state['attempt']['state'],'complete');self.assertEqual(len(self.feed.calls),4)
        identity=state['selected']['id']
        response=self.get(f'/mlb/evidence/{DAY}/{identity}/raw/000.body')
        self.assertEqual(response.content,schedule());self.assertEqual(response.headers['Cache-Control'],'no-store')
        names=['result.json','complete.json']+[r['raw_file'] for r in state['result']['requests'] if r.get('raw_file')]
        for name in names:
            response=self.get(f'/mlb/evidence/{DAY}/{identity}/{name}')
            self.assertEqual(response.status_code,200);self.assertEqual(response.content,self.store.download(DAY,identity,name))
        self.assertEqual(self.get(f'/mlb/evidence/{DAY}/{identity}/secrets.json').status_code,404)
        self.assertEqual(self.get('/api/mlb/day?date='+DAY).json()['selected'],state['selected'])
        self.assertEqual(len(self.feed.calls),4)

    def test_running_and_failed_actions_remain_visible(self):
        entered,release=threading.Event(),threading.Event()
        def blocked(provider,route,params):
            entered.set();release.wait(3);raise ConnectionError('offline failure')
        self.store.fetch=blocked
        self.assertEqual(self.post({'date':DAY}).status_code,200);self.assertTrue(entered.wait(2))
        self.assertTrue(self.get('/api/mlb/day?date='+DAY).json()['running'])
        self.assertEqual(self.post({'date':DAY}).status_code,400)
        release.set();self.store.thread.join(3)
        state=self.get('/api/mlb/day?date='+DAY).json()
        self.assertFalse(state['running']);self.assertEqual(state['attempt']['state'],'failed');self.assertIsNone(state['result'])


if __name__=='__main__':unittest.main()
