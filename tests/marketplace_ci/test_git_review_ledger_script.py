"""git-kit's git-review-ledger.py records one disposition per review finding (#578).

A local, gitignored working ledger holds entries during the fix loop; `promote` moves a merged PR's
entries into a git-tracked directory, one pr-<N>.json per PR (#610), so concurrent PRs never edit
the same file. All are JSON. A corrupt file is refused, never overwritten.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-review-ledger.py"


def _run(tmp_path, *args, extra_env=None):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".claude").mkdir(exist_ok=True)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--local",
            str(tmp_path / ".claude" / "local.json"),
            "--tracked",
            str(tmp_path / ".claude" / "tracked"),
            *args,
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin", **(extra_env or {})},
    )


def _record(tmp_path, finding="c1", disposition="fixed", pr="7", **extra):
    args = ["record", "--pr", pr, "--finding", finding, "--disposition", disposition]
    for key, value in extra.items():
        args += [f"--{key}", value]
    return _run(tmp_path, *args)


def _tracked(tmp_path, pr):
    return tmp_path / ".claude" / "tracked" / f"pr-{pr}.json"


def _entries(path):
    return json.loads(path.read_text(encoding="utf-8"))["entries"]


def test_record_creates_the_local_ledger(tmp_path):
    result = _record(tmp_path, path="a.md", line="3", rule="R13", note="split it")
    assert result.returncode == 0, result.stderr
    (entry,) = _entries(tmp_path / ".claude" / "local.json")
    assert entry["pr"] == 7
    assert entry["finding"] == "c1"
    assert entry["disposition"] == "fixed"
    assert (entry["path"], entry["line"], entry["rule"]) == ("a.md", 3, "R13")
    assert entry["recorded_at"]


def test_recording_again_replaces_the_same_finding(tmp_path):
    _record(tmp_path, disposition="declined")
    _record(tmp_path, disposition="false_positive")
    (entry,) = _entries(tmp_path / ".claude" / "local.json")
    assert entry["disposition"] == "false_positive"


def test_same_finding_id_on_another_pr_is_a_separate_entry(tmp_path):
    _record(tmp_path, pr="7")
    _record(tmp_path, pr="8")
    assert len(_entries(tmp_path / ".claude" / "local.json")) == 2


def test_unknown_disposition_is_refused(tmp_path):
    result = _record(tmp_path, disposition="wontfix")
    assert result.returncode == 2
    assert not (tmp_path / ".claude" / "local.json").exists()


def test_corrupt_ledger_is_refused_and_left_alone(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "local.json").write_text("{not json", encoding="utf-8")
    result = _record(tmp_path)
    assert result.returncode == 2
    assert (tmp_path / ".claude" / "local.json").read_text(encoding="utf-8") == "{not json"


def test_wrong_shape_is_refused(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "local.json").write_text('{"entries": "no"}', encoding="utf-8")
    assert _record(tmp_path).returncode == 2


def test_refuted_lists_only_false_positive_for_that_pr_not_a_decline(tmp_path):
    _record(tmp_path, finding="a", disposition="fixed")
    _record(tmp_path, finding="b", disposition="false_positive", note="gate test passes")
    _record(tmp_path, finding="c", disposition="declined")
    _record(tmp_path, finding="d", disposition="false_positive", pr="9")
    result = _run(tmp_path, "refuted", "--pr", "7")
    assert result.returncode == 0, result.stderr
    assert {e["finding"] for e in json.loads(result.stdout)["refuted"]} == {"b"}


def test_refuted_with_no_ledger_is_empty_not_an_error(tmp_path):
    result = _run(tmp_path, "refuted", "--pr", "7")
    assert result.returncode == 0
    assert json.loads(result.stdout)["refuted"] == []


def test_promote_moves_one_prs_entries_to_the_tracked_file(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _record(tmp_path, finding="b", pr="8")
    result = _run(tmp_path, "promote", "--pr", "7")
    assert result.returncode == 0, result.stderr
    assert [e["finding"] for e in _entries(_tracked(tmp_path, 7))] == ["a"]
    assert [e["finding"] for e in _entries(tmp_path / ".claude" / "local.json")] == ["b"]
    assert not _tracked(tmp_path, 8).exists()


def test_promote_twice_does_not_duplicate(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _run(tmp_path, "promote", "--pr", "7")
    _record(tmp_path, finding="a", pr="7", disposition="declined")
    _run(tmp_path, "promote", "--pr", "7")
    (entry,) = _entries(_tracked(tmp_path, 7))
    assert entry["disposition"] == "declined"


def test_promote_with_nothing_to_move_succeeds(tmp_path):
    result = _run(tmp_path, "promote", "--pr", "7")
    assert result.returncode == 0
    assert not (tmp_path / ".claude" / "tracked").exists()


def test_promote_refuses_a_corrupt_tracked_file_and_keeps_local_entries(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _tracked(tmp_path, 7).parent.mkdir()
    _tracked(tmp_path, 7).write_text("[", encoding="utf-8")
    result = _run(tmp_path, "promote", "--pr", "7")
    assert result.returncode == 2
    assert [e["finding"] for e in _entries(tmp_path / ".claude" / "local.json")] == ["a"]


# --- security review (#578): confinement and a tracked local ledger ----------------------------


def test_ledger_path_outside_dot_claude_is_refused(tmp_path):
    result = _run(tmp_path, "--local", str(tmp_path / "outside.json"), "refuted", "--pr", "7")
    assert result.returncode == 2
    assert not (tmp_path / "outside.json").exists()


def test_stale_git_location_variables_in_the_environment_are_ignored(tmp_path):
    env = {
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "no-such-objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "no-such-alternates"),
        "GIT_NAMESPACE": "stale-namespace",
    }
    args = ["record", "--pr", "7", "--finding", "c1", "--disposition", "fixed"]
    result = _run(tmp_path, *args, extra_env=env)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".claude" / "local.json").exists()


def test_symlinked_dot_claude_root_is_refused_by_every_subcommand(tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (tmp_path / ".claude").symlink_to(outside)
    for args in (
        ["record", "--pr", "7", "--finding", "c1", "--disposition", "fixed"],
        ["refuted", "--pr", "7"],
        ["promote", "--pr", "7"],
    ):
        result = _run(tmp_path, *args)
        assert result.returncode == 2, (args, result.stderr)
        assert "symlink" in result.stderr
    assert list(outside.iterdir()) == []


def test_symlink_escape_from_dot_claude_is_refused(tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "link").symlink_to(outside)
    result = _run(
        tmp_path,
        "--local",
        str(tmp_path / ".claude" / "link" / "x.json"),
        "record",
        "--pr",
        "7",
        "--finding",
        "c1",
        "--disposition",
        "fixed",
    )
    assert result.returncode == 2
    assert not (outside / "x.json").exists()


def test_tracked_local_ledger_is_refused(tmp_path):
    _record(tmp_path, finding="a", pr="7", disposition="false_positive")
    subprocess.run(["git", "add", "-f", ".claude/local.json"], cwd=tmp_path, check=True)
    for args in (["refuted", "--pr", "7"], ["promote", "--pr", "7"]):
        assert _run(tmp_path, *args).returncode == 2
    assert _record(tmp_path, finding="b").returncode == 2


def test_local_and_tracked_must_be_different_files(tmp_path):
    same = str(tmp_path / ".claude" / "same.json")
    result = _run(tmp_path, "--local", same, "--tracked", same, "promote", "--pr", "7")
    assert result.returncode == 2


def test_the_local_ledger_must_be_json(tmp_path):
    result = _run(
        tmp_path, "--local", str(tmp_path / ".claude" / "rules.md"), "promote", "--pr", "7"
    )
    assert result.returncode == 2


def test_the_tracked_path_must_be_a_directory_under_claude(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    (tmp_path / ".claude" / "old.json").write_text('{"entries": []}', encoding="utf-8")
    for tracked in (tmp_path / ".claude" / "old.json", tmp_path / "outside"):
        result = _run(tmp_path, "--tracked", str(tracked), "promote", "--pr", "7")
        assert result.returncode == 2


def test_the_local_ledger_may_not_sit_inside_the_tracked_directory(tmp_path):
    inside = str(tmp_path / ".claude" / "tracked" / "pr-7.json")
    result = _run(tmp_path, "--local", inside, "promote", "--pr", "7")
    assert result.returncode == 2


def test_refuted_also_reads_the_promoted_entries(tmp_path):
    _record(tmp_path, finding="a", pr="7", disposition="false_positive")
    _run(tmp_path, "promote", "--pr", "7")
    result = _run(tmp_path, "refuted", "--pr", "7")
    assert {e["finding"] for e in json.loads(result.stdout)["refuted"]} == {"a"}


def test_a_later_local_record_overrides_a_promoted_false_positive(tmp_path):
    _record(tmp_path, finding="a", pr="7", disposition="false_positive")
    _run(tmp_path, "promote", "--pr", "7")
    _record(tmp_path, finding="a", pr="7", disposition="fixed")
    result = _run(tmp_path, "refuted", "--pr", "7")
    assert json.loads(result.stdout)["refuted"] == []


def test_record_keeps_the_local_ledger_out_of_git_status(tmp_path):
    assert _record(tmp_path).returncode == 0
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "local.json" not in status
    exclude = tmp_path / ".git" / "info" / "exclude"
    assert "/.claude/local.json" in exclude.read_text(encoding="utf-8")
    assert _record(tmp_path, finding="c2").returncode == 0
    assert exclude.read_text(encoding="utf-8").count("/.claude/local.json") == 1


def _init_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".claude").mkdir(exist_ok=True)
    return tmp_path


def _exclude_text(tmp_path):
    exclude = tmp_path / ".git" / "info" / "exclude"
    return exclude.read_text(encoding="utf-8") if exclude.exists() else ""


def test_a_newline_in_the_ledger_path_cannot_write_rules_into_info_exclude(tmp_path):
    hostile = str(tmp_path / ".claude" / "x\n!/.env\nq.json")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--local", hostile, "record"]
        + ["--pr", "7", "--finding", "c1", "--disposition", "fixed"],
        capture_output=True,
        text=True,
        cwd=_init_repo(tmp_path),
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "!/.env" not in _exclude_text(tmp_path)


def test_a_symlinked_ledger_path_is_refused(tmp_path):
    root = _init_repo(tmp_path)
    (root / ".claude" / "real.json").write_text('{"entries": []}\n', encoding="utf-8")
    (root / ".claude" / "link.json").symlink_to("real.json")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--local", str(root / ".claude" / "link.json"), "record"]
        + ["--pr", "7", "--finding", "c1", "--disposition", "fixed"],
        capture_output=True,
        text=True,
        cwd=root,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "symlink" in result.stderr
    assert json.loads((root / ".claude" / "real.json").read_text(encoding="utf-8")) == {
        "entries": []
    }


def test_a_path_that_is_not_utf8_is_refused_not_a_traceback(tmp_path):
    root = _init_repo(tmp_path)
    odd = os.fsdecode(bytes(root / ".claude") + b"/bad\xff.json")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--local", odd, "record"]
        + ["--pr", "7", "--finding", "c1", "--disposition", "fixed"],
        capture_output=True,
        text=True,
        cwd=root,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_a_ledger_a_repository_rule_already_ignores_is_not_excluded_again(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("*.local.*\n", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    local = tmp_path / ".claude" / "x.local.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--local", str(local), "record"]
        + ["--pr", "7", "--finding", "c1", "--disposition", "fixed"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    exclude = tmp_path / ".git" / "info" / "exclude"
    assert "x.local.json" not in (exclude.read_text(encoding="utf-8") if exclude.exists() else "")


# --- per-PR files (#610): promotions from different PRs cannot conflict ---------------------------


def _git(tmp_path, *args):
    return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True, check=True)


def test_promote_leaves_other_prs_files_byte_unchanged(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _run(tmp_path, "promote", "--pr", "7")
    before = _tracked(tmp_path, 7).read_bytes()
    _record(tmp_path, finding="b", pr="8")
    _run(tmp_path, "promote", "--pr", "8")
    assert _tracked(tmp_path, 7).read_bytes() == before
    assert [e["finding"] for e in _entries(_tracked(tmp_path, 8))] == ["b"]


def test_promotions_from_two_prs_merge_without_conflict(tmp_path):
    """The #610 case: two branches cut from one base, each promoting a different PR."""
    _init_repo(tmp_path)
    _record(tmp_path, finding="base", pr="6")
    _run(tmp_path, "promote", "--pr", "6")
    _git(tmp_path, "add", "-f", ".claude/tracked")
    git = ["-c", "user.email=t@example.com", "-c", "user.name=t"]
    _git(tmp_path, *git, "commit", "-qm", "base")
    _git(tmp_path, "branch", "pr-a")
    _git(tmp_path, "branch", "pr-b")
    for branch, pr in (("pr-a", "7"), ("pr-b", "8")):
        _git(tmp_path, "checkout", "-q", branch)
        _record(tmp_path, finding="f" + pr, pr=pr)
        _run(tmp_path, "promote", "--pr", pr)
        _git(tmp_path, "add", "-f", ".claude/tracked")
        _git(tmp_path, *git, "commit", "-qm", branch)
    merge = subprocess.run(
        ["git", *git, "merge", "--no-edit", "pr-a"], cwd=tmp_path, capture_output=True, text=True
    )
    assert merge.returncode == 0, merge.stdout + merge.stderr
    for pr in (6, 7, 8):
        assert _tracked(tmp_path, pr).exists()


def test_a_second_promote_for_the_same_pr_stays_in_its_own_file_sorted_by_finding(tmp_path):
    for finding in ("20", "3", "abc"):
        _record(tmp_path, finding=finding, pr="7")
    _run(tmp_path, "promote", "--pr", "7")
    _record(tmp_path, finding="1", pr="7")
    _run(tmp_path, "promote", "--pr", "7")
    assert [e["finding"] for e in _entries(_tracked(tmp_path, 7))] == ["1", "3", "20", "abc"]


def test_a_tracked_file_carrying_another_prs_entry_is_refused(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _tracked(tmp_path, 7).parent.mkdir()
    _tracked(tmp_path, 7).write_text(
        '{"entries": [{"pr": 9, "finding": "x", "disposition": "fixed"}]}', encoding="utf-8"
    )
    assert _run(tmp_path, "promote", "--pr", "7").returncode == 2
    assert _run(tmp_path, "refuted", "--pr", "7").returncode == 2


def test_a_symlinked_pr_file_is_refused(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _tracked(tmp_path, 7).parent.mkdir()
    real = tmp_path / ".claude" / "real.json"
    real.write_text('{"entries": []}', encoding="utf-8")
    _tracked(tmp_path, 7).symlink_to(real)
    assert _run(tmp_path, "promote", "--pr", "7").returncode == 2


def test_every_command_refuses_a_pr_number_below_one_before_touching_a_file(tmp_path):
    for pr in ("0", "-3", "x"):
        for args in (
            ["record", f"--pr={pr}", "--finding", "a", "--disposition", "fixed"],
            ["refuted", f"--pr={pr}"],
            ["promote", f"--pr={pr}"],  # an empty ledger must not turn this into a no-op success
        ):
            assert _run(tmp_path, *args).returncode == 2, args
    assert not (tmp_path / ".claude" / "local.json").exists()
    assert not (tmp_path / ".claude" / "tracked").exists()


def _load_script():
    import importlib.util

    spec = importlib.util.spec_from_file_location("git_review_ledger", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_dir_reads_every_pr_in_pr_number_order(tmp_path):
    for pr in ("10", "7"):
        _record(tmp_path, finding="f" + pr, pr=pr)
        _run(tmp_path, "promote", "--pr", pr)
    ledger = _load_script()
    entries = ledger.load_dir(tmp_path / ".claude" / "tracked")
    assert [e["pr"] for e in entries] == [7, 10]
    assert ledger.load_dir(tmp_path / ".claude" / "absent") == []


def test_load_dir_refuses_a_stray_name_and_a_corrupt_file(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _run(tmp_path, "promote", "--pr", "7")
    ledger = _load_script()
    directory = tmp_path / ".claude" / "tracked"
    (directory / "notes.txt").write_text("x", encoding="utf-8")
    try:
        ledger.load_dir(directory)
    except ledger.LedgerError:
        pass
    else:
        raise AssertionError("a stray file name was accepted")
    (directory / "notes.txt").unlink()
    _tracked(tmp_path, 7).write_text("[", encoding="utf-8")
    try:
        ledger.load_dir(directory)
    except ledger.LedgerError:
        return
    raise AssertionError("a corrupt file was accepted")


def test_load_dir_ignores_an_interrupted_saves_temp_file_but_not_other_strays(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _run(tmp_path, "promote", "--pr", "7")
    ledger = _load_script()
    directory = tmp_path / ".claude" / "tracked"
    (directory / "pr-7.json.k3x_9ab2.tmp").write_text("{", encoding="utf-8")
    assert [e["finding"] for e in ledger.load_dir(directory)] == ["a"]
    for stray in ("pr-7.json.tmp", "pr-x.json.abc.tmp", "other.json.abc.tmp"):
        (directory / stray).write_text("x", encoding="utf-8")
        try:
            ledger.load_dir(directory)
        except ledger.LedgerError:
            (directory / stray).unlink()
        else:
            raise AssertionError(f"{stray} was ignored")


# --- hardened git (PR #610 parity review): the git that runs is not picked by the PATH ---------

ALLOWED_GIT_ENV = {
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TZ",
    "PATH",
    "GIT_CONFIG_NOSYSTEM",
    "GIT_CONFIG_GLOBAL",
    "GIT_NO_LAZY_FETCH",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OPTIONAL_LOCKS",
    "GIT_TERMINAL_PROMPT",
    "PWD",  # added by the /bin/sh wrapper below, not by the script
    "SHLVL",
    "_",
    "OLDPWD",
}


RECORD_ARGS = ("record", "--pr", "7", "--finding", "c1", "--disposition", "fixed")


def _marker_for(tmp_path):
    return tmp_path.parent / f"{tmp_path.name}-ran"


def _plant_git(path, marker):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def test_a_git_planted_in_the_repository_is_never_run(tmp_path):
    for planted in ("git", "bin/git", "sub/deeper/git"):
        marker = _marker_for(tmp_path)
        plant = tmp_path / planted
        _plant_git(plant, marker)
        path = f"{plant.parent}:/usr/bin:/bin"
        result = _run(tmp_path, *RECORD_ARGS, extra_env={"PATH": path})
        assert result.returncode == 2, (planted, result.stderr)
        assert "no usable git" in result.stderr
        assert not marker.exists(), planted
        plant.unlink()


def test_a_symlink_into_the_repository_is_never_run(tmp_path):
    link = tmp_path / "bin" / "git"
    link.parent.mkdir()
    link.symlink_to(shutil.which("git"))
    result = _run(tmp_path, *RECORD_ARGS, extra_env={"PATH": f"{link.parent}:/usr/bin:/bin"})
    assert result.returncode == 2
    assert "no usable git" in result.stderr


def test_a_missing_git_is_a_refusal_not_a_traceback(tmp_path):
    result = _run(tmp_path, *RECORD_ARGS, extra_env={"PATH": str(tmp_path.parent / "no-such-bin")})
    assert result.returncode == 2
    assert result.stderr.startswith("Refused: no usable git")
    assert "Traceback" not in result.stderr


def test_git_gets_only_the_pinned_environment_and_hardening_flags(tmp_path, tmp_path_factory):
    bin_dir = tmp_path_factory.mktemp("fakebin")  # a sibling of the repository, not inside it
    log = bin_dir / "log"
    env_tool, real_git = shutil.which("env"), shutil.which("git")
    (bin_dir / "git").write_text(
        "#!/bin/sh\n"
        f"{env_tool} >> {log}\n"
        f'printf "ARGS:%s\\n" "$*" >> {log}\n'
        f'exec {real_git} "$@"\n',
        encoding="utf-8",
    )
    (bin_dir / "git").chmod(0o755)
    home = tmp_path_factory.mktemp("home")
    trusted = str(tmp_path.resolve())
    (home / ".gitconfig").write_text(
        f"[safe]\n\tdirectory = {trusted}\n[core]\n\tsshCommand = false\n", encoding="utf-8"
    )
    hostile = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(tmp_path_factory.mktemp("xdg")),
        "GIT_TRACE": "1",
        "GIT_EXEC_PATH": str(tmp_path / "no-such-exec-path"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "touch /tmp/never",
        "GIT_SSH_COMMAND": "false",
        "PAGER": "false",
    }
    result = _run(tmp_path, *RECORD_ARGS, extra_env=hostile)
    assert result.returncode == 0, result.stderr
    calls, keys = [], {}
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.startswith("ARGS:"):
            calls.append((line, keys))
            keys = {}
        elif "=" in line:
            name, value = line.split("=", 1)
            keys[name] = value
    assert calls, "the wrapper recorded no call"
    reads = [c for c in calls if "config --global -z --get-all safe.directory" in c[0]]
    others = [c for c in calls if c not in reads]
    assert len(reads) == 1 and others
    # the one call that reads the user's global config sees HOME, and nothing else extra
    assert set(reads[0][1]) <= ALLOWED_GIT_ENV | {"HOME", "XDG_CONFIG_HOME"}
    assert reads[0][1]["HOME"] == str(home)
    for args, env in others:
        assert set(env) <= ALLOWED_GIT_ENV, sorted(set(env) - ALLOWED_GIT_ENV)
        assert env["GIT_CONFIG_GLOBAL"] == os.devnull
        assert env["GIT_CONFIG_NOSYSTEM"] == "1"
        assert env["PATH"] == str(bin_dir)  # git's own directory and nothing else
        assert "-c core.fsmonitor=false -c core.hooksPath=" in args, args
        assert f"-c safe.directory={trusted}" in args  # the user's entry, passed as data
        assert "sshcommand" not in args.lower()  # no other global setting is carried over


# --- the "git is not inside the repository" guard (security review of PR #610) ---------------


def _make_repo(path):
    path.mkdir(parents=True)
    commit = ["-c", "user.email=t@example.com", "-c", "user.name=t"]
    for args in (
        ["init", "-q", "-b", "main"],
        [*commit, "commit", "-q", "--allow-empty", "-m", "x"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    return path


def _stub_git(directory):
    directory.mkdir(parents=True, exist_ok=True)
    stub = directory / "git"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _find_git_from(monkeypatch, cwd, *path_dirs):
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("PATH", os.pathsep.join([*map(str, path_dirs), "/usr/bin", "/bin"]))
    return _load_script()._find_git()


def test_the_guard_still_accepts_a_git_outside_the_repository(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo")
    tools = _stub_git(tmp_path / "tools").parent
    assert _find_git_from(monkeypatch, repo, tools) == str(tools / "git")
    assert _find_git_from(monkeypatch, repo) is not None  # the system git


def test_a_git_planted_in_the_repository_is_refused_from_any_subdirectory(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo")
    plant = _stub_git(repo / "bin").parent
    deeper = repo / "sub" / "deeper"
    deeper.mkdir(parents=True)
    for start in (repo, repo / "sub", deeper):
        assert _find_git_from(monkeypatch, start, plant) is None, start


def test_a_link_outside_the_repository_that_points_into_it_is_refused(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo")
    target = _stub_git(repo / "bin")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "git").symlink_to(target)
    assert _find_git_from(monkeypatch, repo, outside) is None


def test_a_git_in_the_main_checkout_is_refused_from_a_linked_worktree(tmp_path, monkeypatch):
    main = _make_repo(tmp_path / "main")
    linked = tmp_path / "linked"
    subprocess.run(
        ["git", "worktree", "add", "-q", "--detach", str(linked)],
        cwd=main,
        check=True,
        capture_output=True,
    )
    plant = _stub_git(main / "bin").parent
    assert _find_git_from(monkeypatch, linked, plant) is None
    assert _find_git_from(monkeypatch, linked / ".." / "linked", plant) is None


def test_a_git_in_an_outer_repository_is_refused_from_a_nested_one(tmp_path, monkeypatch):
    outer = _make_repo(tmp_path / "outer")
    inner = _make_repo(outer / "vendor" / "inner")
    plant = _stub_git(outer / "bin").parent
    assert _find_git_from(monkeypatch, inner, plant) is None


def test_a_git_entry_that_cannot_be_read_is_not_trusted(tmp_path, monkeypatch):
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / ".git").write_text("not a pointer\n", encoding="utf-8")
    tools = _stub_git(tmp_path / "tools").parent
    assert _find_git_from(monkeypatch, broken, tools) is None


def _file_system_ignores_case(directory):
    probe = directory / "CaseProbe"
    probe.mkdir()
    return (directory / "caseprobe").exists()


def test_a_path_spelled_with_other_letter_case_is_still_inside_the_repository(
    tmp_path, monkeypatch
):
    if not _file_system_ignores_case(tmp_path):
        pytest.skip("needs a case-insensitive file system (the default on macOS)")
    repo = _make_repo(tmp_path / "Repo")
    plant = _stub_git(repo / "bin").parent
    respelled = tmp_path / "repo" / "bin"
    assert _find_git_from(monkeypatch, repo, respelled) is None
    assert plant.exists()


# --- safe.directory (review of PR #610: Codex P1) ------------------------------------------------


def _other_owner_git(directory):
    """A git that behaves as if another user owned every checkout (git's own test switch)."""
    directory.mkdir(parents=True, exist_ok=True)
    stub = directory / "git"
    stub.write_text(
        f'#!/bin/sh\nexport GIT_TEST_ASSUME_DIFFERENT_OWNER=1\nexec {shutil.which("git")} "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return directory


def _home_with_safe_directory(tmp_path_factory, *directories):
    home = tmp_path_factory.mktemp("home")
    entries = "".join(f"\tdirectory = {d}\n" for d in directories)
    (home / ".gitconfig").write_text(f"[safe]\n{entries}", encoding="utf-8")
    return home


def test_a_checkout_owned_by_another_user_works_when_the_users_global_config_trusts_it(
    tmp_path, tmp_path_factory
):
    bin_dir = _other_owner_git(tmp_path_factory.mktemp("ownerbin"))
    home = _home_with_safe_directory(tmp_path_factory, tmp_path.resolve())
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(home)}
    result = _run(tmp_path, *RECORD_ARGS, extra_env=env)
    assert result.returncode == 0, result.stderr


def test_a_checkout_owned_by_another_user_is_still_refused_when_nothing_trusts_it(
    tmp_path, tmp_path_factory
):
    bin_dir = _other_owner_git(tmp_path_factory.mktemp("ownerbin"))
    unrelated = _home_with_safe_directory(tmp_path_factory, tmp_path / "some-other-checkout")
    empty = tmp_path_factory.mktemp("emptyhome")
    for home in (unrelated, empty):
        env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(home)}
        result = _run(tmp_path, *RECORD_ARGS, extra_env=env)
        assert result.returncode == 2, result.stderr
        assert "Traceback" not in result.stderr
    assert not (tmp_path / ".claude" / "local.json").exists()


def test_without_a_usable_home_there_are_no_trusted_directories(monkeypatch, tmp_path):
    ledger = _load_script()
    for home in (None, "relative/path", str(tmp_path / "does-not-exist")):
        ledger._trusted_directories.cache_clear()
        if home is None:
            monkeypatch.delenv("HOME", raising=False)
        else:
            monkeypatch.setenv("HOME", home)
        assert ledger._trusted_directories() == ()


# --- finding ids (review of PR #610: CodeRabbit) -----------------------------------------


def test_promote_never_fails_on_an_odd_finding_id_already_in_a_file():
    ledger = _load_script()
    odd = ["\u00b2", "\u2460", "9" * 5000, "007", "20", "3", "abc", ""]
    keys = [ledger._sort_key({"finding": value}) for value in odd]  # must not raise
    assert len(keys) == len(odd)
    ordered = [e["finding"] for e in sorted(({"finding": v} for v in odd), key=ledger._sort_key)]
    assert ordered[:3] == ["3", "007", "20"]  # ASCII digit ids first, by numeric value
    assert ordered[3] == "9" * 5000


def test_record_accepts_real_finding_ids_and_refuses_anything_else(tmp_path):
    for good in ("4316749516", "c1", "PRRC_kwDOab-1", "a.b:c_d-9", "9" * 64):
        assert _record(tmp_path, finding=good).returncode == 0, good
    for bad in ("\u00b2", "\u2460", "9" * 65, "a b", "-leading", "x/y", "new\nline"):
        result = _record(tmp_path, finding=bad)
        assert result.returncode == 2, repr(bad)
        if not bad.startswith("-"):  # argparse itself intercepts a leading dash as an option
            assert "not a finding id" in result.stderr
    stored = {e["finding"] for e in _entries(tmp_path / ".claude" / "local.json")}
    assert stored == {"4316749516", "c1", "PRRC_kwDOab-1", "a.b:c_d-9", "9" * 64}


def _write_global_config(home, text):
    (home / ".gitconfig").write_text(text, encoding="utf-8")
    return home


def _plain_git_trusts(home, repo):
    """Whether the user's own git, with this global config, accepts the other-owner checkout."""
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}
    done = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=repo, env=env, capture_output=True, text=True
    )
    return done.returncode == 0


def test_a_revoked_safe_directory_stays_revoked(tmp_path, tmp_path_factory):
    """An empty value resets git's list; the script must trust exactly what the user's git does."""
    bin_dir = _other_owner_git(tmp_path_factory.mktemp("ownerbin"))
    repo = tmp_path.resolve()
    home = _write_global_config(
        tmp_path_factory.mktemp("home"), f"[safe]\n\tdirectory = {repo}\n\tdirectory =\n"
    )
    _run(tmp_path, "promote", "--pr", "9")  # make the repository exist
    expected_ok = _plain_git_trusts(home, repo)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(home)}
    result = _run(tmp_path, *RECORD_ARGS, extra_env=env)
    assert (result.returncode == 0) == expected_ok, (expected_ok, result.stderr)


def test_a_value_with_an_escaped_newline_is_not_split_into_a_wildcard(tmp_path, tmp_path_factory):
    bin_dir = _other_owner_git(tmp_path_factory.mktemp("ownerbin"))
    home = _write_global_config(
        tmp_path_factory.mktemp("home"), "[safe]\n\tdirectory = /nowhere\\n*\n"
    )
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(home)}
    result = _run(tmp_path, *RECORD_ARGS, extra_env=env)
    assert result.returncode == 2, result.stderr


def test_a_global_config_inside_the_checkout_is_not_the_users_own(tmp_path, tmp_path_factory):
    """If HOME is the checkout (some containers), the branch decides what the file says."""
    bin_dir = _other_owner_git(tmp_path_factory.mktemp("ownerbin"))
    _write_global_config(tmp_path, f"[safe]\n\tdirectory = {tmp_path.resolve()}\n")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path)}
    result = _run(tmp_path, *RECORD_ARGS, extra_env=env)
    assert result.returncode == 2, result.stderr


@pytest.mark.skipif(os.geteuid() == 0, reason="root can enter a directory with no permissions")
def test_a_home_directory_that_cannot_be_entered_does_not_stop_the_script(
    tmp_path, tmp_path_factory
):
    home = tmp_path_factory.mktemp("lockedhome")
    home.chmod(0o000)
    try:
        result = _run(tmp_path, *RECORD_ARGS, extra_env={"HOME": str(home)})
    finally:
        home.chmod(0o700)
    assert result.returncode == 0, result.stderr


def test_a_global_config_that_is_a_link_into_the_checkout_is_not_the_users_own(
    tmp_path, tmp_path_factory
):
    """HOME is outside the checkout, but ~/.gitconfig points at a file the branch controls."""
    bin_dir = _other_owner_git(tmp_path_factory.mktemp("ownerbin"))
    planted = tmp_path / "planted-gitconfig"
    planted.write_text(f"[safe]\n\tdirectory = {tmp_path.resolve()}\n", encoding="utf-8")
    home = tmp_path_factory.mktemp("home")
    (home / ".gitconfig").symlink_to(planted)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(home)}
    result = _run(tmp_path, *RECORD_ARGS, extra_env=env)
    assert result.returncode == 2, result.stderr


def test_a_global_config_that_is_a_link_to_a_file_elsewhere_still_counts(
    tmp_path, tmp_path_factory
):
    """A dotfiles directory outside the checkout is the user's own, so a link to it is honoured."""
    bin_dir = _other_owner_git(tmp_path_factory.mktemp("ownerbin"))
    dotfiles = tmp_path_factory.mktemp("dotfiles")
    (dotfiles / "gitconfig").write_text(
        f"[safe]\n\tdirectory = {tmp_path.resolve()}\n", encoding="utf-8"
    )
    home = tmp_path_factory.mktemp("home")
    (home / ".gitconfig").symlink_to(dotfiles / "gitconfig")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(home)}
    result = _run(tmp_path, *RECORD_ARGS, extra_env=env)
    assert result.returncode == 0, result.stderr
