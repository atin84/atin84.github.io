"""Safe semantic tables for preview team strength and sourced football recap metrics."""
from __future__ import annotations
from datetime import datetime, timezone
from html import escape
import math
from urllib.parse import urlsplit, parse_qsl

UI = {
 'en': ('Date','Opponent','Score','Result','Metric','Unit','Source','No data','Official team comparison','Match data comparison','Expected value','Defense and pressing','Creation and progression','Passing and possession','Goalkeeping','Scope'),
 'ko': ('날짜','상대팀','스코어','결과','지표','단위','출처','자료 없음','공식 팀 전력 비교','경기 데이터 비교','기대 가치','수비·압박','찬스 창출·전진','패스·점유','골키퍼','집계 범위'),
 'es': ('Fecha','Rival','Marcador','Resultado','Métrica','Unidad','Fuente','Sin datos','Comparación de equipos','Datos del partido','Valor esperado','Defensa y presión','Creación y progresión','Pases y posesión','Portería','Periodo'),
 'ja': ('日付','対戦相手','スコア','結果','指標','単位','出典','データなし','公式チーム比較','試合データ比較','期待値','守備・プレス','創出・前進','パス・保持','ゴールキーパー','集計範囲'),
 'pt-BR': ('Data','Adversário','Placar','Resultado','Métrica','Unidade','Fonte','Sem dados','Comparação das equipes','Dados da partida','Valor esperado','Defesa e pressão','Criação e progressão','Passes e posse','Goleiros','Período'),
 'fr': ('Date','Adversaire','Score','Résultat','Indicateur','Unité','Source','Indisponible','Comparaison des équipes','Données du match','Valeur attendue','Défense et pressing','Création et progression','Passes et possession','Gardiens','Période'),
 'de': ('Datum','Gegner','Ergebnis','Ausgang','Kennzahl','Einheit','Quelle','Keine Daten','Teamvergleich','Spieldaten','Erwartungswerte','Abwehr und Pressing','Kreation und Fortschritt','Pässe und Ballbesitz','Torhüter','Zeitraum'),
 'hi': ('तारीख','प्रतिद्वंद्वी','स्कोर','परिणाम','आँकड़ा','इकाई','स्रोत','डेटा नहीं','टीम तुलना','मैच डेटा तुलना','अपेक्षित मान','रक्षा और प्रेसिंग','मौका निर्माण','पासिंग और कब्ज़ा','गोलकीपिंग','अवधि'),
}
CATEGORIES = ('expected','defensive','creation','passing','goalkeeping','strength')


def url(value):
    p = urlsplit(value if isinstance(value, str) else '')
    if p.scheme != 'https' or not p.hostname or p.username or p.password or any(k.lower() in ('token','key','api_key','access_token') for k,_ in parse_qsl(p.query)):
        raise ValueError('Public source must be HTTPS without credentials')
    return value


def normalize(raw, league, kind, field):
    if raw is None:
        return None
    if (not isinstance(raw, dict) or league not in ('NBA','EPL') or
        (field == 'football_statistics' and (league != 'EPL' or kind != 'recap')) or
        (field == 'official_comparison' and kind != 'preview')):
        raise ValueError('Statistics component on incompatible article')
    t = datetime.fromisoformat(raw['as_of'].replace('Z','+00:00'))
    if t.tzinfo is None:
        raise ValueError('Statistics as_of must have timezone')
    for k in ('scope','home','away'):
        if not isinstance(raw.get(k), str) or not raw[k].strip():
            raise ValueError('Statistics names/scope missing')
    if raw['home'] == raw['away']:
        raise ValueError('Statistics team identities must differ')
    sources = {}
    for source in raw.get('sources', []):
        if not all(isinstance(source.get(k), str) and source[k] for k in ('id','title','provider','url')):
            raise ValueError('Incomplete statistics source')
        if source['id'] in sources:
            raise ValueError('Duplicate source ID')
        url(source['url']); sources[source['id']] = dict(source)
    rows = []
    seen = set()
    for row in raw.get('metrics', []):
        if not isinstance(row, dict) or row.get('source_id') not in sources:
            raise ValueError('Missing metric provenance')
        if not all(isinstance(row.get(k), str) and row[k] for k in ('id','name','unit','period','definition')):
            raise ValueError('Missing metric method/unit/period')
        if row['id'] in seen or row.get('category') not in CATEGORIES:
            raise ValueError('Duplicate/invalid metric')
        seen.add(row['id'])
        h, a = row.get('home'), row.get('away')
        if h is None and a is None:
            continue
        for value in (h, a):
            if value is not None:
                if type(value) not in (int,float) or not math.isfinite(value):
                    raise ValueError('Invalid metric value')
                if row['unit'] == '%' and not 0 <= value <= 100:
                    raise ValueError('Percent outside 0..100')
                if value < 0 and row['id'] not in ('xt','psxg_plus_minus','net_rating','goal_difference'):
                    raise ValueError('Unexpected negative metric')
        if row['id'] == 'clean_sheet_pct' and row['period'] == 'match':
            raise ValueError('Clean-sheet percentage needs multi-match scope')
        rows.append(dict(row))
    if not rows or len(rows) > 50:
        raise ValueError('Statistics requires 1..50 observed rows')
    return {k: raw[k] for k in ('scope','home','away')} | {
        'as_of': t.astimezone(timezone.utc).isoformat(), 'sources': list(sources.values()), 'metrics': rows}


def wrap_table(caption, headings, rows):
    return ('<div class="qi-table-scroll" tabindex="0" role="region" aria-label="' + escape(caption,quote=True) + '">'
      '<table class="qi-data-table"><caption>' + escape(caption) + '</caption><thead><tr>' +
      ''.join('<th scope="col">' + escape(h) + '</th>' for h in headings) + '</tr></thead><tbody>' +
      ''.join(rows) + '</tbody></table></div>')


def recent_table(team, locale):
    u = UI.get(locale, UI['en'])
    rows=[]
    for g in team['recent']:
        rows.append('<tr><th scope="row"><time datetime="' + g['date'] + '">' + g['date'] + '</time></th>'
            '<td>' + escape(g['opponent']) + '</td><td class="qi-number"><strong class="qi-result-score">' +
            str(g['for']) + '–' + str(g['against']) + '</strong></td><td><span class="qi-result-badge qi-outcome-' +
            g['result'].lower() + '">' + g['result'] + '</span></td></tr>')
    return wrap_table(team['name'], u[:4], rows)


def h2h_table(data, locale):
    u = UI.get(locale, UI['en'])
    rows=[]
    for g in data['head_to_head']:
        rows.append('<tr><th scope="row"><time datetime="' + g['date'] + '">' + g['date'] + '</time></th><td>' +
            escape(g['home_team']) + '</td><td class="qi-number"><strong>' + str(g['home_score']) + ' – ' +
            str(g['away_score']) + '</strong></td><td>' + escape(g['away_team']) + '</td></tr>')
    # Historical home/away are explicit; the upcoming venue must not reverse wins.
    home = {'ko':'홈팀','ja':'ホーム','es':'Local','pt-BR':'Mandante','fr':'Domicile','de':'Heim','hi':'घरेलू'}.get(locale,'Home')
    away = {'ko':'원정팀','ja':'アウェイ','es':'Visitante','pt-BR':'Visitante','fr':'Extérieur','de':'Auswärts','hi':'मेहमान'}.get(locale,'Away')
    return wrap_table(data['home']['name'] + ' / ' + data['away']['name'], (u[0],home,u[2],away), rows)


def render(data, locale, field):
    u = UI.get(locale, UI['en']); sources = {s['id']:s for s in data['sources']}
    out=['<section class="qi-statistics"><h2>' + u[8 if field=='official_comparison' else 9] + '</h2>',
         '<p class="qi-caveat">' + escape(u[15] + ': ' + data['scope'] + ' · ' + data['as_of']) + '</p>']
    for index, category in enumerate(CATEGORIES):
        entries = [r for r in data['metrics'] if r['category']==category]
        if not entries: continue
        title=u[10+index] if index<5 else u[8]
        rows=[]
        for row in entries:
            source=sources[row['source_id']]
            cells=[]
            for side in ('home','away'):
                value=row.get(side)
                formatted=('<span aria-label="' + escape(u[7],quote=True) + '">—</span>') if value is None else f'{value:g}'
                cells.append('<td class="qi-number">' + formatted + '</td>')
            rows.append('<tr><th scope="row">' + escape(row['name']) + '</th>' + ''.join(cells) +
                '<td>' + escape(row['unit']) + '</td><td><details><summary>' + escape(source['provider']) +
                '</summary><p>' + escape(row['definition'] + ' · ' + row['period']) + '</p><a href="' +
                escape(source['url'],quote=True) + '" rel="noopener noreferrer">' + escape(source['title']) + '</a></details></td></tr>')
        out.append(wrap_table(title, (u[4],data['home'],data['away'],u[5],u[6]), rows))
    return ''.join(out) + '</section>'
