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

    def test_league_indexes_filter_language_and_league_and_link_both_platforms(self):
        for code in builder.LANGUAGES:
            self.write(self.raw(code))
            recap = self.raw(code, "blogger", "nba-recap")
            recap["article_kind"] = "recap"
            recap["blogger_url"] = f"https://blog.example.test/2026/10/nba-recap-{code.lower()}.html"
            self.write(recap)
            epl = self.raw(code, "github", "epl-preview")
            epl["league"] = "EPL"
            self.write(epl)
        unconfirmed = self.raw("en", "blogger", "nba-unconfirmed")
        future = self.raw("en", "github", "nba-future")
        future["published_at"] = future["updated_at"] = "2026-10-18T00:00:00Z"
        draft = self.raw("en", "github", "nba-draft")
        draft["status"] = "draft"
        for article in (unconfirmed, future, draft):
            self.write(article)
        self.build()
        expected = {(code, "https://example.test/" + ("" if code == "en" else f"languages/{code}/") + "leagues/nba/")
                    for code in builder.LANGUAGES}
        sitemap = ET.parse(self.root / "dist" / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        sitemap_urls = {node.text for node in sitemap.findall("s:url/s:loc", ns)}
        for code in builder.LANGUAGES:
            path = "leagues/nba/" if code == "en" else f"languages/{code}/leagues/nba/"
            body = (self.root / "dist" / path / "index.html").read_text()
            tags = Tags(body)
            with self.subTest(language=code):
                self.assertEqual(tags.select("html")[0]["lang"], code)
                self.assertEqual(tags.select("link", rel="canonical")[0]["href"], "https://example.test/" + path)
                alternates = {(tag["hreflang"], tag["href"]) for tag in tags.select("link", rel="alternate") if "hreflang" in tag}
                self.assertEqual(alternates, expected)
                self.assertEqual(len(tags.select("article", **{"class": "post-card"})), 2)
                self.assertIn(f"nba-preview title {code}", body)
                self.assertIn(f"nba-recap title {code}", body)
                self.assertNotIn("epl-preview title", body)
                self.assertNotIn("nba-unconfirmed title", body)
                self.assertNotIn("nba-future title", body)
                self.assertNotIn("nba-draft title", body)
                self.assertNotIn("Verified nba-recap text", body)
                self.assertIn(f'href="https://blog.example.test/2026/10/nba-recap-{code.lower()}.html"', body)
                self.assertTrue(tags.select("h2", id="previews"))
                self.assertTrue(tags.select("h2", id="results"))
                self.assertIn("https://example.test/" + path, sitemap_urls)
                self.assertFalse((self.root / "dist" / "posts" / f"nba-recap-{code.lower()}").exists())
                prefix = "../../" if code == "en" else "../../../../"
                self.assertIn(f'href="{prefix}posts/nba-preview-{code.lower()}/"', body)
                self.assertIn(f'href="{prefix}{path}" aria-current="page"', body)
        korean = (self.root / "dist" / "languages/ko/leagues/nba/index.html").read_text()
        self.assertNotIn("nba-preview title en", korean)
        self.assertIn('href="../../../../languages/ko/leagues/premier-league/"', korean)
        article_body = (self.root / "dist" / "posts/nba-preview-ko/index.html").read_text()
        self.assertIn('href="../../languages/ko/leagues/nba/" aria-current="location"', article_body)
        self.assertIn('"articleSection":"NBA"', article_body)

    def test_new_league_configuration_creates_categories_with_name_fallback(self):
        self.config["leagues"] = {"MLB": {"slug": "mlb", "names": {"en": "Major League Baseball", "ko": "메이저리그"}}}
        (self.root / "config.json").write_text(json.dumps(self.config), encoding="utf-8")
        for code in ("ko", "hi"):
            article = self.raw(code, "github", "mlb-recap")
            article["league"] = "MLB"
            article["article_kind"] = "recap"
            self.write(article)
        self.build()
        korean = (self.root / "dist" / "languages/ko/leagues/mlb/index.html").read_text()
        hindi = (self.root / "dist" / "languages/hi/leagues/mlb/index.html").read_text()
        self.assertIn("<h1>메이저리그</h1>", korean)
        self.assertIn("<h1>Major League Baseball</h1>", hindi)
        self.assertFalse((self.root / "dist" / "leagues/nba").exists())
        self.assertFalse((self.root / "dist" / "leagues/mlb").exists())  # No empty English category.
        self.assertNotIn('href="../../../../leagues/nba/"', hindi)
        with self.assertRaisesRegex(ValueError, "league slugs must be unique"):
            builder.normalize_leagues({"MLB": {"slug": "nba", "names": {"en": "Major League Baseball"}}})
        with self.assertRaisesRegex(ValueError, "requires an English fallback"):
            builder.normalize_leagues({"MLB": {"slug": "mlb", "names": {"ko": "메이저리그"}}})

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


    def sample_comparison(self):
        return {
            "as_of": "2026-10-17T11:00:00Z", "scope": "Last verified league games",
            "sources": {
                "recent": {"title": "Official form", "url": "https://source.example.test/form"},
                "head_to_head": {"title": "Official meetings", "url": "https://source.example.test/h2h"}},
            "home": {"name": "Blue", "recent": [
                {"date": "2026-10-16", "opponent": "Rival <A>", "for": 102, "against": 99},
                {"date": "2026-10-14", "opponent": "Rival B", "for": 100, "against": 110},
                {"date": "2026-10-12", "opponent": "Rival C", "for": 110, "against": 100}]},
            "away": {"name": "Orange", "recent": [
                {"date": "2026-10-15", "opponent": "Other A", "for": 99, "against": 105},
                {"date": "2026-10-13", "opponent": "Other B", "for": 111, "against": 100}]},
            "head_to_head": [
                {"date": "2026-10-10", "home_team": "Blue", "away_team": "Orange", "home_score": 102, "away_score": 99},
                {"date": "2026-10-05", "home_team": "Orange", "away_team": "Blue", "home_score": 105, "away_score": 110},
                {"date": "2026-10-01", "home_team": "Orange", "away_team": "Blue", "home_score": 108, "away_score": 100}
            ]}

    def test_preview_html_form_and_meetings_are_score_derived(self):
        article = self.raw()
        article["preview_comparison"] = self.sample_comparison()
        self.write(article)
        self.build()
        page = (self.root / "dist" / "posts" / "nba-preview-en" / "index.html").read_text()
        self.assertIn('class="qi-comparison"', page)
        self.assertIn("66.7%", page)   # 2 out of 3 recent games won by Blue
        self.assertIn("50%", page)     # Orange won 1 out of 2 recent games
        self.assertIn("33.3%", page)   # Orange won 1 out of 3 meetings
        self.assertIn("Rival &lt;A&gt;", page)
        self.assertNotIn("Rival <A>", page)
        self.assertIn('role="meter"', page)
        self.assertIn("Historical rates, not predictions", page)

    def test_preview_comparison_checks_phase_restricted_article_and_score(self):
        raw = self.raw()
        raw["preview_comparison"] = self.sample_comparison()
        for key, value in (("article_kind", "recap"), ("league", "OTHER")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                builder.normalize_article({**raw, key: value}, Path("test.json"))
        invalid = self.sample_comparison()
        invalid["home"]["recent"][0]["for"] = "fake"
        with self.assertRaises(ValueError):
            builder.normalize_article({**raw, "preview_comparison": invalid}, Path("test.json"))
        invalid = self.sample_comparison()
        invalid["head_to_head"][0]["away_team"] = "Unrelated"
        with self.assertRaises(ValueError):
            builder.normalize_article({**raw, "preview_comparison": invalid}, Path("test.json"))

    def test_epl_draw_rates_and_reversed_historical_venues(self):
        raw = self.raw()
        raw["league"] = "EPL"
        data = self.sample_comparison()
        data["home"]["recent"][0]["for"] = 99
        data["head_to_head"][0]["away_score"] = 102
        raw["preview_comparison"] = data
        n = builder.normalize_article(raw, Path("test.json"))
        output = builder.preview_comparison_html(n["preview_comparison"], "ko")
        self.assertIn("양팀 맞대결", output)
        self.assertIn("33.3%", output)
        self.assertIn('class="qi-h2h-draw"', output)

    def test_blogger_comparison_is_html_with_css(self):
        raw = self.raw(platform="blogger")
        raw["preview_comparison"] = self.sample_comparison()
        n = builder.normalize_article(raw, Path("test.json"))
        body = builder.blogger_payload(n, self.config)["content"]
        self.assertIn("<style>", body)
        self.assertIn(".qi-compare-grid", body)
        self.assertIn("qi-h2h-bar", body)

    def test_insufficient_samples_never_claim_zero_win_rate(self):
        raw = self.raw()
        data = self.sample_comparison()
        data["home"]["recent"] = []
        data["head_to_head"] = []
        raw["preview_comparison"] = data
        n = builder.normalize_article(raw, Path("test.json"))
        html = builder.preview_comparison_html(n["preview_comparison"], "en")
        self.assertIn("No verified games", html)
        self.assertNotIn("0%", html)



if __name__ == "__main__":
    unittest.main()
