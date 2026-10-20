#!/usr/bin/env python3
"""Generic fixed-reference English summary SVG. Reuses existing Graphic primitives.

Inputs are reviewed fact packs, never the example match's hard-coded values.
Full statistical tables, recent form and H2H stay in HTML.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_sports_charts import Graphic, TEAL, BLUE, INK, MUTED


class SummaryGraphic(Graphic):
    def font_css(self):
        # Do not distribute local font binaries. Keep measured text within margins.
        return 'text{font-family:"DejaVu Sans",Arial,sans-serif}'


def number(v):
    if type(v) not in (int,float) or not math.isfinite(v) or v < 0:
        raise ValueError('Nonnegative finite observed value required')
    return v


def label(v):
    if not isinstance(v,str) or not v.strip() or len(v)>110 or any(ord(c)>591 for c in v):
        raise ValueError('Short English/Latin functional label required')
    return v


def panel(g,y,title):
    g.rect(40,y,880,42,'#EAF2F6',radius=8)
    g.text(58,y+30,title,size=24,weight=700)
    return y+72


def compare(g,y,row):
    h,a=number(row['home']),number(row['away'])
    scale=number(row.get('scale',100 if row.get('unit')=='%' else max(h,a,1)))
    if not scale or max(h,a)>scale:
        raise ValueError('Comparison axis excludes data')
    title=label(row['label'])
    if row.get('unit'): title += ' ('+label(row['unit'])+')'
    g.block(64,y-20,242,title,size=21,gap=1.15)
    for i,(v,c) in enumerate(((h,TEAL),(a,BLUE))):
        yy=y+6+i*25
        g.rect(320,yy,v/scale*425,16,c,radius=3)
        g.text(780,yy+15,f'{v:g}',size=21,color=c)
    return y+85


def render(pack, template, font):
    e=pack['event'];kind=pack['kind'];data=pack['data']['image_data']
    if template['template_id']!='quickiris-match-summary' or template['language']!='en':
        raise ValueError('Unsupported image contract')
    profile=template['profiles'][e['league']+':'+kind]
    home=label(data.get('home_label',e['home']['name']))
    away=label(data.get('away_label',e['away']['name']))
    metrics=data.get('metrics',[])
    if not 2<=len(metrics)<=8:
        raise ValueError('At least two sourced numeric metric comparisons required')
    facts={'league':e['league'],'translation_group':pack['group'],'sources':pack['sources']}
    g=SummaryGraphic('en',{'title':home+' — '+away,'alt':'Verified match data summary','caption':''},facts,Path(font))
    y=g.header(e['start_utc'][:16].replace('T',' ')+' UTC')
    g.text(64,y,home,size=24,color=TEAL,weight=700)
    g.text(896,y,away,size=24,color=BLUE,anchor='end',weight=700);y+=55
    panels=0
    if kind=='recap':
        hs,aws=number(e['home']['score']),number(e['away']['score'])
        g.text(480,y+10,f'{hs:g} — {aws:g}',size=52,anchor='middle',weight=700);y+=65
    y=panel(g,y,'Match statistics' if kind=='recap' else 'Comparable team metrics')
    for row in metrics: y=compare(g,y,row)
    panels+=1
    if kind=='preview':
        strength=data.get('strength_profile',[])
        if len(strength)<2 or any(not r.get('normalization') for r in strength):
            raise ValueError('Preview needs documented comparable profile scales')
        y=panel(g,y,'Strength profile')
        for row in strength[:5]: y=compare(g,y,row)
        panels+=1
        forecast=data.get('forecast')
        if forecast:
            keys=('home','draw','away') if e['league']=='EPL' else ('home','away')
            vals=[number(forecast[k]) for k in keys]
            if abs(sum(vals)-100)>.11 or not forecast.get('source_id') or not forecast.get('method'):
                raise ValueError('Forecast requires source/method and normalized outcomes')
            y=panel(g,y,'Model estimate · not a result')
            for k,v in zip(keys,vals):
                g.text(64,y,k.title(),size=22);g.rect(230,y-20,v*5.5,24,TEAL if k=='home' else BLUE)
                g.text(815,y,f'{v:g}%',size=23);y+=48
    else:
        incidents=data.get('incidents',[]);phase=data.get('phase',[]);flow=data.get('score_flow',[])
        if not incidents or not phase or len(flow)<2:
            raise ValueError('Recap requires incidents, phase data and observed score progression')
        y=panel(g,y,'Key incidents')
        elapsed=-1
        for row in incidents[:10]:
            minute=number(row['elapsed'])
            if minute<elapsed: raise ValueError('Incident chronology invalid')
            elapsed=minute
            g.text(64,y,f'{minute:g} min',size=23,color=TEAL)
            y=g.block(210,y-23,680,label(row['label']),size=24,gap=1.3)+24
        panels+=1
        y=panel(g,y,label(data.get('phase_title','Verified phase breakdown')))
        for row in phase[:6]: y=compare(g,y,row)
        panels+=1
        y=panel(g,y,'Score progression · checkpoints')
        previous=(-1,0,0)
        for row in flow:
            t,h,a=number(row['elapsed']),number(row['home']),number(row['away'])
            if t<previous[0] or h<previous[1] or a<previous[2]:
                raise ValueError('Score progression not monotone; supply confirmed checkpoints')
            previous=(t,h,a)
        if flow[0]['elapsed']!=0 or flow[0]['home']!=0 or flow[0]['away']!=0 or (previous[1],previous[2])!=(hs,aws):
            raise ValueError('Progression does not reconcile to final score')
        duration=previous[0]
        if duration<=0: raise ValueError('Score progression duration missing')
        ymax=max(hs,aws,1);left,right,top,bottom=105,875,y,y+180
        for i in range(5):
            yy=bottom-i*45;g.line(left,yy,right,yy)
            g.text(80,yy+6,f'{i*ymax/4:g}',size=18,anchor='end')
        for side,color in (('home',TEAL),('away',BLUE)):
            pts=[];old=0
            for row in flow:
                x=left+row['elapsed']/duration*(right-left)
                pts.extend([(x,bottom-old/ymax*180),(x,bottom-row[side]/ymax*180)])
                old=row[side]
            g.elements.append('<polyline points="'+' '.join(f'{x:g},{z:g}' for x,z in pts)+f'" fill="none" stroke="{color}" stroke-width="4"/>')
        for t in (0,duration/2,duration):
            g.text(left+t/duration*(right-left),bottom+30,f'{t:g}',size=19,anchor='middle')
        y=bottom+85;panels+=1
        performers=data.get('performers',[])
        if performers:
            y=panel(g,y,'Scoring and key performers')
            for row in performers[:5]:
                g.text(64,y,label(row['name']),size=24)
                g.text(780,y,f'{number(row["value"]):g} '+label(row['unit']),size=23,
                    color=TEAL if row['team']=='home' else BLUE,anchor='end');y+=46
    if panels<profile['minimum_data_panels']: raise ValueError('Insufficient reference-level information density')
    g.line(64,y,896,y);y+=35
    g.text(64,y,'QuickIris · verified source snapshot',size=20,color=MUTED)
    return g.finish(y+50)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack',required=True);p.add_argument('--template',required=True)
    p.add_argument('--font',default='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf');p.add_argument('--out',required=True)
    a=p.parse_args();pack=json.loads(Path(a.pack).read_text());template=json.loads(Path(a.template).read_text())
    output=render(pack,template,a.font);Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(output)
    print(json.dumps({'asset':a.out,'language':'en','bytes':len(output.encode())}))
if __name__=='__main__': main()
