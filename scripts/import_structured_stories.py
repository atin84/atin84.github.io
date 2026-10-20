#!/usr/bin/env python3
"""Expand reviewed multilingual copy and observed facts; no model/API-key calls.

Use generic match-summary/table/SVG renderers. Never overwrite a different
published revision. Source checks are supervised, not automatic fact approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import import_reviewed_stories as base
import render_summary_image
builder=base.builder
LANGS=base.LANGS
TEMPLATE={'template_id':'quickiris-match-summary','language':'en','profiles':{'EPL:preview':{'minimum_data_panels':2},'EPL:recap':{'minimum_data_panels':4}}}


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def moment(raw):
    d=datetime.fromisoformat(raw.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Offset-aware source time required')
    return d.astimezone(timezone.utc)
def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'QuickIris-Reviewed-Release/2','Accept':'application/json'}),timeout=20) as r:
        raw=r.read(3_000_001)
        if len(raw)>3_000_000:raise ValueError('Source response exceeds limit')
        return json.loads(raw)


def preflight(facts,revision):
    existing=[load(p) for p in (ROOT/'content').glob('*.json')]
    checks=[]
    for kind,g in facts['stories'].items():
        for a in existing:
            if a.get('league')=='EPL' and str(a.get('match_id'))==g['official_id'] and a.get('article_kind')==kind:
                if a.get('translation_group')!=g['id'] or a.get('quickiris_revision')!=revision:
                    raise ValueError('Existing article reserves identity; use explicit correction')
        url='https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event='+g['provider_id']
        p=fetch(url);h=p['header'];c=h['competitions'][0];state=c['status']['type']
        sides={x['homeAway']:x for x in c['competitors']}
        if str(h['id'])!=g['provider_id'] or moment(c['date'])!=moment(g['start_utc']):raise ValueError('Fixture ID/time changed')
        for side in ('home','away'):
            if sides[side]['team']['displayName']!=g[side]:raise ValueError('Fixture team identity changed')
        if kind=='preview' and (state['state']!='pre' or moment(g['start_utc'])<=datetime.now(timezone.utc)):
            raise ValueError('Preview no longer upcoming')
        if kind=='recap' and (state.get('completed') is not True or [int(sides[s]['score']) for s in ('home','away')]!=g['final_score']):
            raise ValueError('Final score changed')
        checks.append({'group':g['id'],'provider_id':g['provider_id'],'status':g['status'],'fixture_checked':True})
    feed=fetch('https://quickiris.blogspot.com/feeds/posts/default?alt=json&max-results=150')['feed']
    entries=feed.get('entry',[])
    if int(feed['openSearch$totalResults']['$t'])!=len(entries):raise ValueError('Incomplete public Blogger feed')
    for entry in entries:
        body=entry.get('content',{}).get('$t','')
        if any('/posts/'+g['id']+'-' in body for g in facts['stories'].values()):
            raise ValueError('Candidate is referenced by Blogger; reconcile before creating')
    return {'fixtures':checks,'public_blogger_entries':len(entries),'author_inventory':False}


def components(facts,kind,locale):
    g=facts['stories'][kind];li=LANGS.index(locale);sources=facts['sources']
    def metric(id,name,unit,h,a,category,source,formula=''):
        return {'id':id,'name':base.LABELS.get(id,(name,)*8)[li],'unit':unit,'home':h,'away':a,
            'category':category,'period':base.SCOPES['season' if kind=='preview' else 'match'][li],
            'definition':base.METHOD[li]+(' '+formula if formula else ''),'source_id':source}
    def table(rows,scope,source):
        return {'as_of':g['as_of'],'scope':base.SCOPES[scope][li],'home':g['home'],'away':g['away'],
            'sources':[{'id':source,'provider':'ESPN',**sources[source]}],'metrics':rows}
    summary={k:g[k] for k in ('official_id','status','home','away','venue','season','start_utc','matchweek')}
    summary.update(competition='Premier League',venue_timezone='Europe/London',verified_at=g['as_of'],
        sources=[sources['fixture' if kind=='preview' else 'rec_fixture'],sources['kickoff' if kind=='preview' else 'palace_report']])
    if kind=='preview':
        totals={r[0]:(r[3],r[4]) for r in g['season_rows']}
        rows=[metric(*r,'strength','pre_stats') for r in g['season_rows']]
        gp=totals['games_played'];gf=totals['goals_for'];ga=totals['goals_against']
        attack=[round(gf[i]/gp[i],2) for i in (0,1)];defense=[round(ga[i]/gp[i],2) for i in (0,1)]
        rows += [metric('goals_per_game','Goals per game','/match',*attack,'strength','pre_stats','GF / GP'),
                 metric('conceded_per_game','Conceded per game','/match',*defense,'strength','pre_stats','GA / GP')]
        comparison={'as_of':g['as_of'],'scope':('Premier League only; latest five results and league H2H' if locale=='en' else base.SCOPES['recent'][li]),
            'sources':{'recent':sources['pre_stats'],'head_to_head':sources['pre_stats']},'head_to_head':[]}
        for side in ('home','away'):
            comparison[side]={'name':g[side],'recent':[dict(zip(('date','opponent','for','against'),r[:4])) for r in g['recent_'+side]]}
        comparison['head_to_head']=[dict(zip(('date','home_team','away_team','home_score','away_score'),r[:5])) for r in g['head_to_head']]
        image={'metrics':[{'label':name,'unit':unit,'home':h,'away':a} for id,name,unit,h,a in g['season_rows'] if id in ('points','goals_for','goals_against','goal_assists')],
            'strength_profile':[{'label':'Goals per game','unit':'goals/game','home':attack[0],'away':attack[1],'scale':max(1,math.ceil(max(attack))),
                 'normalization':'Observed total / games played; shared axis, not a rating'},
                {'label':'Conceded per game','unit':'goals/game','home':defense[0],'away':defense[1],'scale':max(1,math.ceil(max(defense))),
                 'normalization':'Observed total / games played; lower is better'}]}
        return {'match_summary':summary,'preview_comparison':comparison,'official_comparison':table(rows,'season','pre_stats')},image
    summary.update(final_score=g['final_score'],halftime_score=g['halftime_score'],goals=g['goals'])
    v=g['observed'];pass_rate=[round(v['accuratePasses'][i]/v['totalPasses'][i]*100,2) for i in (0,1)]
    rows=[]
    for id,name,unit,key,category in [('shots','Shots','#','totalShots','creation'),('shots_on_target','Shots on target','#','shotsOnTarget','creation'),
        ('possession_pct','Possession','%','possessionPct','passing'),('passes_completed','Completed passes','#','accuratePasses','passing'),
        ('passes_attempted','Attempted passes','#','totalPasses','passing'),('interceptions','Interceptions','#','interceptions','defensive'),
        ('fouls','Fouls','#','foulsCommitted','defensive'),('yellow_cards','Yellow cards','#','yellowCards','defensive'),('saves','Saves','#','saves','goalkeeping')]:
        rows.append(metric(id,name,unit,*v[key],category,'rec_stats'))
    rows.append(metric('pass_completion_pct','Pass completion','%',*pass_rate,'passing','rec_stats','Completed / attempted × 100'))
    # Own goals make naive goals-plus-saves denominators unsafe; do not invent save%.
    image={'metrics':[{'label':label,'unit':unit,'home':values[0],'away':values[1]} for label,unit,values in
          [('Possession','%',v['possessionPct']),('Shots','count',v['totalShots']),('Shots on target','count',v['shotsOnTarget']),('Pass completion','%',pass_rate)]],
        'incidents':[{'elapsed':r['minute']+r.get('added',0),'label':r['player']+(' (own goal)' if r.get('own_goal') else '')+' · '+'-'.join(map(str,r['score']))} for r in g['goals']],
        'phase_title':'Goals by half · not xG','phase':[
            {'label':'First half','unit':'goals','home':g['halftime_score'][0],'away':g['halftime_score'][1]},
            {'label':'Second half','unit':'goals','home':g['final_score'][0]-g['halftime_score'][0],'away':g['final_score'][1]-g['halftime_score'][1]}],
        'score_flow':[{'elapsed':0,'home':0,'away':0}]+[{'elapsed':r['minute']+r.get('added',0),'home':r['score'][0],'away':r['score'][1]} for r in g['goals']]+[{'elapsed':g['final_minute'],'home':g['final_score'][0],'away':g['final_score'][1]}],
        'performers':[{'name':r['player'],'team':r['team'],'value':1,'unit':'goal'} for r in g['goals'] if not r.get('own_goal')]}
    return {'match_summary':summary,'football_statistics':table(rows,'match','rec_stats')},image


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--facts',required=True);p.add_argument('--text',required=True);p.add_argument('--out',required=True);p.add_argument('--refresh',action='store_true');args=p.parse_args()
    facts=load(args.facts);copy=load(args.text);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    inputs=[Path(args.facts),Path(args.text),Path(__file__),ROOT/'scripts/match_summary.py',ROOT/'scripts/render_summary_image.py',ROOT/'scripts/comparison_tables.py',ROOT/'assets/style.css',ROOT/'build.py']
    revision=sha(b''.join(p.read_bytes() for p in inputs));now=datetime.now(timezone.utc).isoformat()
    proof=preflight(facts,revision) if args.refresh else {'fixture_refresh':'not_run'}
    names=[];images=[];urls=[]
    for kind,g in facts['stories'].items():
        if set(copy[kind])!=set(LANGS):raise ValueError('Exactly eight locales required')
        event={'league':'EPL','start_utc':g['start_utc'],'home':{'name':g['home']},'away':{'name':g['away']}}
        if kind=='recap':event['home']['score'],event['away']['score']=g['final_score']
        source=[facts['sources'][k] for k in g['source_ids']]
        _,data=components(facts,kind,'en')
        pack={'event':event,'kind':kind,'group':g['id'],'sources':source,'data':{'image_data':data}}
        svg=render_summary_image.render(pack,TEMPLATE,'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        image='assets/charts/'+g['id']+'-summary-en.svg';(ROOT/image).write_text(svg,encoding='utf-8');images.append(image)
        for locale in LANGS:
            text=copy[kind][locale];tables,_=components(facts,kind,locale)
            id=g['id']+'-'+locale.lower();path=ROOT/'content'/(id+'.json');old=load(path) if path.exists() else None
            if old and old.get('quickiris_revision')!=revision:raise ValueError('Existing different article revision must not be overwritten')
            article={'id':id,'slug':id,'platform':'github','status':'ready','language':locale,'league':'EPL','match_id':g['official_id'],
                'article_kind':kind,'translation_group':g['id'],'canonical_group':'EPL:2026-27:league:'+g['official_id']+':'+kind,
                'quickiris_revision':revision,'title':text['title'],'description':text['description'],'published_at':old['published_at'] if old else now,
                'updated_at':old['updated_at'] if old else now,'labels':['EPL',kind],'sections':text['sections'],'sources':source,
                'figures':[{'src':'https://atin84.github.io/'+image,'alt':text['alt'],'caption':text['caption']}],**tables}
            builder.normalize_article(article,Path(id+'.json'))
            path.write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');names.append('content/'+id+'.json');urls.append('https://atin84.github.io/posts/'+id+'/')
    result={'revision':revision,'articles':names,'images':images,'urls':urls,'image_hashes':{p:sha((ROOT/p).read_bytes()) for p in images},
        'preflight':proof,'mode':'supervised-structured-publication','model_api_calls':0}
    (out/'release-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'articles':len(names),'images':len(images),'revision':revision,'preflight':proof,'model_api_calls':0}))
if __name__=='__main__':main()
