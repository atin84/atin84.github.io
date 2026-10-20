"""Semantic match facts: localized timetable, scoreboard and goal-event table.

No model or browser scripting. All times derive from one verified UTC instant.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

UI = {
 'en': ('Match at a glance','Scheduled','Final','Venue','Venue time','Korea time','Competition','Matchweek','Season','Half-time','Second half','Goals','Minute','Team','Scorer','Score','Own goal','Source','Verified','UTC time'),
 'ko': ('경기 한눈에 보기','경기 예정','경기 종료','경기장','현지 시간','한국 시간','대회','라운드','시즌','전반','후반','득점 타임라인','시간','팀','득점자','스코어','자책골','출처','확인 시각','UTC 시간'),
 'es': ('El partido de un vistazo','Programado','Finalizado','Estadio','Hora local','Hora de Corea','Competición','Jornada','Temporada','Descanso','Segunda parte','Goles','Minuto','Equipo','Goleador','Marcador','Autogol','Fuente','Verificado','Hora UTC'),
 'ja': ('試合概要','開催予定','試合終了','会場','現地時間','韓国時間','大会','節','シーズン','前半','後半','得点経過','時間','チーム','得点者','スコア','オウンゴール','出典','確認時刻','UTC時刻'),
 'pt-BR': ('O jogo em resumo','Agendado','Encerrado','Estádio','Hora local','Hora da Coreia','Competição','Rodada','Temporada','Intervalo','Segundo tempo','Gols','Minuto','Equipe','Goleador','Placar','Gol contra','Fonte','Verificado','Hora UTC'),
 'fr': ('Le match en bref','À venir','Terminé','Stade','Heure locale','Heure en Corée','Compétition','Journée','Saison','Mi-temps','Seconde période','Buts','Minute','Équipe','Buteur','Score','Contre son camp','Source','Vérifié','Heure UTC'),
 'de': ('Das Spiel auf einen Blick','Angesetzt','Beendet','Stadion','Ortszeit','Korea-Zeit','Wettbewerb','Spieltag','Saison','Halbzeit','Zweite Halbzeit','Tore','Minute','Team','Torschütze','Spielstand','Eigentor','Quelle','Geprüft','UTC-Zeit'),
 'hi': ('मैच एक नज़र में','निर्धारित','समाप्त','मैदान','स्थानीय समय','कोरिया समय','प्रतियोगिता','मैच सप्ताह','सीज़न','पहला हाफ','दूसरा हाफ','गोल क्रम','मिनट','टीम','गोलकर्ता','स्कोर','आत्मघाती गोल','स्रोत','सत्यापित','UTC समय'),
}
DAYS = {
 'en': ('Mon','Tue','Wed','Thu','Fri','Sat','Sun'), 'ko': ('월','화','수','목','금','토','일'),
 'es': ('lun','mar','mié','jue','vie','sáb','dom'), 'ja': ('月','火','水','木','金','土','日'),
 'pt-BR': ('seg','ter','qua','qui','sex','sáb','dom'), 'fr': ('lun','mar','mer','jeu','ven','sam','dim'),
 'de': ('Mo','Di','Mi','Do','Fr','Sa','So'), 'hi': ('सोम','मंगल','बुध','गुरु','शुक्र','शनि','रवि'),
}


def instant(value):
    try:
        d = datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None: raise ValueError()
        return d.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Match summary needs offset-aware timestamps') from None


def text(value, maximum=160):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum:
        raise ValueError('Invalid match summary text')
    return value.strip()


def score(value):
    if not isinstance(value,list) or len(value)!=2 or any(type(n) is not int or not 0<=n<=300 for n in value):
        raise ValueError('Invalid home/away score')
    return value


def normalize(raw, league, kind, official_id):
    if raw is None: return None
    if not isinstance(raw,dict) or league not in ('EPL','NBA') or kind not in ('preview','recap'):
        raise ValueError('Invalid match summary article type')
    expected='scheduled' if kind=='preview' else 'final'
    if raw.get('status')!=expected or str(raw.get('official_id',''))!=official_id:
        raise ValueError('Match summary identity/lifecycle mismatch')
    out={k:text(raw.get(k)) for k in ('home','away','venue','competition','season')}
    if out['home'].casefold()==out['away'].casefold(): raise ValueError('Match teams must differ')
    start=instant(raw.get('start_utc'));checked=instant(raw.get('verified_at'))
    if (kind=='preview' and start<=checked) or (kind=='recap' and start>checked):
        raise ValueError('Match summary timestamps conflict with lifecycle')
    try: zone=ZoneInfo(raw.get('venue_timezone'))
    except (ValueError,KeyError,TypeError): raise ValueError('Verified venue IANA timezone required') from None
    if league=='EPL' and zone.key!='Europe/London': raise ValueError('EPL requires Europe/London')
    week=raw.get('matchweek')
    if week is not None and (type(week) is not int or not 1<=week<=100): raise ValueError('Invalid matchweek')
    refs=[]
    for ref in raw.get('sources',[]):
        url=text(ref.get('url'),1000);p=urlsplit(url)
        if p.scheme!='https' or not p.hostname or p.username or p.password: raise ValueError('Invalid summary source')
        refs.append({'title':text(ref.get('title')), 'url':url})
    if not refs: raise ValueError('Match summary needs evidence sources')
    out.update(status=expected,official_id=official_id,start_utc=start.isoformat(),verified_at=checked.isoformat(),
        venue_timezone=zone.key,matchweek=week,sources=refs,goals=[])
    if kind=='preview':
        if any(raw.get(k) for k in ('final_score','halftime_score','goals')):
            raise ValueError('Preview must not contain future scores or goals')
        return out
    final=score(raw.get('final_score'));out['final_score']=final
    if league=='NBA' and final[0]==final[1]:raise ValueError('NBA final cannot be tied')
    ht=raw.get('halftime_score')
    if ht is not None:
        ht=score(ht)
        if any(ht[i]>final[i] for i in (0,1)):raise ValueError('Half-time exceeds final score')
        out['halftime_score']=ht
    previous=(0,0);order=(-1,-1)
    if len(raw.get('goals',[]))>30:raise ValueError('Unexpected number of goal events')
    for row in raw.get('goals',[]):
        if league!='EPL':raise ValueError('Football goal timeline on non-football match')
        minute=row.get('minute');added=row.get('added',0)
        if type(minute) is not int or type(added) is not int or not 0<=minute<=120 or not 0<=added<=30:
            raise ValueError('Invalid goal minute')
        if added and minute not in (45,90,105,120):raise ValueError('Added time needs period boundary')
        # 45+3 stays before 46; do not confuse displayed added time with elapsed time.
        if (minute,added)<order:raise ValueError('Goal events are out of order')
        side=row.get('team');current=score(row.get('score'))
        if side not in ('home','away'):raise ValueError('Invalid scoring team')
        i=0 if side=='home' else 1
        if current[i]!=previous[i]+1 or current[1-i]!=previous[1-i]:raise ValueError('Goal score does not reconcile')
        if any(current[j]>final[j] for j in (0,1)):raise ValueError('Goal exceeds final score')
        own=row.get('own_goal',False)
        if type(own) is not bool:raise ValueError('own_goal must be boolean')
        out['goals'].append({'minute':minute,'added':added,'team':side,'player':text(row.get('player')),
            'own_goal':own,'score':current})
        previous=tuple(current);order=(minute,added)
    if out['goals'] and list(previous)!=final:raise ValueError('Goal timeline incomplete or inconsistent')
    if ht is not None and out['goals']:
        first_half=[g for g in out['goals'] if g['minute']<=45]
        if (first_half[-1]['score'] if first_half else [0,0])!=ht:raise ValueError('Goals disagree with half-time score')
    return out


def time_html(value,zone,language):
    d=instant(value).astimezone(ZoneInfo(zone))
    day=DAYS.get(language,DAYS['en'])[d.weekday()]
    return '<time datetime="'+escape(d.isoformat(),quote=True)+'"><b>'+d.strftime('%Y-%m-%d')+' ('+day+')</b> '+d.strftime('%H:%M')+' <span class="qi-zone">'+escape(d.tzname() or zone)+'</span></time>'


def render(data,language):
    u=UI.get(language,UI['en']);esc=lambda x:escape(str(x),quote=True)
    final=data['status']=='final'
    out=['<section class="qi-match-summary" aria-label="'+esc(u[0])+'">',
        '<div class="qi-match-eyebrow"><span>'+esc(data['competition'])+' · '+esc(data['season'])+'</span>',
        '<strong class="qi-match-status">'+esc(u[2] if final else u[1])+'</strong></div>',
        '<div class="qi-scoreboard"><div class="qi-score-team qi-score-home">'+esc(data['home'])+'</div>',
        '<div class="qi-score-main">'+(' – '.join(map(str,data['final_score'])) if final else 'VS')+'</div>',
        '<div class="qi-score-team qi-score-away">'+esc(data['away'])+'</div></div>']
    if final and 'halftime_score' in data:
        ht=data['halftime_score'];ft=data['final_score']
        out.append('<div class="qi-period-score"><span>'+esc(u[9])+': <b>'+str(ht[0])+'–'+str(ht[1])+'</b></span><span>'+esc(u[10])+': <b>'+str(ft[0]-ht[0])+'–'+str(ft[1]-ht[1])+'</b></span></div>')
    rows=[(u[5],time_html(data['start_utc'],'Asia/Seoul',language)),
          (u[4],time_html(data['start_utc'],data['venue_timezone'],language)),
          (u[3],esc(data['venue']))]
    if data.get('matchweek') is not None:rows.append((u[7],str(data['matchweek'])))
    out += ['<table class="qi-match-facts"><caption>'+esc(u[0])+'</caption><tbody>']
    for label,value in rows:out.append('<tr><th scope="row">'+esc(label)+'</th><td>'+value+'</td></tr>')
    out.append('</tbody></table>')
    out.append('<details class="qi-match-source"><summary>'+esc(u[17])+' / '+esc(u[18])+'</summary><p>'+esc(u[19])+': '+time_html(data['start_utc'],'UTC',language)+'</p><p>'+esc(u[18])+': '+time_html(data['verified_at'],'UTC',language)+'</p>')
    for ref in data['sources']:out.append('<a href="'+esc(ref['url'])+'" rel="noopener noreferrer">'+esc(ref['title'])+'</a> ')
    out.append('</details></section>')
    if data['goals']:
        out += ['<section class="qi-match-goals"><h2>'+esc(u[11])+'</h2>',
            '<div class="qi-table-scroll" tabindex="0" role="region" aria-label="'+esc(u[11])+'"><table class="qi-data-table"><caption>'+esc(data['home'])+' / '+esc(data['away'])+'</caption><thead><tr>',
            ''.join('<th scope="col">'+esc(label)+'</th>' for label in (u[12],u[13],u[14],u[15])),'</tr></thead><tbody>']
        for goal in data['goals']:
            minute=str(goal['minute'])+('+'+str(goal['added']) if goal['added'] else '')+'′'
            scorer=esc(goal['player'])+(' <small class="qi-own-goal">'+esc(u[16])+'</small>' if goal['own_goal'] else '')
            out.append('<tr><th scope="row">'+minute+'</th><td>'+esc(data[goal['team']])+'</td><td>'+scorer+'</td><td class="qi-number"><b>'+'–'.join(map(str,goal['score']))+'</b></td></tr>')
        out.append('</tbody></table></div></section>')
    return '\n'.join(out)
