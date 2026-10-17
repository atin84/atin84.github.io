#!/usr/bin/env python3
"""Render reviewed JSON articles without publishing or making network requests.

Usage: python build.py --out dist --config config.json --content content
Only status=ready articles whose published_at is at or before the build time
are emitted. Use --now ISO8601 to set a reproducible cutoff instead of current
UTC. Blogger payloads go to exports/blogger, outside the GitHub Pages output.
Optional --pages JSON files provide undated, ad-free information pages.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
ADSENSE_RE = re.compile(r"ca-pub-[0-9]{16}\Z")
MANIFEST = ".build-manifest"
ROOT = Path(__file__).resolve().parent
LANGUAGES = {
    "en": "English", "ko": "한국어", "es": "Español", "ja": "日本語",
    "pt-BR": "Português (Brasil)", "fr": "Français", "de": "Deutsch", "hi": "हिन्दी",
}
UI = {
    "en": {"articles": "Articles", "sources": "Sources", "empty": "No articles have been published yet.", "back": "All articles", "skip": "Skip to content", "published": "Published", "updated": "Updated", "language": "Language", "main": "Main navigation", "information": "Site information"},
    "ko": {"articles": "글 목록", "sources": "참고 자료", "empty": "아직 공개된 글이 없습니다.", "back": "모든 글 보기", "skip": "본문으로 이동", "published": "게시", "updated": "수정", "language": "언어", "main": "주요 메뉴", "information": "사이트 안내"},
    "es": {"articles": "Artículos", "sources": "Fuentes", "empty": "Todavía no hay artículos publicados.", "back": "Todos los artículos", "skip": "Ir al contenido", "published": "Publicado", "updated": "Actualizado", "language": "Idioma", "main": "Navegación principal", "information": "Información del sitio"},
    "ja": {"articles": "記事一覧", "sources": "参考資料", "empty": "公開された記事はまだありません。", "back": "すべての記事", "skip": "本文へ移動", "published": "公開日", "updated": "更新日", "language": "言語", "main": "メインナビゲーション", "information": "サイト情報"},
    "pt-BR": {"articles": "Artigos", "sources": "Fontes", "empty": "Ainda não há artigos publicados.", "back": "Todos os artigos", "skip": "Ir para o conteúdo", "published": "Publicado", "updated": "Atualizado", "language": "Idioma", "main": "Navegação principal", "information": "Informações do site"},
    "fr": {"articles": "Articles", "sources": "Sources", "empty": "Aucun article n’a encore été publié.", "back": "Tous les articles", "skip": "Aller au contenu", "published": "Publié", "updated": "Mis à jour", "language": "Langue", "main": "Navigation principale", "information": "Informations du site"},
    "de": {"articles": "Artikel", "sources": "Quellen", "empty": "Es wurden noch keine Artikel veröffentlicht.", "back": "Alle Artikel", "skip": "Zum Inhalt", "published": "Veröffentlicht", "updated": "Aktualisiert", "language": "Sprache", "main": "Hauptnavigation", "information": "Website-Informationen"},
    "hi": {"articles": "लेख", "sources": "स्रोत", "empty": "अभी कोई लेख प्रकाशित नहीं हुआ है।", "back": "सभी लेख", "skip": "मुख्य सामग्री पर जाएँ", "published": "प्रकाशित", "updated": "अपडेट किया गया", "language": "भाषा", "main": "मुख्य नेविगेशन", "information": "वेबसाइट की जानकारी"},
}


def text(value: object, field: str, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if not value and not empty:
        raise ValueError(f"{field} must not be empty")
    if any((ord(c) < 32 and c not in "\t\n\r") or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in {0xFFFE, 0xFFFF} for c in value):
        raise ValueError(f"{field} contains an invalid control or Unicode character")
    return value


def string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return [text(item, f"{field}[{i}]") for i, item in enumerate(value)]


def http_url(value: object, field: str, *, base: bool = False) -> str:
    value = text(value, field, empty=base)
    if not value:
        return ""
    if any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError(f"{field} must be an absolute HTTP(S) URL without whitespace")
    try:
        parts = urlsplit(value)
        _ = parts.port
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid URL") from exc
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None or parts.password is not None:
        raise ValueError(f"{field} must be an absolute HTTP(S) URL without credentials")
    if base and (parts.query or parts.fragment):
        raise ValueError(f"{field} must not contain a query or fragment")
    return value.rstrip("/") if base else value


def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_keys)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected one JSON object")
    return data


def load_config(path: Path) -> dict:
    raw = load_json(path)
    config = {
        "site_title": text(raw.get("site_title"), "site_title"),
        "site_description": text(raw.get("site_description", ""), "site_description", empty=True),
        "github_base_url": http_url(raw.get("github_base_url", ""), "github_base_url", base=True),
        "blogger_base_url": http_url(raw.get("blogger_base_url", ""), "blogger_base_url", base=True),
        "adsense_enabled": raw.get("adsense_enabled", False),
        "adsense_client_id": text("" if raw.get("adsense_client_id") is None else raw["adsense_client_id"], "adsense_client_id", empty=True),
        "language": text(raw.get("language", "en"), "language"),
    }
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", config["language"]):
        raise ValueError("language must be a valid language tag such as ko or en")
    if type(config["adsense_enabled"]) is not bool:
        raise ValueError("adsense_enabled must be a JSON boolean")
    client = config["adsense_client_id"]
    if client and not ADSENSE_RE.fullmatch(client):
        raise ValueError("adsense_client_id must be ca-pub- followed by exactly 16 digits")
    if config["adsense_enabled"] and not client:
        raise ValueError("adsense_enabled=true requires a valid adsense_client_id")
    return config


def parse_date(value: object, field: str) -> datetime:
    value = text(value, field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO 8601") from exc
    if parsed.tzinfo is None:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            raise ValueError(f"{field} needs a timezone offset (for example +09:00 or Z)")
    return parsed


def slug(value: object, field: str) -> str:
    value = text(value, field)
    if len(value) > 80 or not SLUG_RE.fullmatch(value):
        raise ValueError(f"{field} must be 1-80 lowercase ASCII letters/digits joined by single hyphens")
    return value


def article_language(value: object, field: str) -> str:
    value = text(value, field)
    canonical = next((code for code in LANGUAGES if code.lower() == value.lower()), None)
    if canonical is None:
        raise ValueError(f"{field} must be one of {', '.join(LANGUAGES)}")
    return canonical


def normalize_article(raw: dict, path: Path, *, information_page: bool = False) -> dict:
    prefix = str(path)
    article_id = slug(raw.get("id"), f"{prefix}: id")
    article_slug = slug(raw.get("slug", article_id), f"{prefix}: slug")
    platform = raw.get("platform", "github" if information_page else None)
    status = raw.get("status", "ready" if information_page else "draft")
    if platform not in {"github", "blogger"}:
        raise ValueError(f"{prefix}: platform must be github or blogger")
    if information_page and platform != "github":
        raise ValueError(f"{prefix}: information pages are only supported on GitHub")
    if status not in {"draft", "ready"}:
        raise ValueError(f"{prefix}: status must be draft or ready")
    sections = raw.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError(f"{prefix}: sections must be a nonempty list")
    clean_sections = []
    for i, section in enumerate(sections):
        field = f"{prefix}: sections[{i}]"
        if not isinstance(section, dict):
            raise ValueError(f"{field} must be an object")
        paragraphs = string_list(section.get("paragraphs", []), f"{field}.paragraphs")
        bullets = string_list(section.get("bullets", []), f"{field}.bullets")
        if not paragraphs and not bullets:
            raise ValueError(f"{field} needs at least one paragraph or bullet")
        clean_sections.append({
            "heading": text(section.get("heading", ""), f"{field}.heading", empty=True),
            "paragraphs": paragraphs,
            "bullets": bullets,
        })
    sources = raw.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError(f"{prefix}: sources must be a list")
    clean_sources = []
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(f"{prefix}: sources[{i}] must be an object")
        clean_sources.append({
            "title": text(source.get("title"), f"{prefix}: sources[{i}].title"),
            "url": http_url(source.get("url"), f"{prefix}: sources[{i}].url"),
        })
    language = article_language(raw["language"], f"{prefix}: language") if "language" in raw else None
    published_at = None if information_page else parse_date(raw.get("published_at"), f"{prefix}: published_at")
    updated_at = parse_date(raw["updated_at"], f"{prefix}: updated_at") if "updated_at" in raw else published_at
    if published_at and updated_at < published_at:
        raise ValueError(f"{prefix}: updated_at must not precede published_at")
    metadata = {key: text(raw[key], f"{prefix}: {key}") if key in raw else ""
                for key in ("league", "match_id", "article_kind", "translation_group")}
    for key, value in metadata.items():
        if value and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}", value):
            raise ValueError(f"{prefix}: {key} must be a short ASCII identifier")
    if metadata["translation_group"] and not language:
        raise ValueError(f"{prefix}: translation_group requires an explicit language")
    blogger_value = raw.get("blogger_url")
    blogger_url = "" if blogger_value is None or blogger_value == "" else http_url(blogger_value, f"{prefix}: blogger_url")
    if blogger_url and platform != "blogger":
        raise ValueError(f"{prefix}: blogger_url is only valid for Blogger articles")
    figures = raw.get("figures", [])
    if not isinstance(figures, list):
        raise ValueError(f"{prefix}: figures must be a list")
    clean_figures = []
    for i, figure in enumerate(figures):
        field = f"{prefix}: figures[{i}]"
        if not isinstance(figure, dict):
            raise ValueError(f"{field} must be an object")
        clean_figures.append({"src": http_url(figure.get("src"), f"{field}.src"),
                              "alt": text(figure.get("alt"), f"{field}.alt"),
                              "caption": text(figure.get("caption", ""), f"{field}.caption", empty=True)})
    return {
        "id": article_id,
        "slug": article_slug,
        "platform": platform,
        "status": status,
        "title": text(raw.get("title"), f"{prefix}: title"),
        "description": text(raw.get("description", ""), f"{prefix}: description", empty=True),
        "published_at": published_at,
        "updated_at": updated_at,
        "language": language,
        **metadata,
        "figures": clean_figures,
        "blogger_url": blogger_url,
        "labels": list(dict.fromkeys(string_list(raw.get("labels", []), f"{prefix}: labels"))),
        "sections": clean_sections,
        "sources": clean_sources,
        "source_file": str(path),
    }


def load_articles(directory: Path) -> list[dict]:
    if not directory.is_dir():
        raise ValueError(f"content directory does not exist: {directory}")
    articles = []
    identifiers: dict[str, str] = {}
    slugs: dict[str, str] = {}
    bodies: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        if not path.is_file():
            continue
        article = normalize_article(load_json(path), path)
        for field, seen in (("id", identifiers), ("slug", slugs)):
            value = article[field]
            if value in seen:
                raise ValueError(f"duplicate {field} '{value}': {seen[value]} and {path}")
            seen[value] = str(path)
        # Detect the same body assigned to both destinations under different IDs.
        normalized = json.dumps(article["sections"], ensure_ascii=False, sort_keys=True)
        normalized = " ".join(unicodedata.normalize("NFC", normalized).split()).casefold()
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if fingerprint in bodies and bodies[fingerprint]["platform"] != article["platform"]:
            other = bodies[fingerprint]
            raise ValueError(f"same article body assigned to both platforms: {other['source_file']} and {path}")
        bodies[fingerprint] = article
        articles.append(article)
    return sorted(articles, key=lambda a: (a["published_at"], a["id"]), reverse=True)


def load_site_pages(directory: Path, articles: list[dict]) -> list[dict]:
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise ValueError(f"information page directory is not a directory: {directory}")
    seen = {field: {article[field] for article in articles} for field in ("id", "slug")}
    pages = []
    for path in sorted(directory.glob("*.json")):
        if not path.is_file():
            continue
        page = normalize_article(load_json(path), path, information_page=True)
        for field in seen:
            if page[field] in seen[field]:
                raise ValueError(f"{path}: duplicate {field} '{page[field]}'")
            seen[field].add(page[field])
        if page["status"] == "ready":
            pages.append(page)
    return pages


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def words(config: dict) -> dict:
    code = config["language"]
    ui = UI.get(code, UI.get(code.split("-")[0], UI["en"]))
    return {**ui, "blogger": "Blogger"}


def localized_config(config: dict, article: dict) -> dict:
    return {**config, "default_language": config.get("default_language", config["language"]),
            "language": article.get("language") or config["language"]}


def language_path(config: dict, language: str) -> str:
    return "" if language == config.get("default_language", config["language"]) else f"languages/{language}/"


def public_article_url(config: dict, article: dict) -> str:
    if article["platform"] == "blogger":
        return article.get("blogger_url", "")
    return absolute_url(config, f'posts/{article["slug"]}/')


def connect_translations(config: dict, articles: list[dict], due: list[dict]) -> None:
    """Validate identities; link only renderable GitHub or confirmed Blogger URLs."""
    groups: dict[str, list[dict]] = {}
    urls: dict[str, str] = {}
    for article in articles:
        group = article.get("translation_group")
        if group:
            members = groups.setdefault(group, [])
            for other in members:
                if article["language"] == other["language"]:
                    raise ValueError(f"duplicate language {article['language']} in translation_group {group}")
                for key in ("league", "match_id", "article_kind"):
                    if article.get(key) != other.get(key):
                        raise ValueError(f"translation_group {group} has inconsistent {key}")
            members.append(article)
        blogger_url = article.get("blogger_url")
        if blogger_url:
            base = urlsplit(config["blogger_base_url"])
            candidate = urlsplit(blogger_url)
            if base.netloc and candidate.netloc != base.netloc:
                raise ValueError(f"{article['id']}: blogger_url is outside the configured Blogger site")
            if candidate.path in {"", "/"} or candidate.fragment:
                raise ValueError(f"{article['id']}: blogger_url must identify a post, without a fragment")
            if blogger_url in urls:
                raise ValueError(f"duplicate blogger_url: {article['id']} and {urls[blogger_url]}")
            urls[blogger_url] = article["id"]
    public_ids = {article["id"] for article in due}
    order = {code: i for i, code in enumerate(LANGUAGES)}
    for article in due:
        members = groups.get(article.get("translation_group"), [])
        article["translations"] = [
            {"language": member["language"], "url": public_article_url(config, member)}
            for member in sorted(members, key=lambda item: order[item["language"]])
            if member["id"] in public_ids and public_article_url(config, member)
        ]


def language_navigation(config: dict, translations: list[dict], *, current: str) -> str:
    if not translations:
        return ""
    links = []
    for translation in translations:
        code, url = translation["language"], translation["url"]
        active = ' aria-current="page"' if code == current else ""
        links.append(f'<a href="{esc(url)}" hreflang="{esc(code)}" lang="{esc(code)}"{active}>{esc(LANGUAGES.get(code, code))}</a>')
    return f'<nav class="language-nav" aria-label="{esc(words(config)["language"])}" style="display:flex;flex-wrap:wrap;gap:.45rem 1rem;margin:1.4rem 0"><span class="language-label">{esc(words(config)["language"])}</span>{" ".join(links)}</nav>'


def index_language_navigation(config: dict, *, prefix: str = "") -> str:
    translations = [{"language": code, "url": prefix + language_path(config, code) or "./"}
                    for code in config.get("available_languages", [])]
    return language_navigation(config, translations, current=config["language"])


def article_dates(article: dict, config: dict) -> str:
    ui = words(config)
    dates = [(ui["published"], article["published_at"])]
    if article.get("updated_at") and article["updated_at"] != article["published_at"]:
        dates.append((ui["updated"], article["updated_at"]))
    return '<p class="article-dates">' + " · ".join(
        f'{esc(label)}: <time datetime="{esc(date.isoformat())}">{esc(date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))}</time>'
        for label, date in dates) + "</p>"


def article_body(article: dict, config: dict) -> str:
    config = localized_config(config, article)
    blocks = []
    if article["description"]:
        blocks.append(f'<p class="article-summary">{esc(article["description"])}</p>')
    for figure in article.get("figures", []):
        caption = f'<figcaption>{esc(figure["caption"])}</figcaption>' if figure["caption"] else ""
        blocks.append(f'<figure class="article-figure" style="margin:2rem 0;max-width:100%"><a href="{esc(figure["src"])}"><img src="{esc(figure["src"])}" alt="{esc(figure["alt"])}" decoding="async" style="display:block;width:100%;max-width:100%;height:auto"></a>{caption}</figure>')
    for section in article["sections"]:
        blocks.append("<section>")
        if section["heading"]:
            blocks.append(f'<h2>{esc(section["heading"])}</h2>')
        blocks.extend(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
        if section["bullets"]:
            blocks.append("<ul>" + "".join(f"<li>{esc(item)}</li>" for item in section["bullets"]) + "</ul>")
        blocks.append("</section>")
    if article["sources"]:
        items = "".join(f'<li><a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(source["title"])}</a></li>' for source in article["sources"])
        blocks.append(f'<section class="sources"><h2>{words(config)["sources"]}</h2><ol>{items}</ol></section>')
    return "\n".join(blocks)


def absolute_url(config: dict, path: str = "") -> str:
    base = config["github_base_url"]
    return f"{base}/{path}" if base else ""


def json_script(data: dict) -> str:
    return (json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def document(config: dict, title: str, description: str, body: str, *, path: str = "", prefix: str = "", article: dict | None = None, site_pages: list[dict] | None = None) -> str:
    if article:
        config = localized_config(config, article)
    canonical = absolute_url(config, path)
    ui = words(config)
    metadata = [f'<meta name="description" content="{esc(description)}">']
    if config["adsense_client_id"]:
        metadata.append(f'<meta name="google-adsense-account" content="{esc(config["adsense_client_id"])}">')
    if canonical:
        metadata.append(f'<link rel="canonical" href="{esc(canonical)}">')
        metadata.append(f'<meta property="og:url" content="{esc(canonical)}">')
        metadata.append(f'<link rel="alternate" type="application/rss+xml" title="{esc(config["site_title"])}" href="{esc(absolute_url(config, "rss.xml"))}">')
    else:
        metadata.append('<meta name="robots" content="noindex, nofollow">')
    metadata += [f'<meta property="og:title" content="{esc(title)}">', f'<meta property="og:description" content="{esc(description)}">', f'<meta property="og:type" content="{"article" if article else "website"}">']
    if article:
        data = {"@context": "https://schema.org", "@type": "Article", "headline": article["title"], "description": article["description"], "datePublished": article["published_at"].isoformat(), "dateModified": (article.get("updated_at") or article["published_at"]).isoformat(), "inLanguage": config["language"], "keywords": article["labels"]}
        if canonical:
            data.update({"url": canonical, "mainEntityOfPage": {"@type": "WebPage", "@id": canonical}})
        for translation in article.get("translations", []):
            metadata.append(f'<link rel="alternate" hreflang="{esc(translation["language"])}" href="{esc(translation["url"])}">')
        if article.get("figures"):
            data["image"] = [figure["src"] for figure in article["figures"]]
            metadata.append(f'<meta property="og:image" content="{esc(article["figures"][0]["src"])}">')
            metadata.append(f'<meta property="og:image:alt" content="{esc(article["figures"][0]["alt"])}">')
        metadata.append(f'<script type="application/ld+json">{json_script(data)}</script>')
    if config["adsense_enabled"]:
        metadata.append(f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={config["adsense_client_id"]}" crossorigin="anonymous"></script>')
    home_path = prefix + language_path(config, config["language"]) or "./"
    nav = [f'<a href="{home_path}">{ui["articles"]}</a>']
    if canonical:
        nav.append(f'<a href="{prefix}rss.xml">RSS</a>')
    if config["blogger_base_url"]:
        nav.append(f'<a href="{esc(config["blogger_base_url"])}">{words(config)["blogger"]}</a>')
    footer_links = " · ".join(f'<a href="{prefix}pages/{page["slug"]}/">{esc(page["title"])}</a>' for page in site_pages or [])
    footer_nav = f'<nav aria-label="{esc(ui["information"])}">{footer_links}</nav>' if footer_links else ""
    return f'''<!doctype html>
<html lang="{esc(config['language'])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{chr(10).join(metadata)}
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<a class="skip-link" href="#main">{ui['skip']}</a>
<header class="site-header"><div class="container header-inner"><a class="brand" href="{prefix or './'}">{esc(config['site_title'])}</a><nav aria-label="{esc(ui['main'])}">{' '.join(nav)}</nav></div></header>
<main id="main" class="container">{body}</main>
<footer class="site-footer container"><span>{esc(config['site_title'])}</span>{footer_nav}</footer>
</body>
</html>
'''


def label_html(article: dict) -> str:
    if not article["labels"]:
        return ""
    return '<ul class="labels">' + "".join(f"<li>{esc(label)}</li>" for label in article["labels"]) + "</ul>"


def build_index(config: dict, articles: list[dict], site_pages: list[dict] | None = None, *, language: str | None = None) -> str:
    config = {**config, "language": language or config["language"]}
    path = language_path(config, config["language"])
    prefix = "../../" if path else ""
    cards = []
    for article in articles:
        if (article.get("language") or config.get("default_language", config["language"])) != config["language"]:
            continue
        if article["platform"] == "blogger" and not article.get("blogger_url"):
            continue
        date = article["published_at"].date().isoformat()
        target = article["blogger_url"] if article["platform"] == "blogger" else f'{prefix}posts/{article["slug"]}/'
        destination = ' <span class="post-destination">Blogger</span>' if article["platform"] == "blogger" else ""
        cards.append(f'''<article class="post-card"><time datetime="{esc(article['published_at'].isoformat())}">{date}</time>{destination}<h2><a href="{esc(target)}">{esc(article['title'])}</a></h2><p>{esc(article['description'])}</p>{label_html(article)}</article>''')
    listing = "\n".join(cards) if cards else f'<p class="empty-state">{words(config)["empty"]}</p>'
    subtitle = config["site_description"] if not path else f'{words(config)["articles"]} · {LANGUAGES.get(config["language"], config["language"])}'
    body = f'<section class="intro"><h1>{esc(config["site_title"])}</h1><p>{esc(subtitle)}</p>{index_language_navigation(config, prefix=prefix)}</section><section class="post-list" aria-label="{words(config)["articles"]}">{listing}</section>'
    return document(config, config["site_title"], subtitle, body, path=path, prefix=prefix, site_pages=site_pages)


def build_article(config: dict, article: dict, site_pages: list[dict] | None = None) -> str:
    config = localized_config(config, article)
    translations = language_navigation(config, article.get("translations", []), current=config["language"])
    back = "../../" + language_path(config, config["language"])
    body = f'''<article class="article"><header class="article-header">{article_dates(article, config)}<h1>{esc(article['title'])}</h1>{label_html(article)}{translations}</header><div class="prose">{article_body(article, config)}</div></article><p class="back-link"><a href="{back}">← {words(config)['back']}</a></p>'''
    return document(config, f'{article["title"]} · {config["site_title"]}', article["description"], body, path=f'posts/{article["slug"]}/', prefix="../../", article=article, site_pages=site_pages)


def build_site_page(config: dict, page: dict, site_pages: list[dict]) -> str:
    body = f'''<article class="article"><header class="article-header"><h1>{esc(page['title'])}</h1></header><div class="prose">{article_body(page, config)}</div></article>'''
    return document({**config, "adsense_enabled": False}, f'{page["title"]} · {config["site_title"]}', page["description"], body, path=f'pages/{page["slug"]}/', prefix="../../", site_pages=site_pages)


def xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def sitemap(config: dict, articles: list[dict], site_pages: list[dict] | None = None) -> bytes:
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    if config["github_base_url"]:
        home = ET.SubElement(root, "url")
        ET.SubElement(home, "loc").text = absolute_url(config)
        for article in articles:
            node = ET.SubElement(root, "url")
            ET.SubElement(node, "loc").text = absolute_url(config, f'posts/{article["slug"]}/')
            ET.SubElement(node, "lastmod").text = (article.get("updated_at") or article["published_at"]).isoformat()
        for language in config.get("available_languages", []):
            path = language_path(config, language)
            if path:
                node = ET.SubElement(root, "url")
                ET.SubElement(node, "loc").text = absolute_url(config, path)
        for page in site_pages or []:
            node = ET.SubElement(root, "url")
            ET.SubElement(node, "loc").text = absolute_url(config, f'pages/{page["slug"]}/')
    return xml_bytes(root)


def rss(config: dict, articles: list[dict]) -> bytes:
    articles = [article for article in articles
                if (article.get("language") or config["language"]) == config["language"]
                and public_article_url(config, article)]
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = config["site_title"]
    ET.SubElement(channel, "description").text = config["site_description"] or config["site_title"]
    ET.SubElement(channel, "link").text = absolute_url(config)
    ET.SubElement(channel, "language").text = config["language"]
    # No fabricated public URLs or preview entries when a base URL is unset.
    if config["github_base_url"]:
        if articles:
            ET.SubElement(channel, "lastBuildDate").text = format_datetime(articles[0]["published_at"].astimezone(timezone.utc), usegmt=True)
        for article in articles:
            item = ET.SubElement(channel, "item")
            url = public_article_url(config, article)
            ET.SubElement(item, "title").text = article["title"]
            ET.SubElement(item, "link").text = url
            ET.SubElement(item, "guid", isPermaLink="true").text = url
            ET.SubElement(item, "description").text = article["description"]
            ET.SubElement(item, "pubDate").text = format_datetime(article["published_at"].astimezone(timezone.utc), usegmt=True)
            for label in article["labels"]:
                ET.SubElement(item, "category").text = label
    return xml_bytes(root)


def blogger_payload(article: dict, config: dict) -> dict:
    """Export body HTML only; Blogger owns its document head and canonical tag.

    publish_blogger.py attaches the existing stable identity marker on loading.
    Do not put that reserved marker in exports or change the export filenames.
    """
    config = localized_config(config, article)
    navigation = language_navigation(config, article.get("translations", []), current=config["language"])
    content = f'<div class="quickiris-article" lang="{esc(config["language"])}">{article_dates(article, config)}{navigation}{article_body(article, config)}</div>'
    return {"title": article["title"], "content": content, "labels": article["labels"]}


def chart_assets(config: dict, articles: list[dict]) -> dict[str, bytes]:
    """Ship shared factual graphics, including those embedded by Blogger."""
    result = {}
    directory = ROOT / "assets" / "charts"
    if directory.exists():
        for asset in sorted(directory.rglob("*")):
            if asset.is_symlink():
                raise ValueError(f"chart assets must not be symlinks: {asset}")
            if asset.is_file() and asset.suffix.lower() in {".svg", ".png", ".webp", ".jpg", ".jpeg", ".gif"}:
                result[asset.relative_to(ROOT).as_posix()] = asset.read_bytes()
    local_prefix = absolute_url(config, "assets/charts/")
    if local_prefix:
        for article in articles:
            for figure in article.get("figures", []):
                if figure["src"].startswith(local_prefix):
                    relative = "assets/charts/" + figure["src"][len(local_prefix):].split("?", 1)[0].split("#", 1)[0]
                    if relative not in result:
                        raise ValueError(f"{article['id']}: missing shared figure asset {relative}")
    return result


def ensure_safe_outputs(outputs: list[Path], inputs: list[Path]) -> None:
    for output in outputs:
        if output == Path(output.anchor) or output == Path.cwd().resolve():
            raise ValueError(f"output must be a dedicated directory: {output}")
        for source in inputs:
            if output == source or output in source.parents or source in output.parents:
                # Output children of the code directory are normal, but it may
                # never replace the directory containing this script.
                if source == ROOT and source in output.parents:
                    continue
                raise ValueError(f"output overlaps protected input: {output} / {source}")
    a, b = outputs
    if a == b or a in b.parents or b in a.parents:
        raise ValueError("Blogger exports and GitHub output must be separate directories")


def managed_path(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or ".." in relative.parts or "\\" in name:
        raise ValueError(f"unsafe build manifest entry: {name!r}")
    target = root.joinpath(*relative.parts)
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"output path escapes its directory: {target}")
    return target


def previous_files(root: Path) -> set[str]:
    manifest = root / MANIFEST
    if not manifest.exists():
        return set()
    try:
        items = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read build manifest: {manifest}") from exc
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise ValueError(f"invalid build manifest: {manifest}")
    for item in items:
        managed_path(root, item)
    return set(items)


def write_tree(root: Path, files: dict[str, bytes], previous: set[str]) -> None:
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    for name in files:
        managed_path(root, name)
    stage = Path(tempfile.mkdtemp(prefix=".publishing-build-", dir=root.parent))
    try:
        for name, data in files.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for name in files:
            target = managed_path(root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / name, target)
        for name in sorted(previous - set(files), reverse=True):
            target = managed_path(root, name)
            if target.is_file() or target.is_symlink():
                target.unlink()
            parent = target.parent
            while parent != root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        manifest_temp = stage / MANIFEST
        manifest_temp.write_text(json.dumps(sorted(files), indent=2) + "\n", encoding="utf-8")
        os.replace(manifest_temp, root / MANIFEST)
    finally:
        shutil.rmtree(stage)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="dist", help="GitHub Pages static output directory")
    parser.add_argument("--config", default="config.json", help="site configuration JSON")
    parser.add_argument("--content", default="content", help="directory of article JSON files")
    parser.add_argument("--pages", default="site_pages", help="optional directory of undated information page JSON files")
    parser.add_argument("--blogger-out", default="exports/blogger", help="Blogger API payload output directory")
    parser.add_argument("--now", help="publication cutoff in ISO 8601 (default: current UTC)")
    args = parser.parse_args(argv)
    try:
        build_time = parse_date(args.now, "--now") if args.now is not None else datetime.now(timezone.utc)
        config_path = Path(args.config).resolve()
        content_path = Path(args.content).resolve()
        pages_path = Path(args.pages).resolve()
        output = Path(args.out).resolve()
        exports = Path(args.blogger_out).resolve()
        ensure_safe_outputs([output, exports], [config_path, content_path, pages_path, ROOT])
        config = load_config(config_path)
        config["default_language"] = config["language"]
        articles = load_articles(content_path)
        site_pages = load_site_pages(pages_path, articles)
        due = [a for a in articles if a["status"] == "ready" and a["published_at"] <= build_time]
        connect_translations(config, articles, due)
        github = [a for a in due if a["platform"] == "github"]
        blogger = [a for a in due if a["platform"] == "blogger"]
        config["available_languages"] = [code for code in LANGUAGES
                                         if any((a["language"] or config["language"]) == code for a in due)]
        # Empty sites, including those with only future posts, must not show ads.
        config["adsense_enabled"] = config["adsense_enabled"] and bool(github)
        css = (ROOT / "assets" / "style.css").read_bytes()
        files = {"index.html": build_index(config, due, site_pages).encode("utf-8"), "assets/style.css": css, "sitemap.xml": sitemap(config, github, site_pages), "rss.xml": rss(config, due)}
        files.update(chart_assets(config, due))
        for language in config["available_languages"]:
            path = language_path(config, language)
            if path:
                files[f"{path}index.html"] = build_index(config, due, site_pages, language=language).encode("utf-8")
        for article in github:
            files[f'posts/{article["slug"]}/index.html'] = build_article(config, article, site_pages).encode("utf-8")
        for page in site_pages:
            files[f'pages/{page["slug"]}/index.html'] = build_site_page(config, page, site_pages).encode("utf-8")
        if config["github_base_url"]:
            robots = f'User-agent: *\nAllow: /\nSitemap: {absolute_url(config, "sitemap.xml")}\n'
        else:
            robots = "User-agent: *\nDisallow: /\n"
        files["robots.txt"] = robots.encode("utf-8")
        if config["adsense_enabled"]:
            publisher = config["adsense_client_id"].removeprefix("ca-")
            files["ads.txt"] = f"google.com, {publisher}, DIRECT, f08c47fec0942fa0\n".encode("utf-8")
        payloads = {}
        for article in blogger:
            payload = blogger_payload(article, config)
            payloads[f'{article["id"]}.json'] = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        old_files = previous_files(output)
        old_payloads = previous_files(exports)
        write_tree(output, files, old_files)
        write_tree(exports, payloads, old_payloads)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Built {len(github)} GitHub article(s) in {output}")
    print(f"Built {len(site_pages)} information page(s) without publication dates or ads")
    print(f"Exported {len(blogger)} Blogger payload(s) to {exports}; no posts were uploaded")
    print(f"Skipped {sum(a['status'] == 'draft' for a in articles)} draft article(s)")
    print(f"Deferred {sum(a['status'] == 'ready' and a['published_at'] > build_time for a in articles)} future article(s); cutoff {build_time.astimezone(timezone.utc).isoformat()}")
    if not config["github_base_url"]:
        print("Preview mode: noindex; robots disallows crawling; sitemap and RSS have no public entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
