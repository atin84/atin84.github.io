"""Behavioral tests: no real credentials, network calls, or Blogger writes."""

from contextlib import redirect_stderr
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publish_blogger.py"
spec = importlib.util.spec_from_file_location("publish_blogger_under_test", MODULE_PATH)
publisher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = publisher
spec.loader.exec_module(publisher)

ENV = {"BLOGGER_BLOG_ID": "123456", "GOOGLE_CLIENT_ID": "test-client-id",
       "GOOGLE_CLIENT_SECRET": "SECRET_CLIENT_DO_NOT_LOG",
       "GOOGLE_REFRESH_TOKEN": "SECRET_REFRESH_DO_NOT_LOG"}
TOKEN = "ya29.SECRET_ACCESS_DO_NOT_LOG"


class Response:
    def __init__(self, body):
        self.raw = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return 200

    def read(self, count):
        return self.raw[:count]


class FakeGoogle:
    """A stateful API double, including mutations committed before a timeout."""

    def __init__(self):
        self.posts = {"live": [], "draft": [], "scheduled": []}
        self.calls = []
        self.page_size = 100
        self.fail_insert = None
        self.fail_publish = False
        self.fail_token = False
        self.hide_posts = False
        self.strip_marker = False
        self.loop_pagination = False
        self.fail_status = None

    @property
    def writes(self):
        return [x for x in self.calls if x["method"] != "GET" and x["url"].startswith(publisher.API_BASE)]

    def add(self, post, *, status="draft", post_id="900"):
        item = {"id": post_id, "content": post.content + "\n" + post.marker,
                "title": "Original title", "status": status.upper()}
        self.posts[status].append(item)
        return item

    def open(self, req, *, timeout):
        call = {"method": req.get_method(), "url": req.full_url, "data": req.data,
                "headers": dict(req.header_items()), "timeout": timeout}
        self.calls.append(call)
        if req.full_url == publisher.TOKEN_URL:
            if self.fail_token:
                raise urllib.error.HTTPError(req.full_url + "?secret=" + ENV["GOOGLE_CLIENT_SECRET"],
                                             401, ENV["GOOGLE_REFRESH_TOKEN"], {}, io.BytesIO(TOKEN.encode()))
            return Response({"access_token": TOKEN, "token_type": "Bearer", "expires_in": 3600})
        url = urllib.parse.urlsplit(req.full_url)
        query = urllib.parse.parse_qs(url.query)
        if req.get_method() == "GET":
            status = query["status"][0]
            if self.fail_status == status:
                raise urllib.error.HTTPError(req.full_url, 403, "No author access", {}, io.BytesIO(b"secret body"))
            items = [] if self.hide_posts else self.posts[status]
            start = int(query.get("pageToken", ["0"])[0])
            body = {"items": items[start:start + self.page_size]}
            if self.loop_pagination:
                body["nextPageToken"] = "1"
            elif start + self.page_size < len(items):
                body["nextPageToken"] = str(start + self.page_size)
            return Response(body)
        if req.get_method() != "POST":
            raise AssertionError("Unexpected destructive/update method")
        if url.path.endswith("/publish"):
            post_id = url.path.split("/")[-2]
            found = next(p for p in self.posts["draft"] if p["id"] == post_id)
            self.posts["draft"].remove(found)
            found["status"] = "LIVE"
            self.posts["live"].append(found)
            if self.fail_publish:
                self.fail_publish = False
                raise urllib.error.URLError(TOKEN)
            return Response(found)
        if query.get("isDraft") != ["true"]:
            raise AssertionError("New posts must always be inserted as drafts")
        body = json.loads(req.data)
        body["id"] = str(1000 + sum(len(x) for x in self.posts.values()))
        body["status"] = "DRAFT"
        if self.strip_marker:
            body["content"] = publisher.MARKER_RE.sub("", body["content"])
        self.posts["draft"].append(body)
        if self.fail_insert == "timeout_after_commit":
            self.fail_insert = None
            raise TimeoutError(ENV["GOOGLE_CLIENT_SECRET"])
        if self.fail_insert == "503_after_commit":
            self.fail_insert = None
            raise urllib.error.HTTPError(req.full_url, 503, TOKEN, {}, io.BytesIO(TOKEN.encode()))
        if self.fail_insert == "redirect_after_commit":
            self.fail_insert = None
            raise urllib.error.HTTPError(req.full_url, 307, TOKEN,
                                         {"Location": "https://untrusted.example/collect"}, io.BytesIO())
        return Response(body)


class BloggerPublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exports = self.root / "exports"
        self.exports.mkdir()
        self.state_dir = self.root / "private"
        self.google = FakeGoogle()
        self.write_export("sample-article", title="검증된 테스트 글", content="<p>Prepared HTML</p>")

    def write_export(self, stem, **values):
        payload = {"title": "Prepared title", "content": "<p>Prepared</p>", "labels": ["테스트"]}
        payload.update(values)
        (self.exports / f"{stem}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def prepared(self, index=0):
        return publisher.load_posts(self.exports)[index]

    def run_cli(self, *flags, environ=None):
        out, err = io.StringIO(), io.StringIO()
        code = publisher.main(["--input-dir", str(self.exports), "--state-dir", str(self.state_dir), *flags],
                              environ=ENV if environ is None else environ, opener=self.google,
                              stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def pending(self):
        path = self.state_dir / "blogger-123456.state.json"
        return json.loads(path.read_text())["pending"]

    def test_default_is_offline_dry_run_without_credentials_or_private_files(self):
        code, out, err = self.run_cli(environ={})
        self.assertEqual(code, 0, err)
        self.assertIn("검증된 테스트 글", out)
        self.assertIn('"target": "draft"', out)
        self.assertIn('"network_used": false', out)
        self.assertEqual(self.google.calls, [])
        self.assertFalse(self.state_dir.exists())

    def test_publish_flag_without_apply_remains_offline(self):
        code, out, err = self.run_cli("--publish", environ={})
        self.assertEqual(code, 0, err)
        self.assertIn('"target": "publish"', out)
        self.assertEqual(self.google.calls, [])

    def test_apply_creates_only_a_draft_with_correct_oauth_and_no_secret_logs(self):
        code, out, err = self.run_cli("--apply", "--report", "--timeout", "7")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.google.writes), 1)
        self.assertEqual(len(self.google.posts["draft"]), 1)
        self.assertEqual(self.google.posts["live"], [])
        posted = json.loads(self.google.writes[0]["data"])
        self.assertEqual(posted["content"].count(self.prepared().marker), 1)
        self.assertEqual(set(posted), {"title", "content", "labels"})
        oauth = urllib.parse.parse_qs(self.google.calls[0]["data"].decode())
        self.assertEqual(oauth["grant_type"], ["refresh_token"])
        self.assertEqual(oauth["client_secret"], [ENV["GOOGLE_CLIENT_SECRET"]])
        self.assertTrue(all(x["timeout"] == 7 for x in self.google.calls))
        self.assertTrue(all("secret=" not in x["url"] for x in self.google.calls))
        self.assertEqual(self.pending(), {})
        report = (self.state_dir / "blogger-123456.report.json").read_text()
        for secret in (TOKEN, ENV["GOOGLE_CLIENT_SECRET"], ENV["GOOGLE_REFRESH_TOKEN"]):
            self.assertNotIn(secret, out + err + report)
        if os.name == "posix":
            self.assertEqual((self.state_dir / "blogger-123456.report.json").stat().st_mode & 0o777, 0o600)

    def test_paginated_author_inventory_covers_all_states_before_skipping_existing_draft(self):
        self.google.page_size = 1
        other = publisher.PreparedPost("other", "Other", "<p>Other</p>", ())
        self.google.add(other, post_id="800")
        self.google.add(self.prepared(), post_id="901")
        code, out, err = self.run_cli("--apply")
        self.assertEqual(code, 0, err)
        self.assertIn("skipped_existing_draft", out)
        self.assertEqual(self.google.writes, [])
        queries = [urllib.parse.parse_qs(urllib.parse.urlsplit(x["url"]).query)
                   for x in self.google.calls if x["method"] == "GET"]
        self.assertEqual({q["status"][0] for q in queries}, {"live", "draft", "scheduled"})
        self.assertTrue(all(q["view"] == ["AUTHOR"] and q["fetchBodies"] == ["true"] for q in queries))
        self.assertTrue(any(q.get("pageToken") == ["1"] for q in queries))

    def test_existing_live_and_scheduled_posts_are_not_modified(self):
        for status in ("live", "scheduled"):
            with self.subTest(status=status):
                self.google = FakeGoogle()
                original = self.google.add(self.prepared(), status=status)
                before = dict(original)
                code, out, err = self.run_cli("--apply", "--publish")
                self.assertEqual(code, 0, err)
                self.assertEqual(self.google.writes, [])
                self.assertEqual(original, before)
                self.assertIn("skipped_existing_" + status, out)

    def test_existing_draft_is_published_without_inserting_or_updating_content(self):
        original = self.google.add(self.prepared(), post_id="777")
        original_content = original["content"]
        self.write_export("sample-article", title="Changed locally", content="<p>Changed locally</p>")
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.google.writes), 1)
        self.assertTrue(self.google.writes[0]["url"].endswith("/posts/777/publish"))
        self.assertIsNone(self.google.writes[0]["data"])
        self.assertEqual(self.google.posts["live"][0]["content"], original_content)
        self.assertIn("published_existing_draft", out)

    def test_new_publish_uses_two_steps_and_rerun_does_not_duplicate(self):
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.google.writes), 2)
        self.assertIn("isDraft=true", self.google.writes[0]["url"])
        self.assertTrue(self.google.writes[1]["url"].endswith("/publish"))
        self.assertIn("published_new", out)
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.google.writes), 2)
        self.assertEqual(len(self.google.posts["live"]), 1)

    def test_timeout_after_insert_is_not_retried_and_later_remote_scan_recovers(self):
        self.google.fail_insert = "timeout_after_commit"
        code, out, err = self.run_cli("--apply", "--publish", "--report")
        self.assertEqual(code, 1)
        self.assertEqual(len(self.google.writes), 1)
        self.assertEqual(len(self.google.posts["draft"]), 1)
        self.assertTrue(self.pending())
        report = json.loads((self.state_dir / "blogger-123456.report.json").read_text())
        self.assertTrue(report["uncertain"])
        self.assertNotIn(ENV["GOOGLE_CLIENT_SECRET"], out + err + json.dumps(report))
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.google.writes), 2)  # A publish, never a second insertion.
        self.assertTrue(self.google.writes[-1]["url"].endswith("/publish"))
        self.assertEqual(len(self.google.posts["live"]), 1)
        self.assertEqual(self.pending(), {})

    def test_uncertain_insert_still_hidden_in_later_scan_stops_before_any_new_post(self):
        self.google.fail_insert = "503_after_commit"
        self.assertEqual(self.run_cli("--apply")[0], 1)
        self.google.hide_posts = True
        self.write_export("aaa-new-article")
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 1)
        self.assertIn("Unresolved prior mutation", err)
        self.assertEqual(len(self.google.writes), 1)
        self.assertTrue(self.pending())

    def test_timeout_after_publish_does_not_retry_and_live_post_is_skipped_on_rerun(self):
        self.google.add(self.prepared(), post_id="888")
        self.google.fail_publish = True
        self.assertEqual(self.run_cli("--apply", "--publish")[0], 1)
        self.assertEqual(len(self.google.writes), 1)
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 0, err)
        self.assertIn("skipped_existing_live", out)
        self.assertEqual(len(self.google.writes), 1)

    def test_mutation_redirect_is_not_followed_or_treated_as_a_safe_retry(self):
        self.google.fail_insert = "redirect_after_commit"
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 307", err)
        self.assertTrue(self.pending())
        self.assertEqual(len(self.google.writes), 1)
        self.assertFalse(any("untrusted.example" in call["url"] for call in self.google.calls))

    def test_duplicate_remote_markers_fail_without_post_mutations(self):
        self.google.add(self.prepared(), status="live", post_id="700")
        self.google.add(self.prepared(), status="draft", post_id="701")
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 1)
        self.assertIn("Duplicate remote identity", err)
        self.assertEqual(self.google.writes, [])

    def test_incomplete_author_scan_blocks_all_mutations(self):
        self.google.fail_status = "scheduled"
        code, out, err = self.run_cli("--apply")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 403", err)
        self.assertEqual(self.google.writes, [])

    def test_repeated_pagination_token_fails_without_infinite_loop_or_mutation(self):
        self.google.loop_pagination = True
        code, out, err = self.run_cli("--apply")
        self.assertEqual(code, 1)
        self.assertIn("pagination", err)
        self.assertEqual(len(self.google.calls), 3)  # Token plus two list requests.
        self.assertEqual(self.google.writes, [])

    def test_missing_body_or_unsafe_remote_id_blocks_mutations(self):
        for item in ({"id": "1"}, {"id": "123/../../posts", "content": "<p>test</p>"}):
            with self.subTest(item=item):
                self.google = FakeGoogle()
                self.google.posts["draft"].append(item)
                self.assertEqual(self.run_cli("--apply")[0], 1)
                self.assertEqual(self.google.writes, [])

    def test_lost_marker_in_insert_response_blocks_publish_and_recreation(self):
        self.google.strip_marker = True
        code, out, err = self.run_cli("--apply", "--publish")
        self.assertEqual(code, 1)
        self.assertIn("identity could not be verified", err)
        self.assertEqual(len(self.google.writes), 1)
        self.assertEqual(self.run_cli("--apply", "--publish")[0], 1)
        self.assertEqual(len(self.google.writes), 1)

    def test_invalid_blog_id_and_malformed_exports_never_connect(self):
        env = dict(ENV, BLOGGER_BLOG_ID="123/../../other-blog")
        self.assertEqual(self.run_cli("--apply", environ=env)[0], 1)
        self.assertEqual(self.google.calls, [])
        self.write_export("bad-article", labels="not-a-list")
        self.assertEqual(self.run_cli("--apply")[0], 1)
        self.assertEqual(self.google.calls, [])

    def test_duplicate_input_keys_and_reserved_markers_fail_offline(self):
        bad = self.exports / "bad.json"
        bad.write_text('{"title":"one","title":"two","content":"text"}', encoding="utf-8")
        self.assertEqual(self.run_cli()[0], 1)
        bad.unlink()
        self.write_export("bad", content="<p>" + publisher.MARKER_PREFIX + "</p>")
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.google.calls, [])

    def test_export_symlink_is_rejected_before_credentials_or_network(self):
        outside = self.root / "outside.json"
        outside.write_text('{"title":"outside","content":"private"}', encoding="utf-8")
        (self.exports / "linked.json").symlink_to(outside)
        self.assertEqual(self.run_cli("--apply")[0], 1)
        self.assertEqual(self.google.calls, [])

    def test_local_concurrent_apply_is_rejected(self):
        state_dir = publisher._private_directory(self.state_dir)
        with publisher.blog_lock(state_dir, ENV["BLOGGER_BLOG_ID"]):
            code, out, err = self.run_cli("--apply")
        self.assertEqual(code, 1)
        self.assertIn("Another local publisher", err)
        self.assertEqual(self.google.calls, [])

    def test_oauth_error_does_not_expose_response_body_reason_or_url_secrets(self):
        self.google.fail_token = True
        code, out, err = self.run_cli("--apply", "--report")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 401", err)
        report = (self.state_dir / "blogger-123456.report.json").read_text()
        for secret in (TOKEN, ENV["GOOGLE_CLIENT_SECRET"], ENV["GOOGLE_REFRESH_TOKEN"]):
            self.assertNotIn(secret, out + err + report)
        self.assertEqual(len(self.google.calls), 1)

    def test_redirect_handler_refuses_to_forward_bearer_request(self):
        request = publisher.urllib.request.Request(publisher.API_BASE + "/blogs/123/posts",
                                                  headers={"Authorization": "Bearer " + TOKEN})
        handler = publisher.NoRedirects()
        self.assertIsNone(handler.redirect_request(request, None, 307, "redirect", {},
                                                  "https://untrusted.example/collect"))

    def test_draft_and_publish_are_mutually_exclusive(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            publisher.main(["--draft", "--publish"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
