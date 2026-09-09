from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import requests
import retrieve_kalshi_nfl as n


def market(ticker='KXNFLGAME-26SEP09NESEA-SEA',day='Sep 9, 2026'):
    game='New England vs Seattle'
    return dict(ticker=ticker,event_ticker=ticker.rsplit('-',1)[0],market_type='binary',status='active',
        yes_sub_title='Seattle',no_sub_title='Seattle',
        rules_primary=f'If Seattle wins the {game} professional football game originally scheduled for {day}, then the market resolves to Yes.',
        rules_secondary=f'The following market refers to the team who wins the {game} professional football game originally scheduled for {day}. If the game ends in a tie, the market will resolve to $0.50 for each team.')


BOOK=dict(orderbook_fp=dict(yes_dollars=[['0.6000','10.25']],no_dollars=[['0.3500','20.50']]))
SERIES=dict(series=dict(ticker=n.SERIES,product_metadata=dict(scope='Game'),fee_type='quadratic_with_maker_fees',fee_multiplier=1))


class Fake:
    def __init__(self,pages=None,book=None):self.calls=[];self.pages=pages or [dict(markets=[market()],cursor='')];self.book=book if book is not None else BOOK
    def __call__(self,route,params):
        self.calls.append((route,dict(params)))
        if route.startswith('/series/'):obj=SERIES
        elif route=='/markets':obj=self.pages[0 if not params.get('cursor') else 1]
        else:
            if isinstance(self.book,Exception):raise self.book
            obj=self.book
        return 200,json.dumps(obj).encode()


class NFLRetrievalTests(unittest.TestCase):
    def test_complete_capture_replay_exact_raw_and_opposite_bid(self):
        with TemporaryDirectory() as tmp:
            fake=Fake();run,summary=n.capture(tmp,'2026-09-09','2026-09-14',fake)
            self.assertEqual(summary['state'],'complete');self.assertEqual(len(fake.calls),3)
            self.assertEqual(summary,n.replay(run))
            row=summary['rows'][0]
            self.assertEqual(row['offers']['yes']['offer_price'],'0.6500')
            self.assertEqual(row['offers']['yes']['offer_quantity'],'20.50')
            self.assertEqual(row['offers']['no']['offer_price'],'0.4000')
            self.assertEqual((run/'response-003.body').read_bytes(),json.dumps(BOOK).encode())
            self.assertIn('not assessed',summary['eligibility'])
            self.assertNotIn('kickoff',row)

    def test_date_window_filter_uses_rules_not_ticker(self):
        m=market(day='Sep 21, 2026')
        with TemporaryDirectory() as tmp:
            fake=Fake(pages=[dict(markets=[m],cursor='')]);_,s=n.capture(tmp,'2026-09-09','2026-09-14',fake)
            self.assertEqual(s['selected_market_count'],0);self.assertEqual(len(fake.calls),2)

    def test_pagination_cursor_and_duplicate_market_fail_closed(self):
        pages=[dict(markets=[market()],cursor='page & two'),dict(markets=[],cursor='')]
        with TemporaryDirectory() as tmp:
            fake=Fake(pages);run,s=n.capture(tmp,'2026-09-09','2026-09-14',fake)
            self.assertEqual(s['state'],'complete');self.assertEqual(fake.calls[2][1]['cursor'],'page & two');n.replay(run)
        pages[1]['markets']=[market()]
        with TemporaryDirectory() as tmp:
            fake=Fake(pages);_,s=n.capture(tmp,'2026-09-09','2026-09-14',fake)
            self.assertEqual(s['state'],'failed');self.assertFalse(any('orderbook' in x[0] for x in fake.calls))

    def test_repeated_cursor_stops_without_books(self):
        pages=[dict(markets=[],cursor='again'),dict(markets=[],cursor='again')]
        with TemporaryDirectory() as tmp:
            fake=Fake(pages);_,s=n.capture(tmp,'2026-09-09','2026-09-14',fake)
            self.assertEqual(s['state'],'failed');self.assertEqual(len(fake.calls),3)

    def test_failed_book_keeps_raw_catalog_and_later_book(self):
        m2=market('KXNFLGAME-26SEP10SFLAR-LAR','Sep 10, 2026')
        fake=Fake([dict(markets=[market(),m2],cursor='')]);original=fake.__call__
        def call(route,params):
            if route.endswith('SEA/orderbook'):return 503,b'service unavailable'
            return original(route,params)
        with TemporaryDirectory() as tmp:
            run,s=n.capture(tmp,'2026-09-09','2026-09-14',call)
            self.assertEqual(s['state'],'partial');self.assertEqual(s['rows'][0]['state'],'unavailable')
            self.assertEqual(s['rows'][1]['state'],'captured');self.assertEqual(n.replay(run),s)
            self.assertEqual((run/'response-003.body').read_bytes(),b'service unavailable')

    def test_transport_and_non_json_catalog_failure_are_visible(self):
        for answer in [('timeout',None),(200,b'not json'),(401,b'unauthorized')]:
            def call(route,params):
                if route.startswith('/series/'):return 200,json.dumps(SERIES).encode()
                if answer[0]=='timeout':raise requests.Timeout()
                return answer
            with self.subTest(answer=answer),TemporaryDirectory() as tmp:
                run,s=n.capture(tmp,'2026-09-09','2026-09-14',call)
                self.assertEqual(s['state'],'failed');self.assertEqual(s['request_count'],2)
                self.assertTrue((run/'response-002.json').exists());n.replay(run)

    def test_unknown_rules_and_foreign_catalog(self):
        for changes,state in [(dict(rules_primary='quarter game'),'partial'),(dict(yes_sub_title='Boston'),'partial'),(dict(event_ticker='KXMLBGAME-X'),'failed')]:
            m=market();m.update(changes)
            with self.subTest(changes=changes),TemporaryDirectory() as tmp:
                fake=Fake([dict(markets=[m],cursor='')]);_,s=n.capture(tmp,'2026-09-09','2026-09-14',fake)
                self.assertEqual(s['state'],state);self.assertEqual(len(fake.calls),2)

    def test_rejects_bad_books_without_guessing_units(self):
        for levels in [[[60,'1']], [['60','1']], [['NaN','1']], [['.4','0']], [['.4','-1']], [['.4','Infinity']], [['.4','1'],['.40','2']]]:
            bad=deepcopy(BOOK);bad['orderbook_fp']['yes_dollars']=levels
            with self.subTest(levels=levels),self.assertRaises(ValueError):n.book_view(bad,'X')
        bad=deepcopy(BOOK);bad['orderbook_fp']['yes_dollars']=[['.8','1']]
        with self.assertRaisesRegex(ValueError,'crossed'):n.book_view(bad,'X')
        with self.assertRaises(ValueError):n.book_view(dict(orderbook={'yes':[],'no':[]}),'X')

    def test_empty_depth_and_nonopen_not_actionable(self):
        empty=dict(orderbook_fp=dict(yes_dollars=[],no_dollars=[]))
        with TemporaryDirectory() as tmp:
            _,s=n.capture(tmp,'2026-09-09','2026-09-14',Fake(book=empty))
            self.assertEqual(s['state'],'complete');self.assertEqual(s['rows'][0]['state'],'missing-depth')
            self.assertIsNone(s['rows'][0]['offers']['yes']['offer_price'])

    def test_tamper_and_interrupted_run_cannot_replay(self):
        with TemporaryDirectory() as tmp:
            run,_=n.capture(tmp,'2026-09-09','2026-09-14',Fake())
            (run/'response-003.body').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'digest'):n.replay(run)
        with TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):n.replay(tmp)

    def test_limits_and_fixed_routes(self):
        for a,b in [('2026-09-09','2026-09-17'),('2026-09-10','2026-09-09')]:
            with self.assertRaises(ValueError):n.window(a,b)
        with patch.object(n.requests,'Session') as session:
            with self.assertRaises(ValueError):n.public_get('/portfolio/orders',{})
            session.assert_not_called()

    def test_backwards_clock_cannot_be_complete(self):
        times=iter(['2026-09-09T12:00:00Z','2026-09-09T12:00:00Z','2026-09-09T11:59:00Z','2026-09-09T12:00:00Z'])
        with TemporaryDirectory() as tmp:
            _,s=n.capture(tmp,'2026-09-09','2026-09-14',Fake(),lambda:next(times))
            self.assertEqual(s['state'],'failed')

if __name__=='__main__':unittest.main()
