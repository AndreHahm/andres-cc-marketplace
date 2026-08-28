"""Tests for scripts/pr_review_fetcher.py -- normalize/load_fixture behavior,
the CLI's fixture and live-argument-validation paths, and _run_gh_api's
--paginate/--slurp flattening."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import pr_review_fetcher  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "pr_reviews"


def _load(name: str) -> dict:
    data = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    return data


def test_normalize_review_level_record():
    data = _load("pr47.json")
    records = pr_review_fetcher.normalize(data["reviews"], data["comments"])

    reviews = [r for r in records if r["kind"] == "review"]
    assert len(reviews) == 1
    review = reviews[0]
    assert review["reviewer"] == "chatgpt-codex-connector[bot]"
    assert review["file"] is None
    assert review["line"] is None
    assert review["submitted_at"] == "2026-08-17T11:44:17Z"
    assert review["review_id"] == 4951194864
    assert review["comment_id"] is None
    assert review["in_reply_to_id"] is None


def test_normalize_standalone_inline_comment():
    data = _load("pr47.json")
    records = pr_review_fetcher.normalize(data["reviews"], data["comments"])

    standalone = next(r for r in records if r.get("comment_id") == 3796051996)
    assert standalone["kind"] == "inline_comment"
    assert standalone["reviewer"] == "coderabbitai[bot]"
    assert standalone["file"] == ".claude/scripts/cleanup-scratchpad.ps1"
    # line was null in the raw payload; original_line is the fallback.
    assert standalone["line"] == 51
    assert standalone["in_reply_to_id"] is None


def test_normalize_reply_to_reply_thread():
    data = _load("pr47.json")
    records = pr_review_fetcher.normalize(data["reviews"], data["comments"])

    parent = next(r for r in records if r.get("comment_id") == 3796032432)
    reply = next(r for r in records if r.get("comment_id") == 3796124001)

    assert parent["in_reply_to_id"] is None
    assert reply["in_reply_to_id"] == parent["comment_id"]
    assert reply["reviewer"] == "AndreHahm"
    assert parent["file"] == reply["file"] == ".claude/scripts/cleanup-scratchpad.sh"


def test_normalize_pr_with_zero_review_comments():
    data = _load("empty.json")
    records = pr_review_fetcher.normalize(data["reviews"], data["comments"])
    assert records == []


def test_normalize_null_user_does_not_crash():
    # GitHub returns "user": null for a review/comment whose author's account
    # has since been deleted -- dict.get("user", {}) does NOT catch this,
    # since the key is present with value None, not absent.
    reviews = [{"id": 1, "user": None, "body": "", "submitted_at": "2026-01-01T00:00:00Z"}]
    comments = [
        {
            "id": 2,
            "user": None,
            "path": "f.py",
            "line": 1,
            "body": "",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    records = pr_review_fetcher.normalize(reviews, comments)
    assert records[0]["reviewer"] is None
    assert records[1]["reviewer"] is None


def test_run_gh_api_flattens_multi_page_slurp_output():
    # gh api --paginate --slurp wraps each page's own JSON array into one
    # outer array of pages -- a multi-page result must be flattened, not
    # passed through as a list of lists.
    page_1 = [{"id": 1}, {"id": 2}]
    page_2 = [{"id": 3}]
    mock_result = subprocess.CompletedProcess(
        args=["gh", "api", "some/path", "--paginate", "--slurp"],
        returncode=0,
        stdout=json.dumps([page_1, page_2]),
        stderr="",
    )
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = pr_review_fetcher._run_gh_api("some/path")
    assert result == [{"id": 1}, {"id": 2}, {"id": 3}]
    called_args = mock_run.call_args.args[0]
    assert "--paginate" in called_args
    assert "--slurp" in called_args


def test_run_gh_api_handles_single_page_slurp_output():
    mock_result = subprocess.CompletedProcess(
        args=["gh", "api", "some/path", "--paginate", "--slurp"],
        returncode=0,
        stdout=json.dumps([[{"id": 1}]]),
        stderr="",
    )
    with patch("subprocess.run", return_value=mock_result):
        result = pr_review_fetcher._run_gh_api("some/path")
    assert result == [{"id": 1}]


def test_load_fixture_missing_keys_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"reviews": []}), encoding="utf-8")
    with pytest.raises(pr_review_fetcher.FetchError):
        pr_review_fetcher.load_fixture(bad)


def test_load_fixture_non_list_reviews_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"reviews": "oops", "comments": []}), encoding="utf-8")
    with pytest.raises(pr_review_fetcher.FetchError):
        pr_review_fetcher.load_fixture(bad)


def test_load_fixture_unreadable_path_raises(tmp_path):
    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(pr_review_fetcher.FetchError):
        pr_review_fetcher.load_fixture(missing)


def test_cli_fixture_mode_prints_json_and_exits_zero():
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "pr_review_fetcher.py"),
            "--fixture-file",
            str(FIXTURES_DIR / "pr47.json"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    records = json.loads(result.stdout)
    assert len(records) == 4  # 1 review + 3 comments
    assert {r["kind"] for r in records} == {"review", "inline_comment"}


def test_cli_pr_without_repo_errors():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pr_review_fetcher.py"), "--pr", "1"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode != 0
    assert "--repo" in result.stderr
