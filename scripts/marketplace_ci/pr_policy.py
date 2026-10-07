"""PR title/template validation and live author privilege policy.

Deterministic checks (title format, template shape) never claim more than
regex/structural certainty — semantic review of the PR's actual English
prose is Codex's job (Phase 4), not this module's.
"""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_CODEOWNERS_CANDIDATES = ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")

# Matches the "Type of Change" checklist in .github/pull_request_template.md —
# this repo's own authoritative list, not a generic conventional-commit guess.
DEFAULT_ALLOWED_TYPES = ("feat", "fix", "docs", "refactor", "perf", "test", "chore", "experiment")

MERGE_CAPABLE_PERMISSIONS = ("write", "maintain", "admin")

# Exact (case-insensitive) logins of automation accounts exempt from the
# collaborator/CODEOWNERS author checks. GitHub reserves the `[bot]` suffix,
# so no human account can claim one of these logins; the match must stay an
# exact-string compare, never a suffix or prefix match.
TRUSTED_BOT_LOGINS = ("dependabot[bot]",)
# The login is the PR's opener and stays fixed for the PR's life, so the merge
# check also requires every changed path to be a root dependency
# manifest/lockfile: a later commit pushed to the branch touching anything
# else falls back to the normal CODEOWNERS check.
TRUSTED_BOT_PATHS = frozenset({"uv.lock", "pyproject.toml", "package.json", "pnpm-lock.yaml"})
# GitHub signs dependabot's commits itself: author dependabot[bot], committer
# web-flow, signature verified. A forged author email alone fails the committer
# and signature checks, and a collaborator's web-UI edit is authored by them.
TRUSTED_BOT_COMMITTER = "web-flow"

_EMOJI_PATTERN = re.compile("[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]")
# GitHub-flavored markdown renders `:sparkles:`-style shortcodes as emoji too;
# reject the syntax itself rather than trying to enumerate every shortcode name.
_EMOJI_SHORTCODE_PATTERN = re.compile(r":[a-z0-9_+-]+:")
_TITLE_PATTERN = re.compile(r"^[a-z]+(\([a-z0-9_/-]+\))?!?: .+$")


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reason: str | None = None


@dataclass(frozen=True)
class RightsResult:
    allowed: bool
    reason: str | None = None


@dataclass(frozen=True)
class PrPolicyResult:
    title: CheckResult
    template: CheckResult
    pr_privilege: RightsResult
    merge_privilege: RightsResult

    @property
    def passed(self) -> bool:
        return (
            self.title.passed
            and self.template.passed
            and self.pr_privilege.allowed
            and self.merge_privilege.allowed
        )


def check_pr_title(
    title: str, allowed_types: tuple[str, ...] = DEFAULT_ALLOWED_TYPES
) -> CheckResult:
    if _EMOJI_PATTERN.search(title) or _EMOJI_SHORTCODE_PATTERN.search(title):
        return CheckResult(passed=False, reason="title must not contain emoji")
    if not _TITLE_PATTERN.match(title):
        return CheckResult(
            passed=False,
            reason="title must match 'type(scope): description' or 'type: description'",
        )
    commit_type = title.split("(")[0].split(":")[0].rstrip("!")
    if commit_type not in allowed_types:
        return CheckResult(passed=False, reason=f"unknown commit type: {commit_type!r}")
    return CheckResult(passed=True)


def _extract_headings(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def check_template(template: str, body: str) -> CheckResult:
    """Require the PR body's `##` headings to be a subsequence of the primary
    template's own headings, in the same relative order, with no unknown
    heading added. This is a structural check only — it says nothing about
    whether the *content* under each heading is any good."""
    expected = _extract_headings(template)
    actual = _extract_headings(body)

    for heading in actual:
        if heading not in expected:
            return CheckResult(passed=False, reason=f"unexpected heading: {heading}")

    expected_subsequence = [h for h in expected if h in actual]
    if actual != expected_subsequence:
        return CheckResult(passed=False, reason="headings out of order")

    return CheckResult(passed=True)


class GitHubApi(Protocol):
    """Duck-typed live-privilege data source. `owner`/`user` are login
    names (case-insensitive comparison, per GitHub's own username rules)."""

    owner: str
    user: str

    def collaborator_permission(self, username: str) -> str | None: ...
    def codeowners(self) -> tuple[tuple[str, tuple[str, ...]], ...]: ...


def check_pr_rights(api: GitHubApi) -> RightsResult:
    if api.user.lower() == api.owner.lower():
        return RightsResult(allowed=True, reason="repository owner")
    if api.user.lower() in TRUSTED_BOT_LOGINS:
        return RightsResult(allowed=True, reason="trusted automation account")
    permission = api.collaborator_permission(api.user)
    if permission in MERGE_CAPABLE_PERMISSIONS:
        return RightsResult(allowed=True, reason=f"collaborator permission: {permission}")
    return RightsResult(
        allowed=False, reason=f"insufficient collaborator permission: {permission!r}"
    )


def check_merge_rights(
    api: GitHubApi, changed_paths: list[str], *, bot_commits_verified: bool = False
) -> RightsResult:
    if api.user.lower() == api.owner.lower():
        return RightsResult(allowed=True, reason="repository owner")
    if (
        api.user.lower() in TRUSTED_BOT_LOGINS
        and bot_commits_verified
        and changed_paths
        and all(path in TRUSTED_BOT_PATHS for path in changed_paths)
    ):
        return RightsResult(
            allowed=True,
            reason="trusted automation account, verified bot commits, manifest paths only",
        )

    matched_owners: tuple[str, ...] | None = None
    for pattern, owners in api.codeowners():
        if any(fnmatch.fnmatch(path, pattern) for path in changed_paths):
            matched_owners = owners  # last matching entry wins, per CODEOWNERS semantics

    if matched_owners is not None:
        normalized = {o.lower().lstrip("@") for o in matched_owners}
        if api.user.lower() in normalized:
            return RightsResult(allowed=True, reason="direct CODEOWNERS match")
        return RightsResult(
            allowed=False,
            reason=(
                "not listed as a direct CODEOWNERS entry for the changed paths; "
                "team membership cannot be verified from this data source"
            ),
        )

    permission = api.collaborator_permission(api.user)
    if permission in MERGE_CAPABLE_PERMISSIONS:
        return RightsResult(allowed=True, reason=f"collaborator permission: {permission}")
    return RightsResult(
        allowed=False, reason=f"insufficient collaborator permission: {permission!r}"
    )


def evaluate_pr_policy(
    api: GitHubApi,
    *,
    title: str,
    body: str,
    template: str,
    changed_paths: list[str],
    allowed_types: tuple[str, ...] = DEFAULT_ALLOWED_TYPES,
    bot_commits_verified: bool = False,
) -> PrPolicyResult:
    return PrPolicyResult(
        title=check_pr_title(title, allowed_types),
        template=check_template(template, body),
        pr_privilege=check_pr_rights(api),
        merge_privilege=check_merge_rights(
            api, changed_paths, bot_commits_verified=bot_commits_verified
        ),
    )


def _parse_codeowners(text: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    entries: list[tuple[str, tuple[str, ...]]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        entries.append((parts[0], tuple(parts[1:])))
    return tuple(entries)


class RealGitHubApi:
    """Live `GitHubApi` backed by `gh api` and the repository's own
    CODEOWNERS file (never a plugin-owned copy — repo root or `.github/`
    only, per GitHub's own supported CODEOWNERS locations)."""

    def __init__(self, *, owner: str, user: str, full_name: str, repo: Path) -> None:
        self.owner = owner
        self.user = user
        self._full_name = full_name
        self._repo = repo

    def collaborator_permission(self, username: str) -> str | None:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{self._full_name}/collaborators/{username}/permission",
                "--jq",
                ".permission",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        permission = result.stdout.strip()
        return permission or None

    def codeowners(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        for candidate in _CODEOWNERS_CANDIDATES:
            path = self._repo / candidate
            if path.is_file():
                return _parse_codeowners(path.read_text(encoding="utf-8"))
        return ()


def commits_verified_from_trusted_bot(
    full_name: str, number: int | None, head_sha: str, expected_count: int | None
) -> bool:
    """True only if the PR's commit list is exactly the event's commits (count
    and head SHA both match, below the API's 250-commit cap) and every commit
    is authored by a trusted bot, committed by `web-flow`, with a verified
    signature. Any API error, malformed output or missing field returns False
    (fail closed, so the caller falls back to the normal CODEOWNERS check)."""
    # The commits endpoint returns at most 250, so a count of exactly 250 can't
    # be told apart from a truncated list: fail closed rather than trust it.
    if number is None or not isinstance(expected_count, int) or not 0 < expected_count < 250:
        return False
    result = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/{full_name}/pulls/{number}/commits",
            "--jq",
            ".[] | {s: .sha, a: .author.login, c: .committer.login,"
            " v: .commit.verification.verified}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    try:
        commits = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError:
        return False
    return (
        len(commits) == expected_count
        and all(isinstance(c, dict) for c in commits)
        and commits[-1].get("s") == head_sha
        and all(
            isinstance(c.get("a"), str)
            and c["a"].lower() in TRUSTED_BOT_LOGINS
            and c.get("c") == TRUSTED_BOT_COMMITTER
            and c.get("v") is True
            for c in commits
        )
    )
