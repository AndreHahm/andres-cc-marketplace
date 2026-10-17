"""Corpus case validation for the reviewer eval (Phase 4 of #568, issue #586)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.reviewer_eval import corpus

HEAD = "db90a98e" + "0" * 32


def _case() -> dict:
    return {
        "schema_version": 1,
        "pr": 579,
        "head_sha": HEAD,
        "kind": "findings",
        "findings": [
            {
                "id": "f1",
                "reviewer": "security",
                "path": "plugins/git-kit/scripts/git-review-ledger.py",
                "line": 38,
                "rule": None,
                "label": "true",
                "source": "ledger",
                "note": "git environment variables",
                "known_issue": "k1",
            },
            {
                "id": "f2",
                "reviewer": "security",
                "path": "docs/ci.md",
                "line": None,
                "rule": None,
                "label": "false_positive",
                "source": "thread",
                "note": "",
                "known_issue": None,
            },
        ],
        "known_issues": [
            {"id": "k1", "path": "plugins/git-kit/scripts/git-review-ledger.py", "description": "x"}
        ],
    }


def _write(directory: Path, case: dict, name: str | None = None) -> Path:
    path = directory / (name or f"pr-{case['pr']}-{case['head_sha'][:8]}.json")
    path.write_text(json.dumps(case), encoding="utf-8")
    return path


def test_valid_case_has_no_errors():
    assert corpus.validate_case(_case()) == []


def test_clean_case_with_false_positive_only_is_valid():
    case = _case()
    case["kind"] = "clean"
    case["known_issues"] = []
    case["findings"] = [dict(case["findings"][1])]
    assert corpus.validate_case(case) == []


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda c: c.update(schema_version=2), "schema_version"),
        (lambda c: c.update(pr=0), "pr"),
        (lambda c: c.update(pr=True), "pr"),
        (lambda c: c.update(head_sha="ABC"), "head_sha"),
        (lambda c: c.update(head_sha="Z" * 40), "head_sha"),
        (lambda c: c.update(kind="other"), "kind"),
        (lambda c: c.update(extra=1), "unknown key"),
        (lambda c: c["findings"][0].update(label="maybe"), "label"),
        (lambda c: c["findings"][0].update(source="guess"), "source"),
        (lambda c: c["findings"][0].update(reviewer=""), "reviewer"),
        (lambda c: c["findings"][0].update(path=""), "path"),
        (lambda c: c["findings"][0].update(line=0), "line"),
        (lambda c: c["findings"][0].update(line=True), "line"),
        (lambda c: c["findings"][0].update(id="f2"), "duplicate"),
        (lambda c: c["findings"][0].update(known_issue="nope"), "known_issue"),
        (lambda c: c["findings"][0].update(extra=1), "unknown key"),
        (lambda c: c["known_issues"][0].update(extra=1), "unknown key"),
        (lambda c: c["known_issues"].append(dict(c["known_issues"][0])), "duplicate"),
        (lambda c: c["findings"][1].update(known_issue="k1"), "must be labelled true"),
        (lambda c: c.pop("findings"), "findings"),
    ],
)
def test_invalid_case_reports_the_problem(mutate, fragment):
    case = _case()
    mutate(case)
    errors = corpus.validate_case(case)
    assert errors
    assert any(fragment in error for error in errors), errors


def test_clean_case_rejects_known_issues_and_true_findings():
    case = _case()
    case["kind"] = "clean"
    errors = corpus.validate_case(case)
    assert any("clean" in error and "known_issues" in error for error in errors)
    assert any("clean" in error and "true" in error for error in errors)


def test_non_object_case_is_rejected():
    assert corpus.validate_case([]) == ["case must be a JSON object"]


def test_validation_does_not_mutate_the_case():
    case = _case()
    snapshot = copy.deepcopy(case)
    corpus.validate_case(case)
    assert case == snapshot


def test_load_corpus_returns_cases_in_filename_order(tmp_path):
    second = _case()
    second["pr"] = 580
    _write(tmp_path, second)
    _write(tmp_path, _case())
    assert [c["pr"] for c in corpus.load_corpus(tmp_path)] == [579, 580]


def test_load_corpus_rejects_a_filename_that_does_not_match_the_case(tmp_path):
    _write(tmp_path, _case(), name="pr-1-deadbeef.json")
    with pytest.raises(corpus.CorpusError, match="filename"):
        corpus.load_corpus(tmp_path)


def test_load_corpus_rejects_invalid_json_and_names_the_file(tmp_path):
    (tmp_path / "pr-1-deadbeef.json").write_text("{", encoding="utf-8")
    with pytest.raises(corpus.CorpusError, match="pr-1-deadbeef.json"):
        corpus.load_corpus(tmp_path)


def test_load_corpus_collects_errors_from_every_bad_file(tmp_path):
    bad = _case()
    bad["kind"] = "other"
    other = _case()
    other["pr"] = 580
    other["head_sha"] = "1" * 40
    other["findings"][0]["label"] = "maybe"
    _write(tmp_path, bad)
    _write(tmp_path, other)
    with pytest.raises(corpus.CorpusError) as caught:
        corpus.load_corpus(tmp_path)
    message = str(caught.value)
    assert "kind" in message
    assert "label" in message


def test_load_corpus_ignores_non_json_files(tmp_path):
    (tmp_path / "README.md").write_text("notes", encoding="utf-8")
    assert corpus.load_corpus(tmp_path) == []


def test_load_corpus_of_a_missing_directory_is_an_error(tmp_path):
    with pytest.raises(corpus.CorpusError, match="not a directory"):
        corpus.load_corpus(tmp_path / "absent")


def test_load_corpus_rejects_a_duplicate_pr_and_head(tmp_path):
    _write(tmp_path, _case())
    _write(tmp_path, _case(), name="pr-579-db90a98e-copy.json")
    with pytest.raises(corpus.CorpusError, match="filename"):
        corpus.load_corpus(tmp_path)


def test_cli_validate_succeeds_on_a_good_corpus(tmp_path, capsys):
    _write(tmp_path, _case())
    assert corpus.main(["validate", str(tmp_path)]) == 0
    assert "1 case" in capsys.readouterr().out


def test_cli_validate_fails_with_the_errors_on_stderr(tmp_path, capsys):
    bad = _case()
    bad["kind"] = "other"
    _write(tmp_path, bad)
    assert corpus.main(["validate", str(tmp_path)]) == 1
    assert "kind" in capsys.readouterr().err
