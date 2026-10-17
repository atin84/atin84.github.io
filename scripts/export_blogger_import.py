#!/usr/bin/env python3
"""Prepare a one-time Blogger Atom import from validated renderer exports.

This creates a local file only. Upload it through Blogger's supported Import
Content UI, keep automatic publishing off, and verify the resulting drafts.
The alternate URLs request stable slugs; actual URLs must be checked after
import and recorded separately before treating them as published.

Schema reference: https://developers.google.com/blogger/docs/2.0/reference
Current import UI: https://support.google.com/blogger/answer/41387?hl=en
The retired v2 API is not called.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from publish_blogger import load_posts

ROOT = Path(__file__).resolve().parents[1]
ATOM = 'http://www.w3.org/2005/Atom'
APP = 'http://www.w3.org/2007/app'
ET.register_namespace('', ATOM)
ET.register_namespace('app', APP)
LANGUAGES = [('en', 'English'), ('ko', '한국어'), ('es', 'Español'),
             ('ja', '日本語'), ('pt-BR', 'Português (Brasil)'),
             ('fr', 'Français'), ('de', 'Deutsch'), ('hi', 'हिन्दी')]


def child(parent, name, text=None, **attrs):
    node = ET.SubElement(parent, f'{{{ATOM}}}{name}', attrs)
    node.text = text
    return node


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepared = {p.stem: p for p in load_posts(ROOT / 'exports/blogger')}
    posts = [json.loads(p.read_text(encoding='utf-8'))
             for p in sorted((ROOT / 'content').glob('*.json'))]
    posts = [p for p in posts if p.get('platform') == 'blogger'
             and p.get('league') in {'NBA', 'EPL'} and p.get('status') == 'ready']
    assert len(posts) == 16, f'Expected the authorized 16-post test batch; got {len(posts)}'
    now = datetime.now(timezone.utc).isoformat()
    feed = ET.Element(f'{{{ATOM}}}feed')
    child(feed, 'id', 'urn:quickiris:sports-publishing-test:2026-10-17')
    child(feed, 'updated', now)
    child(feed, 'title', 'QuickIris sports publishing test', type='text')
    child(feed, 'generator', 'Blogger', version='7.00', uri='https://www.blogger.com')
    author = child(feed, 'author')
    child(author, 'name', 'QuickIris')
    manifest = []
    for post in posts:
        body = prepared[post['id']].body()
        slug = post.get('slug', post['id'])
        date = datetime.fromisoformat(post['published_at'].replace('Z', '+00:00'))
        requested_url = f'https://quickiris.blogspot.com/{date:%Y/%m}/{slug}.html'
        entry = child(feed, 'entry')
        identity = str(int(hashlib.sha256(post['id'].encode()).hexdigest()[:15], 16))
        child(entry, 'id', f'tag:blogger.com,1999:blog-6780211422264222342.post-{identity}')
        child(entry, 'published', post['published_at'])
        child(entry, 'updated', post.get('updated_at', post['published_at']))
        child(entry, 'category', scheme='http://schemas.google.com/g/2005#kind',
              term='http://schemas.google.com/blogger/2008/kind#post')
        labels = list(dict.fromkeys([*body['labels'], f"lang:{post['language']}",
                                    'Sports test 2026-10-17']))
        for label in labels:
            child(entry, 'category', scheme='http://www.blogger.com/atom/ns#', term=label)
        child(entry, 'title', body['title'], type='text')
        # The import can preserve the requested permalink; verify, never assume.
        child(entry, 'link', rel='alternate', type='text/html', href=requested_url)
        child(entry, 'content', body['content'], type='html')
        control = ET.SubElement(entry, f'{{{APP}}}control')
        ET.SubElement(control, f'{{{APP}}}draft').text = 'yes'
        manifest.append({'id': post['id'], 'language': post['language'],
                         'title': body['title'], 'requested_url': requested_url,
                         'state': 'prepared-not-imported'})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(feed).write(args.output, encoding='utf-8', xml_declaration=True)
    ET.parse(args.output)
    args.output.with_suffix('.manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Prepared {len(posts)} draft entries: {args.output}')


if __name__ == '__main__':
    main()
