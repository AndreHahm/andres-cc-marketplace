"""git-kit's git-review-api.py is the only way handling-review-findings reaches GitHub (#580).

The wrapper replaces broad `gh`, `git remote` and `sed` grants with fixed subcommands. These tests
pin the exact argv each subcommand builds, the validation that keeps caller input from becoming
extra arguments, how a body file is read and confined, and the single-use marker the write
subcommands require.
"""

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins/git-kit/scripts/git-review-api.py"
MARKER_WRITER = ROOT / "plugins/git-kit/scripts/git-write-marker.sh"
GUARD = "gh-pr-review-wrapper"


def _load_module():
    spec = importlib.util.spec_from_file_location("git_review_api", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["git_review_api"] = module
    spec.loader.exec_module(module)
    return module


M = _load_module()


class FakeRun:
    """Stands in for subprocess.run: answers `git rev-parse --git-dir`, records every other call."""

    def __init__(self, git_dir, stdout="", returncode=0, raises=None, probe_raises=None):
        self.git_dir = git_dir
        self.stdout = stdout
        self.returncode = returncode
        self.raises = raises  # raised by every call except the git-dir probe
        self.probe_raises = probe_raises  # raised by the git-dir probe
        self.calls = []  # (argv, input) for everything except the git-dir probe

    @property
    def gh_calls(self):
        return [argv for argv, _ in self.calls]

    def __call__(self, argv, **kwargs):
        assert isinstance(argv, list), "must run with a static argv, never a shell string"
        assert not kwargs.get("shell"), "must never run through a shell"
        assert kwargs.get("timeout", 0) > 0, "every child process needs a finite timeout"
        if argv[:2] == ["git", "rev-parse"]:
            if self.probe_raises:
                raise self.probe_raises
            return subprocess.CompletedProcess(argv, 0, stdout=f"{self.git_dir}\n", stderr="")
        if self.raises:
            raise self.raises
        self.calls.append((argv, kwargs.get("input")))
        return subprocess.CompletedProcess(argv, self.returncode, stdout=self.stdout, stderr="")


@pytest.fixture
def env(tmp_path, monkeypatch):
    git_dir = tmp_path / "gitdir"
    git_dir.mkdir()
    root = tmp_path / "claude-root"  # stands in for <temp>/claude-<uid>
    scratch = root / "project" / "scratchpad"
    scratch.mkdir(parents=True)
    body = scratch / "body.txt"
    body.write_text("hello")
    monkeypatch.setattr(M, "allowed_body_roots", lambda: [os.path.realpath(root)])
    return git_dir, FakeRun(git_dir), body


def _write_marker(git_dir, guard=GUARD, age=0):
    (git_dir / "git-kit-marker.txt").write_text(f"{guard} {int(time.time()) - age} handling\n")


def _run(fake, argv):
    return M.main(argv, run=fake)


COMMON = ["--owner", "AndreHahm", "--repo", "andres-cc-marketplace", "--pr", "579"]
REPO = ["--owner", "AndreHahm", "--repo", "andres-cc-marketplace"]


# --- argv built per subcommand -----------------------------------------------------------------


def test_threads_first_page_sends_typed_null_cursor(env):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["threads", *COMMON]) == 0
    ((argv, stdin),) = fake.calls
    assert stdin is None
    assert argv[:3] == ["gh", "api", "graphql"]
    assert ["-f", "owner=AndreHahm"] == argv[3:5]
    assert ["-f", "name=andres-cc-marketplace"] == argv[5:7]
    assert ["-F", "number=579"] == argv[7:9]
    assert ["-F", "cursor=null"] == argv[9:11]
    assert argv[11] == "-f" and argv[12].startswith("query=")
    assert "reviewThreads(first: 50, after: $cursor)" in argv[12]
    assert "mutation" not in argv[12]


def test_threads_sends_owner_and_name_as_strings_not_typed_values(env):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["threads", "--owner", "123", "--repo", "true", "--pr", "1"]) == 0
    ((argv, _),) = fake.calls
    assert ["-f", "owner=123"] == argv[3:5] and ["-f", "name=true"] == argv[5:7]


def test_threads_next_page_sends_cursor_as_string(env):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["threads", *COMMON, "--cursor", "Y3Vyc29yOnYy"]) == 0
    ((argv, _),) = fake.calls
    assert ["-f", "cursor=Y3Vyc29yOnYy"] == argv[9:11]
    assert "cursor=null" not in argv


def test_resolve_builds_the_one_mutation(env):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["resolve", "--thread-id", "PRRT_kwDOabc-123_x"]) == 0
    ((argv, _),) = fake.calls
    assert argv[:3] == ["gh", "api", "graphql"]
    assert argv[-2:] == ["-f", "id=PRRT_kwDOabc-123_x"]
    assert "resolveReviewThread" in argv[4] and "mergePullRequest" not in argv[4]


def test_reply_posts_to_the_reply_endpoint_with_the_body_on_stdin(env):
    git_dir, fake, body = env
    _write_marker(git_dir)
    assert _run(fake, ["reply", *COMMON, "--comment-id", "42", "--body-file", str(body)]) == 0
    ((argv, stdin),) = fake.calls
    assert argv == [
        "gh",
        "api",
        "repos/AndreHahm/andres-cc-marketplace/pulls/579/comments/42/replies",
        "-F",
        "body=@-",
        "--silent",
    ]
    assert stdin == b"hello"


def test_trigger_comment_posts_top_level_comment_with_the_body_on_stdin(env):
    git_dir, fake, body = env
    _write_marker(git_dir)
    assert _run(fake, ["trigger-comment", *COMMON, "--body-file", str(body)]) == 0
    ((argv, stdin),) = fake.calls
    assert argv == [
        "gh",
        "pr",
        "comment",
        "579",
        "-R",
        "AndreHahm/andres-cc-marketplace",
        "--body-file",
        "-",
    ]
    assert stdin == b"hello"


def test_issue_create_files_in_the_named_repo_with_the_body_on_stdin(env):
    git_dir, fake, body = env
    _write_marker(git_dir)
    argv_in = ["issue-create", *REPO, "--title", "Fix the thing", "--body-file", str(body)]
    assert _run(fake, argv_in) == 0
    ((argv, stdin),) = fake.calls
    assert argv == [
        "gh",
        "issue",
        "create",
        "-R",
        "AndreHahm/andres-cc-marketplace",
        "--title",
        "Fix the thing",
        "--body-file",
        "-",
    ]
    assert stdin == b"hello"


def test_list_comments_is_a_paginated_read_and_needs_no_marker(env):
    _, fake, _ = env
    assert _run(fake, ["list-comments", *COMMON]) == 0
    assert fake.gh_calls == [
        ["gh", "api", "repos/AndreHahm/andres-cc-marketplace/pulls/579/comments", "--paginate"]
    ]


def test_whoami_reads_only_the_login_and_needs_no_marker(env):
    _, fake, _ = env
    assert _run(fake, ["whoami"]) == 0
    assert fake.gh_calls == [["gh", "api", "user", "--jq", ".login"]]


def test_push_destinations_lists_normalized_slugs_and_needs_no_marker(env, capsys):
    git_dir, _, _ = env
    fake = FakeRun(
        git_dir,
        stdout="https://github.com/AndreHahm/repo-a.git\ngit@github.com:AndreHahm/repo-b.git\n",
    )
    assert _run(fake, ["push-destinations"]) == 0
    assert fake.gh_calls == [["git", "remote", "get-url", "--push", "--all", "origin"]]
    assert capsys.readouterr().out.splitlines() == ["AndreHahm/repo-a", "AndreHahm/repo-b"]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/AndreHahm/repo.git", "AndreHahm/repo"),
        ("https://github.com/AndreHahm/repo", "AndreHahm/repo"),
        ("https://github.com/AndreHahm/repo/", "AndreHahm/repo"),
        ("https://github.com/AndreHahm/repo.git/", "AndreHahm/repo"),
        ("https://x-access-token@github.com/AndreHahm/repo.git", "AndreHahm/repo"),
        ("git@github.com:AndreHahm/repo.git", "AndreHahm/repo"),
        ("ssh://git@github.com/AndreHahm/repo.git", "AndreHahm/repo"),
        ("ssh://github.com/AndreHahm/repo", "AndreHahm/repo"),
    ],
)
def test_push_destinations_normalizes_every_github_remote_form(env, capsys, url, expected):
    git_dir, _, _ = env
    fake = FakeRun(git_dir, stdout=f"{url}\n")
    assert _run(fake, ["push-destinations"]) == 0
    assert capsys.readouterr().out.strip() == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/github.com/AndreHahm/repo.git",
        "https://gitlab.com/AndreHahm/repo.git",
        "https://user:s3cret-token@evil.example/AndreHahm/repo.git",
        "https://github.com@evil.example/AndreHahm/repo.git",
        "ssh://git@github.com:2222/AndreHahm/repo.git",
        # a recognized GitHub prefix must not make the rest of the URL safe to echo
        "https://github.com/AndreHahm/repo?token=s3cret",
        "https://github.com/AndreHahm/repo.git?access_token=s3cret",
        "https://github.com/AndreHahm/repo#s3cret-fragment",
        "https://github.com/AndreHahm/repo/extra/s3cret",
        "git@github.com:AndreHahm/repo.git?x=s3cret",
        "https://github.com/AndreHahm/repo\\s3cret",
    ],
)
def test_an_unsupported_push_url_is_never_printed_and_fails(env, capsys, url):
    git_dir, _, _ = env
    fake = FakeRun(git_dir, stdout=f"{url}\n")
    assert _run(fake, ["push-destinations"]) == 1
    out = capsys.readouterr().out
    assert out.strip() == M.UNSUPPORTED_URL
    assert "s3cret" not in out and "evil.example" not in out and "AndreHahm" not in out


def test_push_destinations_with_one_unsupported_url_among_good_ones_fails(env, capsys):
    git_dir, _, _ = env
    stdout = "https://github.com/AndreHahm/repo.git\nhttps://token@evil.example/x/y.git\n"
    assert _run(FakeRun(git_dir, stdout=stdout), ["push-destinations"]) == 1
    assert capsys.readouterr().out.splitlines() == ["AndreHahm/repo", M.UNSUPPORTED_URL]


def test_push_destinations_with_no_url_fails_instead_of_passing_vacuously(env, capsys):
    git_dir, _, _ = env
    assert _run(FakeRun(git_dir, stdout="\n"), ["push-destinations"]) == 1
    assert capsys.readouterr().out == ""


def test_push_destinations_propagates_a_failing_git_call_without_output(env, capsys):
    git_dir, _, _ = env
    assert _run(FakeRun(git_dir, stdout="", returncode=2), ["push-destinations"]) == 2
    assert capsys.readouterr().out == ""


# --- timeouts: no child process can block the skill forever -------------------------------------


def test_a_gh_call_that_times_out_returns_a_nonzero_result(env, capsys):
    git_dir, _, _ = env
    fake = FakeRun(git_dir, raises=subprocess.TimeoutExpired(["gh"], M.CALL_TIMEOUT))
    assert _run(fake, ["list-comments", *COMMON]) == 124
    assert "timed out" in capsys.readouterr().err


def test_a_marker_probe_that_times_out_refuses_the_write(env, capsys):
    git_dir, _, _ = env
    fake = FakeRun(git_dir, probe_raises=subprocess.TimeoutExpired(["git"], M.PROBE_TIMEOUT))
    _write_marker(git_dir)
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) == 2
    assert fake.gh_calls == []
    assert "timed out" in capsys.readouterr().err


# --- marker handshake --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["threads", *COMMON],
        ["resolve", "--thread-id", "PRRT_abc"],
        ["reply", *COMMON, "--comment-id", "42", "--body-file", "BODY"],
        ["trigger-comment", *COMMON, "--body-file", "BODY"],
        ["issue-create", *REPO, "--title", "t", "--body-file", "BODY"],
    ],
)
def test_write_subcommands_refuse_without_a_marker(env, argv):
    _, fake, body = env
    argv = [str(body) if a == "BODY" else a for a in argv]
    assert _run(fake, argv) != 0
    assert fake.gh_calls == []


def test_marker_is_consumed_so_a_second_call_is_refused(env):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) == 0
    assert not (git_dir / "git-kit-marker.txt").exists()
    assert _run(fake, ["resolve", "--thread-id", "PRRT_b"]) != 0
    assert len(fake.gh_calls) == 1


def test_consuming_a_marker_leaves_no_claim_file_behind(env):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) == 0
    assert list(git_dir.iterdir()) == []


def test_a_marker_swapped_in_by_another_guard_before_the_claim_is_restored_not_deleted(
    env, monkeypatch
):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    real_rename = os.rename

    def swap_then_rename(src, dst):
        Path(src).write_text(f"gh-pr-review {int(time.time())} other\n")
        real_rename(src, dst)

    monkeypatch.setattr(M.os, "rename", swap_then_rename)
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) != 0
    assert fake.gh_calls == []
    assert (git_dir / "git-kit-marker.txt").read_text().startswith("gh-pr-review ")
    assert [p.name for p in git_dir.iterdir()] == ["git-kit-marker.txt"]


def test_stale_marker_is_refused(env):
    git_dir, fake, _ = env
    _write_marker(git_dir, age=61)
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) != 0
    assert fake.gh_calls == []


def test_future_dated_marker_is_refused(env):
    git_dir, fake, _ = env
    _write_marker(git_dir, age=-30)
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) != 0
    assert fake.gh_calls == []


def test_the_existing_guards_marker_type_does_not_authorize_the_wrapper(env):
    git_dir, fake, _ = env
    _write_marker(git_dir, guard="gh-pr-review")
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) != 0
    assert (git_dir / "git-kit-marker.txt").exists(), "a marker for another guard is left alone"
    assert fake.gh_calls == []


@pytest.mark.parametrize("stamp", ["not-a-number", "¹²³", "12345678901", ""])
def test_malformed_marker_is_refused(env, stamp):
    git_dir, fake, _ = env
    (git_dir / "git-kit-marker.txt").write_text(f"{GUARD} {stamp} x\n")
    assert _run(fake, ["resolve", "--thread-id", "PRRT_a"]) != 0
    assert fake.gh_calls == []


def test_invalid_input_runs_no_gh_and_keeps_the_marker_for_the_corrected_call(env):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["resolve", "--thread-id", "not-a-thread-id"]) != 0
    assert fake.gh_calls == []
    assert _run(fake, ["resolve", "--thread-id", "PRRT_ok"]) == 0


# --- validation: caller input never becomes an extra argument -----------------------------------


@pytest.mark.parametrize("owner", ["", "-x", "a b", "a/b", "a;b", "$(id)", "a\nb", "@file"])
def test_bad_owner_is_rejected(env, owner):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    argv = ["threads", "--owner", owner, "--repo", "r", "--pr", "1"]
    assert _run(fake, argv) != 0
    assert fake.gh_calls == []


@pytest.mark.parametrize("repo", ["", "-x", ".", "..", "a b", "a/b", "a;b", "@file"])
def test_bad_repo_is_rejected(env, repo):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    argv = ["threads", "--owner", "o", "--repo", repo, "--pr", "1"]
    assert _run(fake, argv) != 0
    assert fake.gh_calls == []


@pytest.mark.parametrize("pr", ["0", "-1", "01", "1.5", "abc", "99999999999", ""])
def test_bad_pr_number_is_rejected(env, pr):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["threads", "--owner", "o", "--repo", "r", "--pr", pr]) != 0
    assert fake.gh_calls == []


@pytest.mark.parametrize("tid", ["", "abc", "PRRT_", "PRRT_a b", "PRRT_a;b", "-fid=1", "PRRT_a\n"])
def test_bad_thread_id_is_rejected(env, tid):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["resolve", "--thread-id", tid]) != 0
    assert fake.gh_calls == []


@pytest.mark.parametrize("cursor", ["", "a b", "a;b", "@file", "-x", "null\n"])
def test_bad_cursor_is_rejected(env, cursor):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    assert _run(fake, ["threads", *COMMON, "--cursor", cursor]) != 0
    assert fake.gh_calls == []


@pytest.mark.parametrize("title", ["", "   ", "a\nb", "a\x00b", "x" * 257])
def test_bad_issue_title_is_rejected(env, title):
    git_dir, fake, body = env
    _write_marker(git_dir)
    argv = ["issue-create", *REPO, "--title", title, "--body-file", str(body)]
    assert _run(fake, argv) != 0
    assert fake.gh_calls == []


def test_unknown_subcommand_is_rejected(env):
    _, fake, _ = env
    assert _run(fake, ["merge", *COMMON]) != 0
    assert fake.gh_calls == []


def test_embedded_documents_are_one_read_query_and_one_resolve_mutation():
    assert "mutation" not in M.THREADS_QUERY
    assert M.RESOLVE_MUTATION.count("mutation") == 1
    assert "resolveReviewThread" in M.RESOLVE_MUTATION
    assert "mergePullRequest" not in M.THREADS_QUERY + M.RESOLVE_MUTATION
    assert "--input" not in SCRIPT.read_text()


# --- body file: confined, read here, never handed to gh as a path -------------------------------


def _trigger(env, path):
    git_dir, fake, _ = env
    _write_marker(git_dir)
    return _run(fake, ["trigger-comment", *COMMON, "--body-file", str(path)]), fake


def test_missing_body_file_is_rejected(env):
    _, _, body = env
    code, fake = _trigger(env, body.parent / "absent.txt")
    assert code != 0 and fake.gh_calls == []


def test_body_file_that_is_a_symlink_is_rejected_even_inside_the_root(env):
    _, _, body = env
    outside = body.parent.parent / "outside.txt"
    outside.write_text("secret")
    link = body.parent / "link.txt"
    link.symlink_to(outside)
    code, fake = _trigger(env, link)
    assert code != 0 and fake.gh_calls == []


def test_a_symlink_to_another_file_inside_the_scratchpad_is_rejected(env):
    _, _, body = env
    target = body.parent / "someone-elses-output.txt"
    target.write_text("not the agent's own file")
    link = body.parent / "reply.txt"
    link.symlink_to(target)
    code, fake = _trigger(env, link)
    assert code != 0 and fake.gh_calls == []


def test_a_hard_link_to_a_file_outside_the_scratchpad_is_rejected(env):
    _, _, body = env
    outside = body.parent.parent / "owned-file-outside-scratchpad.txt"
    outside.write_text("an owned file elsewhere in the scratch tree")
    link = body.parent / "reply.txt"
    os.link(outside, link)
    code, fake = _trigger(env, link)
    assert code != 0 and fake.gh_calls == []


def test_a_file_in_the_scratch_tree_but_outside_a_scratchpad_directory_is_rejected(env):
    _, _, body = env
    tasks = body.parent.parent / "tasks"
    tasks.mkdir()
    (tasks / "transcript.output").write_text("session transcript")
    code, fake = _trigger(env, tasks / "transcript.output")
    assert code != 0 and fake.gh_calls == []


def test_a_file_owned_by_another_user_is_rejected(env, monkeypatch):
    _, _, body = env
    other_uid = os.getuid() + 1
    monkeypatch.setattr(M.os, "getuid", lambda: other_uid)
    code, fake = _trigger(env, body)
    assert code != 0 and fake.gh_calls == []


def test_real_roots_are_the_per_user_claude_tree_under_the_temp_directory():
    roots = M.allowed_body_roots()
    assert roots and all(r.endswith(f"claude-{os.getuid()}") for r in roots)


def test_body_file_reached_through_a_symlinked_directory_is_rejected(env):
    _, _, body = env
    outside_dir = body.parent.parent / "elsewhere"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("secret")
    (body.parent / "dirlink").symlink_to(outside_dir)
    code, fake = _trigger(env, body.parent / "dirlink" / "secret.txt")
    assert code != 0 and fake.gh_calls == []


def test_body_file_outside_the_temp_root_is_rejected(env):
    _, _, body = env
    outside = body.parent.parent / "outside.txt"
    outside.write_text("secret")
    code, fake = _trigger(env, outside)
    assert code != 0 and fake.gh_calls == []


@pytest.mark.skipif(not os.path.exists("/proc/self/environ"), reason="needs procfs")
def test_procfs_file_is_rejected(env):
    code, fake = _trigger(env, "/proc/self/environ")
    assert code != 0 and fake.gh_calls == []


def test_body_file_that_is_a_directory_is_rejected(env):
    _, _, body = env
    code, fake = _trigger(env, body.parent)
    assert code != 0 and fake.gh_calls == []


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs mkfifo")
def test_body_file_that_is_a_fifo_is_rejected_without_blocking(env):
    _, _, body = env
    fifo = body.parent / "pipe"
    os.mkfifo(fifo)
    code, fake = _trigger(env, fifo)
    assert code != 0 and fake.gh_calls == []


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"  \n",
        b"\xff\xfe bad utf-8",
        b"x" * (M.MAX_BODY_CHARS + 1),
        b"x" * (M.MAX_BODY_BYTES + 1),
    ],
)
def test_empty_non_utf8_or_oversized_body_is_rejected(env, content):
    _, _, body = env
    body.write_bytes(content)
    code, fake = _trigger(env, body)
    assert code != 0 and fake.gh_calls == []


def test_a_body_at_the_character_limit_is_accepted(env):
    _, _, body = env
    body.write_bytes(b"x" * M.MAX_BODY_CHARS)
    code, fake = _trigger(env, body)
    assert code == 0 and fake.calls[0][1] == b"x" * M.MAX_BODY_CHARS


# --- the marker writer accepts the new guard type ----------------------------------------------


def test_marker_writer_accepts_the_wrapper_guard_type(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    result = subprocess.run(
        ["bash", str(MARKER_WRITER), GUARD, "handling-review-findings"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    guard, ts, skill = (tmp_path / ".git/git-kit-marker.txt").read_text().split()
    assert (guard, skill) == (GUARD, "handling-review-findings")
    assert ts.isdigit()


# --- the skill's smoke check rejects broad raw grants ------------------------------------------

SMOKE = ROOT / "plugins/git-kit/skills/handling-review-findings/scripts/smoke_test.py"
WRAPPER_GRANT = "Bash(python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py:*)"
MARKER_GRANT = "Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh gh-pr-review-wrapper:*)"
KEPT_GRANTS = (
    "Bash(gh pr checks:*), Bash(gh pr view:*), Bash(gh repo view:*), Bash(gh issue list:*)"
)


def _smoke_module():
    spec = importlib.util.spec_from_file_location("handling_review_findings_smoke", SMOKE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _skill_md(tmp_path, grants):
    path = tmp_path / "SKILL.md"
    path.write_text(f"---\nname: x\nallowed-tools: {grants}\n---\nbody\n")
    return path


def test_smoke_check_accepts_the_intended_grants(tmp_path):
    grants = f"{KEPT_GRANTS}, {WRAPPER_GRANT}, {MARKER_GRANT}, Read, Write, Skill(commit)"
    ok, message = _smoke_module().check_no_raw_github_grants(_skill_md(tmp_path, grants))
    assert ok, message


@pytest.mark.parametrize(
    "extra",
    [
        "Bash(gh:*)",
        "Bash(gh api:*)",
        "Bash(gh " + "api graphql:*)",
        "Bash(gh " + "api user:*)",
        "Bash(gh " + "pr comment:*)",
        "Bash(gh " + "issue create:*)",
        "Bash(sed -E:*)",
        "Bash(sed:*)",
        "Bash(git remote get-url:*)",
    ],
)
def test_smoke_check_rejects_any_broad_or_replaced_grant(tmp_path, extra):
    grants = f"{KEPT_GRANTS}, {WRAPPER_GRANT}, {MARKER_GRANT}, {extra}"
    ok, message = _smoke_module().check_no_raw_github_grants(_skill_md(tmp_path, grants))
    assert not ok and "replaced" in message


@pytest.mark.parametrize(
    ("grants", "expected"),
    [
        # the wrapper named only in a non-Bash grant, or in an unrelated Bash grant
        (f"{KEPT_GRANTS}, Read(/x/git-review-api.py), {MARKER_GRANT}", "pinned"),
        (f"{KEPT_GRANTS}, Bash(cat /x/git-review-api.py:*), {MARKER_GRANT}", "pinned"),
        # the wrapper grant without the isolated-interpreter flag
        (
            f"{KEPT_GRANTS}, Bash(python3 ${{CLAUDE_PLUGIN_ROOT}}/scripts/git-review-api.py:*), "
            f"{MARKER_GRANT}",
            "pinned",
        ),
        # the marker writer named only in a non-Bash grant
        (
            f"{KEPT_GRANTS}, {WRAPPER_GRANT}, Read(git-write-marker.sh gh-pr-review-wrapper)",
            "pinned",
        ),
    ],
)
def test_smoke_check_requires_both_pinned_commands_as_bash_grants(tmp_path, grants, expected):
    ok, message = _smoke_module().check_no_raw_github_grants(_skill_md(tmp_path, grants))
    assert not ok and expected in message


def test_smoke_check_rejects_an_unpinned_marker_writer(tmp_path):
    unpinned = "Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh:*)"
    grants = f"{KEPT_GRANTS}, {WRAPPER_GRANT}, {unpinned}"
    ok, message = _smoke_module().check_no_raw_github_grants(_skill_md(tmp_path, grants))
    assert not ok and "pinned" in message
