#!/usr/bin/env python3
"""Deterministic, localized dashboards from published match facts.

Run with --font-cjk PATH --font-hi PATH. No scraping or model calls.
The Poisson baseline is intentionally uncalibrated and fully reproducible.
"""
import argparse, json, math
from pathlib import Path
from render_sports_charts import Graphic, TEAL, BLUE, GOLD, INK, MUTED
ROOT=Path(__file__).resolve().parents[1]

def poisson(home,away):
    lh=(home['gf']/6+away['ga']/6)/2
    la=(away['gf']/6+home['ga']/6)/2
    p=lambda k,l: math.exp(-l)*l**k/math.factorial(k)
    out=[0.,0.,0.]
    for i in range(21):
        for j in range(21): out[0 if i>j else 1 if i==j else 2]+=p(i,lh)*p(j,la)
    total=sum(out); raw=[v/total*1000 for v in out]; ints=[int(v) for v in raw]
    for i in sorted(range(3),key=lambda i:raw[i]-ints[i],reverse=True)[:1000-sum(ints)]: ints[i]+=1
    return [v/10 for v in ints], [lh,la]

def panel(g,y,title):
    g.rect(40,y,880,42,'#EAF2F6',radius=8)
    g.text(58,y+30,title,size=24,weight=700)
    return y+65

def compare(g,y,label,values,scale=None):
    g.text(64,y,label,size=21)
    scale=scale or max(values) or 1
    for i,(v,c) in enumerate(zip(values,[TEAL,BLUE])):
        yy=y+12+i*25;g.rect(320,yy,max(0,v)/scale*440,16,c,radius=3)
        g.text(785,yy+15,f'{v:g}',size=20,color=c)
    return y+85

def preview(g,l,f):
    y=g.header(f['date']+' · '+f['venue'])
    g.text(64,y,l[30],size=22,color=MUTED);y+=30
    g.text(64,y,'Leeds United',size=24,color=TEAL,weight=700)
    g.text(510,y,'Manchester United',size=24,color=BLUE,weight=700);y+=25
    y=panel(g,y,l[1]);probs,lam=poisson(f['season']['home'],f['season']['away'])
    x=64
    for i,p in enumerate(probs):
        w=832*p/100;g.rect(x,y,w,50,[TEAL,'#778799',BLUE][i]);g.text(x+w/2,y+33,f'{p:.1f}%',size=25,color='white',anchor='middle');x+=w
    for i in range(3):g.text(64+290*i,y+82,l[12+i],size=23)
    y=g.block(64,y+100,832,l[31],size=20,color=MUTED)+20
    y=panel(g,y,l[0]);cx,cy,r=475,y+135,100
    for radius in [25,50,75,100]:
        pts=[(cx,cy-radius),(cx+radius,cy),(cx,cy+radius),(cx-radius,cy)]
        g.elements.append('<polygon points="'+' '.join(f'{x},{z}' for x,z in pts)+'" fill="none" stroke="#D6E2E8"/>')
    for side,c in [('home',TEAL),('away',BLUE)]:
        s=f['season'][side];vals=[s['gf']/18,1-s['ga']/18,s['points']/18,s['clean']/6]
        assert all(0<=v<=1 for v in vals)
        pts=[(cx,cy-r*vals[0]),(cx+r*vals[1],cy),(cx,cy+r*vals[2]),(cx-r*vals[3],cy)]
        g.elements.append('<polygon points="'+' '.join(f'{x},{z}' for x,z in pts)+f'" fill="{c}" fill-opacity="0.18" stroke="{c}" stroke-width="3"/>')
    for x,z,t in [(cx,cy-r-18,l[8]),(cx+r+90,cy,l[9]),(cx,cy+r+32,l[10]),(cx-r-100,cy,l[11])]:g.text(x,z,t,size=22,anchor='middle')
    y=cy+r+60
    g.text(64,y,'0–1 · GF/18 · 1−GA/18 · PTS/18 · CS/6',size=20,color=MUTED);y+=30
    y=panel(g,y,l[3]);h,a=f['season']['home'],f['season']['away']
    for label,vals in [(l[4],[round(h['gf']/6,2),round(a['gf']/6,2)]),(l[5],[round(h['ga']/6,2),round(a['ga']/6,2)]),(l[6],[h['points']/6,a['points']/6]),(l[7],[h['clean'],a['clean']])]:y=compare(g,y,label,vals)
    y=panel(g,y,l[2])
    for side,c,name in [('home',TEAL,'LEE'),('away',BLUE,'MUN')]:
        g.text(64,y+25,name,size=22,color=c,weight=700)
        for i,(date,opp,score,res) in enumerate(f['form'][side]):
            x=160+i*148;g.rect(x,y,134,40,{'W':TEAL,'D':'#6B7B8E','L':'#BD4754'}[res],radius=6)
            g.text(x+67,y+28,res+' '+score,size=22,color='white',anchor='middle')
            g.text(x+67,y+65,date+' '+opp,size=18,anchor='middle')
        y+=100
    y=panel(g,y,l[35])
    for d,s in f['h2h']:g.text(64,y,d+'     '+s,size=24);y+=40
    g.labels['caption']=l[34];g.labels['alt']=g.labels['title']+'; '+', '.join(map(str,probs))+'%'
    return g.finish(g.footer(y+15,'2026-10-18 · QuickIris · model v1'))

def recap(g,l,f):
    y=g.header(f['date'])
    g.text(64,y+40,'LIVERPOOL',size=28,color=TEAL,weight=700)
    g.text(475,y+45,'0 — 3',size=52,anchor='middle',weight=700)
    g.text(890,y+40,'MAN CITY',size=28,color=BLUE,anchor='end',weight=700);y+=95
    y=panel(g,y,l[16]);g.text(64,y,'LIV',size=22,color=TEAL);g.text(785,y,'MCI',size=22,color=BLUE);y+=30
    for key,label in [('possession',l[20]),('shots',l[21]),('sot',l[22]),('xg','xG'),('passing',l[23]),('fouls',l[24])]:y=compare(g,y,label,f['stats'][key])
    y=panel(g,y,l[15])
    for minute,name,kind in f['incidents']:
        g.text(64,y,f'{minute}′',size=27,color=TEAL,weight=700)
        g.text(160,y,name,size=25);g.text(630,y,{'sub':l[27],'red':l[28],'goal':l[29]}[kind],size=22,color='#BD4754' if kind=='red' else BLUE);y+=46
    y+=10;y=panel(g,y,l[17]);g.text(64,y,'Manchester City',size=23,color=BLUE);y+=20
    for label,v in [(l[25],0.16),(l[26],1.12)]:
        g.text(64,y+22,label,size=21);g.rect(350,y,v/1.28*430,28,BLUE,radius=5);g.text(805,y+23,f'{v:.2f}',size=23);y+=52
    g.text(350,y,'0.16 + 1.12 = 1.28 xG',size=23,color=BLUE);y+=25
    y=g.block(64,y,832,l[32],size=20,color=MUTED)+20
    y=panel(g,y,l[18]);left,right,top,bottom=100,850,y,y+140
    for v in range(4):
        yy=bottom-v*40;g.line(left,yy,right,yy);g.text(70,yy+7,str(v),size=18)
    xx=lambda m:left+m/90*(right-left)
    pts=[(xx(0),bottom),(xx(65),bottom),(xx(65),bottom-40),(xx(68),bottom-40),(xx(68),bottom-80),(xx(78),bottom-80),(xx(78),bottom-120),(xx(90),bottom-120)]
    g.elements.append('<polyline points="'+' '.join(f'{x},{z}' for x,z in pts)+f'" fill="none" stroke="{BLUE}" stroke-width="4"/>')
    g.line(left,bottom,right,bottom,color=TEAL,width=3)
    for m in [0,45,62,90]:g.text(xx(m),bottom+30,str(m),size=18,anchor='middle')
    g.line(xx(62),top,xx(62),bottom,color='#BD4754',dash='5 5');y=bottom+65
    y=panel(g,y,l[19])
    for name,minute in [('Haaland',65),('Doku',68),('Cherki',78)]:
        g.text(64,y,name,size=24);g.rect(350,y-20,210,24,BLUE,radius=4);g.text(590,y,'1 · '+str(minute)+'′',size=23);y+=45
    g.text(64,y,'Donnarumma · 6 saves',size=24,color=TEAL);y+=45
    g.labels['caption']=l[33];g.labels['alt']=g.labels['title']+'; 0–3; 62, 65, 68, 78; xG 0.94–1.28'
    return g.finish(g.footer(y,'2026-10-11 · QuickIris'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--font-cjk',required=True);p.add_argument('--font-hi',required=True);a=p.parse_args()
    facts=json.loads((ROOT/'data/match-dashboards.json').read_text());labels=json.loads((ROOT/'data/dashboard-labels.json').read_text())
    for kind,f in facts.items():
        for locale,l in labels.items():
            font=Path(a.font_cjk if locale in ['ko','ja'] else a.font_hi if locale=='hi' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
            title=f['home']+' — '+f['away']
            g=Graphic(locale,{'title':title,'alt':title,'caption':''},f,font)
            output=preview(g,l,f) if kind=='preview' else recap(g,l,f)
            (ROOT/'assets/charts'/f"{f['translation_group']}-{locale.lower()}.svg").write_text(output)
    print(json.dumps({'charts':16,'probabilities':poisson(facts['preview']['season']['home'],facts['preview']['season']['away'])}))
if __name__=='__main__':main()
