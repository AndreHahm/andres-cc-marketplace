import pytest

from scripts.marketplace_ci.pr_policy import (
    check_merge_rights,
    check_pr_rights,
    check_pr_title,
    check_template,
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
