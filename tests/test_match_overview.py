"""Synthetic structured overview contracts; never fixture evidence."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import match_overview as m
spec=importlib.util.spec_from_file_location('overview_site_builder',ROOT/'build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def sample(kind='preview'):
    x={'match_id':'test-123','competition':'Premier League','season':'2026/27','status':'scheduled',
       'home':'Home & One','away':'Away <Two>','venue':'Synthetic Ground','venue_timezone':'Europe/London',
       'start_utc':'2026-10-25T14:00:00Z','as_of':'2026-10-21T00:00:00Z',
       'sources':[{'title':'Synthetic source','url':'https://example.test/fixture'}]}
    if kind=='recap':
        x.update(status='final',start_utc='2026-10-18T13:00:00Z',final_score={'home':2,'away':0},halftime_score={'home':1,'away':0},
                 goals=[{'minute':45,'added':2,'period':1,'scorer':'Opposing Player','team':'home','own_goal':True,'score':{'home':1,'away':0}},
                        {'minute':49,'period':2,'scorer':'Home Player','team':'home','score':{'home':2,'away':0}}])
    return x


class MatchOverviewTests(unittest.TestCase):
    def test_dst_and_korean_date_computed_not_translated_by_model(self):
        x=m.normalize(sample(),'EPL','preview','test-123');out=m.render(x,'ko')
        self.assertIn('2026-10-25 (일) 14:00 GMT',out)
        self.assertIn('2026-10-25 (일) 23:00 KST',out)
        a=sample();a['start_utc']='2026-10-24T16:30:00Z'
        out=m.render(m.normalize(a,'EPL','preview','test-123'),'ko')
        self.assertIn('2026-10-24 (토) 17:30 BST',out)
        self.assertIn('2026-10-25 (일) 01:30 KST',out)

    def test_all_locales_use_semantic_tables_and_escaped_names(self):
        for language in m.LABELS:
            out=m.render(m.normalize(sample(),'EPL','preview','test-123'),language)
            self.assertIn('<table class="qi-match-facts">',out)
            self.assertIn('scope="row"',out);self.assertIn('datetime=',out)
            self.assertIn('Away &lt;Two&gt;',out);self.assertNotIn('Away <Two>',out)
            self.assertNotIn('<img',out)

    def test_score_and_goals_are_visible_with_own_goal_disclosure(self):
        out=m.render(m.normalize(sample('recap'),'EPL','recap','test-123'),'ko')
        self.assertIn('qi-scoreboard',out);self.assertIn('전반',out)
        self.assertIn('자책골',out);self.assertIn('45+2′',out)
        self.assertIn('득점 타임라인',out)

    def test_invalid_identity_lifecycle_and_naive_datetime_block(self):
        for changes in ({'match_id':'wrong'},{'status':'final'},{'start_utc':'2026-10-25T14:00'}, {'venue_timezone':'Asia/Seoul'}, {'venue_timezone':'Wrong/Zone'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):m.normalize({**sample(),**changes},'EPL','preview','test-123')

    def test_future_scores_or_goals_block(self):
        for k,v in [('final_score',{'home':1,'away':0}),('goals',[])]:
            with self.subTest(k=k),self.assertRaises(ValueError):m.normalize({**sample(),k:v},'EPL','preview','test-123')

    def test_halftime_final_and_running_scores_reconcile(self):
        for change in ('final','half','goal','order','bool'):
            x=sample('recap')
            if change=='final':x['final_score']['home']=3
            elif change=='half':x['halftime_score']['home']=2
            elif change=='goal':x['goals'][1]['score']['home']=3
            elif change=='order':x['goals'].reverse()
            elif change=='bool':x['final_score']['home']=True
            with self.subTest(change=change),self.assertRaises(ValueError):m.normalize(x,'EPL','recap','test-123')

    def test_scoreless_match_does_not_fabricate_goals(self):
        x=sample('recap');x.update(final_score={'home':0,'away':0},halftime_score={'home':0,'away':0},goals=[])
        out=m.render(m.normalize(x,'EPL','recap','test-123'),'en')
        self.assertNotIn('qi-goal-table',out);self.assertIn('qi-scoreboard',out)

    def test_source_url_and_empty_venue_block(self):
        for change in ('source','venue'):
            x=sample()
            if change=='source':x['sources'][0]['url']='javascript:alert(1)'
            else:x['venue']=''
            with self.assertRaises(ValueError):m.normalize(x,'EPL','preview','test-123')

    def test_builder_and_blogger_render_overview_without_other_components(self):
        a={'id':'overview-test','slug':'overview-test','platform':'blogger','status':'ready','language':'ko','league':'EPL',
           'match_id':'test-123','article_kind':'preview','translation_group':'overview','title':'Synthetic','description':'Synthetic summary',
           'published_at':'2026-10-21T00:00:00Z','updated_at':'2026-10-21T00:00:00Z',
           'sections':[{'heading':'Lead','paragraphs':['Unique reason to watch.']}], 'sources':[], 'figures':[], 'match_overview':sample()}
        n=b.normalize_article(a,Path('test.json'))
        cfg={'site_title':'Test','site_description':'Test','github_base_url':'https://example.test','blogger_base_url':'https://blog.example.test',
             'adsense_enabled':False,'adsense_client_id':'','language':'en','default_language':'en'}
        body=b.blogger_payload(n,cfg)['content']
        self.assertIn('<style>',body);self.assertIn('.qi-match-facts',body)
        self.assertLess(body.index('Unique reason to watch.'),body.index('class="qi-match-overview"'))
        self.assertIn('한국시간 시작',body)

if __name__=='__main__':unittest.main()
