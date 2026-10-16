#!/usr/bin/env python3
"""The only GitHub entry point for handling-review-findings (#580).

The skill used to hold broad `gh api graphql`, `gh api .../pulls/*/comments`, `gh pr comment`,
`gh issue create`, `gh api user` and `sed` grants, which also allow GraphQL mutations such as
`mergePullRequest`, arbitrary comment bodies and, via GNU sed's `e` command, arbitrary commands.
This script replaces them with fixed subcommands. Each runs exactly one `gh` (or `git`) call built
from a static argv (no shell), so no caller input can add an argument or swap the GraphQL document.

A body file is never handed to `gh` as a path: it must not be a symlink, must resolve to a regular
file you own below a `scratchpad` directory of <temp>/claude-<uid>, is opened without following a
final symlink, is size- and UTF-8-checked here, and its content is passed to `gh` on stdin. It
needs a POSIX platform (owner and no-follow checks).

The subcommands that write or use GraphQL can no longer be seen by git-guard-raw-pr-review.sh (this
script's own command text contains none of the words that guard matches), so they enforce the
marker handshake themselves: a fresh `gh-pr-review-wrapper` marker written by
`git-write-marker.sh` in the call right before, consumed here on first use. A separate guard type
is needed because that hook deletes every `gh-pr-review` marker on the next Bash call, before this
script could read it. Like the hook's own marker, this is a guardrail against forgetting the
handshake, not a security boundary: anything able to run the marker writer can satisfy it.

Subcommands:
  threads            reviewThreads query, one page (--owner --repo --pr [--cursor])   marker
  resolve            resolveReviewThread mutation (--thread-id)                        marker
  reply              reply to an inline comment (--owner --repo --pr --comment-id
                     --body-file)                                                      marker
  trigger-comment    top-level PR comment (--owner --repo --pr --body-file)            marker
  issue-create       file an issue (--owner --repo --title --body-file)                marker
  list-comments      all inline comments, paginated (--owner --repo --pr)              read-only
  whoami             login of the authenticated account                                read-only
  push-destinations  origin's push URLs as owner/repo, one per line                    read-only
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GUARD = "gh-pr-review-wrapper"
MARKER_MAX_AGE = 60
MAX_BODY_BYTES = 262144
MAX_BODY_CHARS = 65536
MAX_TITLE_CHARS = 256
PROBE_TIMEOUT = 30  # seconds, the marker's git rev-parse probe
CALL_TIMEOUT = 300  # seconds, the gh/git call itself (a paginated list can be slow)
UNSUPPORTED_URL = "unsupported-push-url"

OWNER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
REPO_RE = re.compile(r"[A-Za-z0-9._-]+")
NUMBER_RE = re.compile(r"[1-9][0-9]{0,9}")
THREAD_RE = re.compile(r"PRRT_[A-Za-z0-9_-]+")
CURSOR_RE = re.compile(r"[A-Za-z0-9+/=_-]+")
STAMP_RE = re.compile(r"[0-9]{1,10}")
GITHUB_URL_PREFIX_RE = re.compile(
    r"^(?:https?://(?:[^@/]+@)?github\.com/|ssh://(?:[^@/]+@)?github\.com/|git@github\.com:)"
)

THREADS_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          path
          line
          comments(first: 1) {
            nodes { databaseId body author { login } }
          }
        }
      }
    }
  }
}
"""

RESOLVE_MUTATION = (
    "mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) "
    "{ thread { id isResolved } } }"
)

WRITE_COMMANDS = {"threads", "resolve", "reply", "trigger-comment", "issue-create"}


class UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def _check(value: str, pattern: re.Pattern, what: str) -> str:
    if not pattern.fullmatch(value):
        raise UsageError(f"invalid {what}: {value!r}")
    return value


def _repo_slug(args) -> tuple[str, str]:
    owner = _check(args.owner, OWNER_RE, "--owner")
    repo = _check(args.repo, REPO_RE, "--repo")
    if repo in (".", ".."):
        raise UsageError(f"invalid --repo: {repo!r}")
    return owner, repo


def allowed_body_roots() -> list[str]:
    """Per-user roots a body file may live under: <temp>/claude-<uid> (Claude Code's scratch)."""
    if not hasattr(os, "getuid"):
        raise UsageError("--body-file needs a POSIX platform (owner and no-follow checks)")
    temps = {os.path.realpath(tempfile.gettempdir()), os.path.realpath("/tmp")}
    return sorted(os.path.join(temp, f"claude-{os.getuid()}") for temp in temps)


def _in_scratchpad(real: str, roots: list[str]) -> bool:
    """True when `real` sits under a root and below a directory named `scratchpad`."""
    for root in roots:
        if os.path.commonpath([root, real]) == root:
            return "scratchpad" in os.path.relpath(real, root).split(os.sep)[:-1]
    return False


def read_body(raw: str) -> bytes:
    """Return the body file's content, or raise UsageError.

    The path itself must not be a symlink. It is then resolved (so a symlinked parent directory
    cannot hide the real location), must sit below a `scratchpad` directory of the per-user
    scratch tree, and is opened with O_NOFOLLOW and checked with fstat on the opened descriptor
    (regular file, owned by the caller, a single link so a hard link to a file elsewhere is
    refused). procfs-style files fail the location check. Residuals: other sessions' files in the
    same scratch tree remain readable, and a concurrent process running as the same user could swap
    a parent directory between the resolve and the open; such a process already holds the user's
    GitHub credentials, so that race is outside this check's threat model.
    """
    if os.path.islink(raw):
        raise UsageError(f"--body-file must not be a symlink: {raw!r}")
    real = os.path.realpath(raw)
    if not _in_scratchpad(real, allowed_body_roots()):
        raise UsageError(
            f"--body-file must be in your scratchpad (<temp>/claude-<uid>/.../scratchpad): {raw!r}"
        )
    try:
        fd = os.open(real, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise UsageError(f"cannot open --body-file {raw!r}: {exc.strerror}") from exc
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        os.close(fd)
        raise UsageError(f"--body-file is not a single-link regular file owned by you: {raw!r}")
    with os.fdopen(fd, "rb") as handle:
        data = handle.read(MAX_BODY_BYTES + 1)
    if len(data) > MAX_BODY_BYTES:
        raise UsageError(f"--body-file is larger than {MAX_BODY_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UsageError("--body-file is not valid UTF-8") from exc
    if not text.strip():
        raise UsageError("--body-file is empty")
    if len(text) > MAX_BODY_CHARS:
        raise UsageError(f"--body-file is longer than {MAX_BODY_CHARS} characters")
    return data


def _title(raw: str) -> str:
    if (
        not raw.strip()
        or len(raw) > MAX_TITLE_CHARS
        or any(ord(c) < 32 or ord(c) == 127 for c in raw)
    ):
        raise UsageError("invalid --title: must be 1-256 characters with no control characters")
    return raw


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    def repo_flags(p, pr=True):
        p.add_argument("--owner", required=True)
        p.add_argument("--repo", required=True)
        if pr:
            p.add_argument("--pr", required=True)

    threads = sub.add_parser("threads")
    repo_flags(threads)
    threads.add_argument("--cursor")
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--thread-id", required=True)
    reply = sub.add_parser("reply")
    repo_flags(reply)
    reply.add_argument("--comment-id", required=True)
    reply.add_argument("--body-file", required=True)
    trigger = sub.add_parser("trigger-comment")
    repo_flags(trigger)
    trigger.add_argument("--body-file", required=True)
    issue = sub.add_parser("issue-create")
    repo_flags(issue, pr=False)
    issue.add_argument("--title", required=True)
    issue.add_argument("--body-file", required=True)
    repo_flags(sub.add_parser("list-comments"))
    sub.add_parser("whoami")
    sub.add_parser("push-destinations")
    return parser


def build_call(args) -> tuple[list[str], bytes | None]:
    """Validate the parsed arguments; return the one argv they select and its stdin (if any)."""
    command = args.command
    if command == "whoami":
        return ["gh", "api", "user", "--jq", ".login"], None
    if command == "push-destinations":
        return ["git", "remote", "get-url", "--push", "--all", "origin"], None
    if command == "resolve":
        thread_id = _check(args.thread_id, THREAD_RE, "--thread-id")
        return [
            "gh", "api", "graphql", "-f", f"query={RESOLVE_MUTATION}", "-f", f"id={thread_id}",
        ], None  # fmt: skip

    owner, repo = _repo_slug(args)
    if command == "issue-create":
        title = _title(args.title)
        body = read_body(args.body_file)
        return [
            "gh", "issue", "create", "-R", f"{owner}/{repo}", "--title", title, "--body-file", "-",
        ], body  # fmt: skip

    pr = _check(args.pr, NUMBER_RE, "--pr")
    if command == "threads":
        cursor = ["-F", "cursor=null"]
        if args.cursor is not None:
            cursor = ["-f", f"cursor={_check(args.cursor, CURSOR_RE, '--cursor')}"]
        return [
            "gh", "api", "graphql",
            "-f", f"owner={owner}", "-f", f"name={repo}", "-F", f"number={pr}",
            *cursor, "-f", f"query={THREADS_QUERY}",
        ], None  # fmt: skip
    if command == "reply":
        comment_id = _check(args.comment_id, NUMBER_RE, "--comment-id")
        body = read_body(args.body_file)
        endpoint = f"repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies"
        return ["gh", "api", endpoint, "-F", "body=@-", "--silent"], body
    if command == "trigger-comment":
        body = read_body(args.body_file)
        return ["gh", "pr", "comment", pr, "-R", f"{owner}/{repo}", "--body-file", "-"], body
    return ["gh", "api", f"repos/{owner}/{repo}/pulls/{pr}/comments", "--paginate"], None


def consume_marker(run, now: float) -> None:
    """Require a fresh wrapper marker and delete it; raise UsageError if there is none."""
    try:
        probe = run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
            timeout=PROBE_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise UsageError("git rev-parse timed out, so no marker can be checked") from exc
    if probe.returncode != 0 or not probe.stdout.strip():
        raise UsageError("not inside a git repository, so no marker can be checked")
    marker = Path(probe.stdout.strip()) / "git-kit-marker.txt"
    if marker.is_symlink() or not marker.is_file():
        raise UsageError(_missing_marker_message())
    if not _is_wrapper_marker(marker.read_text(errors="replace").split()):
        raise UsageError(_missing_marker_message())
    # Claim the marker with an atomic rename before trusting it: a concurrent caller loses the
    # rename, and a marker another guard wrote after the check above is restored, never deleted.
    claimed = marker.with_name(f"{marker.name}.claim.{os.getpid()}")
    try:
        os.rename(marker, claimed)
        fields = claimed.read_text(errors="replace").split()
    except OSError as exc:
        raise UsageError(f"could not consume the marker: {exc}") from exc
    if not _is_wrapper_marker(fields):
        try:
            os.link(claimed, marker)
        except OSError:
            pass
        claimed.unlink(missing_ok=True)
        raise UsageError(_missing_marker_message())
    try:
        claimed.unlink()
    except OSError as exc:
        raise UsageError(f"could not consume the marker: {exc}") from exc
    age = now - int(fields[1])
    if not 0 <= age <= MARKER_MAX_AGE:
        raise UsageError(f"the {GUARD} marker is stale or future-dated; write a fresh one")


def _is_wrapper_marker(fields: list[str]) -> bool:
    return len(fields) >= 2 and fields[0] == GUARD and bool(STAMP_RE.fullmatch(fields[1]))


def _missing_marker_message() -> str:
    return (
        f"no {GUARD} marker. Run `git-write-marker.sh {GUARD} handling-review-findings` in its "
        "own Bash call immediately before this one (the marker is single-use, 60 seconds)."
    )


def _print_push_destinations(output: str) -> bool:
    """Print one `owner/repo` per push URL; True only if there was at least one and all parsed.

    A URL in an unsupported form prints a fixed marker instead of itself: it can carry credentials,
    and the caller's comparison against the head repository fails on the marker anyway.
    """
    urls = [line.strip() for line in output.splitlines() if line.strip()]
    for url in urls:
        if GITHUB_URL_PREFIX_RE.match(url):
            print(GITHUB_URL_PREFIX_RE.sub("", url).rstrip("/").removesuffix(".git"))
        else:
            print(UNSUPPORTED_URL)
    return bool(urls) and all(GITHUB_URL_PREFIX_RE.match(url) for url in urls)


def main(argv=None, *, run=subprocess.run, now=time.time) -> int:
    try:
        args = build_parser().parse_args(argv)
        gh_argv, stdin = build_call(args)
        if args.command in WRITE_COMMANDS:
            consume_marker(run, now())
    except UsageError as exc:
        print(f"git-review-api.py: {exc}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    try:
        if args.command == "push-destinations":
            result = run(gh_argv, capture_output=True, text=True, check=False, timeout=CALL_TIMEOUT)
            sys.stderr.write(result.stderr)
            if result.returncode != 0:
                return result.returncode
            return 0 if _print_push_destinations(result.stdout) else 1
        return run(gh_argv, input=stdin, check=False, timeout=CALL_TIMEOUT).returncode
    except FileNotFoundError:
        print(f"git-review-api.py: {gh_argv[0]} is not installed", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired:
        print(f"git-review-api.py: {gh_argv[0]} timed out after {CALL_TIMEOUT}s", file=sys.stderr)
        return 124


if __name__ == "__main__":
    sys.exit(main())
