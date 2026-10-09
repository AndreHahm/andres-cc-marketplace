#!/usr/bin/env python3
"""Read-only GitHub lookups for triaging-dependabot-prs, in place of raw `gh api` calls.

The skill needs three reads for its Codex-bypass conditions: a PR's changed files, a PR's commits,
and a `uv.lock` file at a ref. A raw `gh api` grant cannot be narrowed to those (its wildcards also
match writes), so this script does exactly these three things and nothing else. It has no code path
that posts, closes, edits or deletes anything on GitHub.

`gh` and `git` are run by absolute path with an argument list (no shell). `gh api` always gets
--method GET and --hostname github.com against this checkout's own `origin` repository, and the
environment passed to both has GH_HOST, GH_REPO and the enterprise token variables removed.

Usage:
  dependabot_pr_read.py files PR_NUMBER
  dependabot_pr_read.py commits PR_NUMBER
  dependabot_pr_read.py uv-lock --role base|head --ref REF --dir DIR
`files` and `commits` print a compact summary of the first page (100 entries); "truncated" is true
when that page is full. `uv-lock` writes the file only to DIR/base-uv.lock or DIR/head-uv.lock
(DIR must be an existing absolute directory; the target must not be a symlink; at most 8 MiB).
Prints one JSON object with an "ok" field. Exit 0 = done, 2 = bad arguments, 4 = `gh` or `git`
failed or was unavailable, or the file could not be written.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

PR_RE = re.compile(r"[1-9][0-9]{0,8}")
REF_RE = re.compile(r"[0-9a-f]{40}|[A-Za-z0-9][A-Za-z0-9._/@+=-]{0,199}")
ORIGIN_RE = re.compile(
    r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9._-]+/[A-Za-z0-9._-]+?)(?:\.git)?"
)
HOST = "github.com"
DROPPED_ENV = ("GH_HOST", "GH_REPO", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
GH_TIMEOUT_SECONDS = 60
PAGE_SIZE = 100
MAX_LOCK_BYTES = 8 * 1024 * 1024
ROLES = ("base", "head")

EXIT_OK, EXIT_USAGE, EXIT_PRECONDITION, EXIT_TOOL = 0, 2, 3, 4


class Refusal(Exception):
    """A request this script will not carry out; `code` is the exit code to use."""

    def __init__(self, message, code=EXIT_USAGE):
        super().__init__(message)
        self.code = code


# --- helpers shared, by identical copy, with dependabot_pr_action.py (a test keeps them equal) ---


def scrubbed_env(environ=None):
    """The environment for gh and git: host and repository overrides removed, prompts off."""
    source = os.environ if environ is None else environ
    env = {k: v for k, v in source.items() if k not in DROPPED_ENV}
    env["GH_PROMPT_DISABLED"] = "1"
    return env


def resolve_tool(which, name):
    """The absolute path of `name` found via PATH, or a tool error; a relative result is refused."""
    path = which(name)
    if not path or not os.path.isabs(path):
        raise Refusal(f"{name} was not found on PATH", EXIT_TOOL)
    return path


def _run(run, argv, outcome_unknown_on_timeout=False):
    """Run one external command from an argument list; any failure to run it is a tool error."""
    name = os.path.basename(argv[0])
    try:
        return run(
            argv,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=GH_TIMEOUT_SECONDS,
            check=False,
            env=scrubbed_env(),
        )
    except subprocess.TimeoutExpired as exc:
        if outcome_unknown_on_timeout:
            msg = f"{name} timed out; the outcome is unknown, re-read the PR before anything else"
        else:
            msg = f"{name} timed out"
        raise Refusal(msg, EXIT_TOOL) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refusal(f"could not run {name}: {type(exc).__name__}", EXIT_TOOL) from exc


def origin_repo(run, git):
    """The owner/repo of this checkout's `origin` remote."""
    done = _run(run, [git, "remote", "get-url", "origin"])
    match = ORIGIN_RE.fullmatch(done.stdout.strip()) if done.returncode == 0 else None
    if not match:
        raise Refusal("cannot resolve a github.com owner/repo from the origin remote", EXIT_TOOL)
    return match.group(1)


# --- end of shared helpers ---


RAW_ACCEPT = "Accept: application/vnd.github.raw"


def _api_get(run, gh, endpoint, *fields, raw=False):
    """One `gh api` GET against github.com; `raw` asks for the file body, not JSON metadata."""
    argv = [gh, "api", "--hostname", HOST, "--method", "GET", endpoint]
    for field in fields:
        argv += ["-f", field]
    if raw:
        argv += ["-H", RAW_ACCEPT]
    return _run(run, argv)


def list_page(run, gh, repo, kind, pr):
    """The first page of a PR's files or commits, reduced to the few fields the skill reads."""
    done = _api_get(run, gh, f"repos/{repo}/pulls/{pr}/{kind}", f"per_page={PAGE_SIZE}")
    if done.returncode != 0:
        raise Refusal(f"gh api pulls/{pr}/{kind} failed", EXIT_TOOL)
    try:
        raw = json.loads(done.stdout)
        if not isinstance(raw, list):
            raise TypeError("not a list")
        if kind == "files":
            items = [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "previous_filename": f.get("previous_filename"),
                }
                for f in raw
            ]
        else:
            items = [
                {
                    "sha": c["sha"],
                    "verified": c["commit"]["verification"]["verified"],
                    "author": (c.get("author") or {}).get("login"),
                    "committer": (c.get("committer") or {}).get("login"),
                }
                for c in raw
            ]
    except (ValueError, KeyError, TypeError) as exc:
        raise Refusal(f"gh api pulls/{pr}/{kind} returned an unexpected shape", EXIT_TOOL) from exc
    return {"count": len(items), "truncated": len(items) >= PAGE_SIZE, "items": items}


def fetch_uv_lock(run, gh, repo, ref, role, directory):
    """Write uv.lock at REF to DIRECTORY/<role>-uv.lock; return what was written."""
    if not REF_RE.fullmatch(ref) or ".." in ref:
        raise Refusal("--ref must be a 40-hex SHA or a plain branch name")
    if not os.path.isabs(directory) or not os.path.isdir(directory):
        raise Refusal("--dir must be an existing absolute directory")
    target = os.path.join(os.path.realpath(directory), f"{role}-uv.lock")
    if os.path.islink(target) or os.path.isdir(target):
        raise Refusal(f"{role}-uv.lock in --dir is a symlink or a directory; refusing to write")
    done = _api_get(run, gh, f"repos/{repo}/contents/uv.lock", f"ref={ref}", raw=True)
    if done.returncode != 0:
        raise Refusal("gh api contents/uv.lock failed", EXIT_TOOL)
    data = done.stdout.encode("utf-8")
    if not data or len(data) > MAX_LOCK_BYTES:
        raise Refusal("uv.lock came back empty or larger than 8 MiB", EXIT_TOOL)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target, flags, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except OSError as exc:
        raise Refusal(f"could not write {role}-uv.lock: {type(exc).__name__}", EXIT_TOOL) from exc
    return {"path": target, "bytes": len(data)}


def parse_args(argv):
    """Parse the command line; argparse's own errors exit 2 with no JSON, as documented."""
    parser = argparse.ArgumentParser(description="Read-only Dependabot PR lookups.")
    sub = parser.add_subparsers(dest="kind", required=True)
    for kind in ("files", "commits"):
        sub.add_parser(kind).add_argument("pr_number")
    lock = sub.add_parser("uv-lock")
    lock.add_argument("--role", required=True, choices=ROLES)
    lock.add_argument("--ref", required=True)
    lock.add_argument("--dir", required=True)
    return parser.parse_args(argv)


def main(argv=None, run=subprocess.run, which=shutil.which):
    """Validate, look the data up, and print one JSON object."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = {"ok": False, "kind": args.kind}
    try:
        if args.kind != "uv-lock" and not PR_RE.fullmatch(args.pr_number):
            raise Refusal("PR number must be plain digits")
        git, gh = resolve_tool(which, "git"), resolve_tool(which, "gh")
        repo = origin_repo(run, git)
        result["repo"] = repo
        if args.kind == "uv-lock":
            result.update(role=args.role, ref=args.ref)
            result.update(fetch_uv_lock(run, gh, repo, args.ref, args.role, args.dir))
        else:
            result["pr"] = args.pr_number
            result.update(list_page(run, gh, repo, args.kind, args.pr_number))
        result["ok"] = True
        code = EXIT_OK
    except Refusal as exc:
        result["refused"] = str(exc)
        code = exc.code
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
