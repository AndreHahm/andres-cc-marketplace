"""Coverage disclosure and advisory status for `run-codex-review` (issue #713, fixes 2 and 3).

A clean result used to say nothing about what the dispatched reviewers could judge: on a diff of
CI scripts and workflows every reviewer is plugin-component-focused, so "clean" did not mean the
code was checked for correctness. And a change to the review-dispatch code or the reviewers' own
definitions was flagged only by a stdout line in the parity wrapper. Both are now fields in the
result file: `coverage` and `advisory`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.marketplace_ci import review_contract
from scripts.marketplace_ci.review import (
    ADVISORY_DISPATCH_FILES,
    general_correctness_coverage,
    review_advisory,
)
from scripts.marketplace_ci.trust_boundary import TIER1_FILES

BASELINE = ("plugin-rulebook-checker", "dependency-reviewer", "security-reviewer")
ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "plugins/git-kit/scripts/git-codex-parity-review.py"


# --- coverage -------------------------------------------------------------------------------


def test_code_with_only_plugin_reviewers_is_not_covered():
    paths = (
        "scripts/marketplace_ci/conversion.py",
        ".github/workflows/marketplace-ci.yml",
        "plugins/git-kit/skills/commit/SKILL.md",
    )
    coverage = general_correctness_coverage(paths, BASELINE)
    assert coverage == {
        "general_correctness_reviewers": [],
        "uncovered_paths": [
            ".github/workflows/marketplace-ci.yml",
            "scripts/marketplace_ci/conversion.py",
        ],
        "complete": False,
    }


@pytest.mark.parametrize(
    "path",
    [
        "docs/ci.md",  # documentation
        "README.MD",
        "plugins/git-kit/skills/commit/SKILL.md",  # what the component reviewers are built for
        ".claude/agents/security-reviewer.md",
    ],
)
def test_markdown_is_not_code(path):
    assert general_correctness_coverage((path,), BASELINE)["complete"] is True


@pytest.mark.parametrize(
    "path",
    [
        "tests/marketplace_ci/test_cli.py",
        "pyproject.toml",
        ".github/dependabot.yml",
        # Classified by type, not location (security review of issue #713, M2): plugin scripts and
        # hooks get no general-correctness review either.
        "plugins/git-kit/scripts/git-codex-parity-review.py",
        ".claude/scripts/git-codex-parity-review.py",
        "plugins/git-kit/hooks/hooks.json",
    ],
)
def test_every_non_markdown_file_is_code(path):
    assert general_correctness_coverage((path,), BASELINE)["uncovered_paths"] == [path]


def test_a_dispatched_general_correctness_reviewer_covers_the_paths():
    coverage = general_correctness_coverage(
        ("scripts/x.py",), (*BASELINE, "code-reviewer"), general_reviewers={"code-reviewer"}
    )
    assert coverage == {
        "general_correctness_reviewers": ["code-reviewer"],
        "uncovered_paths": [],
        "complete": True,
    }


def test_a_general_reviewer_that_was_not_dispatched_covers_nothing():
    coverage = general_correctness_coverage(
        ("scripts/x.py",), BASELINE, general_reviewers={"code-reviewer"}
    )
    assert coverage["complete"] is False


def test_no_reviewer_checks_general_correctness_yet():
    # Issue #713 fix 1 (a separate PR) adds the first one; it must flip this flag in ROSTER.
    assert review_contract.general_correctness_reviewers() == frozenset()


def test_the_default_general_reviewers_come_from_the_roster(monkeypatch):
    roster = (*review_contract.ROSTER, review_contract.Reviewer("x-reviewer", "audit:x", True))
    monkeypatch.setattr(review_contract, "ROSTER", roster)
    assert general_correctness_coverage(("scripts/x.py",), ("x-reviewer",))["complete"] is True


# --- advisory -------------------------------------------------------------------------------


def test_an_ordinary_change_is_not_advisory():
    assert review_advisory(("README.md", "plugins/git-kit/skills/commit/SKILL.md")) == {
        "advisory": False,
        "reasons": [],
        "paths": [],
    }


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("scripts/marketplace_ci/conversion.py", "review-dispatch-critical"),
        ("pyproject.toml", "review-dispatch-critical"),
        (".codex/agents/security-reviewer.toml", "reviewer-steering"),
        (".codex/config.toml", "reviewer-steering"),
        ("AGENTS.md", "reviewer-steering"),
        ("plugins/git-kit/AGENTS.override.md", "reviewer-steering"),
        ("REVIEW.md", "reviewer-steering"),
        # Matched without case: a case-insensitive file system loads these too.
        ("agents.md", "reviewer-steering"),
        ("plugins/x/Agents.Local.MD", "reviewer-steering"),
        ("Review.md", "reviewer-steering"),
        ("plugins/plugin-devkit/agents/security-reviewer.md", "reviewer-definition"),
        (".claude/agents/scripts-reviewer.md", "reviewer-definition"),
    ],
)
def test_dispatch_steering_and_reviewer_files_make_a_result_advisory(path, reason):
    assert review_advisory(("README.md", path)) == {
        "advisory": True,
        "reasons": [reason],
        "paths": [path],
    }


@pytest.mark.parametrize(
    "path",
    [
        "docs/REVIEW.md",  # only the root REVIEW.md steers a reviewer (R10)
        "plugins/plugin-devkit/agents/agent-creator.md",  # not a dispatched reviewer
        "scripts/marketplace_ci/sync.py",  # Tier 2
        "notcodex/.codex",
    ],
)
def test_lookalike_paths_are_not_advisory(path):
    assert review_advisory((path,))["advisory"] is False


def test_reasons_and_paths_are_sorted_and_unique():
    advisory = review_advisory(("REVIEW.md", "pyproject.toml", "AGENTS.md", "pyproject.toml"))
    assert advisory["reasons"] == ["review-dispatch-critical", "reviewer-steering"]
    assert advisory["paths"] == ["AGENTS.md", "REVIEW.md", "pyproject.toml"]


def test_the_advisory_list_holds_every_tier1_file():
    # run-codex-review may not import trust_boundary (test_import_isolation's allowlist), so
    # review.py keeps its own copy; it must never fall behind the canonical list.
    assert ADVISORY_DISPATCH_FILES == TIER1_FILES


# --- import shadows (security review of issue #713, M1) --------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "scripts/marketplace_ci/review/__init__.py",  # a package beside review.py
        "scripts/marketplace_ci/__pycache__/review.cpython-313.pyc",
        "scripts/marketplace_ci/review.so",
        "scripts/tools/__init__.py",
        "json.py",  # a top-level stdlib shadow
        "yaml/__init__.py",
        ".venv/lib/site.py",
    ],
)
def test_an_added_import_shadow_makes_a_result_advisory(path):
    assert review_advisory((path,), (path,)) == {
        "advisory": True,
        "reasons": ["import-shadow"],
        "paths": [path],
    }


def test_the_shadow_patterns_apply_only_to_added_or_changed_paths():
    # The old side of a rename or a deleted file cannot shadow anything.
    assert review_advisory(("json.py",), ())["advisory"] is False


@pytest.mark.parametrize(
    "path", ["scripts/marketplace_ci/review_helpers.py", "scripts/tool.py", "docs/json.py.md"]
)
def test_ordinary_added_files_are_not_shadows(path):
    assert review_advisory((path,), (path,))["advisory"] is False


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        # Security re-check of issue #713, M-A: on a case-insensitive checkout these land on disk
        # as the lower-case path that runs or is loaded.
        ("Scripts/marketplace_ci/review.py", "review-dispatch-critical"),
        ("PyProject.toml", "review-dispatch-critical"),
        (".Codex/config.toml", "reviewer-steering"),
        ("Plugins/Plugin-Devkit/Agents/Security-Reviewer.md", "reviewer-definition"),
        ("Scripts/marketplace_ci/Review/__init__.py", "import-shadow"),
        ("JSON.PY", "import-shadow"),
        # M-A2: NTFS compares by simple uppercase, under which a dotless i equals i.
        ("scrıpts/marketplace_ci/review.py", "review-dispatch-critical"),
        ("scripts/marketplace_ci/revıew.py", "review-dispatch-critical"),
    ],
)
def test_advisory_names_are_matched_without_case(path, reason):
    assert review_advisory((path,), (path,))["reasons"] == [reason]


def test_a_tier1_reason_wins_over_the_shadow_reason():
    path = "scripts/marketplace_ci/__init__.py"
    assert review_advisory((path,), (path,))["reasons"] == ["review-dispatch-critical"]


def test_the_shadow_patterns_are_the_workflows_and_the_wrappers():
    import importlib.util

    from scripts.marketplace_ci import review

    workflow = (ROOT / ".github/workflows/marketplace-ci.yml").read_text(encoding="utf-8")
    assert f"'{review.SCRIPTS_SHADOW_PATTERN}'" in workflow
    assert f"'{review.TOP_LEVEL_SHADOW_PATTERN}'" in workflow
    spec = importlib.util.spec_from_file_location("parity", WRAPPER)
    assert spec is not None and spec.loader is not None
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    assert wrapper._SCRIPTS_SHADOW_PATTERN == review.SCRIPTS_SHADOW_PATTERN
    assert wrapper._TOP_LEVEL_SHADOW_PATTERN == review.TOP_LEVEL_SHADOW_PATTERN
