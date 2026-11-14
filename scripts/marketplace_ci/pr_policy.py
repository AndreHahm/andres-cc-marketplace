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
# A verified dependabot PR that changes only the root npm manifest and lockfile
# changes nothing ruff, ty and pytest check (scripts/ and tests/), so the
# `python-quality` job may be skipped for it; the one check lost is its
# end-of-file-fixer over those two files. Narrower than
# TRUSTED_BOT_PATHS on purpose: uv.lock and pyproject.toml change the Python
# toolchain those checks run with.
PYTHON_QUALITY_SKIP_PATHS = frozenset({"package.json", "pnpm-lock.yaml"})
# A verified dependabot github_actions PR changes workflow and composite-action
# files, so it can never meet TRUSTED_BOT_PATHS. It is exempted instead only
# when every changed file is one of these and every changed line is a
# ratchet-pinned `uses:` line whose new SHA is the commit its tag names in the
# action's own repository (actions_pin_bump_verified).
_ACTIONS_PIN_FILE = re.compile(
    r"\.github/workflows/[^/]+\.ya?ml|\.github/actions/[^/]+/action\.ya?ml"
)
_OWNER_REPO = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}"
_ACTION_PATH = rf"{_OWNER_REPO}(?:/[A-Za-z0-9._-]+)*"
_USES_PIN_LINE = re.compile(
    r"(?P<prefix>[ ]*(?:-[ ]+)?uses:[ ]+)(?P<quote>['\"]?)"
    rf"(?P<action>{_ACTION_PATH})@(?P<sha>[0-9a-f]{{40}})(?P=quote)"
    rf"[ ]+#[ ]ratchet:(?P<ratchet>{_ACTION_PATH})@(?P<tag>[A-Za-z0-9._-]{{1,100}})"
)
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
# One tag lookup (a single `gh api` call) may take this long before it counts
# as failed; the hygiene job's own timeout-minutes bounds the whole check.
_TAG_LOOKUP_TIMEOUT_SECONDS = 30
# The same bound for each local `git diff` in actions_pin_bump_verified.
_GIT_DIFF_TIMEOUT_SECONDS = 60
_HUNK_HEADER = re.compile(r"@@ -\d+(?:,(?P<old>\d+))? \+\d+(?:,(?P<new>\d+))? @@")

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


def python_quality_skip_allowed(
    user: str, changed_paths: list[str], *, bot_commits_verified: bool
) -> bool:
    """True only for a trusted bot's PR whose commits were verified and whose
    every changed path is in PYTHON_QUALITY_SKIP_PATHS. An empty path list is
    never "npm only" (fail closed, the same guard check_merge_rights uses)."""
    return (
        user.lower() in TRUSTED_BOT_LOGINS
        and bot_commits_verified
        and bool(changed_paths)
        and all(path in PYTHON_QUALITY_SKIP_PATHS for path in changed_paths)
    )


def codex_review_skip_allowed(
    user: str,
    changed_paths: list[str],
    *,
    bot_commits_verified: bool,
    actions_pins_verified: bool = False,
) -> bool:
    """True only for a trusted bot's PR whose commits were verified and whose
    every changed path is in TRUSTED_BOT_PATHS, or whose diff is a verified
    actions pin bump (actions_pin_bump_verified): the same conditions as the
    merge-privilege exemption in check_merge_rights. `Publish Codex policy
    result` then accepts the skipped Codex delta review (it never runs for
    Dependabot, whose runs get no secrets) without the bypass attestation
    (#704). An empty path list never qualifies (fail closed)."""
    return (
        user.lower() in TRUSTED_BOT_LOGINS
        and bot_commits_verified
        and bool(changed_paths)
        and (all(path in TRUSTED_BOT_PATHS for path in changed_paths) or actions_pins_verified)
    )


def check_merge_rights(
    api: GitHubApi,
    changed_paths: list[str],
    *,
    bot_commits_verified: bool = False,
    actions_pins_verified: bool = False,
) -> RightsResult:
    if api.user.lower() == api.owner.lower():
        return RightsResult(allowed=True, reason="repository owner")
    if api.user.lower() in TRUSTED_BOT_LOGINS and bot_commits_verified and changed_paths:
        if all(path in TRUSTED_BOT_PATHS for path in changed_paths):
            return RightsResult(
                allowed=True,
                reason="trusted automation account, verified bot commits, manifest paths only",
            )
        if actions_pins_verified:
            return RightsResult(
                allowed=True,
                reason=(
                    "trusted automation account, verified bot commits, "
                    "tag-verified actions pin bump only"
                ),
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
    actions_pins_verified: bool = False,
) -> PrPolicyResult:
    return PrPolicyResult(
        title=check_pr_title(title, allowed_types),
        template=check_template(template, body),
        pr_privilege=check_pr_rights(api),
        merge_privilege=check_merge_rights(
            api,
            changed_paths,
            bot_commits_verified=bot_commits_verified,
            actions_pins_verified=actions_pins_verified,
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


def _safe_api_segment(value: str) -> bool:
    """A repository or tag name used as a REST path segment: never `.`, `..`
    or anything containing `..`, so it cannot climb out of its endpoint."""
    return ".." not in value and value not in {"", "."}


def resolve_action_tag_sha(owner_repo: str, tag: str) -> str | None:
    """The commit SHA that `tag` names in `owner_repo` right now, read from
    GitHub (`git/ref/tags/<tag>`, an exact-name lookup, peeling annotated
    tags). Any API error, timeout, malformed answer or unexpected shape
    returns None, so the caller fails closed."""
    owner, _, repo = owner_repo.partition("/")
    if not all(_safe_api_segment(part) for part in (owner, repo, tag)):
        return None

    def get(path: str) -> dict | None:
        try:
            result = subprocess.run(
                ["gh", "api", "--method", "GET", f"repos/{owner}/{repo}/{path}"],
                capture_output=True,
                text=True,
                timeout=_TAG_LOOKUP_TIMEOUT_SECONDS,
            )
        except (subprocess.TimeoutExpired, OSError, UnicodeDecodeError):
            return None
        if result.returncode != 0:
            return None
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    ref = get(f"git/ref/tags/{tag}")
    if ref is None or ref.get("ref") != f"refs/tags/{tag}":
        return None
    obj = ref.get("object")
    # An annotated tag points at a tag object; peel a short chain of them.
    for _ in range(3):
        if not isinstance(obj, dict) or not isinstance(obj.get("sha"), str):
            return None
        if obj.get("type") == "commit":
            sha = obj["sha"]
            return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else None
        if obj.get("type") != "tag" or not re.fullmatch(r"[0-9a-f]{40}", obj["sha"]):
            return None
        tag_obj = get(f"git/tags/{obj['sha']}")
        obj = tag_obj.get("object") if tag_obj else None
    return None


def _pin_pair_ok(old: str, new: str, resolve_tag, cache: dict) -> bool:
    old_m = _USES_PIN_LINE.fullmatch(old)
    new_m = _USES_PIN_LINE.fullmatch(new)
    if old_m is None or new_m is None:
        return False
    action = new_m["action"]
    if (
        old_m["prefix"] != new_m["prefix"]
        or old_m["quote"] != new_m["quote"]
        or old_m["action"] != action
        or new_m["ratchet"] != action
    ):
        return False
    owner_repo = "/".join(action.split("/")[:2])
    key = (owner_repo.lower(), new_m["tag"])
    if key not in cache:
        cache[key] = resolve_tag(owner_repo, new_m["tag"])
    return cache[key] == new_m["sha"]


def actions_pin_bump_verified(
    repo: Path,
    base_sha: str,
    head_sha: str,
    changed_paths: list[str],
    *,
    resolve_tag=None,
) -> bool:
    """True only if the PR (`base_sha...head_sha`) modifies nothing but
    workflow or composite-action YAML files (_ACTIONS_PIN_FILE), and every
    changed line is one `uses: <action>@<sha> # ratchet:<action>@<tag>` line
    replaced by the same line shape for the same action, whose new SHA is the
    commit `<tag>` names in the action's own repository right now. That last
    check means the pin cannot point at a commit that exists only in a
    third-party fork of the action (a tag moved inside the action's own
    repository is still trusted). Anything else (an added or deleted file, a mode change, a
    changed line of any other kind, a git or API error or timeout) returns False, so the
    caller falls back to the normal CODEOWNERS check."""
    resolve_tag = resolve_tag or resolve_action_tag_sha
    if not changed_paths or not all(_ACTIONS_PIN_FILE.fullmatch(p) for p in changed_paths):
        return False
    # The SHAs come from the event file. Only a full commit SHA may reach git,
    # so no value can be read as an option.
    if not (_COMMIT_SHA.fullmatch(base_sha) and _COMMIT_SHA.fullmatch(head_sha)):
        return False
    revisions = f"{base_sha}...{head_sha}"
    try:
        status = subprocess.run(  # nosec B603 B607  # literal git subcommand, no shell, validated SHAs
            [
                "git",
                "diff",
                "--no-renames",
                "--no-ext-diff",
                "--no-textconv",
                "--no-color",
                "-z",
                "--name-status",
                revisions,
            ],
            cwd=repo,
            capture_output=True,
            timeout=_GIT_DIFF_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    if status.returncode != 0:
        return False
    fields = status.stdout.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 2:
        return False
    pairs = list(zip(fields[::2], fields[1::2], strict=True))
    try:
        listed = {path.decode("utf-8") for _, path in pairs}
    except UnicodeDecodeError:
        return False
    if any(kind != b"M" for kind, _ in pairs) or listed != set(changed_paths):
        return False

    # --literal-pathspecs: a changed path is matched as its exact name, never as a glob.
    try:
        diff = subprocess.run(  # nosec B603 B607  # literal git subcommand, no shell, paths after --
            [
                "git",
                "--literal-pathspecs",
                "diff",
                "--no-renames",
                "--no-ext-diff",
                "--no-textconv",
                "--no-color",
                "-U0",
                revisions,
                "--",
                *changed_paths,
            ],
            cwd=repo,
            capture_output=True,
            timeout=_GIT_DIFF_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    if diff.returncode != 0:
        return False
    try:
        lines = diff.stdout.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        return False
    if lines and lines[-1] == "":
        lines.pop()

    cache: dict = {}
    hunks = 0
    # Every changed path must yield at least one checked hunk under its own
    # `+++ b/<path>` header, so no file can drop out of the content check.
    current: str | None = None
    covered: set[str] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            current = None
            i += 1
            continue
        if line.startswith("+++ b/"):
            # git ends the name with a tab when it contains whitespace.
            current = line[len("+++ b/") :].removesuffix("\t")
            i += 1
            continue
        if line.startswith(("index ", "--- a/")):
            i += 1
            continue
        header = _HUNK_HEADER.match(line)
        if header is None:
            return False  # a mode change, binary file or anything unexpected
        if current is None:
            return False  # a hunk with no file header
        old_count = int(header["old"] or 1)
        new_count = int(header["new"] or 1)
        if old_count != new_count or old_count == 0:
            return False
        body = lines[i + 1 : i + 1 + old_count + new_count]
        if len(body) != old_count + new_count:
            return False
        removed, added = body[:old_count], body[old_count:]
        if not all(r.startswith("-") for r in removed) or not all(a.startswith("+") for a in added):
            return False
        for old, new in zip(removed, added, strict=True):
            if not _pin_pair_ok(old[1:], new[1:], resolve_tag, cache):
                return False
        hunks += 1
        covered.add(current)
        i += 1 + old_count + new_count
    return hunks > 0 and covered == set(changed_paths)
