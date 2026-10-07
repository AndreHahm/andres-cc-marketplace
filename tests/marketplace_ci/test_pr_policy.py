import json
import subprocess

import pytest

from scripts.marketplace_ci.pr_policy import (
    check_merge_rights,
    check_pr_rights,
    check_pr_title,
    check_template,
    commits_verified_from_trusted_bot,
    evaluate_pr_policy,
)

PRIMARY_TEMPLATE = """## Summary

## Type of Change

## Related Issue

## Changes

## Testing

## Checklist
"""

BODY_WITH_EXTRA_HEADING = """## Summary

Adds a thing.

## Deployment

Special rollout notes.
"""


class FakeApi:
    def __init__(self, user: str, owner: str, permission: str | None = None, codeowners=()):
        self.user = user
        self.owner = owner
        self._permission = permission
        self._codeowners = codeowners
        self.collaborator_calls = 0

    def collaborator_permission(self, username: str) -> str | None:
        self.collaborator_calls += 1
        return self._permission

    def codeowners(self):
        return self._codeowners


def test_pr_template_requires_exact_order_and_no_extra_sections():
    result = check_template(PRIMARY_TEMPLATE, BODY_WITH_EXTRA_HEADING)
    assert result.passed is False
    assert result.reason == "unexpected heading: Deployment"


def test_owner_short_circuits_merge_rights():
    api = FakeApi(user="andre", owner="Andre")
    assert check_merge_rights(api, ["plugins/git-kit/x"]).allowed is True
    assert api.collaborator_calls == 0


def test_template_passes_with_subset_of_headings_in_order():
    body = "## Summary\n\nDid a thing.\n\n## Checklist\n\n- [x] done\n"
    result = check_template(PRIMARY_TEMPLATE, body)
    assert result.passed is True


def test_template_fails_when_headings_out_of_order():
    body = "## Checklist\n\n- [x] done\n\n## Summary\n\nDid a thing.\n"
    result = check_template(PRIMARY_TEMPLATE, body)
    assert result.passed is False
    assert result.reason == "headings out of order"


@pytest.mark.parametrize(
    "title",
    [
        "feat(ci): add marketplace sync registry models",
        "fix: resolve failing pipeline tests",
        "feat!: require re-authentication",
    ],
)
def test_valid_titles_pass(title):
    assert check_pr_title(title).passed is True


def test_title_rejects_emoji():
    result = check_pr_title("feat: :sparkles: add feature")
    assert result.passed is False


def test_title_rejects_unicode_emoji():
    result = check_pr_title("feat: add feature ✨")
    assert result.passed is False
    assert result.reason is not None and "emoji" in result.reason


def test_title_rejects_unknown_type():
    result = check_pr_title("wip: quick hack")
    assert result.passed is False
    assert result.reason is not None and "unknown commit type" in result.reason


def test_title_rejects_missing_colon():
    result = check_pr_title("feat add a thing")
    assert result.passed is False


def test_pr_rights_owner_short_circuits():
    api = FakeApi(user="andre", owner="andre")
    assert check_pr_rights(api).allowed is True


def test_pr_rights_requires_write_permission():
    api = FakeApi(user="contributor", owner="andre", permission="read")
    result = check_pr_rights(api)
    assert result.allowed is False
    assert result.reason is not None and "read" in result.reason


def test_pr_rights_allows_write_permission():
    api = FakeApi(user="contributor", owner="andre", permission="write")
    assert check_pr_rights(api).allowed is True


def test_merge_rights_direct_codeowners_match_allows():
    api = FakeApi(
        user="reviewer1",
        owner="andre",
        permission="read",
        codeowners=(("plugins/git-kit/**", ("reviewer1", "reviewer2")),),
    )
    result = check_merge_rights(api, ["plugins/git-kit/skills/commit/SKILL.md"])
    assert result.allowed is True
    assert result.reason == "direct CODEOWNERS match"


def test_merge_rights_non_owner_not_in_codeowners_denied_without_collaborator_fallback():
    api = FakeApi(
        user="outsider",
        owner="andre",
        permission="write",
        codeowners=(("plugins/git-kit/**", ("reviewer1",)),),
    )
    result = check_merge_rights(api, ["plugins/git-kit/skills/commit/SKILL.md"])
    assert result.allowed is False
    assert result.reason is not None and "team membership cannot be verified" in result.reason


def test_merge_rights_last_matching_codeowners_entry_wins():
    api = FakeApi(
        user="late-owner",
        owner="andre",
        codeowners=(
            ("plugins/**", ("early-owner",)),
            ("plugins/git-kit/**", ("late-owner",)),
        ),
    )
    result = check_merge_rights(api, ["plugins/git-kit/skills/commit/SKILL.md"])
    assert result.allowed is True


def test_merge_rights_falls_back_to_collaborator_permission_with_no_codeowners_match():
    api = FakeApi(user="contributor", owner="andre", permission="maintain", codeowners=())
    result = check_merge_rights(api, ["scripts/marketplace_ci/sync.py"])
    assert result.allowed is True
    assert result.reason is not None and "maintain" in result.reason


def test_evaluate_pr_policy_combines_all_checks():
    api = FakeApi(user="andre", owner="andre")
    result = evaluate_pr_policy(
        api,
        title="feat(ci): add pr policy",
        body=PRIMARY_TEMPLATE,
        template=PRIMARY_TEMPLATE,
        changed_paths=["scripts/marketplace_ci/pr_policy.py"],
    )
    assert result.passed is True


def test_evaluate_pr_policy_fails_when_any_check_fails():
    api = FakeApi(user="andre", owner="andre")
    result = evaluate_pr_policy(
        api,
        title="not a valid title",
        body=PRIMARY_TEMPLATE,
        template=PRIMARY_TEMPLATE,
        changed_paths=["scripts/marketplace_ci/pr_policy.py"],
    )
    assert result.passed is False


def test_trusted_bot_passes_pr_rights_without_api_lookup():
    api = FakeApi(user="dependabot[bot]", owner="andre")
    assert check_pr_rights(api).allowed is True
    assert api.collaborator_calls == 0


@pytest.mark.parametrize("login", ["dependabot[bot]", "Dependabot[bot]"])
def test_trusted_bot_merge_rights_for_manifest_paths_only(login):
    api = FakeApi(user=login, owner="andre", codeowners=(("*", ("@andre",)),))
    assert (
        check_merge_rights(api, ["uv.lock", "pyproject.toml"], bot_commits_verified=True).allowed
        is True
    )
    assert api.collaborator_calls == 0


@pytest.mark.parametrize(
    "paths",
    [
        ["uv.lock", "scripts/marketplace_ci/pr_policy.py"],
        [".github/workflows/x.yml"],
        ["sub/uv.lock"],
        [".github/security-tools/package.json"],
        ["UV.lock"],
        ["package-lock.json"],
        [],
    ],
)
def test_trusted_bot_denied_when_any_path_outside_manifests(paths):
    # permission="write" proves the denial comes from the CODEOWNERS branch
    # (or the empty-list guard), not from a None collaborator lookup.
    api = FakeApi(
        user="dependabot[bot]",
        owner="andre",
        permission="write" if not paths else None,
        codeowners=(("*", ("@andre",)),),
    )
    result = check_merge_rights(api, paths, bot_commits_verified=True)
    if paths:
        assert result.allowed is False
        assert result.reason is not None and "CODEOWNERS" in result.reason
    else:
        # No exemption for an empty path list: falls through to the normal
        # branches rather than being waved through as "manifests only".
        assert result.reason != "trusted automation account, manifest paths only"


@pytest.mark.parametrize(
    "login", ["dependabot", "app/dependabot", "evil-dependabot[bot]", "other[bot]"]
)
def test_lookalike_bot_logins_are_not_trusted(login):
    api = FakeApi(user=login, owner="andre", permission=None)
    assert check_pr_rights(api).allowed is False
    assert check_merge_rights(api, ["uv.lock"]).allowed is False


def test_trusted_bot_denied_without_verified_bot_commits():
    api = FakeApi(user="dependabot[bot]", owner="andre", codeowners=(("*", ("@andre",)),))
    result = check_merge_rights(api, ["uv.lock"])
    assert result.allowed is False
    assert result.reason is not None and "CODEOWNERS" in result.reason


def _fake_gh(monkeypatch, stdout="", returncode=0):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)


def _commit_line(a="dependabot[bot]", c="web-flow", v=True, sha="head"):
    return json.dumps({"s": sha, "a": a, "c": c, "v": v})


def test_commits_verified_accepts_genuine_dependabot_commits(monkeypatch):
    _fake_gh(monkeypatch, _commit_line() + "\n" + _commit_line() + "\n")
    assert commits_verified_from_trusted_bot("o/r", 1, "head", 2) is True


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        _commit_line() + "\n" + _commit_line(a="collaborator") + "\n",
        _commit_line(c="collaborator"),
        _commit_line(v=False),
        _commit_line(v="true"),
        '{"s": "head", "a": null, "c": "web-flow", "v": true}',
        "not json",
    ],
)
def test_commits_verified_fails_closed(monkeypatch, stdout):
    _fake_gh(monkeypatch, stdout)
    assert commits_verified_from_trusted_bot("o/r", 1, "head", 2) is False


def test_commits_verified_fails_closed_on_api_error_or_missing_number(monkeypatch):
    _fake_gh(monkeypatch, _commit_line(), returncode=1)
    assert commits_verified_from_trusted_bot("o/r", 1, "head", 2) is False
    _fake_gh(monkeypatch, _commit_line())
    assert commits_verified_from_trusted_bot("o/r", None, "head", 1) is False


@pytest.mark.parametrize("count", [None, 0, 1, 3, 250, "2"])
def test_commits_verified_fails_closed_on_count_mismatch_or_cap(monkeypatch, count):
    _fake_gh(monkeypatch, _commit_line() + "\n" + _commit_line() + "\n")
    assert commits_verified_from_trusted_bot("o/r", 1, "head", count) is False


def test_commits_verified_fails_closed_when_head_sha_differs(monkeypatch):
    _fake_gh(monkeypatch, _commit_line(sha="old") + "\n" + _commit_line(sha="old") + "\n")
    assert commits_verified_from_trusted_bot("o/r", 1, "head", 2) is False


def test_commits_verified_gh_argv(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=_commit_line() + "\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert commits_verified_from_trusted_bot("o/r", 7, "head", 1) is True
    assert seen["cmd"][:4] == ["gh", "api", "--paginate", "repos/o/r/pulls/7/commits"]
