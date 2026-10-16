#!/usr/bin/env python3
"""The only GitHub entry point for handling-review-findings (#580).

The skill used to hold broad `gh api graphql`, `gh api .../pulls/*/comments`, `gh pr comment`,
`gh issue create`, `gh api user` and `sed` grants, which also allow GraphQL mutations such as
`mergePullRequest`, arbitrary comment bodies and, via GNU sed's `e` command, arbitrary commands.
This script replaces them with fixed subcommands. Each runs exactly one `gh` (or `git`) call built
from a static argv (no shell), so no caller input can add an argument or swap the GraphQL document.

A body file is never handed to `gh` as a path: it must resolve (symlinks followed) to a regular file
under the system temp directory, is opened without following a final symlink, is size- and
UTF-8-checked here, and its content is passed to `gh` on stdin.

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

OWNER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
REPO_RE = re.compile(r"[A-Za-z0-9._-]+")
NUMBER_RE = re.compile(r"[1-9][0-9]{0,9}")
THREAD_RE = re.compile(r"PRRT_[A-Za-z0-9_-]+")
CURSOR_RE = re.compile(r"[A-Za-z0-9+/=_-]+")
STAMP_RE = re.compile(r"[0-9]{1,10}")
GITHUB_URL_PREFIX_RE = re.compile(r"^(https://github\.com/|git@github\.com:)")

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


def allowed_body_root() -> str:
    return os.path.realpath(tempfile.gettempdir())


def read_body(raw: str) -> bytes:
    """Return the body file's content, or raise UsageError.

    The path is resolved first (so a symlinked parent directory cannot hide the real location),
    must sit under the temp root, and is then opened with O_NOFOLLOW and checked with fstat so a
    swap after the check cannot change what is read. procfs-style files fail the root check.
    """
    root = allowed_body_root()
    real = os.path.realpath(raw)
    if os.path.commonpath([root, real]) != root:
        raise UsageError(f"--body-file must be under {root}: {raw!r}")
    try:
        fd = os.open(real, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise UsageError(f"cannot open --body-file {raw!r}: {exc.strerror}") from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise UsageError(f"--body-file is not a regular file: {raw!r}")
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
    probe = run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True, check=False)
    if probe.returncode != 0 or not probe.stdout.strip():
        raise UsageError("not inside a git repository, so no marker can be checked")
    marker = Path(probe.stdout.strip()) / "git-kit-marker.txt"
    if marker.is_symlink() or not marker.is_file():
        raise UsageError(_missing_marker_message())
    fields = marker.read_text(errors="replace").split()
    if len(fields) < 2 or fields[0] != GUARD or not STAMP_RE.fullmatch(fields[1]):
        raise UsageError(_missing_marker_message())
    age = now - int(fields[1])
    try:
        marker.unlink()
    except OSError as exc:
        raise UsageError(f"could not consume the marker: {exc}") from exc
    if not 0 <= age <= MARKER_MAX_AGE:
        raise UsageError(f"the {GUARD} marker is stale or future-dated; write a fresh one")


def _missing_marker_message() -> str:
    return (
        f"no {GUARD} marker. Run `git-write-marker.sh {GUARD} handling-review-findings` in its "
        "own Bash call immediately before this one (the marker is single-use, 60 seconds)."
    )


def _print_push_destinations(output: str) -> None:
    for line in output.splitlines():
        line = GITHUB_URL_PREFIX_RE.sub("", line.strip())
        print(line.removesuffix(".git"))


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
            result = run(gh_argv, capture_output=True, text=True, check=False)
            _print_push_destinations(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
        return run(gh_argv, input=stdin, check=False).returncode
    except FileNotFoundError:
        print(f"git-review-api.py: {gh_argv[0]} is not installed", file=sys.stderr)
        return 127


if __name__ == "__main__":
    sys.exit(main())
