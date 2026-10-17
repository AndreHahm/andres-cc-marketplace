"""Precision, recall and stability scoring for the reviewer eval (Phase 4 of #568, issue #586)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.reviewer_eval import score


def _finding(fid: str, reviewer: str, label: str, known_issue: str | None = None) -> dict:
    return {
        "id": fid,
        "reviewer": reviewer,
        "path": "a.py",
        "line": 1,
        "rule": None,
        "label": label,
        "source": "owner",
        "note": "",
        "known_issue": known_issue,
    }


def _case(pr: int, findings: list[dict], known: list[str]) -> dict:
    return {
        "schema_version": 1,
        "pr": pr,
        "head_sha": f"{pr:08x}" + "0" * 32,
        "kind": "findings",
        "findings": findings,
        "known_issues": [{"id": k, "path": "a.py", "description": ""} for k in known],
    }


def test_precision_counts_only_true_labels_per_reviewer():
    cases = [
        _case(
            1,
            [
                _finding("f1", "security", "true", "k1"),
                _finding("f2", "security", "false_positive"),
                _finding("f3", "security", "pre_existing"),
                _finding("f4", "skill", "out_of_scope"),
            ],
            ["k1"],
        )
    ]
    result = score.score_corpus(cases)
    assert result["security"]["reported"] == 3
    assert result["security"]["true"] == 1
    assert result["security"]["precision"] == pytest.approx(1 / 3)
    assert result["skill"]["precision"] == 0.0


def test_recall_is_known_issues_found_over_all_known_issues_in_the_corpus():
    cases = [
        _case(1, [_finding("f1", "security", "true", "k1")], ["k1", "k2"]),
        _case(2, [_finding("f1", "skill", "true", "k1")], ["k1"]),
    ]
    result = score.score_corpus(cases)
    assert result["security"]["known_found"] == 1
    assert result["security"]["recall"] == pytest.approx(1 / 3)
    assert result["skill"]["recall"] == pytest.approx(1 / 3)
    assert result[score.OVERALL]["known_found"] == 2
    assert result[score.OVERALL]["recall"] == pytest.approx(2 / 3)


def test_two_findings_on_one_known_issue_count_it_once():
    cases = [
        _case(
            1,
            [_finding("f1", "security", "true", "k1"), _finding("f2", "security", "true", "k1")],
            ["k1"],
        )
    ]
    result = score.score_corpus(cases)
    assert result["security"]["known_found"] == 1
    assert result["security"]["recall"] == 1.0


def test_a_reviewer_with_no_findings_is_absent_and_empty_corpus_has_no_rates():
    assert score.score_corpus([]) == {
        score.OVERALL: {
            "reported": 0,
            "true": 0,
            "precision": None,
            "known_found": 0,
            "known_total": 0,
            "recall": None,
        }
    }


def test_clean_case_counts_every_finding_against_precision():
    clean = _case(1, [_finding("f1", "security", "false_positive")], [])
    clean["kind"] = "clean"
    result = score.score_corpus([clean])
    assert result["security"]["precision"] == 0.0
    assert result[score.OVERALL]["recall"] is None


def _result(*findings: tuple[str, str, int, bool]) -> dict:
    return {
        "findings": [
            {"reviewer": r, "path": p, "line": line, "blocking": b} for r, p, line, b in findings
        ]
    }


def test_blocking_set_accepts_an_explicit_null_line():
    result = {"findings": [{"reviewer": "r", "path": "a.py", "line": None, "blocking": True}]}
    assert score.blocking_set(result, "r") == frozenset({("a.py", None)})


def test_blocking_set_is_the_reviewers_blocking_findings_only():
    result = _result(
        ("security", "a.py", 1, True),
        ("security", "b.py", 2, False),
        ("skill", "c.py", 3, True),
    )
    assert score.blocking_set(result, "security") == frozenset({("a.py", 1)})


@pytest.mark.parametrize(
    "result",
    [
        [],
        "result",
        None,
        {},
        {"findings": "none"},
        {"findings": [["a.py", 1]]},
        {"findings": [{"reviewer": "security", "path": ["a.py"], "line": 1, "blocking": True}]},
        {"findings": [{"reviewer": "security", "path": "a.py", "line": 1}]},
        {"findings": [{"reviewer": "security", "path": "a.py", "line": True, "blocking": True}]},
        {"findings": [{"reviewer": "security", "path": "a.py", "blocking": True}]},
    ],
)
def test_blocking_set_rejects_a_result_that_is_not_shaped_like_one(result):
    """An archived result is untrusted: report a clear error, not a KeyError or TypeError."""
    with pytest.raises(ValueError, match="archived result"):
        score.blocking_set(result, "security")


def test_stability_needs_the_full_number_of_repeats():
    sets = [frozenset({("a.py", 1)})] * 4
    assert score.stability(sets) == {"repeats": 4, "agree": 4, "stable": None}


def test_stability_requires_four_of_five_identical():
    same = frozenset({("a.py", 1)})
    other = frozenset({("b.py", 2)})
    assert score.stability([same, same, same, same, other])["stable"] is True
    result = score.stability([same, same, same, other, frozenset()])
    assert result == {"repeats": 5, "agree": 3, "stable": False}


def test_stability_scales_the_four_of_five_rule_to_more_repeats():
    same = frozenset({("a.py", 1)})
    others = [frozenset({("b.py", i)}) for i in range(6)]
    assert score.stability([same] * 4 + others) == {"repeats": 10, "agree": 4, "stable": False}
    assert score.stability([same] * 8 + others[:2])["stable"] is True


def test_empty_blocking_sets_agree_with_each_other():
    empty = frozenset()
    assert score.stability([empty] * 5) == {"repeats": 5, "agree": 5, "stable": True}


def test_cli_prints_json_for_a_corpus_directory(tmp_path: Path, capsys: pytest.CaptureFixture):
    case = _case(7, [_finding("f1", "security", "true", "k1")], ["k1"])
    (tmp_path / f"pr-7-{case['head_sha'][:8]}.json").write_text(json.dumps(case), encoding="utf-8")
    assert score.main([str(tmp_path)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["security"]["precision"] == 1.0


def test_cli_reports_an_invalid_corpus(tmp_path: Path, capsys: pytest.CaptureFixture):
    (tmp_path / "pr-1-00000001.json").write_text("{}", encoding="utf-8")
    assert score.main([str(tmp_path)]) == 1
    assert "pr-1-00000001.json" in capsys.readouterr().err
