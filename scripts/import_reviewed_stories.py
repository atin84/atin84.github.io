#!/usr/bin/env python3
"""Supervised publication adapter; no model/API-key calls or invented approvals.

Reuses the site's existing table validator and fixed SVG renderer. Input is
finished, source-reviewed copy plus observed facts. This is not the unattended
private API writer, and never marks its factual/language/rights reviews approved.
"""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import render_summary_image
spec=importlib.util.spec_from_file_location('reviewed_site_builder',ROOT/'build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
LANGS=('en','ko','es','ja','pt-BR','fr','de','hi')
FACTS=ROOT/'data/reviewed/epl-trial-2026-10-20-facts.json'
TEXT=ROOT/'data/reviewed/epl-trial-2026-10-20-text.json'

# Short statistical labels are translated once, never regenerated per fixture.
LABELS={
 'games_played':('Matches played','경기 수','Partidos','試合数','Jogos','Matches','Spiele','मैच'),
 'rank':('League position','리그 순위','Posición','順位','Posição','Classement','Platz','स्थान'),
 'points':('Points','승점','Puntos','勝点','Pontos','Points','Punkte','अंक'),
 'wins':('Wins','승리','Victorias','勝利','Vitórias','Victoires','Siege','जीत'),
 'goals_for':('Goals scored','득점','Goles a favor','得点','Gols marcados','Buts marqués','Tore','किए गोल'),
 'goals_against':('Goals conceded','실점','Goles en contra','失点','Gols sofridos','Buts encaissés','Gegentore','खाए गोल'),
 'goal_assists':('Assists','도움','Asistencias','アシスト','Assistências','Passes décisives','Vorlagen','असिस्ट'),
 'goals_per_game':('Goals per game','경기당 득점','Goles por partido','平均得点','Gols por jogo','Buts par match','Tore pro Spiel','गोल प्रति मैच'),
 'conceded_per_game':('Conceded per game','경기당 실점','Encajados por partido','平均失点','Sofridos por jogo','Encaissés par match','Gegentore pro Spiel','खाए गोल प्रति मैच'),
 'shots':('Shots','슈팅','Remates','シュート','Finalizações','Tirs','Schüsse','शॉट'),
 'shots_on_target':('Shots on target','유효슈팅','Remates a puerta','枠内シュート','No alvo','Tirs cadrés','Torschüsse','निशाने पर शॉट'),
 'possession_pct':('Possession','점유율','Posesión','保持率','Posse','Possession','Ballbesitz','कब्ज़ा'),
 'passes_completed':('Completed passes','성공 패스','Pases completados','成功パス','Passes certos','Passes réussies','Angekommene Pässe','सफल पास'),
 'passes_attempted':('Attempted passes','시도 패스','Pases intentados','試行パス','Passes tentados','Passes tentées','Passversuche','कुल पास'),
 'interceptions':('Interceptions','인터셉트','Intercepciones','インターセプト','Interceptações','Interceptions','Abgefangene Bälle','इंटरसेप्शन'),
 'fouls':('Fouls','파울','Faltas','ファウル','Faltas','Fautes','Fouls','फाउल'),
 'yellow_cards':('Yellow cards','경고','Amarillas','警告','Amarelos','Cartons jaunes','Gelbe Karten','पीले कार्ड'),
 'saves':('Saves','선방','Paradas','セーブ','Defesas','Arrêts','Paraden','सेव'),
 'pass_completion_pct':('Pass completion','패스 성공률','Precisión de pase','パス成功率','Acerto de passe','Réussite des passes','Passquote','पास सफलता'),
 'long_pass_completion_pct':('Long pass completion','긴 패스 성공률','Pase largo completado','ロングパス成功率','Acerto de passe longo','Réussite des passes longues','Lange Passquote','लंबे पास सफलता'),
 'tackles_won_pct':('Successful tackles / attempts','성공 태클 / 시도','Entradas exitosas / intentos','成功タックル / 試行','Desarmes certos / tentativas','Tacles réussis / tentés','Erfolgreiche Tacklings / Versuche','सफल टैकल / प्रयास'),
 'save_pct':('Save percentage','선방률','Porcentaje de paradas','セーブ率','Taxa de defesas','Taux d’arrêts','Paradenquote','सेव प्रतिशत')}
SCOPES={
 'recent':('Premier League only · latest 5 results; H2H 2024–2026','리그 최근 5경기 · 맞대결 2024–2026','Solo Premier League · últimos 5; duelos 2024–2026','リーグ直近5試合・直接対決2024–2026','Só Premier League · últimos 5; duelos 2024–2026','Premier League seulement · 5 derniers; duels 2024–2026','Nur Premier League · letzte 5; Duelle 2024–2026','केवल लीग · पिछले 5; आमने-सामने 2024–2026'),
 'season':('2026/27 Premier League · 7 matches per team','2026/27 프리미어리그 · 양팀 각 7경기','Premier League 2026/27 · 7 por equipo','2026/27リーグ・各7試合','Premier League 2026/27 · 7 por equipe','Premier League 2026/27 · 7 par équipe','Premier League 2026/27 · je 7 Spiele','2026/27 लीग · प्रत्येक टीम के 7 मैच'),
 'match':('Full match · observed counts and derived rates','전체 경기 · 관측 횟수와 계산한 비율','Partido completo · recuentos y tasas calculadas','試合全体・観測回数と計算率','Jogo completo · contagens e taxas calculadas','Match entier · décomptes et taux calculés','Gesamtes Spiel · Zählwerte und berechnete Quoten','पूरा मैच · वास्तविक गिनती और गणना दर')}
METHOD=('Provider definitions apply; calculated rates are not model predictions.','공급자 정의를 따릅니다. 계산한 비율은 예측 모델이 아닙니다.','Se aplica la definición del proveedor; las tasas no son pronósticos.','提供元の定義に従います。計算率は予測ではありません。','Vale a definição do fornecedor; taxas não são previsões.','Définition du fournisseur ; taux calculés, pas de prédictions.','Anbieterdefinition; berechnete Quoten sind keine Prognosen.','प्रदाता की परिभाषा लागू; गणना दर भविष्यवाणी नहीं है।')
TEMPLATE={'template_id':'quickiris-match-summary','language':'en','profiles':{'EPL:preview':{'minimum_data_panels':2},'EPL:recap':{'minimum_data_panels':4}}}


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(data): return hashlib.sha256(data).hexdigest()
def revision():
    return sha(FACTS.read_bytes()+TEXT.read_bytes()+Path(__file__).read_bytes()+(ROOT/'scripts/render_summary_image.py').read_bytes()+(ROOT/'scripts/comparison_tables.py').read_bytes()+(ROOT/'assets/style.css').read_bytes())
def instant(value): return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'QuickIris-Reviewed-Release/1','Accept':'application/json'}),timeout=20) as r:
        body=r.read(3_000_001)
        if len(body)>3_000_000: raise ValueError('Source response exceeds bound')
        return json.loads(body)


def preflight(facts):
    """Known source identity check plus complete public Blogger feed, not AUTHOR access."""
    existing=[load(p) for p in (ROOT/'content').glob('*.json')]
    for kind in ('preview','recap'):
        g=facts[kind]
        for a in existing:
            if a.get('league')=='EPL' and str(a.get('match_id'))==g['official_id'] and a.get('article_kind')==kind:
                if a.get('translation_group')!=g['id']:
                    raise ValueError('Existing different story already owns this match/kind')
        p=fetch('https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event='+g['provider_id'])
        h=p['header'];c=h['competitions'][0];state=c['status']['type']
        if h['id']!=g['provider_id'] or instant(c['date'])!=instant(g['start_utc']): raise ValueError('Fixture ID/start changed')
        if kind=='preview' and (state['state']!='pre' or instant(g['start_utc'])<=datetime.now(timezone.utc)): raise ValueError('Preview no longer upcoming')
        if kind=='recap':
            sides={x['homeAway']:x for x in c['competitors']}
            if state.get('completed') is not True or [int(sides[s]['score']) for s in ('home','away')]!=g['final_score']:
                raise ValueError('Final result changed')
    feed=fetch('https://quickiris.blogspot.com/feeds/posts/default?alt=json&max-results=150')['feed']
    entries=feed.get('entry',[])
    if int(feed['openSearch$totalResults']['$t'])!=len(entries):raise ValueError('Incomplete public Blogger inventory')
    for e in entries:
        body=e.get('content',{}).get('$t','')
        if any('/posts/'+facts[k]['id']+'-' in body for k in ('preview','recap')):
            raise ValueError('Blogger already references candidate group; reconcile before creating')
    return {'public_blogger_entries':len(entries),'fixture_refresh':'passed','author_inventory':False}


def components(facts,kind,locale):
    g=facts[kind];li=LANGS.index(locale);sources=facts['sources'];asof=facts['as_of']
    def src(k):return {'id':k,'provider':'ESPN',**sources[k]}
    def table(rows,scope,sid):
        return {'as_of':asof,'scope':SCOPES[scope][li],'home':g['home'],'away':g['away'],'sources':[src(sid)],'metrics':rows}
    def row(id,name,unit,h,a,category,sid,formula=''):
        return {'id':id,'name':LABELS.get(id,(name,)*8)[li],'unit':unit,'home':h,'away':a,'category':category,'period':SCOPES['season' if kind=='preview' else 'match'][li],'definition':METHOD[li]+(' '+formula if formula else ''),'source_id':sid}
    if kind=='preview':
        pairs={r[0]:(r[3],r[4]) for r in g['season_rows']};rows=[row(*r,'strength','pre_stats') for r in g['season_rows']]
        gp=pairs['games_played'];gf=pairs['goals_for'];ga=pairs['goals_against']
        attack=[round(gf[i]/gp[i],2) for i in (0,1)];defense=[round(ga[i]/gp[i],2) for i in (0,1)]
        rows += [row('goals_per_game','Goals per game','/match',*attack,'strength','pre_stats','GF / GP'),row('conceded_per_game','Conceded per game','/match',*defense,'strength','pre_stats','GA / GP')]
        comparison={'as_of':asof,'scope':SCOPES['recent'][li],'sources':{'recent':sources['pre_stats'],'head_to_head':sources['h2h1']},'home':{'name':g['home'],'recent':[]},'away':{'name':g['away'],'recent':[]},'head_to_head':[]}
        for side in ('home','away'):
            comparison[side]['recent']=[dict(zip(('date','opponent','for','against'),r[:4])) for r in g['recent_'+side]]
        comparison['head_to_head']=[dict(zip(('date','home_team','away_team','home_score','away_score'),r[:5])) for r in g['head_to_head']]
        image={'metrics':[{'label':name,'unit':unit,'home':h,'away':a} for id,name,unit,h,a in g['season_rows'] if id in ('points','goals_for','goals_against','goal_assists')], 'strength_profile':[{'label':'Goals per game','unit':'goals/game','home':attack[0],'away':attack[1],'scale':3,'normalization':'Total / 7; shared axis 0–3; not a rating'},{'label':'Conceded per game','unit':'goals/game','home':defense[0],'away':defense[1],'scale':3,'normalization':'Total / 7; lower is better; shared axis 0–3'}]}
        return {'preview_comparison':comparison,'official_comparison':table(rows,'season','pre_stats')},image
    v=g['observed'];ratio=lambda n,d:[round(v[n][i]/v[d][i]*100,2) for i in (0,1)]
    p=ratio('accuratePasses','totalPasses');l=ratio('accurateLongBalls','totalLongBalls');t=ratio('effectiveTackles','totalTackles')
    rows=[]
    for id,name,unit,key,cat in [('shots','Shots','#','totalShots','creation'),('shots_on_target','Shots on target','#','shotsOnTarget','creation'),('possession_pct','Possession','%','possessionPct','passing'),('passes_completed','Completed passes','#','accuratePasses','passing'),('passes_attempted','Attempted passes','#','totalPasses','passing'),('interceptions','Interceptions','#','interceptions','defensive'),('fouls','Fouls','#','foulsCommitted','defensive'),('yellow_cards','Yellow cards','#','yellowCards','defensive'),('saves','Saves','#','saves','goalkeeping')]:rows.append(row(id,name,unit,*v[key],cat,'rec_stats'))
    rows += [row('pass_completion_pct','Pass completion','%',*p,'passing','rec_stats','499/559; 222/287 × 100'),row('long_pass_completion_pct','Long pass completion','%',*l,'passing','rec_stats','10/27; 30/62 × 100'),row('tackles_won_pct','Tackle success','%',*t,'defensive','rec_stats','8/13; 7/17 × 100'),row('save_pct','Save percentage','%',0,40,'goalkeeping','rec_stats','0/1; 2/5 × 100')]
    goals=g['goals'];ht=g['halftime_score'];ft=g['final_score']
    image={'metrics':[{'label':'Possession','unit':'%','home':65.4,'away':34.6},{'label':'Shots','unit':'count','home':16,'away':12},{'label':'Shots on target','unit':'count','home':5,'away':1},{'label':'Pass completion','unit':'%','home':p[0],'away':p[1]}],
      'incidents':[{'elapsed':r[0],'label':r[2]+' · '+str(r[4])+'-'+str(r[5])+(' (90+6)' if r[0]==96 else '')} for r in goals],
      'phase_title':'Goals by half · not xG','phase':[{'label':'First half','unit':'goals','home':ht[0],'away':ht[1]},{'label':'Second half','unit':'goals','home':ft[0]-ht[0],'away':ft[1]-ht[1]}],
      'score_flow':[{'elapsed':0,'home':0,'away':0}]+[{'elapsed':r[0],'home':r[4],'away':r[5]} for r in goals]+[{'elapsed':g['final_minute'],'home':ft[0],'away':ft[1]}],
      'performers':[{'name':r[2],'team':r[3],'value':1,'unit':'goal'} for r in goals]}
    return {'football_statistics':table(rows,'match','rec_stats')},image


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--refresh',action='store_true');a=p.parse_args()
    facts=load(FACTS);text=load(TEXT);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if set(text['preview'])!=set(LANGS) or set(text['recap'])!=set(LANGS):raise ValueError('Exactly eight locales required')
    proof=preflight(facts) if a.refresh else {'fixture_refresh':'not_run'}
    rev=revision();now=datetime.now(timezone.utc).isoformat();names=[];image_paths=[];urls=[]
    for kind in ('preview','recap'):
        g=facts[kind];expected='epl-'+g['official_id']+'-'+kind
        if g['id']!=expected:raise ValueError('Group identity mismatch')
        event={'league':'EPL','start_utc':g['start_utc'],'home':{'name':g['home']},'away':{'name':g['away']}}
        if kind=='recap':event['home']['score'],event['away']['score']=g['final_score']
        _,image=components(facts,kind,'en')
        source=[facts['sources'][k] for k in g['source_ids']]
        pack={'event':event,'kind':kind,'group':g['id'],'sources':source,'data':{'image_data':image}}
        svg=render_summary_image.render(pack,TEMPLATE,'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        img='assets/charts/'+g['id']+'-summary-en.svg';(ROOT/img).write_text(svg,encoding='utf-8');image_paths.append(img)
        for locale in LANGS:
            copy_=text[kind][locale];tables,_=components(facts,kind,locale)
            if len(copy_['sections'])!=(10 if kind=='preview' else 8):raise ValueError('Incomplete reviewed article sections')
            id=g['id']+'-'+locale.lower();oldpath=ROOT/'content'/(id+'.json')
            old=load(oldpath) if oldpath.exists() else None
            if old and old.get('quickiris_revision')!=rev:raise ValueError('Existing source needs explicit correction workflow')
            article={'id':id,'slug':id,'platform':'github','status':'ready','language':locale,'league':'EPL','match_id':g['official_id'],'article_kind':kind,'translation_group':g['id'],'canonical_group':'EPL:2026-27:league:'+g['official_id']+':'+kind,'quickiris_revision':rev,'title':copy_['title'],'description':copy_['description'],'published_at':old.get('published_at',now) if old else now,'updated_at':old.get('updated_at',now) if old else now,'labels':['EPL',kind],
              'sections':[{'heading':s[0],'paragraphs':s[1:]} for s in copy_['sections']], 'sources':source,
              'figures':[{'src':'https://atin84.github.io/'+img,'alt':copy_['alt'],'caption':copy_['caption']}],**tables}
            builder.normalize_article(article,Path(id+'.json'))
            oldpath.write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');names.append('content/'+id+'.json');urls.append('https://atin84.github.io/posts/'+id+'/')
    report={'revision':rev,'articles':names,'images':image_paths,'urls':urls,'image_hashes':{p:sha((ROOT/p).read_bytes()) for p in image_paths},'preflight':proof,'mode':'supervised_source_reviewed_release','model_api_calls':0}
    (out/'release-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'articles':len(names),'images':len(image_paths),'revision':rev,'preflight':proof,'model_api_calls':0}))
if __name__=='__main__':main()
