"""git-kit's git-review-ledger.py records one disposition per review finding (#578).

A local, gitignored working ledger holds entries during the fix loop; `promote` moves a merged PR's
entries into a git-tracked file. Both are JSON. A corrupt file is refused, never overwritten.
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-review-ledger.py"


def _run(tmp_path, *args):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".claude").mkdir(exist_ok=True)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--local",
            str(tmp_path / ".claude" / "local.json"),
            "--tracked",
            str(tmp_path / ".claude" / "tracked.json"),
            *args,
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )


def _record(tmp_path, finding="c1", disposition="fixed", pr="7", **extra):
    args = ["record", "--pr", pr, "--finding", finding, "--disposition", disposition]
    for key, value in extra.items():
        args += [f"--{key}", value]
    return _run(tmp_path, *args)


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
    assert [e["finding"] for e in _entries(tmp_path / ".claude" / "tracked.json")] == ["a"]
    assert [e["finding"] for e in _entries(tmp_path / ".claude" / "local.json")] == ["b"]


def test_promote_twice_does_not_duplicate(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    _run(tmp_path, "promote", "--pr", "7")
    _record(tmp_path, finding="a", pr="7", disposition="declined")
    _run(tmp_path, "promote", "--pr", "7")
    (entry,) = _entries(tmp_path / ".claude" / "tracked.json")
    assert entry["disposition"] == "declined"


def test_promote_with_nothing_to_move_succeeds(tmp_path):
    result = _run(tmp_path, "promote", "--pr", "7")
    assert result.returncode == 0
    assert not (tmp_path / ".claude" / "tracked.json").exists()


def test_promote_refuses_a_corrupt_tracked_file_and_keeps_local_entries(tmp_path):
    _record(tmp_path, finding="a", pr="7")
    (tmp_path / ".claude" / "tracked.json").write_text("[", encoding="utf-8")
    result = _run(tmp_path, "promote", "--pr", "7")
    assert result.returncode == 2
    assert [e["finding"] for e in _entries(tmp_path / ".claude" / "local.json")] == ["a"]


# --- security review (#578): confinement and a tracked local ledger ----------------------------


def test_ledger_path_outside_dot_claude_is_refused(tmp_path):
    result = _run(tmp_path, "--local", str(tmp_path / "outside.json"), "refuted", "--pr", "7")
    assert result.returncode == 2
    assert not (tmp_path / "outside.json").exists()


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


def test_ledger_files_must_be_json(tmp_path):
    result = _run(
        tmp_path, "--tracked", str(tmp_path / ".claude" / "rules.md"), "promote", "--pr", "7"
    )
    assert result.returncode == 2


def test_refuted_also_reads_the_promoted_entries(tmp_path):
    _record(tmp_path, finding="a", pr="7", disposition="false_positive")
    _run(tmp_path, "promote", "--pr", "7")
    result = _run(tmp_path, "refuted", "--pr", "7")
    assert {e["finding"] for e in json.loads(result.stdout)["refuted"]} == {"a"}
