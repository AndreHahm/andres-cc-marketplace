"""git-kit's git-review-fix-diff.py shows a committed fix's diff, with no raw git diff grant (#582).

The old `Bash(git diff:*)` grant also allowed `git diff --output=<path>`, a write to any path, and
`git diff` itself reads the index and the working tree, where repository configuration or an
inherited environment can run commands. The script runs `git diff-tree` (commit objects only),
takes one validated argument and exits 2, never 0, when it cannot show the diff. Each
execution-route test plants a marker-writing command and asserts the marker never appears while the
diff is still correct. The controls at the end show the same setups do fire under plain `git diff`.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-review-fix-diff.py"
SYSTEM_PATH = os.environ.get("PATH", "/usr/bin:/bin")


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _run(cwd, *args, env=None):
    base = {"PATH": SYSTEM_PATH, "HOME": str(cwd)}
    base.update(env or {})
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=base,
    )


def _commit(repo, rel, text, message):
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text, encoding="utf-8")
    _git(repo, "add", "--", rel)
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _hook(path, marker, body=""):
    path.write_text(f"#!/bin/sh\ntouch {marker}\n{body}", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _commit(root, "a.txt", "one\n", "base")
    return root


@pytest.fixture
def fixed(repo):
    """(repo, base id): HEAD is a fix commit that adds a line on top of the base.

    The working tree is left with an uncommitted edit, the state in which a plain `git diff` reads
    the index and the file and so runs a configured fsmonitor, filter or hook.
    """
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "a.txt", "one\ntwo\n", "fix")
    (repo / "a.txt").write_text("one\ntwo\nlocal edit\n", encoding="utf-8")
    return repo, base


def test_prints_the_committed_fix(fixed):
    repo, base = fixed
    result = _run(repo, "--base", base)
    assert result.returncode == 0
    assert "+two" in result.stdout
    assert "diff --git a/a.txt b/a.txt" in result.stdout


def test_paths_are_repository_relative_from_a_subdirectory(fixed):
    repo, base = fixed
    sub = repo / "sub"
    sub.mkdir()
    _git(repo, "config", "diff.relative", "true")
    result = _run(sub, "--base", base)
    assert result.returncode == 0
    assert "diff --git a/a.txt b/a.txt" in result.stdout


def test_an_empty_diff_exits_2_not_as_no_change(repo):
    base = _git(repo, "rev-parse", "HEAD")  # HEAD against itself: the base is wrong
    result = _run(repo, "--base", base)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "empty" in result.stderr


def test_a_tree_or_blob_id_is_not_accepted_as_the_base(fixed):
    repo, _base = fixed
    for spec in ("HEAD^{tree}", "HEAD:a.txt"):
        result = _run(repo, "--base", _git(repo, "rev-parse", spec))
        assert result.returncode == 2, spec
        assert result.stdout == ""


def test_a_gitmodules_ignore_setting_cannot_hide_a_submodule_pointer_change(repo):
    base = _git(repo, "rev-parse", "HEAD")
    gitlink = "1" * 40
    _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{gitlink},vendor")
    _git(repo, "commit", "-q", "-m", "add a submodule pointer")
    (repo / ".gitmodules").write_text(
        '[submodule "vendor"]\n\tpath = vendor\n\turl = https://example.com/x\n\tignore = all\n',
        encoding="utf-8",
    )
    _git(repo, "config", "submodule.vendor.ignore", "all")
    result = _run(repo, "--base", base)
    assert result.returncode == 0
    assert f"Subproject commit {gitlink}" in result.stdout


def test_a_sha256_object_id_is_accepted_by_the_pattern(tmp_path):
    root = tmp_path / "sha256"
    root.mkdir()
    try:
        _git(root, "init", "-q", "-b", "main", "--object-format=sha256")
    except subprocess.CalledProcessError:
        pytest.skip("this git cannot create a sha256 repository")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    base = _commit(root, "a.txt", "one\n", "base")
    _commit(root, "a.txt", "one\ntwo\n", "fix")
    assert len(base) == 64
    result = _run(root, "--base", base)
    assert result.returncode == 0
    assert "+two" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--base", "HEAD"],
        ["--base", "abc1234"],
        ["--base", "A" * 40],
        ["--base", "g" * 40],
        ["--base", "a" * 40 + "\n"],
        ["--base", "--output=/tmp/x"],
        ["--base", "a" * 40, "extra"],
        ["--base", "a" * 40, "--output=/tmp/x"],
        ["--base", "a" * 40, "--worktree"],
        ["--worktree"],
        ["--b", "a" * 40],
        ["--ba", "a" * 40],
        ["-h"],
        ["--help"],
        ["--unknown"],
        ["@/etc/hostname"],
    ],
)
def test_every_other_argument_is_refused(repo, args):
    result = _run(repo, *args)
    assert result.returncode == 2
    assert result.stdout == ""


def test_an_output_option_cannot_write_a_file(fixed, tmp_path):
    repo, base = fixed
    target = tmp_path / "overwritten.txt"
    target.write_text("original\n", encoding="utf-8")
    for args in (
        ["--base", base, f"--output={target}"],
        ["--base", f"--output={target}"],
        ["--output", str(target), "--base", base],
    ):
        assert _run(repo, *args).returncode == 2
    assert target.read_text(encoding="utf-8") == "original\n"


def test_an_unknown_commit_exits_2_without_echoing_git_errors(repo):
    result = _run(repo, "--base", "0" * 40)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "fatal" not in result.stderr


def test_outside_a_repository_exits_2(tmp_path):
    outside = tmp_path / "plain"
    outside.mkdir()
    result = _run(outside, "--base", "a" * 40)
    assert result.returncode == 2
    assert result.stdout == ""


def test_the_diff_is_cut_off_at_the_size_limit_with_exit_2(fixed):
    repo, base = fixed
    _commit(repo, "big.txt", "x" * 1_100_000 + "\n", "big")
    result = _run(repo, "--base", base)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "over" in result.stderr


# Each case below plants a command that git would run if it consulted the index, the working tree,
# a hook, a filter or an injected setting. The diff must still be correct and the marker absent.


def _assert_correct_and_not_run(result, marker):
    assert result.returncode == 0, result.stderr
    assert "+two" in result.stdout
    assert not marker.exists()


def test_core_fsmonitor_never_runs(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    fsmonitor = tmp_path / "fsmonitor.sh"
    _hook(fsmonitor, marker, "printf '\\0'\n")
    _git(repo, "config", "core.fsmonitor", str(fsmonitor))
    _assert_correct_and_not_run(_run(repo, "--base", base), marker)


def test_a_clean_filter_never_runs(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    clean = tmp_path / "clean.sh"
    _hook(clean, marker, "cat\n")
    _git(repo, "config", "filter.x.clean", str(clean))
    _git(repo, "config", "filter.x.process", str(clean))
    (repo / ".gitattributes").write_text("*.txt filter=x\n", encoding="utf-8")
    (repo / "a.txt").write_text("one\ntwo\ndirty\n", encoding="utf-8")
    _assert_correct_and_not_run(_run(repo, "--base", base), marker)


def test_a_post_index_change_hook_never_runs(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    _hook(repo / ".git/hooks/post-index-change", marker)
    os.utime(repo / "a.txt", None)
    _assert_correct_and_not_run(_run(repo, "--base", base), marker)


def test_a_configured_external_diff_and_textconv_never_run(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    hook = tmp_path / "hook.sh"
    _hook(hook, marker, 'cat "$1"\n')
    _git(repo, "config", "diff.external", str(hook))
    _git(repo, "config", "diff.tc.textconv", str(hook))
    (repo / ".gitattributes").write_text("*.txt diff=tc\n", encoding="utf-8")
    _assert_correct_and_not_run(_run(repo, "--base", base), marker)


def test_hooks_path_pointing_at_a_planted_directory_never_runs(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    for name in ("post-index-change", "post-checkout", "reference-transaction"):
        _hook(hooks / name, marker)
    _git(repo, "config", "core.hooksPath", str(hooks))
    _assert_correct_and_not_run(_run(repo, "--base", base), marker)


@pytest.mark.parametrize("variable", ["GIT_EXTERNAL_DIFF", "GIT_PAGER", "GIT_SSH_COMMAND"])
def test_an_inherited_command_variable_is_ignored(fixed, tmp_path, variable):
    repo, base = fixed
    marker = tmp_path / "ran"
    hook = tmp_path / "hook.sh"
    _hook(hook, marker, "cat\n")
    _assert_correct_and_not_run(_run(repo, "--base", base, env={variable: str(hook)}), marker)


def test_injected_config_variables_are_ignored(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    fsmonitor = tmp_path / "fsmonitor.sh"
    _hook(fsmonitor, marker, "printf '\\0'\n")
    env = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": str(fsmonitor),
        "GIT_CONFIG_PARAMETERS": f"'core.fsmonitor={fsmonitor}'",
    }
    _assert_correct_and_not_run(_run(repo, "--base", base, env=env), marker)


@pytest.mark.parametrize(
    "variable", ["GIT_TRACE", "GIT_TRACE2", "GIT_TRACE2_EVENT", "GIT_TRACE_SETUP"]
)
def test_a_trace_variable_cannot_write_a_file(fixed, tmp_path, variable):
    repo, base = fixed
    trace = tmp_path / "trace.txt"
    result = _run(repo, "--base", base, env={variable: str(trace)})
    assert result.returncode == 0
    assert not trace.exists()


def test_a_global_config_named_by_the_environment_is_ignored(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    fsmonitor = tmp_path / "fsmonitor.sh"
    _hook(fsmonitor, marker, "printf '\\0'\n")
    global_config = tmp_path / "gitconfig"
    global_config.write_text(f"[core]\n\tfsmonitor = {fsmonitor}\n", encoding="utf-8")
    env = {"GIT_CONFIG_GLOBAL": str(global_config), "XDG_CONFIG_HOME": str(tmp_path)}
    _assert_correct_and_not_run(_run(repo, "--base", base, env=env), marker)


def test_a_git_planted_in_the_repository_is_never_used(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    _hook(repo / "git", marker)
    for path in (":" + SYSTEM_PATH, SYSTEM_PATH + ":", "." + ":" + SYSTEM_PATH, str(repo)):
        result = _run(repo, "--base", base, env={"PATH": path})
        assert not marker.exists(), path
        if path in (str(repo),):
            assert result.returncode == 2


def test_a_binary_attribute_does_not_hide_a_change(fixed):
    repo, base = fixed
    (repo / ".gitattributes").write_text("*.txt -diff\n", encoding="utf-8")
    _git(repo, "add", ".gitattributes")
    _git(repo, "commit", "-q", "-m", "attrs")
    result = _run(repo, "--base", base)
    assert result.returncode == 0
    assert "+two" in result.stdout


def test_a_replace_ref_does_not_hide_a_change(fixed):
    repo, base = fixed
    fixed_blob = _git(repo, "rev-parse", "HEAD:a.txt")
    innocent = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo,
        input="one\ninnocent\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git(repo, "replace", fixed_blob, innocent)
    result = _run(repo, "--base", base)
    assert result.returncode == 0
    assert "+two" in result.stdout
    assert "innocent" not in result.stdout


# Controls: the same setups do run a command under a plain `git diff`, so the marker tests above
# are not passing vacuously. A git that does not consult the setting skips, visibly.


def _plain_git_diff(repo, base, env=None):
    return subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=repo,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
    )


def _control_fired_or_skip(marker):
    if not marker.exists():
        pytest.skip("this git does not run the planted command under a plain git diff")


def test_control_plain_git_diff_runs_fsmonitor(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    fsmonitor = tmp_path / "fsmonitor.sh"
    _hook(fsmonitor, marker, "printf '\\0'\n")
    _git(repo, "config", "core.fsmonitor", str(fsmonitor))
    _plain_git_diff(repo, base)
    _control_fired_or_skip(marker)


def test_control_plain_git_diff_runs_injected_config(fixed, tmp_path):
    repo, base = fixed
    marker = tmp_path / "ran"
    fsmonitor = tmp_path / "fsmonitor.sh"
    _hook(fsmonitor, marker, "printf '\\0'\n")
    env = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": str(fsmonitor),
    }
    _plain_git_diff(repo, base, env)
    _control_fired_or_skip(marker)


def test_control_plain_git_diff_writes_a_trace_file(fixed, tmp_path):
    repo, base = fixed
    trace = tmp_path / "trace.txt"
    _plain_git_diff(repo, base, {"GIT_TRACE": str(trace)})
    _control_fired_or_skip(trace)
