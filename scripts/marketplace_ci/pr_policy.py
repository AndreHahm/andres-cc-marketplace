"""PR title/template validation and live author privilege policy.

Deterministic checks (title format, template shape) never claim more than
regex/structural certainty — semantic review of the PR's actual English
prose is Codex's job (Phase 4), not this module's.
"""

from __future__ import annotations

import fnmatch
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
    permission = api.collaborator_permission(api.user)
    if permission in MERGE_CAPABLE_PERMISSIONS:
        return RightsResult(allowed=True, reason=f"collaborator permission: {permission}")
    return RightsResult(
        allowed=False, reason=f"insufficient collaborator permission: {permission!r}"
    )


def check_merge_rights(api: GitHubApi, changed_paths: list[str]) -> RightsResult:
    if api.user.lower() == api.owner.lower():
        return RightsResult(allowed=True, reason="repository owner")

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
) -> PrPolicyResult:
    return PrPolicyResult(
        title=check_pr_title(title, allowed_types),
        template=check_template(template, body),
        pr_privilege=check_pr_rights(api),
        merge_privilege=check_merge_rights(api, changed_paths),
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
