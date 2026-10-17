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
        "language": text(raw.get("language", "ko"), "language"),
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
    return {
        "id": article_id,
        "slug": article_slug,
        "platform": platform,
        "status": status,
        "title": text(raw.get("title"), f"{prefix}: title"),
        "description": text(raw.get("description", ""), f"{prefix}: description", empty=True),
        "published_at": None if information_page else parse_date(raw.get("published_at"), f"{prefix}: published_at"),
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
    if config["language"].lower().startswith("ko"):
        return {"articles": "글 목록", "sources": "참고 자료", "blogger": "Blogger", "empty": "아직 공개된 글이 없습니다.", "back": "모든 글 보기", "skip": "본문으로 이동"}
    return {"articles": "Articles", "sources": "Sources", "blogger": "Blogger", "empty": "No articles have been published yet.", "back": "All articles", "skip": "Skip to content"}


def article_body(article: dict, config: dict) -> str:
    blocks = []
    if article["description"]:
        blocks.append(f'<p class="article-summary">{esc(article["description"])}</p>')
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
    canonical = absolute_url(config, path)
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
        data = {"@context": "https://schema.org", "@type": "Article", "headline": article["title"], "description": article["description"], "datePublished": article["published_at"].isoformat(), "inLanguage": config["language"], "keywords": article["labels"]}
        if canonical:
            data.update({"url": canonical, "mainEntityOfPage": {"@type": "WebPage", "@id": canonical}})
        metadata.append(f'<script type="application/ld+json">{json_script(data)}</script>')
    if config["adsense_enabled"]:
        metadata.append(f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={config["adsense_client_id"]}" crossorigin="anonymous"></script>')
    nav = [f'<a href="{prefix or "./"}">{words(config)["articles"]}</a>']
    if canonical:
        nav.append(f'<a href="{prefix}rss.xml">RSS</a>')
    if config["blogger_base_url"]:
        nav.append(f'<a href="{esc(config["blogger_base_url"])}">{words(config)["blogger"]}</a>')
    footer_links = " · ".join(f'<a href="{prefix}pages/{page["slug"]}/">{esc(page["title"])}</a>' for page in site_pages or [])
    footer_nav = f'<nav aria-label="{"사이트 안내" if config["language"].lower().startswith("ko") else "Site information"}">{footer_links}</nav>' if footer_links else ""
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
<a class="skip-link" href="#main">{words(config)['skip']}</a>
<header class="site-header"><div class="container header-inner"><a class="brand" href="{prefix or './'}">{esc(config['site_title'])}</a><nav aria-label="Main">{' '.join(nav)}</nav></div></header>
<main id="main" class="container">{body}</main>
<footer class="site-footer container"><span>{esc(config['site_title'])}</span>{footer_nav}</footer>
</body>
</html>
'''


def label_html(article: dict) -> str:
    if not article["labels"]:
        return ""
    return '<ul class="labels">' + "".join(f"<li>{esc(label)}</li>" for label in article["labels"]) + "</ul>"


def build_index(config: dict, articles: list[dict], site_pages: list[dict] | None = None) -> str:
    cards = []
    for article in articles:
        date = article["published_at"].date().isoformat()
        cards.append(f'''<article class="post-card"><time datetime="{esc(article['published_at'].isoformat())}">{date}</time><h2><a href="posts/{article['slug']}/">{esc(article['title'])}</a></h2><p>{esc(article['description'])}</p>{label_html(article)}</article>''')
    listing = "\n".join(cards) if cards else f'<p class="empty-state">{words(config)["empty"]}</p>'
    body = f'<section class="intro"><h1>{esc(config["site_title"])}</h1><p>{esc(config["site_description"])}</p></section><section class="post-list" aria-label="{words(config)["articles"]}">{listing}</section>'
    return document(config, config["site_title"], config["site_description"], body, site_pages=site_pages)


def build_article(config: dict, article: dict, site_pages: list[dict] | None = None) -> str:
    published = article["published_at"]
    body = f'''<article class="article"><header class="article-header"><time datetime="{esc(published.isoformat())}">{published.date().isoformat()}</time><h1>{esc(article['title'])}</h1>{label_html(article)}</header><div class="prose">{article_body(article, config)}</div></article><p class="back-link"><a href="../../">← {words(config)['back']}</a></p>'''
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
            ET.SubElement(node, "lastmod").text = article["published_at"].isoformat()
        for page in site_pages or []:
            node = ET.SubElement(root, "url")
            ET.SubElement(node, "loc").text = absolute_url(config, f'pages/{page["slug"]}/')
    return xml_bytes(root)


def rss(config: dict, articles: list[dict]) -> bytes:
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
            url = absolute_url(config, f'posts/{article["slug"]}/')
            ET.SubElement(item, "title").text = article["title"]
            ET.SubElement(item, "link").text = url
            ET.SubElement(item, "guid", isPermaLink="true").text = url
            ET.SubElement(item, "description").text = article["description"]
            ET.SubElement(item, "pubDate").text = format_datetime(article["published_at"].astimezone(timezone.utc), usegmt=True)
            for label in article["labels"]:
                ET.SubElement(item, "category").text = label
    return xml_bytes(root)


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
        articles = load_articles(content_path)
        site_pages = load_site_pages(pages_path, articles)
        due = [a for a in articles if a["status"] == "ready" and a["published_at"] <= build_time]
        github = [a for a in due if a["platform"] == "github"]
        blogger = [a for a in due if a["platform"] == "blogger"]
        # Empty sites, including those with only future posts, must not show ads.
        config["adsense_enabled"] = config["adsense_enabled"] and bool(github)
        css = (ROOT / "assets" / "style.css").read_bytes()
        files = {"index.html": build_index(config, github, site_pages).encode("utf-8"), "assets/style.css": css, "sitemap.xml": sitemap(config, github, site_pages), "rss.xml": rss(config, github)}
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
            payload = {"title": article["title"], "content": article_body(article, config), "labels": article["labels"]}
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
