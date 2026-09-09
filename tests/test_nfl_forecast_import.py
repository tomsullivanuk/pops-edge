import argparse
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from decimal import Decimal
import nfl_forecast_import as n


class NFLImportTests(unittest.TestCase):
    def setUp(self):
        self.raw = b'\x89PNG\r\n\x1a\nfixture'
        self.source = n.digest(self.raw)
        self.receipt = dict(source_sha256=self.source, imported_at='2026-09-08T12:00:00+00:00',mime='image/png')
        self.review = dict(source_sha256=self.source, season=2026,week=1,
            expected_games=1,updated_at='2026-09-07T12:02:00-04:00',metadata_reviewed=True,
            rows=[dict(home='SEA',away='NE',home_win='68.4%',away_win='31.1%',neutral=False,reviewed=True)])

    def test_preserves_probabilities_without_inventing_tie_or_normalizing(self):
        row=n.validate(self.review,self.receipt)[0]
        self.assertEqual(row['home_win'],'68.4%')
        self.assertEqual(row['home_probability'],'0.684')
        self.assertEqual(Decimal(row['home_probability'])+Decimal(row['away_probability']),Decimal('.995'))
        self.assertNotIn('tie_probability',row)

    def test_verification_required_even_for_plausible_wrong_digit(self):
        self.review['rows'][0].update(home_win='69.4%',reviewed=False)
        with self.assertRaisesRegex(ValueError,'visual verification'):n.validate(self.review,self.receipt)

    def test_metadata_count_and_missing_rows(self):
        for change in [dict(metadata_reviewed=False),dict(expected_games=2),dict(week=19),dict(season=True)]:
            with self.subTest(change=change):
                r=deepcopy(self.review);r.update(change)
                with self.assertRaises(ValueError):n.validate(r,self.receipt)

    def test_unknown_duplicate_and_identical_teams(self):
        for change in [dict(home='XYZ'),dict(home='NE'),dict(home_win='NaN%'),dict(home_win='101%'),dict(away_win='40.0%'),dict(neutral='false')]:
            with self.subTest(change=change):
                r=deepcopy(self.review);r['rows'][0].update(change)
                with self.assertRaises(ValueError):n.validate(r,self.receipt)
        self.review['rows']*=2;self.review['expected_games']=2
        with self.assertRaisesRegex(ValueError,'more than one'):n.validate(self.review,self.receipt)

    def test_future_naive_and_conflicting_source(self):
        for change in [dict(updated_at='2026-09-09T00:00:00+00:00'),dict(updated_at='2026-09-07T12:02:00'),dict(source_sha256='0'*64),dict(season=2025)]:
            r=deepcopy(self.review);r.update(change)
            if change==dict(season=2025):r['updated_at']='2027-01-01T00:00:00+00:00'
            with self.subTest(change=change),self.assertRaises(ValueError):n.validate(r,self.receipt)

    def test_ocr_keeps_away_in_away_column_when_home_badge_missing(self):
        def token(text,x):return dict(text=text,x=x,y=.6,h=.01,w=.02)
        ocr=dict(items=[token('1N',.1),token('68.4%',.4),token('NE',.5),token('31.1%',.6)])
        row=n.candidates(ocr)[0]
        self.assertEqual(row['home'],'');self.assertEqual(row['away'],'NE')
        self.assertTrue(row['neutral']);self.assertFalse(row['reviewed'])

    def test_repeat_matchup_in_different_week_has_distinct_source_key(self):
        first=n.validate(self.review,self.receipt)[0]['forecast_match_key']
        self.review['week']=2
        self.assertNotEqual(first,n.validate(self.review,self.receipt)[0]['forecast_match_key'])

    def test_immutable_publication(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'record'
            n.write_once(path,b'original');n.write_once(path,b'original')
            with self.assertRaises(ValueError):n.write_once(path,b'changed')
            self.assertEqual(path.read_bytes(),b'original')

    def test_verify_idempotent_corrections_and_source_tamper(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'sources'/self.source;folder.mkdir(parents=True)
            (folder/'image').write_bytes(self.raw);(folder/'receipt.json').write_bytes(n.encode(self.receipt))
            review=root/'review.json';review.write_bytes(n.encode(self.review))
            args=argparse.Namespace(review=review,store=root,reviewer='Test reviewer',supersedes=None)
            n.verify(args);one=next((root/'verified').glob('*.json'));first=one.read_bytes()
            n.verify(args);self.assertEqual(first,one.read_bytes())
            self.review['rows'][0]['home_win']='68.3%';review.write_bytes(n.encode(self.review))
            args.supersedes=one.stem;n.verify(args)
            self.assertEqual(len(list((root/'verified').glob('*.json'))),2)
            self.assertEqual(first,one.read_bytes())
            (folder/'image').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'identity mismatch'):n.verify(args)

    def test_prepare_preserves_source_and_failure_then_retry(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);image=root/'input.png';image.write_bytes(self.raw)
            args=argparse.Namespace(image=image,store=root/'data',season=2026)
            with patch.object(n,'extract',side_effect=OSError('vision unavailable')):
                with self.assertRaisesRegex(ValueError,'OCR failed'):n.prepare(args)
            source=args.store/'sources'/self.source
            self.assertEqual((source/'image').read_bytes(),self.raw)
            self.assertEqual(len(list((source/'failures').glob('*.json'))),1)
            receipt=(source/'receipt.json').read_bytes()
            with patch.object(n,'extract',return_value=dict(engine='fixture',items=[])):n.prepare(args)
            self.assertEqual(receipt,(source/'receipt.json').read_bytes())
            self.assertFalse((args.store/'verified').exists())
            self.assertEqual(image.read_bytes(),self.raw)

    def test_html_escapes_script_in_review(self):
        self.review['source_update_text']='</script><script>alert(1)</script>'
        out=n.render_review(self.review,self.raw,'image/png','2026-09-08')
        self.assertNotIn('</script><script>alert(1)',out)
        self.assertIn('Save checked review',out)


if __name__=='__main__':unittest.main()
