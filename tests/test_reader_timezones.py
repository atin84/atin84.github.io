"""Synthetic timezone tests; one UTC instant, named reader regions, no geolocation."""
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import reader_timezones as r
import match_overview as m
from test_match_overview import sample

class Times(HTMLParser):
    def __init__(self,markup):
        super().__init__();self.values=[];self.feed(markup)
    def handle_starttag(self,tag,attrs):
        if tag=='time':self.values.append(dict(attrs))

class ReaderTimezoneTests(unittest.TestCase):
    def test_eight_representative_regions_explicit(self):
        expected={'en':'America/New_York','ko':'Asia/Seoul','es':'Europe/Madrid','ja':'Asia/Tokyo',
            'pt-BR':'America/Sao_Paulo','fr':'Europe/Paris','de':'Europe/Berlin','hi':'Asia/Kolkata'}
        self.assertEqual({k:r.profile(k)['zone'] for k in r.LOCALES},expected)
        self.assertTrue(all(r.profile(k)['label'] and r.profile(k)['note'] for k in expected))
    def test_all_editions_are_same_instant(self):
        data=m.normalize(sample(),'EPL','preview','test-123')
        for locale in r.LOCALES:
            out=m.render(data,locale);times=Times(out).values
            self.assertEqual([t['data-timezone'] for t in times[:3]],['Europe/London',r.profile(locale)['zone'],'UTC'])
            for t in times[:3]:self.assertEqual(datetime.fromisoformat(t['datetime']).astimezone(timezone.utc),datetime(2026,10,25,14,tzinfo=timezone.utc))
    def test_october_europe_changes_before_us(self):
        data=m.normalize(sample(),'EPL','preview','test-123')
        expected={'en':('10:00 EDT','UTC-04:00'),'ko':('23:00 KST','UTC+09:00'),
            'es':('15:00 CET','UTC+01:00'),'ja':('23:00 JST','UTC+09:00'),
            'pt-BR':('11:00 -03','UTC-03:00'),'fr':('15:00 CET','UTC+01:00'),
            'de':('15:00 CET','UTC+01:00'),'hi':('19:30 IST','UTC+05:30')}
        for locale,items in expected.items():
            out=m.render(data,locale)
            for x in items:self.assertIn(x,out)
            self.assertIn('14:00 GMT',out);self.assertIn('14:00 UTC',out)
    def test_summer_offsets_and_final_scores_unchanged(self):
        data=sample('recap');data['start_utc']='2026-10-17T14:00:00Z'
        data=m.normalize(data,'EPL','recap','test-123')
        self.assertIn('16:00 CEST',m.render(data,'es'))
        self.assertIn('15:00 BST',m.render(data,'en'))
        self.assertIn('10:00 EDT',m.render(data,'en'))
        self.assertIn('qi-scoreboard',m.render(data,'ja'))
    def test_previous_day_and_next_day(self):
        data=sample();data['start_utc']='2026-10-25T00:30:00Z'
        out=m.render(m.normalize(data,'EPL','preview','test-123'),'en')
        self.assertIn('2026-10-24 (Sat) 20:30 EDT',out)
        data['start_utc']='2026-10-24T23:30:00Z'
        out=m.render(m.normalize(data,'EPL','preview','test-123'),'ja')
        self.assertIn('2026-10-25 (日) 08:30 JST',out)
    def test_us_dst_folds_include_different_offsets(self):
        d=sample();d['start_utc']='2026-11-01T05:30:00Z'
        self.assertIn('01:30 EDT (UTC-04:00)',m.render(m.normalize(d,'EPL','preview','test-123'),'en'))
        d['start_utc']='2026-11-01T06:30:00Z'
        self.assertIn('01:30 EST (UTC-05:00)',m.render(m.normalize(d,'EPL','preview','test-123'),'en'))
    def test_korea_no_longer_a_universal_row(self):
        data=m.normalize(sample(),'EPL','preview','test-123')
        for locale in r.LOCALES:
            out=m.render(data,locale)
            if locale!='ko':self.assertNotIn('KST',out);self.assertNotIn('data-timezone="Asia/Seoul"',out)
        self.assertIn('한국시간 시작 · 서울',m.render(data,'ko'))
    def test_unsupported_locale_fails_closed(self):
        with self.assertRaises(ValueError):r.profile('xx')
        with self.assertRaises(ValueError):m.render(m.normalize(sample(),'EPL','preview','test-123'),'xx')
    def test_profile_cannot_be_mutated_by_caller(self):
        first=r.profile('en');first['zone']='Asia/Seoul'
        self.assertEqual(r.profile('en')['zone'],'America/New_York')

if __name__=='__main__':unittest.main()
