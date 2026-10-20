"""Typed match facts -> compact, localized HTML. No AI arithmetic or raw HTML."""
from __future__ import annotations
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from pathlib import Path
import importlib.util

_reader_spec = importlib.util.spec_from_file_location("qi_reader_timezones", Path(__file__).with_name("reader_timezones.py"))
_reader = importlib.util.module_from_spec(_reader_spec)
_reader_spec.loader.exec_module(_reader)

KEYS = ('heading','status','scheduled','final','competition','season','venue','local_time','utc_time','reader_time','halftime','goals','minute','scorer','team','score','own_goal','as_of','source','home','away')
LABELS = {
 'en': ('Match at a glance','Status','Scheduled','Final','Competition','Season','Venue','Venue-local kick-off','UTC kick-off','Edition time','Half-time','Goal timeline','Minute','Scorer','Scoring team','Score','own goal','Checked','Source','Home','Away'),
 'ko': ('경기 한눈에 보기','상태','경기 예정','경기 종료','대회','시즌','경기장','경기 현지 시작','UTC 시작','언어판 기준 시간','전반','득점 타임라인','시간','득점자','득점 팀','스코어','자책골','확인 시각','출처','홈','원정'),
 'es': ('El partido de un vistazo','Estado','Programado','Final','Competición','Temporada','Estadio','Inicio local','Inicio UTC','Hora de la edición','Descanso','Cronología de goles','Minuto','Goleador','Equipo','Marcador','autogol','Verificado','Fuente','Local','Visitante'),
 'ja': ('試合情報一覧','状態','試合予定','試合終了','大会','シーズン','会場','現地開始時刻','UTC開始','言語版の時刻','前半','得点経過','時間','得点者','得点チーム','スコア','オウンゴール','確認時刻','出典','ホーム','アウェー'),
 'pt-BR': ('O jogo em resumo','Status','Agendado','Final','Competição','Temporada','Estádio','Início local','Início UTC','Horário desta edição','Intervalo','Linha do tempo dos gols','Minuto','Artilheiro','Equipe','Placar','gol contra','Verificado','Fonte','Mandante','Visitante'),
 'fr': ('Le match en bref','Statut','À venir','Terminé','Compétition','Saison','Stade','Coup d’envoi local','Coup d’envoi UTC','Heure de cette édition','Mi-temps','Chronologie des buts','Minute','Buteur','Équipe','Score','contre son camp','Vérifié','Source','Domicile','Extérieur'),
 'de': ('Das Spiel im Überblick','Status','Angesetzt','Beendet','Wettbewerb','Saison','Stadion','Anstoß Ortszeit','Anstoß UTC','Zeit dieser Ausgabe','Halbzeit','Torverlauf','Minute','Torschütze','Team','Spielstand','Eigentor','Geprüft','Quelle','Heim','Auswärts'),
 'hi': ('मैच एक नज़र में','स्थिति','निर्धारित','समाप्त','प्रतियोगिता','सीज़न','स्टेडियम','स्थानीय शुरुआत','UTC शुरुआत','इस संस्करण का समय','हाफ-टाइम','गोल क्रम','मिनट','गोलकर्ता','टीम','स्कोर','आत्मघाती गोल','जाँच समय','स्रोत','घरेलू','बाहरी'),
}
DAYS = {
 'en': ('Mon','Tue','Wed','Thu','Fri','Sat','Sun'), 'ko': ('월','화','수','목','금','토','일'),
 'es': ('lun','mar','mié','jue','vie','sáb','dom'), 'ja': ('月','火','水','木','金','土','日'),
 'pt-BR': ('seg','ter','qua','qui','sex','sáb','dom'), 'fr': ('lun','mar','mer','jeu','ven','sam','dim'),
 'de': ('Mo','Di','Mi','Do','Fr','Sa','So'), 'hi': ('सोम','मंगल','बुध','गुरु','शुक्र','शनि','रवि'),
}


def text(value, field, limit=150):
    if not isinstance(value, str) or not value.strip() or len(value)>limit:
        raise ValueError('match_overview: invalid '+field)
    return value.strip()


def instant(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None: raise ValueError()
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ValueError('match_overview: timezone-aware ISO timestamp required') from None


def score(value):
    if not isinstance(value,dict) or set(value)!={'home','away'}:
        raise ValueError('match_overview: both score sides are required')
    if any(type(v) is not int or not 0<=v<=300 for v in value.values()):
        raise ValueError('match_overview: final scores must be integers')
    return dict(value)


def normalize(raw, league, kind, match_id=''):
    if raw is None: return None
    if not isinstance(raw,dict) or league not in ('EPL','NBA') or kind not in ('preview','recap'):
        raise ValueError('match_overview: unsupported sport/article')
    if str(raw.get('match_id'))!=match_id:
        raise ValueError('match_overview: article/event identity conflict')
    state='scheduled' if kind=='preview' else 'final'
    if raw.get('status')!=state: raise ValueError('match_overview: lifecycle conflict')
    out={k:text(raw.get(k),k) for k in ('competition','season','venue','home','away')}
    if out['home'].casefold()==out['away'].casefold(): raise ValueError('match_overview: teams must differ')
    zone=text(raw.get('venue_timezone'),'venue_timezone')
    try: ZoneInfo(zone)
    except (KeyError,ValueError): raise ValueError('match_overview: invalid IANA timezone') from None
    if league=='EPL' and zone!='Europe/London': raise ValueError('match_overview: EPL timezone must be Europe/London')
    start=instant(raw.get('start_utc'));asof=instant(raw.get('as_of'))
    if kind=='recap' and asof<start: raise ValueError('match_overview: result snapshot predates kickoff')
    sources=raw.get('sources')
    if not isinstance(sources,list) or not 1<=len(sources)<=4: raise ValueError('match_overview: source links required')
    refs=[]
    for s in sources:
        p=urlsplit(s.get('url',''))
        if p.scheme!='https' or not p.hostname or p.username or p.password:
            raise ValueError('match_overview: invalid source URL')
        refs.append({'title':text(s.get('title'),'source title',250),'url':s['url']})
    out.update(match_id=match_id,status=state,start_utc=start.isoformat(),as_of=asof.isoformat(),venue_timezone=zone,sources=refs)
    if kind=='preview':
        if any(raw.get(k) is not None for k in ('final_score','halftime_score','goals')):
            raise ValueError('match_overview: future matches cannot contain result records')
        return out
    out['final_score']=score(raw.get('final_score'))
    if league=='NBA' and out['final_score']['home']==out['final_score']['away']:
        raise ValueError('match_overview: tied NBA final')
    ht=raw.get('halftime_score')
    if ht is not None:
        out['halftime_score']=score(ht)
        if any(ht[k]>out['final_score'][k] for k in ('home','away')):raise ValueError('match_overview: halftime exceeds final')
    if 'goals' in raw:
        if league!='EPL' or not isinstance(raw['goals'],list):raise ValueError('match_overview: goals must be a football list')
        records=[];last=(0,0);running={'home':0,'away':0};half={'home':0,'away':0}
        for g in raw['goals']:
            minute=g.get('minute');added=g.get('added',0);period=g.get('period')
            if type(minute) is not int or type(added) is not int or type(period) is not int or period not in (1,2) or not 0<=added<=30:
                raise ValueError('match_overview: invalid goal clock')
            if not (1<=minute<=45 if period==1 else 46<=minute<=90):raise ValueError('match_overview: minute/period conflict')
            if added and minute not in (45,90):raise ValueError('match_overview: added time needs period boundary')
            order=(period,minute+added)
            if order<last:raise ValueError('match_overview: unsorted goal sequence')
            last=order;team=g.get('team')
            if team not in running:raise ValueError('match_overview: goal credited to unknown team')
            if type(g.get('own_goal',False)) is not bool:raise ValueError('match_overview: own_goal must be boolean')
            running[team]+=1
            if period==1:half[team]+=1
            observed=score(g.get('score'))
            if observed!=running:raise ValueError('match_overview: goal sequence does not reconcile')
            records.append({'minute':minute,'added':added,'period':period,'team':team,'scorer':text(g.get('scorer'),'scorer'),
                            'own_goal':g.get('own_goal',False),'score':observed})
        if running!=out['final_score'] or (ht is not None and half!=ht):
            raise ValueError('match_overview: goal timeline disagrees with final/halftime')
        out['goals']=records
    return out


def time_html(raw, zone, language, *, show_offset=False):
    t=instant(raw).astimezone(ZoneInfo(zone))
    day=DAYS.get(language,DAYS['en'])[t.weekday()]
    value=f'{t:%Y-%m-%d} ({day}) {t:%H:%M} {t.tzname()}'
    if show_offset:
        value += ' (' + _reader.offset_label(t) + ')'
    return '<time datetime="'+escape(t.isoformat(),quote=True)+'" data-timezone="'+escape(zone,quote=True)+'">'+escape(value)+'</time>'


def render(data, locale):
    audience = _reader.profile(locale)
    u=dict(zip(KEYS,LABELS[locale]));esc=escape
    out=['<section class="qi-match-overview"><div class="qi-match-heading"><h2>'+u['heading']+'</h2>',
         '<span class="qi-match-status">'+u[data['status']]+'</span></div>']
    if data['status']=='final':
        f=data['final_score'];label=data['home']+' '+str(f['home'])+' – '+str(f['away'])+' '+data['away']
        out.append('<div class="qi-scoreboard" role="group" aria-label="'+esc(label,quote=True)+'">'
                   '<div><small>'+u['home']+'</small><strong>'+esc(data['home'])+'</strong></div>'
                   '<b class="qi-score">'+str(f['home'])+'<span>–</span>'+str(f['away'])+'</b>'
                   '<div><small>'+u['away']+'</small><strong>'+esc(data['away'])+'</strong></div></div>')
        if data.get('halftime_score'):
            h=data['halftime_score'];out.append('<p class="qi-half-score">'+u['halftime']+' <strong>'+str(h['home'])+'–'+str(h['away'])+'</strong></p>')
    else:
        out.append('<p class="qi-fixture-pair"><strong>'+esc(data['home'])+'</strong><span>vs</span><strong>'+esc(data['away'])+'</strong></p>')
    rows=[(u['competition'],esc(data['competition']+' · '+data['season'])),(u['venue'],esc(data['venue'])),
          (u['local_time'],time_html(data['start_utc'],data['venue_timezone'],locale)),
          (esc(audience['label']),time_html(data['start_utc'],audience['zone'],locale,show_offset=True)),
          (u['utc_time'],time_html(data['start_utc'],'UTC',locale))]
    out.append('<table class="qi-match-facts"><caption class="qi-visually-hidden">'+u['heading']+'</caption><tbody>')
    out.extend('<tr><th scope="row">'+k+'</th><td>'+v+'</td></tr>' for k,v in rows)
    out.append('</tbody></table>')
    out.append('<p class="qi-match-source qi-reader-time-note">'+esc(audience['note'])+'</p>')
    if data.get('goals'):
        out.append('<div class="qi-table-scroll" tabindex="0" role="region" aria-label="'+u['goals']+'"><table class="qi-data-table qi-goal-table"><caption>'+u['goals']+'</caption><thead><tr>'+''.join('<th scope="col">'+u[k]+'</th>' for k in ('minute','scorer','score'))+'</tr></thead><tbody>')
        for g in data['goals']:
            clock=str(g['minute'])+('+'+str(g['added']) if g['added'] else '')+'′'
            name=esc(g['scorer'])+(' <span class="qi-own-goal">'+u['own_goal']+'</span>' if g['own_goal'] else '')
            name+='<small class="qi-goal-side" title="'+esc(data[g['team']],quote=True)+'">'+u[g['team']]+'</small>'
            out.append('<tr><th scope="row">'+clock+'</th><td>'+name+'</td><td class="qi-number"><strong>'+str(g['score']['home'])+'–'+str(g['score']['away'])+'</strong></td></tr>')
        out.append('</tbody></table></div>')
    refs=' · '.join('<a href="'+esc(s['url'],quote=True)+'" rel="noopener noreferrer">'+esc(s['title'])+'</a>' for s in data['sources'])
    out.append('<p class="qi-match-source">'+u['as_of']+': '+time_html(data['as_of'],'UTC',locale)+'<br>'+u['source']+': '+refs+'</p></section>')
    return ''.join(out)
