"""Explicit representative reader time zones; never infer a visitor location.

A language can span countries and time zones. The named city/country is a site
editorial default, not the user's actual time zone. Venue-local and UTC remain.
"""
from __future__ import annotations
from copy import deepcopy
from zoneinfo import ZoneInfo

POLICY_VERSION = 1
LOCALES = {
    "en": {"zone":"America/New_York","label":"U.S. time · New York","note":"Representative time zone for this language edition; not a detected location."},
    "ko": {"zone":"Asia/Seoul","label":"한국시간 시작 · 서울","note":"언어판의 대표 시간대입니다. 접속 위치를 감지한 시간이 아닙니다."},
    "es": {"zone":"Europe/Madrid","label":"Hora de España · Madrid","note":"Zona representativa de esta edición; no se ha detectado tu ubicación."},
    "ja": {"zone":"Asia/Tokyo","label":"日本時間 · 東京","note":"この言語版の代表時間帯です。閲覧者の位置は検出していません。"},
    "pt-BR": {"zone":"America/Sao_Paulo","label":"Hora do Brasil · São Paulo","note":"Fuso representativo desta edição; sua localização não foi detectada."},
    "fr": {"zone":"Europe/Paris","label":"Heure française · Paris","note":"Fuseau de référence de cette édition ; votre position n’est pas détectée."},
    "de": {"zone":"Europe/Berlin","label":"Deutsche Zeit · Berlin","note":"Referenzzeitzone dieser Sprachausgabe; kein ermittelter Standort."},
    "hi": {"zone":"Asia/Kolkata","label":"भारत का समय · नई दिल्ली","note":"इस भाषा संस्करण का प्रतिनिधि समय क्षेत्र; आपकी लोकेशन नहीं जाँची गई है।"}
}


def profile(locale: str) -> dict[str, str]:
    """Fail closed rather than silently showing Korea time for an unknown locale."""
    if locale not in LOCALES:
        raise ValueError('No reviewed reader time-zone mapping for locale: ' + str(locale))
    value = deepcopy(LOCALES[locale])
    ZoneInfo(value['zone'])
    return value


def offset_label(value) -> str:
    offset = value.utcoffset()
    if offset is None:
        raise ValueError('Reader time must be offset-aware')
    minutes = int(offset.total_seconds() // 60)
    sign = '+' if minutes >= 0 else '-'
    hours, mins = divmod(abs(minutes), 60)
    return f'UTC{sign}{hours:02d}:{mins:02d}'
