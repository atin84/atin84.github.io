#!/usr/bin/env python3
"""Render a source-reviewed multilingual batch through existing site components.

No model, translation or approval synthesis. Public release is a separate explicit
revision-bound workflow step. Existing identities are never overwritten implicitly.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import render_summary_image
from import_reviewed_stories import LABELS, METHOD
spec=importlib.util.spec_from_file_location('batch_site_builder',ROOT/'build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
LANGS=('en','ko','es','ja','pt-BR','fr','de','hi')
LABELS={**LABELS,'corners':('Corners','코너킥','Córners','コーナー','Escanteios','Corners','Ecken','कॉर्नर')}
SCOPES={
 'season':('2026/27 Premier League · 7 completed matches each','2026/27 프리미어리그 · 양팀 각 7경기','Premier League 2026/27 · 7 partidos por equipo','2026/27リーグ・各7試合','Premier League 2026/27 · 7 jogos por equipe','Premier League 2026/27 · 7 matches par équipe','Premier League 2026/27 · je 7 Spiele','2026/27 लीग · प्रत्येक टीम के 7 मैच'),
 'recent':('Last 5 league results · 4 verified league H2H meetings','리그 최근 5경기 · 검증된 리그 맞대결 4경기','Últimos 5 de liga · 4 duelos ligueros verificados','リーグ直近5試合・確認済み直接対決4試合','Últimos 5 da liga · 4 confrontos verificados','5 derniers matches de ligue · 4 duels vérifiés','Letzte 5 Ligaspiele · 4 bestätigte Ligaduelle','पिछले 5 लीग मैच · 4 सत्यापित लीग मुकाबले'),
 'match':('Full match · observed counts and calculated rates','전체 경기 · 관측 횟수와 계산한 비율','Partido completo · recuentos y tasas calculadas','試合全体・観測回数と計算率','Jogo completo · contagens e taxas calculadas','Match entier · décomptes et taux calculés','Gesamtes Spiel · Zählwerte und berechnete Quoten','पूरा मैच · वास्तविक गिनती और गणना दर')}
TEMPLATE={'template_id':'quickiris-match-summary','language':'en',
 'profiles':{'EPL:preview':{'minimum_data_panels':2},'EPL:recap':{'minimum_data_panels':4}}}


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def digest(data): return hashlib.sha256(data).hexdigest()
def instant(raw):
    value=datetime.fromisoformat(raw.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('Offset-aware timestamp required')
    return value.astimezone(timezone.utc)


def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'QuickIris-Reviewed-Batch/2','Accept':'application/json'}),timeout=20) as response:
        body=response.read(4_000_001)
        if len(body)>4_000_000:raise ValueError('Source exceeds read bound')
        return json.loads(body)


def revision(input_path):
    paths=[Path(input_path),Path(__file__),ROOT/'build.py',ROOT/'assets/style.css',
           ROOT/'scripts/match_overview.py',ROOT/'scripts/reader_timezones.py',ROOT/'scripts/comparison_tables.py',
           ROOT/'scripts/render_summary_image.py',ROOT/'scripts/import_reviewed_stories.py']
    return digest(b''.join(p.read_bytes() for p in paths))


def check_remote(batch):
    """Public source/feed duplicate check plus fresh secondary fixture observations.

    Official sources are independently reviewed and linked in the batch; this
    ESPN read does not pretend to be an official league API or AUTHOR inventory.
    """
    feed=fetch('https://quickiris.blogspot.com/feeds/posts/default?alt=json&max-results=150')['feed']
    posts=feed.get('entry',[])
    if int(feed['openSearch$totalResults']['$t'])!=len(posts):raise ValueError('Incomplete public Blogger inventory')
    known=[load(p) for p in (ROOT/'content').glob('*.json')]
    for g in batch['groups']:
        for a in known:
            if (a.get('league')==g['league'] and str(a.get('match_id'))==g['match_id'] and a.get('article_kind')==g['kind']
                and a.get('translation_group')!=g['group']):raise ValueError('Another source group owns this fixture/kind')
        for p in posts:
            body=p.get('content',{}).get('$t','')
            if '/posts/'+g['group']+'-' in body:raise ValueError('Blogger references this group; reconcile before creating')
        if not re.fullmatch(r'\d+',g['provider_id']):raise ValueError('Invalid provider identity')
        data=fetch('https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event='+g['provider_id'])
        header=data['header'];event=header['competitions'][0];sides={r['homeAway']:r for r in event['competitors']}
        if str(header['id'])!=g['provider_id'] or instant(event['date'])!=instant(g['overview']['start_utc']):raise ValueError('Fixture ID/time changed')
        if any(sides[s]['team']['displayName']!=g[s] for s in ('home','away')):raise ValueError('Provider team identity changed')
        state=event['status']['type']
        if g['kind']=='preview':
            if state['state']!='pre' or instant(event['date'])<=datetime.now(timezone.utc):raise ValueError('Preview is not upcoming')
        elif state.get('completed') is not True or any(int(sides[s]['score'])!=g['overview']['final_score'][s] for s in ('home','away')):
            raise ValueError('Final result changed')
    return {'fixture_refresh':'passed_secondary_provider','official_sources':'independently_reviewed_linked_sources',
            'public_blogger_entries':len(posts),'author_inventory':False,'checked_at':datetime.now(timezone.utc).isoformat()}


def localize_tables(g,locale):
    idx=LANGS.index(locale);out={}
    if 'preview_comparison' in g:
        c=copy.deepcopy(g['preview_comparison'])
        samples=[len(c[side]['recent']) for side in ('home','away')]
        scope=SCOPES['recent'][idx].replace('5',str(samples[0]) if samples[0]==samples[1] else str(samples[0])+'/'+str(samples[1])).replace('4',str(len(c['head_to_head'])))
        c['scope']=g.get('recent_scope',{}).get(locale,scope);out['preview_comparison']=c
    for field in ('official_comparison','football_statistics'):
        if field not in g:continue
        c=copy.deepcopy(g[field]);c['scope']=SCOPES['season' if field=='official_comparison' else 'match'][idx]
        if field=='official_comparison':
            sample=next((r for r in c['metrics'] if r['id']=='games_played'),None)
            if not sample:raise ValueError('Comparable season data requires played-game denominators')
            n=str(sample['home']) if sample['home']==sample['away'] else str(sample['home'])+'/'+str(sample['away'])
            c['scope']=c['scope'].replace('7 ',n+' ').replace('7경기',n+'경기').replace('7試合',n+'試合').replace('2026/27',g['season'].replace('-','/'))
        for r in c['metrics']:
            r['name']=LABELS.get(r['id'],(r['name'],)*8)[idx]
            r['definition']=METHOD[idx]+' '+r['definition']
            if locale!='en':r['period']=c['scope']
            if r['unit'] in ('count','games','goals','points','rank'):
                r['unit']={'ko':{'count':'회','games':'경기','goals':'골','points':'점','rank':'위'},
                           'ja':{'count':'回','games':'試合','goals':'得点','points':'点','rank':'位'}}.get(locale,{}).get(r['unit'],r['unit'])
        out[field]=c
    return out


def render(input_path,out,refresh=False):
    batch=load(input_path);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if not 1<=len(batch['groups'])<=2:raise ValueError('Bounded review batch must contain 1..2 groups')
    if len({g['group'] for g in batch['groups']})!=len(batch['groups']):raise ValueError('Duplicate batch group')
    proof=check_remote(batch) if refresh else {'fixture_refresh':'not_run_local_validation'}
    rev=revision(input_path);now=datetime.now(timezone.utc).isoformat();names=[];images=[];urls=[]
    for g in batch['groups']:
        expected='epl-'+g['match_id']+'-'+g['kind']
        if g['league']!='EPL' or g['group']!=expected or set(g['copy'])!=set(LANGS):raise ValueError('Group/locale identity invalid')
        overview=g['overview'];builder._overview.normalize(overview,g['league'],g['kind'],g['match_id'])
        event={'league':g['league'],'start_utc':overview['start_utc'],'home':{'name':g['home']},'away':{'name':g['away']}}
        if g['kind']=='recap':
            for side in ('home','away'):event[side]['score']=overview['final_score'][side]
        pack={'event':event,'kind':g['kind'],'group':g['group'],'sources':g['sources'],'data':{'image_data':g['image_data']}}
        svg=render_summary_image.render(pack,TEMPLATE,'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        image_path='assets/charts/'+g['group']+'-summary-en.svg'
        target=ROOT/image_path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(svg,encoding='utf-8');images.append(image_path)
        for locale in LANGS:
            text=g['copy'][locale];article_id=g['group']+'-'+locale.lower();path=ROOT/'content'/(article_id+'.json')
            old=load(path) if path.exists() else None
            if old and old.get('quickiris_revision')!=rev:raise ValueError('Existing content requires an explicit correction release')
            article={'id':article_id,'slug':article_id,'platform':'github','status':'ready','language':locale,
                'league':g['league'],'match_id':g['match_id'],'article_kind':g['kind'],'translation_group':g['group'],
                'canonical_group':':'.join((g['league'],g['season'],'league',g['match_id'],g['kind'])),
                'quickiris_revision':rev,'title':text['title'],'description':text['description'],
                'published_at':old['published_at'] if old else now,'updated_at':old['updated_at'] if old else now,
                'labels':[g['league'],g['kind']],'sections':text['sections'],'sources':g['sources'],
                'match_overview':overview,'figures':[{'src':'https://atin84.github.io/'+image_path,'alt':text['alt'],'caption':text['caption']}],
                **localize_tables(g,locale)}
            builder.normalize_article(article,path)
            path.write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            names.append('content/'+path.name);urls.append('https://atin84.github.io/posts/'+article_id+'/')
    result={'batch_id':batch['batch_id'],'revision':rev,'articles':names,'images':images,'urls':urls,
        'image_hashes':{p:digest((ROOT/p).read_bytes()) for p in images},'preflight':proof,
        'mode':'supervised_source_reviewed_release','model_api_calls':0}
    (out/'release-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--refresh',action='store_true')
    a=p.parse_args();r=render(a.input,a.out,a.refresh)
    print(json.dumps({'articles':len(r['articles']),'images':len(r['images']),'revision':r['revision'],'preflight':r['preflight'],'model_api_calls':0}))
if __name__=='__main__':main()
