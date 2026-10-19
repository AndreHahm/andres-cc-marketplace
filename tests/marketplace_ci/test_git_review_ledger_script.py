"""git-kit's git-review-ledger.py records one disposition per review finding (#578).

A local, gitignored working ledger holds entries during the fix loop; `promote` moves a merged PR's
entries into a git-tracked directory, one pr-<N>.json per PR (#610), so concurrent PRs never edit
the same file. All are JSON. A corrupt file is refused, never overwritten.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

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


def test_promote_refuses_a_pr_number_below_one(tmp_path):
    _record(tmp_path, finding="a", pr="0")
    assert _run(tmp_path, "promote", "--pr", "0").returncode == 2


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
