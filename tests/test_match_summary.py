"""Synthetic timetable/result contracts; no network, publication or model use."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import match_summary as m


def fixture(kind='preview'):
    out={'official_id':'fixture123','status':'scheduled' if kind=='preview' else 'final',
        'home':'Home Club','away':'Away Club','venue':'A Stadium','competition':'Premier League','season':'2026/27',
        'start_utc':'2026-10-25T14:00:00Z' if kind=='preview' else '2026-10-18T13:00:00Z',
        'venue_timezone':'Europe/London','verified_at':'2026-10-20T14:00:00Z','matchweek':8 if kind=='preview' else 7,
        'sources':[{'title':'Synthetic fixture','url':'https://fixture.example.test/match'}]}
    if kind=='recap':out.update(final_score=[2,0],halftime_score=[1,0],goals=[
        {'minute':4,'team':'home','player':'Opponent defender','own_goal':True,'score':[1,0]},
        {'minute':90,'added':6,'team':'home','player':'Home player','score':[2,0]}])
    return out

class MatchSummaryTests(unittest.TestCase):
    def test_timezone_before_and_after_uk_dst(self):
        pre=m.normalize(fixture(),'EPL','preview','fixture123')
        html=m.render(pre,'ko')
        self.assertIn('2026-10-25 (일)',html);self.assertIn('23:00',html);self.assertIn('GMT',html)
        old=fixture();old['start_utc']='2026-10-24T14:00:00Z'
        html=m.render(m.normalize(old,'EPL','preview','fixture123'),'ko')
        self.assertIn('15:00',html);self.assertIn('BST',html)
    def test_all_locales_have_real_tables_and_safe_text(self):
        raw=fixture();raw['venue']='<script>A stadium</script>'
        normalized=m.normalize(raw,'EPL','preview','fixture123')
        for locale in m.UI:
            html=m.render(normalized,locale)
            self.assertIn('<table',html);self.assertIn('scope="row"',html);self.assertIn('<caption>',html)
            self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html);self.assertNotIn('<img',html)
    def test_final_score_and_own_goal_timeline(self):
        html=m.render(m.normalize(fixture('recap'),'EPL','recap','fixture123'),'ko')
        for value in ('2 – 0','전반','후반','자책골','90+6′','득점 타임라인'):self.assertIn(value,html)
        self.assertIn('22:00',html);self.assertIn('14:00',html)
    def test_final_does_not_appear_in_preview(self):
        bad=fixture();bad['final_score']=[1,0]
        with self.assertRaises(ValueError):m.normalize(bad,'EPL','preview','fixture123')
    def test_identity_lifecycle_and_offset_checks(self):
        for field,value in [('official_id','other'),('status','final'),('start_utc','2026-10-25T14:00:00'),('venue_timezone','UTC')]:
            bad=fixture();bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):m.normalize(bad,'EPL','preview','fixture123')
    def test_goals_and_halftime_reconcile(self):
        for field,value in [('final_score',[3,0]),('halftime_score',[0,0])]:
            bad=fixture('recap');bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):m.normalize(bad,'EPL','recap','fixture123')
    def test_added_time_order_does_not_invert_halves(self):
        bad=fixture('recap');bad['goals'][0]['minute']=45;bad['goals'][0]['added']=3
        bad['goals'][1]['minute']=46;bad['goals'][1]['added']=0
        m.normalize(bad,'EPL','recap','fixture123')
    def test_existing_articles_without_summary_unchanged(self):
        self.assertIsNone(m.normalize(None,'EPL','preview','fixture123'))

if __name__=='__main__':unittest.main()
