"""Publication regressions using synthetic articles; no network or publishing."""

from contextlib import redirect_stdout, redirect_stderr
from html.parser import HTMLParser
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET


spec = importlib.util.spec_from_file_location("site_builder", Path(__file__).resolve().parents[1] / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Tags(HTMLParser):
    def __init__(self, value):
        super().__init__()
        self.tags = []
        self.feed(value)

    def handle_starttag(self, name, attrs):
        self.tags.append((name, dict(attrs)))

    def select(self, name, **attrs):
        return [values for tag, values in self.tags if tag == name
                and all(values.get(key) == value for key, value in attrs.items())]


class MultilingualBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = self.root / "content"
        self.content.mkdir()
        self.config = {"site_title": "Test Site", "site_description": "English description",
                       "github_base_url": "https://example.test", "blogger_base_url": "https://blog.example.test",
                       "adsense_enabled": False, "adsense_client_id": "", "language": "en", "default_language": "en"}
        (self.root / "config.json").write_text(json.dumps(self.config), encoding="utf-8")

    def raw(self, language="en", platform="github", group="nba-preview"):
        suffix = language.lower()
        return {"id": f"{group}-{suffix}", "slug": f"{group}-{suffix}",
                "platform": platform, "status": "ready", "language": language,
                "league": "NBA", "match_id": "001-test", "article_kind": "preview", "translation_group": group,
                "title": f"{group} title {language}", "description": f"Summary in {language}",
                "published_at": "2026-10-17T12:00:00Z", "updated_at": "2026-10-17T13:00:00Z",
                "sections": [{"heading": f"First section {language}", "paragraphs": [f"Verified {group} text in {language}."]}],
                "figures": [{"src": "https://media.example.test/score.svg", "alt": f"Score in {language}", "caption": "Official data & context"}],
                "sources": [{"title": "Primary source", "url": "https://source.example.test/"}]}

    def write(self, raw):
        (self.content / f"{raw['id']}.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    def build(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = builder.main(["--config", str(self.root / "config.json"), "--content", str(self.content),
                                   "--pages", str(self.root / "pages"), "--out", str(self.root / "dist"),
                                   "--blogger-out", str(self.root / "exports"), "--now", "2026-10-17T14:00:00Z"])
        self.assertEqual(result, 0)

    def test_eight_languages_have_self_canonical_reciprocal_hreflang_and_correct_figures(self):
        for language in builder.LANGUAGES:
            self.write(self.raw(language))
        self.build()
        expected = {(code, f"https://example.test/posts/nba-preview-{code.lower()}/") for code in builder.LANGUAGES}
        for code in builder.LANGUAGES:
            with self.subTest(language=code):
                body = (self.root / "dist" / "posts" / f"nba-preview-{code.lower()}" / "index.html").read_text()
                tags = Tags(body)
                self.assertEqual(tags.select("html")[0]["lang"], code)
                self.assertEqual(tags.select("link", rel="canonical")[0]["href"], f"https://example.test/posts/nba-preview-{code.lower()}/")
                alternates = {(tag["hreflang"], tag["href"]) for tag in tags.select("link", rel="alternate") if "hreflang" in tag}
                self.assertEqual(alternates, expected)
                self.assertEqual(len(tags.select("a", **{"aria-current": "page"})), 1)
                self.assertIn(f'"inLanguage":"{code}"', body)
                self.assertIn('"dateModified":"2026-10-17T13:00:00+00:00"', body)
                self.assertEqual(tags.select("img")[0]["alt"], f"Score in {code}")
                self.assertLess(body.index('class="article-summary"'), body.index('<figure'))
                self.assertLess(body.index('<figure'), body.index(f'First section {code}'))
                self.assertIn(builder.UI[code]["sources"], body)
        home = (self.root / "dist" / "index.html").read_text()
        self.assertEqual(len(Tags(home).select("article", **{"class": "post-card"})), 1)
        self.assertIn("nba-preview title en", home)
        self.assertNotIn("nba-preview title ko", home)
        korean = (self.root / "dist" / "languages" / "ko" / "index.html").read_text()
        self.assertIn("nba-preview title ko", korean)
        self.assertNotIn("nba-preview title en", korean)
        self.assertIn('href="../../posts/nba-preview-ko/"', korean)
        xml = ET.parse(self.root / "dist" / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        lastmods = [node.text for node in xml.findall("s:url/s:lastmod", ns)]
        self.assertEqual(lastmods, ["2026-10-17T13:00:00+00:00"] * 8)

    def test_blogger_posts_are_linked_but_not_copied_and_payload_language_survives(self):
        for code in builder.LANGUAGES:
            article = self.raw(code, "blogger", "epl-recap")
            article["blogger_url"] = f"https://blog.example.test/2026/10/epl-recap-{code.lower()}.html"
            self.write(article)
        self.build()
        self.assertFalse((self.root / "dist" / "posts").exists())
        home = (self.root / "dist" / "index.html").read_text()
        self.assertIn('href="https://blog.example.test/2026/10/epl-recap-en.html"', home)
        self.assertNotIn("Verified epl-recap text", home)
        sitemap = (self.root / "dist" / "sitemap.xml").read_text()
        self.assertNotIn("blog.example.test/2026", sitemap)
        for code in builder.LANGUAGES:
            payload = json.loads((self.root / "exports" / f"epl-recap-{code.lower()}.json").read_text())
            tags = Tags(payload["content"])
            self.assertEqual(tags.select("div", **{"class": "quickiris-article"})[0]["lang"], code)
            links = {(tag["hreflang"], tag["href"]) for tag in tags.select("a") if "hreflang" in tag}
            expected = {(language, f"https://blog.example.test/2026/10/epl-recap-{language.lower()}.html")
                        for language in builder.LANGUAGES}
            self.assertEqual(links, expected)
            self.assertEqual(tags.select("nav")[0]["aria-label"], builder.UI[code]["language"])
            self.assertEqual(tags.select("a", **{"aria-current": "page"})[0]["hreflang"], code)
            self.assertEqual(tags.select("time"), [])  # Blogger's outer template owns the post date.
            self.assertNotIn("article-dates", payload["content"])
            self.assertEqual(tags.select("link"), [])  # This body cannot claim to configure Blogger's head.
            self.assertIn("width:100%", tags.select("img")[0]["style"])

    def test_blogger_navigation_excludes_unconfirmed_urls_and_other_groups(self):
        expected = set()
        for code in builder.LANGUAGES:
            article = self.raw(code, "blogger", "epl-recap")
            if code != "hi":
                article["blogger_url"] = f"https://blog.example.test/2026/10/actual-{code.lower()}.html"
                expected.add((code, article["blogger_url"]))
            self.write(article)
        unrelated = self.raw("hi", "blogger", "other-match")
        unrelated["match_id"] = "002-other-match"
        unrelated["blogger_url"] = "https://blog.example.test/2026/10/other-match-hi.html"
        self.write(unrelated)
        # A mixed-platform input must not insert a GitHub URL into Blogger's nav.
        mixed_en = self.raw("en", "blogger", "mixed-group")
        mixed_en["blogger_url"] = "https://blog.example.test/2026/10/mixed-en.html"
        mixed_ko = self.raw("ko", "github", "mixed-group")
        self.write(mixed_en)
        self.write(mixed_ko)
        self.build()
        for code in builder.LANGUAGES:
            payload = json.loads((self.root / "exports" / f"epl-recap-{code.lower()}.json").read_text())
            tags = Tags(payload["content"])
            links = {(tag["hreflang"], tag["href"]) for tag in tags.select("a") if "hreflang" in tag}
            self.assertEqual(links, expected)
            self.assertNotIn(unrelated["blogger_url"], payload["content"])
            self.assertNotIn("/epl-recap-hi.html", payload["content"])
        mixed_payload = json.loads((self.root / "exports" / "mixed-group-en.json").read_text())
        links = {(tag["hreflang"], tag["href"]) for tag in Tags(mixed_payload["content"]).select("a") if "hreflang" in tag}
        self.assertEqual(links, {("en", mixed_en["blogger_url"])})
        github_body = (self.root / "dist" / "posts" / "mixed-group-ko" / "index.html").read_text()
        github_alternates = {tag["hreflang"] for tag in Tags(github_body).select("link", rel="alternate") if "hreflang" in tag}
        self.assertEqual(github_alternates, {"en", "ko"})  # Existing GitHub behavior remains unchanged.

    def test_unconfirmed_and_future_urls_are_never_invented(self):
        english = self.raw()
        korean = self.raw("ko")
        korean["published_at"] = korean["updated_at"] = "2026-10-18T00:00:00Z"
        spanish = self.raw("es", "blogger")
        for article in (english, korean, spanish):
            self.write(article)
        self.build()
        html = (self.root / "dist" / "posts" / "nba-preview-en" / "index.html").read_text()
        alternates = [tag for tag in Tags(html).select("link", rel="alternate") if "hreflang" in tag]
        self.assertEqual([tag["hreflang"] for tag in alternates], ["en"])
        self.assertFalse((self.root / "dist" / "posts" / "nba-preview-ko").exists())

    def test_legacy_articles_need_no_new_metadata(self):
        raw = self.raw()
        for field in ("language", "updated_at", "league", "match_id", "article_kind", "translation_group", "figures"):
            raw.pop(field)
        self.write(raw)
        self.build()
        body = (self.root / "dist" / "posts" / "nba-preview-en" / "index.html").read_text()
        self.assertIn('<html lang="en">', body)
        self.assertIn('"dateModified":"2026-10-17T12:00:00+00:00"', body)

    def test_invalid_metadata_and_unsafe_images_are_rejected(self):
        cases = [{"language": "xx"}, {"updated_at": "2026-10-16T00:00:00Z"},
                 {"figures": [{"src": "javascript:alert(1)", "alt": "Invalid"}]},
                 {"figures": [{"src": "https://media.example.test/test.svg", "alt": ""}]},
                 {"blogger_url": "https://blog.example.test/post"}, {"match_id": {"bad": "value"}}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                builder.normalize_article({**self.raw(), **changes}, Path("article.json"))

    def test_duplicate_translation_language_and_mismatched_match_are_rejected(self):
        first = builder.normalize_article(self.raw(), Path("first.json"))
        for raw in (self.raw(), {**self.raw("ko"), "match_id": "different-match"}):
            with self.subTest(raw=raw["language"]), self.assertRaises(ValueError):
                second = builder.normalize_article(raw, Path("second.json"))
                builder.connect_translations(self.config, [first, second], [first, second])

    def test_missing_shared_chart_blocks_the_build(self):
        article = self.raw()
        article["figures"][0]["src"] = "https://example.test/assets/charts/absent-test-fixture.svg"
        normalized = builder.normalize_article(article, Path("article.json"))
        with self.assertRaisesRegex(ValueError, "missing shared figure"):
            builder.chart_assets(self.config, [normalized])


if __name__ == "__main__":
    unittest.main()
