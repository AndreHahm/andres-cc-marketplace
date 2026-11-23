"""Grant findings never block (issue #862): the `allowed-tools-grant` category a model chooses, the
guards around it, and the mislabelled cases those guards must keep blocking."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.marketplace_ci import review_contract as rc
from scripts.marketplace_ci.__main__ import _finding_to_dict
from scripts.marketplace_ci.review import (
    Finding,
    ReviewOutputError,
    ReviewResult,
    aggregate_findings,
    gate_decision,
    validate_review_output,
)

GRANT = rc.CATEGORY_ALLOWED_TOOLS_GRANT
SKILL = "plugins/demo-kit/skills/x/SKILL.md"


def _finding(severity="Major", path=SKILL, category=GRANT, **extra):
    return Finding(
        reviewer=extra.pop("reviewer", "security-reviewer"),
        severity=severity,
        rule=extra.pop("rule", "tool-scoping"),
        path=path,
        evidence="e",
        remediation="r",
        line=extra.pop("line", 3),
        category=category,
        **extra,
    )


def _outcome(finding):
    return gate_decision(finding, in_diff=True).outcome


@pytest.mark.parametrize("severity", ["Critical", "Major"])
@pytest.mark.parametrize(
    "reviewer", ["security-reviewer", "plugin-rulebook-checker", "skill-reviewer"]
)
def test_a_grant_finding_never_blocks_whoever_reports_it(severity, reviewer):
    assert _outcome(_finding(severity, reviewer=reviewer)) == "notice"


@pytest.mark.parametrize(
    "path",
    [
        SKILL,
        "plugins/demo-kit/skills/x/references/a.md",
        "plugins/demo-kit/skills/x/examples/a.md",
        "plugins/demo-kit/commands/a.md",
        ".claude/skills/x/SKILL.md",
        ".claude/commands/a.md",
        "./plugins/demo-kit//commands/a.md",
    ],
)
def test_the_cap_covers_skill_and_command_documents(path):
    assert _outcome(_finding(path=path)) == "notice"


@pytest.mark.parametrize(
    "path",
    [
        "plugins/demo-kit/agents/a.md",  # an agent's `tools` is a real allowlist
        ".claude/agents/a.md",
        ".codex/agents/a.toml",
        "plugins/demo-kit/skills/x/scripts/a.py",
        "plugins/demo-kit/skills/x/scripts/notes.md",
        "plugins/demo-kit/hooks/hooks.json",
        "plugins/demo-kit/rules/a.md",
        ".claude/settings.json",
        ".github/workflows/ci.yml",
        "scripts/marketplace_ci/review.py",
        "AGENTS.md",
        "plugins/demo-kit/skills/x/../../agents/a.md",
        "../plugins/demo-kit/skills/x/SKILL.md",
        "/plugins/demo-kit/skills/x/SKILL.md",
        "docs/plugins/demo-kit/commands/a.md",
        "plugins/demo-kit/skills/x/agents/a.md",
        "plugins/demo-kit/commands/agents/a.md",
        "plugins/demo-kit/skills/x/references/agents/a.md",
        "plugins/demo-kit/skills/x/references/deep/scripts/a.md",
        "plugins/demo-kit/skills/x/examples/hooks/a.md",
        "plugins/demo-kit/skills/x/SKILL.md\n",
        "",
    ],
)
def test_a_grant_label_anywhere_else_still_blocks(path):
    assert _outcome(_finding(path=path)) == "block"


@pytest.mark.parametrize("category", [None, rc.CATEGORY_OTHER])
def test_any_other_category_blocks_like_before(category):
    assert _outcome(_finding(category=category)) == "block"


def test_a_finding_that_also_names_another_file_is_capped_only_if_that_is_covered_too():
    assert _outcome(_finding(components=("plugins/demo-kit/commands/a.md",))) == "notice"
    assert _outcome(_finding(components=("plugins/demo-kit/commands/a.md:27",))) == "notice"
    assert _outcome(_finding(components=("plugins/demo-kit/scripts/a.py",))) == "block"
    assert _outcome(_finding(components=("plugins/demo-kit/scripts/a.py:3",))) == "block"
    assert _outcome(_finding(components=("",))) == "block"
    assert _outcome(_finding(components=("AGENTS.md",))) == "block"


def test_a_script_finding_is_never_capped():
    assert _outcome(_finding(source="script")) == "block"


def _agg(*findings):
    return aggregate_findings(
        [ReviewResult(reviewer=f.reviewer, verdict="fail", findings=(f,)) for f in findings]
    )


@pytest.mark.parametrize("other", [None, rc.CATEGORY_OTHER])
@pytest.mark.parametrize("other_severity", ["Critical", "Major", "Minor"])
def test_reviewers_must_agree_on_the_category(other, other_severity):
    grant = _finding("Major", reviewer="a")
    differs = _finding(other_severity, reviewer="b", category=other)
    for order in ((grant, differs), (differs, grant)):
        (merged,) = _agg(*order)
        assert merged.category is None
        assert _outcome(merged) == "block"


def test_agreeing_reviewers_stay_capped():
    (merged,) = _agg(_finding(reviewer="a"), _finding("Critical", reviewer="b"))
    assert merged.category == GRANT and merged.severity == "Critical"
    assert _outcome(merged) == "notice"


# --- the envelope field --------------------------------------------------------------------


def _envelope(**finding):
    base = {
        "id": "M1",
        "severity": "major",
        "axis": "tool-scoping",
        "location": f"{SKILL}:3",
        "evidence": "e",
        "finding": "f",
        "fix": "x",
        "confidence": "high",
        "components": None,
    }
    return {
        "contract_version": "1",
        "dispatch": {"id": "d", "reviewer": "r", "backend": "codex", "target_paths": [SKILL]},
        "provenance": {},
        "findings": [{**base, **finding}],
        "verdict": "fail",
        "inspection_limits": [],
    }


@pytest.mark.parametrize("category", [*rc.FINDING_CATEGORIES, None])
def test_a_known_category_is_read(category):
    (finding,) = validate_review_output(_envelope(category=category)).findings
    assert finding.category == category


def test_an_envelope_without_a_category_still_parses_and_blocks():
    (finding,) = validate_review_output(_envelope()).findings
    assert finding.category is None and _outcome(finding) == "block"


@pytest.mark.parametrize("category", ["grant", "", "ALLOWED-TOOLS-GRANT", 1, ["other"], {}])
def test_an_unknown_category_fails_the_envelope(category):
    with pytest.raises(ReviewOutputError):
        validate_review_output(_envelope(category=category))


def test_the_result_records_the_category_and_the_reported_severity():
    finding = _finding()
    out = _finding_to_dict(finding, True, False, gate_decision(finding, in_diff=True))
    assert out["category"] == GRANT and out["gate"] == "notice" and out["severity"] == "Major"


# --- the briefing --------------------------------------------------------------------------


def test_the_briefing_defines_every_category_and_what_is_never_a_grant_finding():
    text = rc.render_category_briefing()
    for category in rc.FINDING_CATEGORIES:
        assert f"`{category}`" in text
    for word in ("injection", "path", "secret", "weakened", "`tools`", "minor"):
        assert word in text


# --- saved CI findings (PR #856), labelled by hand -------------------------------------------

_FIXTURE = Path(__file__).parent / "fixtures" / "issue-862-replay" / "results.json"
_RUNS = {
    run["head_sha"][:8]: run["findings"]
    for run in json.loads(_FIXTURE.read_text(encoding="utf-8"))["runs"]
}
# The grant findings among the saved Majors, by (head, index).
_GRANT_FINDINGS = {("c666bfed", 0), ("5b383b02", 0), ("d3a3dcb5", 3), ("0a1c0902", 0)}


def _saved(head, index, category):
    entry = {
        k: v for k, v in _RUNS[head][index].items() if k not in ("in_diff", "blocking", "gate")
    }
    entry["reporters"] = tuple(entry["reporters"])
    entry["components"] = tuple(entry["components"])
    return replace(Finding(**entry), category=category)


def test_correct_labels_clear_exactly_the_grant_findings():
    cleared = {
        (head, index)
        for head, entries in _RUNS.items()
        for index, entry in enumerate(entries)
        if entry["gate"] == "block"
        and _outcome(
            _saved(head, index, GRANT if (head, index) in _GRANT_FINDINGS else rc.CATEGORY_OTHER)
        )
        == "notice"
    }
    assert cleared == _GRANT_FINDINGS


def test_a_tool_scoping_rule_name_alone_never_clears_an_injection_finding():
    """c666bfed: security-reviewer named a shell argument injection `tool-scoping`."""
    finding = _saved("c666bfed", 1, rc.CATEGORY_OTHER)
    assert finding.rule == "tool-scoping" and _outcome(finding) == "block"
    assert _outcome(replace(finding, category=None)) == "block"


def test_a_mislabelled_injection_finding_in_a_skill_document_is_the_accepted_residual():
    """The model's label decides inside the covered documents (issue #862, the owner's choice): this
    pins the residual so a later change to it is deliberate."""
    assert _outcome(_saved("c666bfed", 1, GRANT)) == "notice"
