import pytest

from scripts.marketplace_ci.review import (
    ReviewOutputError,
    ReviewResult,
    aggregate_findings,
    derive_review_scope,
    validate_review_output,
)


def test_skill_change_selects_delta_validate_and_skill_audit(change, dependency_index):
    scope = derive_review_scope([change("plugins/demo-kit/skills/x/SKILL.md")], dependency_index())
    assert scope.mode == "delta"
    assert scope.structural_check == "scripts.marketplace_ci.validators:run_delta_structural_checks"
    assert scope.validate == ("plugin-rulebook-checker", "dependency-reviewer", "security-reviewer")
    assert scope.audit == ("skill-reviewer",)


def test_agent_change_selects_subagent_audit(change, dependency_index):
    scope = derive_review_scope([change("plugins/demo-kit/agents/x.md")], dependency_index())
    assert scope.audit == ("subagent-reviewer",)


def test_hook_change_has_no_launch_time_audit_reviewer(change, dependency_index):
    scope = derive_review_scope([change("plugins/demo-kit/hooks/hooks.json")], dependency_index())
    assert scope.mode == "delta"
    assert scope.validate == ("plugin-rulebook-checker", "dependency-reviewer", "security-reviewer")
    assert scope.audit == ()


def test_rulebook_change_escalates_to_full(change, dependency_index):
    scope = derive_review_scope(
        [change("plugins/plugin-devkit/skills/plugin-rulebook/SKILL.md")], dependency_index()
    )
    assert scope.mode == "full"


def test_non_plugin_change_is_light_mode(change, dependency_index):
    scope = derive_review_scope([change("README.md")], dependency_index())
    assert scope.mode == "light"
    assert scope.validate == ()
    assert scope.audit == ()


def test_unbounded_dependency_closure_escalates_to_full(change):
    changes = [change("plugins/demo-kit/skills/x/SKILL.md")]
    huge_index = {"plugins/demo-kit/skills/x/SKILL.md": tuple(f"dep-{i}" for i in range(100))}
    scope = derive_review_scope(changes, huge_index, dependency_closure_limit=50)
    assert scope.mode == "full"


def test_multiple_component_types_combine_audit_reviewers(change, dependency_index):
    changes = [
        change("plugins/demo-kit/skills/x/SKILL.md"),
        change("plugins/demo-kit/agents/y.md"),
    ]
    scope = derive_review_scope(changes, dependency_index())
    assert scope.audit == ("skill-reviewer", "subagent-reviewer")


VALID_OUTPUT = {
    "mode": "delta",
    "reviewed_paths": ["plugins/demo-kit/skills/x/SKILL.md"],
    "reviewers": {
        "selected": ["plugin-rulebook-checker", "security-reviewer"],
        "completed": ["plugin-rulebook-checker", "security-reviewer"],
        "skipped": [],
        "failed": [],
    },
    "coverage_confirmed": True,
    "findings": [],
}


def test_validate_review_output_accepts_clean_minor_pass():
    result = validate_review_output(VALID_OUTPUT)
    assert isinstance(result, ReviewResult)
    assert result.blocking is False


def test_validate_review_output_critical_finding_blocks():
    data = {
        **VALID_OUTPUT,
        "findings": [
            {
                "reviewer": "security-reviewer",
                "severity": "Critical",
                "rule": "R6",
                "path": "plugins/demo-kit/skills/x/SKILL.md",
                "evidence": "Bash(*) grant",
                "remediation": "scope to Bash(git:*)",
            }
        ],
    }
    result = validate_review_output(data)
    assert result.blocking is True


def test_validate_review_output_minor_finding_does_not_block():
    data = {
        **VALID_OUTPUT,
        "findings": [
            {
                "reviewer": "security-reviewer",
                "severity": "Minor",
                "rule": "R9",
                "path": "x",
                "evidence": "e",
                "remediation": "r",
            }
        ],
    }
    result = validate_review_output(data)
    assert result.blocking is False


def test_validate_review_output_rejects_missing_top_level_field():
    data = {k: v for k, v in VALID_OUTPUT.items() if k != "coverage_confirmed"}
    with pytest.raises(ReviewOutputError, match="missing required field"):
        validate_review_output(data)


def test_validate_review_output_rejects_malformed_finding():
    data = {**VALID_OUTPUT, "findings": [{"reviewer": "x", "severity": "Minor"}]}
    with pytest.raises(ReviewOutputError, match="finding missing required field"):
        validate_review_output(data)


def test_validate_review_output_rejects_unknown_severity():
    data = {
        **VALID_OUTPUT,
        "findings": [
            {
                "reviewer": "x",
                "severity": "Blocker",
                "rule": "r",
                "path": "p",
                "evidence": "e",
                "remediation": "m",
            }
        ],
    }
    with pytest.raises(ReviewOutputError, match="unknown severity"):
        validate_review_output(data)


def test_validate_review_output_rejects_incomplete_coverage():
    data = {
        **VALID_OUTPUT,
        "reviewers": {
            "selected": ["plugin-rulebook-checker", "security-reviewer"],
            "completed": ["plugin-rulebook-checker"],
            "skipped": [],
            "failed": [],
        },
    }
    with pytest.raises(ReviewOutputError, match="incomplete reviewer coverage"):
        validate_review_output(data)


def test_validate_review_output_rejects_coverage_confirmed_false():
    data = {**VALID_OUTPUT, "coverage_confirmed": False}
    with pytest.raises(ReviewOutputError, match="coverage_confirmed"):
        validate_review_output(data)


def _finding(reviewer, severity, rule="R9", path="x", line=1):
    return {
        "reviewer": reviewer,
        "severity": severity,
        "rule": rule,
        "path": path,
        "line": line,
        "evidence": "e",
        "remediation": "m",
    }


def test_aggregate_findings_dedupes_identical_rule_location_using_highest_severity():
    report_a = validate_review_output(
        {**VALID_OUTPUT, "findings": [_finding("plugin-rulebook-checker", "Minor")]}
    )
    report_b = validate_review_output(
        {**VALID_OUTPUT, "findings": [_finding("security-reviewer", "Critical")]}
    )
    aggregated = aggregate_findings([report_a, report_b])
    assert len(aggregated) == 1
    assert aggregated[0].severity == "Critical"
    assert aggregated[0].reporters == ("plugin-rulebook-checker", "security-reviewer")


def test_aggregate_findings_keeps_distinct_locations_separate():
    report = validate_review_output(
        {
            **VALID_OUTPUT,
            "findings": [
                _finding("plugin-rulebook-checker", "Minor", path="a"),
                _finding("plugin-rulebook-checker", "Minor", path="b"),
            ],
        }
    )
    aggregated = aggregate_findings([report])
    assert len(aggregated) == 2
