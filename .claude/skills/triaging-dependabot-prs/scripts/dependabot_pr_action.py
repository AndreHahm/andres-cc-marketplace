#!/usr/bin/env python3
"""Run one action on a Dependabot PR: close it, or post one fixed comment.

Used by triaging-dependabot-prs in place of a raw `gh pr comment` / `gh pr close`, so the limits the
skill states in prose are enforced here, in code. The caller names an ACTION and small tokens; this
script builds the exact comment body itself (the caller never supplies a body, only pattern-checked
dependency and condition tokens), re-reads the PR, and refuses unless all of these hold:

  * the PR number is plain digits and the head SHA is 40 lowercase hex characters;
  * the PR is OPEN, in this checkout's own repository (the `origin` remote), not from a fork,
    authored by the Dependabot app, and on a `dependabot/` branch;
  * the PR's head is still the SHA passed in --head-sha (meant to be the head read for the user's
    approval; this script cannot check that an approval happened, only that the head has not moved);
  * dependency names and ignore conditions match fixed patterns (a name with `@` is refused:
    `@scope` in a comment would notify an account).

`gh` and `git` are run by absolute path with an argument list (no shell). `gh` always gets -R
github.com/<that repository>, and the environment passed to both has GH_HOST, GH_REPO and the
enterprise token variables removed. Never --body-file, --comment or --delete-branch.

Usage: dependabot_pr_action.py [--dry-run] ACTION PR_NUMBER --head-sha SHA [--dep NAME]
                               [--scope SCOPE] [--condition COND]
Actions: rebase, recreate, close, ignore-this (--scope dependency|major|minor|patch),
ignore-dep (--dep, optional --scope major|minor|patch), unignore-all, unignore-dep (--dep, optional
--condition), show-ignore-conditions (--dep). --dry-run runs every check and prints the exact body
without posting or closing anything. The skill pre-approves only the --dry-run form, so a real run
asks the user for permission in Claude Code.
Prints one JSON object with an "ok" field. Exit 0 = done (or dry run passed), 2 = bad arguments,
3 = a precondition failed, 4 = `gh` or `git` failed or was unavailable (when the write itself may
or may not have happened, the message says the outcome is unknown).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

PR_RE = re.compile(r"[1-9][0-9]{0,8}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
DEP_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")
CONDITION_RE = re.compile(r"\[[0-9A-Za-z<>=!~.,*+ -]{1,60}\]")
BRANCH_RE = re.compile(r"dependabot/[A-Za-z0-9._/@+=-]+")
ORIGIN_RE = re.compile(
    r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9._-]+/[A-Za-z0-9._-]+?)(?:\.git)?"
)
PR_URL_RE = re.compile(r"https://github\.com/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)/pull/([0-9]+)")
HOST = "github.com"
DROPPED_ENV = ("GH_HOST", "GH_REPO", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
DEPENDABOT_AUTHOR = "app/dependabot"

ACTIONS = (
    "rebase",
    "recreate",
    "close",
    "ignore-this",
    "ignore-dep",
    "unignore-all",
    "unignore-dep",
    "show-ignore-conditions",
)
THIS_SCOPES = ("dependency", "major", "minor", "patch")
DEP_SCOPES = ("major", "minor", "patch")
GH_TIMEOUT_SECONDS = 60

EXIT_OK, EXIT_USAGE, EXIT_PRECONDITION, EXIT_TOOL = 0, 2, 3, 4


class Refusal(Exception):
    """A request this script will not carry out; `code` is the exit code to use."""

    def __init__(self, message, code=EXIT_USAGE):
        super().__init__(message)
        self.code = code


def build_body(action, dep=None, scope=None, condition=None):
    """Return the exact comment body for ACTION, or None for `close`; refuse anything unexpected."""
    needs_dep = action in ("ignore-dep", "unignore-dep", "show-ignore-conditions")
    allowed_scope = {"ignore-this": THIS_SCOPES, "ignore-dep": DEP_SCOPES}.get(action, ())
    if dep is not None and not needs_dep:
        raise Refusal(f"{action} takes no --dep")
    if scope is not None and not allowed_scope:
        raise Refusal(f"{action} takes no --scope")
    if condition is not None and action != "unignore-dep":
        raise Refusal(f"{action} takes no --condition")
    if needs_dep:
        if dep is None or not DEP_RE.fullmatch(dep):
            raise Refusal(
                "--dep is missing or is not a plain dependency name (no '@', spaces, quotes)"
            )
    if scope is not None and scope not in allowed_scope:
        raise Refusal(f"--scope must be one of {', '.join(allowed_scope)} for {action}")
    if condition is not None and not CONDITION_RE.fullmatch(condition):
        raise Refusal("--condition must look like [< 1.9, > 1.8.0] (at most 60 plain characters)")

    if action == "close":
        return None
    if action in ("rebase", "recreate"):
        return f"@dependabot {action}"
    if action == "ignore-this":
        if scope is None:
            raise Refusal("ignore-this needs --scope")
        if scope == "dependency":
            return "@dependabot ignore this dependency"
        return f"@dependabot ignore this {scope} version"
    if action == "ignore-dep":
        suffix = f" {scope} version" if scope else ""
        return f"@dependabot ignore {dep}{suffix}"
    if action == "unignore-all":
        return "@dependabot unignore *"
    if action == "unignore-dep":
        return f"@dependabot unignore {dep}" + (f" {condition}" if condition else "")
    return f"@dependabot show {dep} ignore conditions"


# --- helpers shared, by identical copy, with dependabot_pr_read.py (a test keeps them equal) ---


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


def check_pr(run, gh, repo, pr, head_sha):
    """Re-read the PR; refuse unless it is an open, same-repo Dependabot PR at the given head."""
    done = _run(
        run,
        [
            gh,
            "pr",
            "view",
            pr,
            "-R",
            f"{HOST}/{repo}",
            "--json",
            "state,author,headRefName,isCrossRepository,headRefOid,url",
        ],
    )
    if done.returncode != 0:
        raise Refusal("gh pr view failed for this PR", EXIT_TOOL)
    try:
        data = json.loads(done.stdout)
        state, author = data["state"], data["author"]
        branch, cross, head, url = (
            data["headRefName"],
            data["isCrossRepository"],
            data["headRefOid"],
            data["url"],
        )
        login, is_bot = author["login"], author["is_bot"]
    except (ValueError, KeyError, TypeError) as exc:
        raise Refusal("gh pr view returned an unexpected shape", EXIT_TOOL) from exc

    url_match = PR_URL_RE.fullmatch(url) if isinstance(url, str) else None
    problems = []
    if state != "OPEN":
        problems.append(f"PR is {state}, not OPEN")
    if cross is not False:
        problems.append("PR head is in a fork")
    if login != DEPENDABOT_AUTHOR or is_bot is not True:
        problems.append("PR is not authored by the Dependabot app")
    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        problems.append("PR branch does not start with dependabot/")
    if head != head_sha:
        problems.append("PR head is no longer the SHA that was passed")
    if not url_match or url_match.group(1).lower() != repo.lower() or url_match.group(2) != pr:
        problems.append("PR does not belong to this checkout's repository")
    if problems:
        raise Refusal("; ".join(problems), EXIT_PRECONDITION)


def perform(run, gh, repo, pr, body):
    """Post the body, or close the PR when body is None; return gh's trimmed stdout."""
    target = f"{HOST}/{repo}"
    if body is None:
        argv = [gh, "pr", "close", pr, "-R", target]
    else:
        argv = [gh, "pr", "comment", pr, "-R", target, "--body", body]
    done = _run(run, argv, outcome_unknown_on_timeout=True)
    if done.returncode != 0:
        raise Refusal(f"gh pr {'close' if body is None else 'comment'} failed", EXIT_TOOL)
    return done.stdout.strip()


def parse_args(argv):
    """Parse the command line; argparse's own errors exit 2 with no JSON, as documented."""
    parser = argparse.ArgumentParser(description="Run one Dependabot PR action.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("pr_number")
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--dep")
    parser.add_argument("--scope")
    parser.add_argument("--condition")
    return parser.parse_args(argv)


def main(argv=None, run=subprocess.run, which=shutil.which):
    """Validate, check the PR, then act (or stop at --dry-run); print one JSON object."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = {"ok": False, "action": args.action, "pr": args.pr_number}
    try:
        if not PR_RE.fullmatch(args.pr_number):
            raise Refusal("PR number must be plain digits")
        if not SHA_RE.fullmatch(args.head_sha):
            raise Refusal("--head-sha must be 40 lowercase hex characters")
        body = build_body(args.action, args.dep, args.scope, args.condition)
        git, gh = resolve_tool(which, "git"), resolve_tool(which, "gh")
        repo = origin_repo(run, git)
        check_pr(run, gh, repo, args.pr_number, args.head_sha)
        result["body"] = body
        result["repo"] = repo
        result["dry_run"] = args.dry_run
        if not args.dry_run:
            result["gh"] = perform(run, gh, repo, args.pr_number, body)
        result["ok"] = True
        code = EXIT_OK
    except Refusal as exc:
        result["refused"] = str(exc)
        code = exc.code
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
