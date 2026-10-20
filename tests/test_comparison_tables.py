"""SYNTHETIC renderer contracts only; no live sports assertions."""
import copy
import importlib.util
import math
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import comparison_tables as t


def data():
    return {'as_of':'2026-10-20T12:00:00Z','scope':'Synthetic same-match dataset','home':'Blue','away':'Orange',
      'sources':[{'id':'s','title':'Synthetic provider','url':'https://provider.example.test/match','provider':'Test'}],
      'metrics':[{'id':'xg','name':'xG','home':1.3,'away':None,'unit':'goals','category':'expected',
                  'period':'match','definition':'Test model','source_id':'s'},
                 {'id':'psxg_plus_minus','name':'PSxG +/-','home':-.4,'away':.3,'unit':'goals','category':'goalkeeping',
                  'period':'match','definition':'Provider-adjusted conceded goals','source_id':'s'}]}


class TablesTests(unittest.TestCase):
    def test_real_semantic_headers_captions_missing_and_negative_values(self):
        normalized=t.normalize(data(),'EPL','recap','football_statistics')
        for locale in t.UI:
            html=t.render(normalized,locale,'football_statistics')
            self.assertIn('<table ',html);self.assertIn('<caption>',html)
            self.assertIn('scope="col"',html);self.assertIn('scope="row"',html)
            self.assertIn('—',html);self.assertIn('-0.4',html)
            self.assertNotIn('<img',html)

    def test_incompatible_units_percent_and_season_stats_block(self):
        d=data();d['metrics'][0].update(unit='%',home=120)
        with self.assertRaises(ValueError):t.normalize(d,'EPL','recap','football_statistics')
        d=data();d['metrics'][0].update(id='clean_sheet_pct',unit='%',home=100,period='match')
        with self.assertRaises(ValueError):t.normalize(d,'EPL','recap','football_statistics')
        d=data();d['metrics'][0]['home']=float('nan')
        with self.assertRaises(ValueError):t.normalize(d,'EPL','recap','football_statistics')
        with self.assertRaises(ValueError):t.normalize(data(),'NBA','recap','football_statistics')

    def test_credential_urls_and_missing_sources_block(self):
        d=data();d['sources'][0]['url']='https://provider.example.test/match?api_key=secret'
        with self.assertRaises(ValueError):t.normalize(d,'EPL','recap','football_statistics')
        d=data();d['metrics'][0]['source_id']='missing'
        with self.assertRaises(ValueError):t.normalize(d,'EPL','recap','football_statistics')

    def test_provider_text_is_escaped_and_all_missing_rows_omitted(self):
        d=data();d['metrics'][0]['name']='<script>alert(1)</script>'
        out=t.render(t.normalize(d,'EPL','recap','football_statistics'),'en','football_statistics')
        self.assertNotIn('<script>',out);self.assertIn('&lt;script&gt;',out)
        d=data();d['metrics'][0].update(home=None,away=None)
        normalized=t.normalize(d,'EPL','recap','football_statistics')
        self.assertEqual(len(normalized['metrics']),1)

if __name__=='__main__':unittest.main()
