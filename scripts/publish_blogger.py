#!/usr/bin/env python3
"""Publish renderer exports through Blogger API v3, using Python's stdlib.

The default is an offline dry run. --apply creates drafts; --apply --publish
publishes existing matching drafts or creates a draft and then publishes it.
The legacy CLI never edits existing bodies. The integrated pipeline can call an
explicit hash-checked patch for an approved correction; posts are never deleted.

Identity is the SHA-256 of the JSON file stem, embedded in an HTML comment.
Keep export filenames stable. All pages of live, draft and scheduled posts are
read in AUTHOR view before any post is changed. Do not run independent writers
for the same blog concurrently: the local lock cannot serialize other machines.
Keep data/private/ out of git and public hosting. Preserve it between runs so an
uncertain insertion stays blocked until a later remote scan finds its marker.

Official API references:
https://developers.google.com/blogger/docs/3.0/reference/posts/list
https://developers.google.com/blogger/docs/3.0/reference/posts/insert
https://developers.google.com/blogger/docs/3.0/reference/posts/publish
https://developers.google.com/identity/protocols/oauth2/web-server
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Callable, Mapping
import urllib.error
import urllib.parse
import urllib.request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://www.googleapis.com/blogger/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
MARKER_PREFIX = "dual-publishing-lab:blogger:v1:"
MARKER_RE = re.compile(r"<!--\s*" + re.escape(MARKER_PREFIX) + r"([0-9a-f]{64})\s*-->")
STEM_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
ID_RE = re.compile(r"[1-9][0-9]{0,29}\Z")
KEY_RE = re.compile(r"[0-9a-f]{64}\Z")
MAX_INPUT_BYTES = 2 * 1024 * 1024  # Local operational guard, not a Blogger limit.
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class PublisherError(Exception):
    """A deliberately redacted, user-displayable failure."""

    def __init__(self, message: str, *, uncertain: bool = False):
        super().__init__(message)
        self.uncertain = uncertain


def checked_id(value: object, name: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise PublisherError(f"{name} must be a positive decimal ID.")
    return value


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublisherError("JSON contains duplicate object keys.")
        result[key] = value
    return result


@dataclass(frozen=True)
class PreparedPost:
    stem: str
    title: str
    content: str
    labels: tuple[str, ...]

    @property
    def key(self) -> str:
        return hashlib.sha256(self.stem.encode("utf-8")).hexdigest()

    @property
    def marker(self) -> str:
        return f"<!-- {MARKER_PREFIX}{self.key} -->"

    def body(self) -> dict:
        return {"title": self.title, "content": self.content + "\n" + self.marker,
                "labels": list(self.labels)}


def load_posts(input_dir: Path) -> list[PreparedPost]:
    """Validate all inputs before any network request or mutation."""
    if input_dir.is_symlink() or not input_dir.is_dir():
        raise PublisherError("Input directory must exist and must not be a symlink.")
    base = input_dir.resolve()
    posts = []
    for path in sorted(base.glob("*.json")):
        if (path.is_symlink() or not path.is_file() or path.resolve().parent != base
                or not STEM_RE.fullmatch(path.stem)):
            raise PublisherError("Exports must be regular JSON files with stable ASCII filenames.")
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise PublisherError(f"Export {path.name} exceeds the local 2 MiB input limit.")
        try:
            value = json.loads(path.read_text(encoding="utf-8"),
                               object_pairs_hook=_no_duplicate_keys)
        except (UnicodeError, json.JSONDecodeError):
            raise PublisherError(f"Export {path.name} is not valid UTF-8 JSON.") from None
        if not isinstance(value, dict):
            raise PublisherError(f"Export {path.name} must contain a JSON object.")
        title, content, labels = value.get("title"), value.get("content"), value.get("labels", [])
        if (not isinstance(title, str) or not title.strip()
                or any(ord(c) < 32 or ord(c) == 127 for c in title)):
            raise PublisherError(f"Export {path.name} needs a nonempty, single-line title.")
        if not isinstance(content, str) or not content.strip():
            raise PublisherError(f"Export {path.name} needs nonempty HTML content.")
        if MARKER_PREFIX in content:
            raise PublisherError(f"Export {path.name} uses the publisher's reserved identity marker.")
        if (not isinstance(labels, list)
                or any(not isinstance(x, str) or not x.strip()
                       or any(ord(c) < 32 or ord(c) == 127 for c in x) for x in labels)):
            raise PublisherError(f"Export {path.name} labels must be a list of nonempty strings.")
        posts.append(PreparedPost(path.stem, title, content, tuple(dict.fromkeys(labels))))
    return posts


@dataclass(frozen=True, repr=False)
class Credentials:
    blog_id: str
    client_id: str
    client_secret: str
    refresh_token: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Credentials":
        names = ("BLOGGER_BLOG_ID", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
        values = []
        for name in names:
            value = env.get(name, "").strip()
            if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise PublisherError(f"Set a valid {name} environment variable before --apply.")
            values.append(value)
        checked_id(values[0], "BLOGGER_BLOG_ID")
        return cls(*values)


class NoRedirects(urllib.request.HTTPRedirectHandler):
    """Never forward OAuth credentials or bearer headers to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class RemotePost:
    post_id: str
    status: str


class BloggerClient:
    def __init__(self, credentials: Credentials, *, timeout: float = 20.0, opener=None):
        self.credentials = credentials
        checked_id(credentials.blog_id, "BLOGGER_BLOG_ID")
        if not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise PublisherError("Network timeout must be greater than 0 and at most 120 seconds.")
        self.timeout = timeout
        self.opener = opener or urllib.request.build_opener(NoRedirects())
        self._access_token = None
        self._expires_at = 0.0

    def _json_request(self, request, operation: str, *, mutation: bool = False) -> dict:
        """One request only: neither OAuth nor post mutations are auto-retried."""
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                status = response.getcode()
                if not 200 <= status < 300:
                    raise PublisherError(f"{operation} returned an unexpected HTTP status.",
                                         uncertain=mutation)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            # Do not read or log the response body, URL, headers, or reason.
            # A redirect or transient error must not clear a pending insertion.
            # Only explicit request/auth/not-found rejections are treated as definite.
            definite_rejection = exc.code in (400, 401, 403, 404, 405, 410, 411, 413, 414, 415, 422)
            uncertain = mutation and not definite_rejection
            suffix = " Outcome is uncertain; no retry was attempted." if uncertain else " No retry was attempted."
            raise PublisherError(f"{operation} failed (HTTP {exc.code})." + suffix,
                                 uncertain=uncertain) from None
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
            raise PublisherError(f"{operation} failed during transport; no retry was attempted.",
                                 uncertain=mutation) from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise PublisherError(f"{operation} response exceeded the local size limit.", uncertain=mutation)
        try:
            result = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
        except (UnicodeError, json.JSONDecodeError, PublisherError):
            raise PublisherError(f"{operation} returned invalid JSON; no retry was attempted.",
                                 uncertain=mutation) from None
        if not isinstance(result, dict) or "error" in result:
            raise PublisherError(f"{operation} returned an unexpected result; no retry was attempted.",
                                 uncertain=mutation)
        return result

    def _token(self) -> str:
        if self._access_token and time.monotonic() < self._expires_at:
            return self._access_token
        fields = {"client_id": self.credentials.client_id,
                  "client_secret": self.credentials.client_secret,
                  "refresh_token": self.credentials.refresh_token, "grant_type": "refresh_token"}
        req = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode(fields).encode("ascii"),
                                     headers={"Content-Type": "application/x-www-form-urlencoded",
                                              "Accept": "application/json"}, method="POST")
        result = self._json_request(req, "OAuth token refresh")
        token = result.get("access_token")
        token_type = result.get("token_type", "Bearer")
        if (not isinstance(token, str) or not token
                or any(ord(c) <= 32 or ord(c) >= 127 for c in token)
                or not isinstance(token_type, str) or token_type.lower() != "bearer"):
            raise PublisherError("OAuth token refresh did not return a valid bearer token.")
        expires = result.get("expires_in", 3600)
        if isinstance(expires, bool) or not isinstance(expires, (int, float)) or not math.isfinite(expires) or expires <= 0:
            raise PublisherError("OAuth token refresh returned an invalid lifetime.")
        self._access_token = token
        self._expires_at = time.monotonic() + max(1, expires - 60)
        return token

    def _call(self, method: str, suffix: str, *, query=None, body=None, operation: str):
        url = f"{API_BASE}/blogs/{self.credentials.blog_id}/posts{suffix}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Authorization": "Bearer " + self._token(), "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        return self._json_request(urllib.request.Request(url, data=data, headers=headers, method=method),
                                  operation, mutation=(method in ("POST", "PATCH")))

    def existing_posts(self) -> dict[str, RemotePost]:
        """A complete AUTHOR-view inventory; fail closed on incomplete or conflicting data."""
        by_key = {}
        seen_ids = {}
        for status in ("live", "draft", "scheduled"):
            page_token = None
            seen_tokens = set()
            while True:
                query = {"status": status, "view": "AUTHOR", "fetchBodies": "true", "maxResults": 100}
                if page_token is not None:
                    query["pageToken"] = page_token
                result = self._call("GET", "", query=query, operation=f"List {status} posts")
                items = result.get("items", [])
                if not isinstance(items, list):
                    raise PublisherError("Remote inventory contains an invalid item list; no posts changed.")
                for item in items:
                    if not isinstance(item, dict) or not isinstance(item.get("content"), str):
                        raise PublisherError("Remote inventory lacks post bodies; no posts changed.")
                    post_id = checked_id(item.get("id"), "Remote post ID")
                    if post_id in seen_ids and seen_ids[post_id] != status:
                        raise PublisherError("Remote post status changed during inventory; rerun after other writers stop.")
                    seen_ids[post_id] = status
                    keys = set(MARKER_RE.findall(item["content"]))
                    if len(keys) > 1 or (MARKER_PREFIX in item["content"] and not keys):
                        raise PublisherError("A remote post has an invalid identity marker; no posts changed.")
                    for key in keys:
                        if key in by_key and by_key[key].post_id != post_id:
                            raise PublisherError("Duplicate remote identity markers found; no posts changed.")
                        by_key[key] = RemotePost(post_id, status)
                next_token = result.get("nextPageToken")
                if next_token in (None, ""):
                    break
                if not isinstance(next_token, str) or next_token in seen_tokens:
                    raise PublisherError("Remote pagination is invalid or repeated; no posts changed.")
                seen_tokens.add(next_token)
                page_token = next_token
        return by_key

    def inventory_details(self) -> list[dict]:
        """AUTHOR inventory including legacy unmarked posts for cross-platform preflight."""
        records = {}
        for status in ("live", "draft", "scheduled"):
            token = None
            seen = set()
            while True:
                query = {"status": status, "view": "AUTHOR", "fetchBodies": "true", "maxResults": 100}
                if token:
                    query["pageToken"] = token
                page = self._call("GET", "", query=query, operation="Read publication inventory")
                if not isinstance(page.get("items", []), list):
                    raise PublisherError("Invalid publication inventory")
                for row in page.get("items", []):
                    post_id = checked_id(row.get("id"), "Post ID")
                    if not isinstance(row.get("content"), str) or post_id in records:
                        raise PublisherError("Conflicting/incomplete publication inventory")
                    records[post_id] = {**row, "status": status}
                token = page.get("nextPageToken")
                if not token:
                    break
                if not isinstance(token, str) or token in seen:
                    raise PublisherError("Invalid publication pagination")
                seen.add(token)
        return list(records.values())

    def get_post(self, post_id: str) -> dict:
        checked_id(post_id, "Post ID")
        return self._call("GET", f"/{post_id}", query={"view": "AUTHOR"}, operation="Read existing post")

    def patch(self, post_id: str, post: PreparedPost, expected_hash: str) -> RemotePost:
        """Explicit correction only; preserve post ID. Caller keeps one persistent writer.

        Compare the live body before the write; never reinterpret a failed PATCH as
        authorization to insert. The pipeline also binds this action to release SHA.
        """
        current = self.get_post(post_id)
        material = {k: current.get(k) for k in ("title", "content", "labels")}
        digest = hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
        if digest != expected_hash:
            raise PublisherError("Existing post changed since preflight; correction held")
        result = self._call("PATCH", f"/{post_id}", body=post.body(), operation="Update existing post")
        if result.get("id") != post_id or set(MARKER_RE.findall(result.get("content", ""))) != {post.key}:
            raise PublisherError("Correction response uncertain; do not insert another post", uncertain=True)
        return RemotePost(post_id, str(result.get("status", "LIVE")).lower())

    def insert_draft(self, post: PreparedPost) -> RemotePost:
        result = self._call("POST", "", query={"isDraft": "true"}, body=post.body(), operation="Insert draft")
        try:
            post_id = checked_id(result.get("id"), "Created post ID")
        except PublisherError:
            raise PublisherError("Draft creation returned no valid ID; outcome is uncertain.", uncertain=True) from None
        content = result.get("content")
        status = result.get("status", "DRAFT")
        if (not isinstance(content, str) or set(MARKER_RE.findall(content)) != {post.key}
                or not isinstance(status, str) or status.upper() != "DRAFT"):
            raise PublisherError("Draft identity could not be verified; do not recreate the post.", uncertain=True)
        return RemotePost(post_id, "draft")

    def publish(self, post_id: str) -> RemotePost:
        checked_id(post_id, "Post ID")
        # posts.publish requires an empty body, not a JSON object.
        result = self._call("POST", f"/{post_id}/publish", operation="Publish draft")
        status = result.get("status", "LIVE")
        if result.get("id") != post_id or not isinstance(status, str) or status.upper() != "LIVE":
            raise PublisherError("Publish response could not be verified; outcome is uncertain.", uncertain=True)
        return RemotePost(post_id, "live")


def _private_directory(path: Path) -> Path:
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise PublisherError("Private state directory cannot use symbolic links.")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise PublisherError("Private state path must be a directory.")
    path.chmod(0o700)
    return path.resolve()


def _write_private_json(path: Path, value: dict):
    if path.is_symlink():
        raise PublisherError("Private output file cannot be a symbolic link.")
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".blogger-", delete=False) as handle:
            temp_name = handle.name
            os.chmod(temp_name, 0o600)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name:
            os.unlink(temp_name)


@contextmanager
def blog_lock(state_dir: Path, blog_id: str):
    try:
        import fcntl
    except ImportError:
        raise PublisherError("--apply requires POSIX file locking; run on Linux or macOS.") from None
    lock_path = state_dir / f"blogger-{checked_id(blog_id, 'Blog ID')}.lock"
    if lock_path.is_symlink():
        raise PublisherError("Private lock file cannot be a symbolic link.")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PublisherError("Another local publisher is running for this blog.") from None
        yield
    finally:
        os.close(fd)


class Journal:
    """Persist intent before a POST; unresolved insertions must not be replayed."""

    def __init__(self, state_dir: Path, blog_id: str):
        self.blog_id = checked_id(blog_id, "Blog ID")
        self.path = state_dir / f"blogger-{blog_id}.state.json"
        self.pending = {}
        if self.path.is_symlink():
            raise PublisherError("Private state file cannot be a symbolic link.")
        if self.path.exists():
            try:
                if self.path.stat().st_size > MAX_INPUT_BYTES:
                    raise ValueError()
                data = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)
                if (not isinstance(data, dict) or data.get("version") != 1
                        or data.get("blog_id") != blog_id or not isinstance(data.get("pending"), dict)):
                    raise ValueError()
                for key, item in data["pending"].items():
                    if (not KEY_RE.fullmatch(key) or not isinstance(item, dict)
                            or item.get("operation") not in ("insert", "publish")):
                        raise ValueError()
                    if item.get("post_id") is not None:
                        checked_id(item["post_id"], "Journal post ID")
                self.pending = data["pending"]
            except (ValueError, UnicodeError, PublisherError):
                raise PublisherError("Private journal is invalid; inspect it before publishing.") from None

    def _save(self):
        _write_private_json(self.path, {"version": 1, "blog_id": self.blog_id, "pending": self.pending})

    def begin(self, key: str, operation: str, post_id: str | None = None):
        self.pending[key] = {"operation": operation, "post_id": post_id,
                             "started_at": datetime.now(timezone.utc).isoformat()}
        self._save()

    def clear(self, key: str):
        if key in self.pending:
            del self.pending[key]
            self._save()


def apply_posts(client: BloggerClient, posts: list[PreparedPost], journal: Journal, *,
                publish: bool, on_result: Callable[[dict], None]):
    existing = client.existing_posts()
    # Preflight every selected identity before changing any post in this batch.
    for post in posts:
        pending = journal.pending.get(post.key)
        remote = existing.get(post.key)
        if pending and remote is None:
            raise PublisherError(f"Unresolved prior mutation for {post.stem}; no matching remote marker found. "
                                 "Inspect Blogger and preserve the private journal before retrying.", uncertain=True)
        if pending and pending.get("post_id") and pending["post_id"] != remote.post_id:
            raise PublisherError("Journal and remote post ID disagree; no posts changed.")
    for post in posts:
        remote = existing.get(post.key)
        created = False
        if remote is None:
            journal.begin(post.key, "insert")
            try:
                remote = client.insert_draft(post)
            except PublisherError as exc:
                if not exc.uncertain:
                    journal.clear(post.key)
                raise
            created = True
            existing[post.key] = remote
        if publish and remote.status == "draft":
            journal.begin(post.key, "publish", remote.post_id)
            try:
                remote = client.publish(remote.post_id)
            except PublisherError as exc:
                if not exc.uncertain:
                    journal.clear(post.key)
                raise
            action = "published_new" if created else "published_existing_draft"
        else:
            action = "created_draft" if created else f"skipped_existing_{remote.status}"
        journal.clear(post.key)
        on_result({"file": post.stem + ".json", "action": action, "post_id": remote.post_id,
                   "status": remote.status})


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", type=Path, default=PROJECT_ROOT / "exports" / "blogger")
    parser.add_argument("--apply", action="store_true", help="Allow remote writes; otherwise list prepared posts offline.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--draft", dest="publish", action="store_false", help="Create drafts only (default).")
    target.add_argument("--publish", dest="publish", action="store_true", help="Publish matching drafts after --apply.")
    parser.set_defaults(publish=False)
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-request timeout in seconds (0 < value <= 120).")
    parser.add_argument("--state-dir", type=Path, default=PROJECT_ROOT / "data" / "private",
                        help="Private, gitignored, persistent journal directory for --apply.")
    parser.add_argument("--report", action="store_true", help="Also save a redacted private result report (--apply only).")
    return parser


def main(argv=None, *, environ=None, opener=None, stdout=None, stderr=None) -> int:
    args = build_parser().parse_args(argv)
    out, err = stdout or sys.stdout, stderr or sys.stderr
    report = {"ok": False, "mode": "apply" if args.apply else "dry-run",
              "target": "publish" if args.publish else "draft", "results": []}
    state_dir = None
    credentials = None
    report_path = None

    def emit(result):
        report["results"].append(result)
        print(json.dumps(result, ensure_ascii=False), file=out, flush=True)

    try:
        posts = load_posts(args.input_dir)
        if not args.apply:
            for post in posts:
                emit({"file": post.stem + ".json", "title": post.title, "action": "prepared",
                      "target": report["target"]})
            print(json.dumps({"mode": "dry-run", "prepared": len(posts), "network_used": False}), file=out)
            return 0
        if not posts:
            print(json.dumps({"mode": "apply", "prepared": 0, "network_used": False}), file=out)
            return 0
        credentials = Credentials.from_env(os.environ if environ is None else environ)
        client = BloggerClient(credentials, timeout=args.timeout, opener=opener)
        state_dir = _private_directory(args.state_dir)
        if args.report:
            report_path = state_dir / f"blogger-{credentials.blog_id}.report.json"
            if report_path.is_symlink():
                raise PublisherError("Private report file cannot be a symbolic link.")
        with blog_lock(state_dir, credentials.blog_id):
            journal = Journal(state_dir, credentials.blog_id)
            try:
                apply_posts(client, posts, journal, publish=args.publish, on_result=emit)
                report["ok"] = True
            except PublisherError as exc:
                report["error"] = str(exc)
                report["uncertain"] = exc.uncertain
                raise
            finally:
                if report_path:
                    _write_private_json(report_path, report)
        return 0
    except PublisherError as exc:
        print("Blogger publisher: " + str(exc), file=err)
        return 1
    except OSError:
        print("Blogger publisher: local I/O failed; preserve private state and inspect file permissions.", file=err)
        return 1
    except KeyboardInterrupt:
        print("Blogger publisher: interrupted; preserve private state before another run.", file=err)
        return 130
    except Exception:
        # Never let arbitrary server error details or credential-bearing objects reach logs.
        print("Blogger publisher: unexpected failure; no automatic retry was attempted.", file=err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
