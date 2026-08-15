import pytest

from scripts.marketplace_ci.review import (
    FULL_ESCALATION_PATHS,
    FULL_MODE_GOVERNANCE_REVIEWERS,
    ReviewOutputError,
    ReviewResult,
    aggregate_findings,
    derive_review_scope,
    validate_review_output,
)


def test_full_escalation_paths_and_governance_reviewers_stay_in_sync():
    # Guards against the exact drift class M1 found: a path present in one
    # list but not the other, either silently never escalating (reverse
    # direction) or hitting the fail-closed guard unexpectedly (this
    # direction) instead of dispatching a real reviewer set.
    assert set(FULL_ESCALATION_PATHS) == set(FULL_MODE_GOVERNANCE_REVIEWERS)
    assert all(reviewers for reviewers in FULL_MODE_GOVERNANCE_REVIEWERS.values())


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
    # Additive: DELTA_VALIDATE's own baseline is always present, union'd with
    # the governance-specific reviewers -- never a replacement (see the
    # "never a subset of delta" test below for why this matters).
    assert scope.validate == (
        "consistency-reviewer",
        "dependency-reviewer",
        "plugin-rulebook-checker",
        "security-reviewer",
    )
    # The changed path is itself under plugins/skills/, so it still earns
    # its own type-specific audit reviewer, same as an ordinary delta change.
    assert scope.audit == ("skill-reviewer",)


def test_marketplace_json_change_escalates_to_full_with_validator(change, dependency_index):
    scope = derive_review_scope([change(".claude-plugin/marketplace.json")], dependency_index())
    assert scope.mode == "full"
    assert scope.validate == (
        "dependency-reviewer",
        "plugin-rulebook-checker",
        "plugin-validator",
        "security-reviewer",
    )
    assert scope.audit == ()


def test_multiple_governance_paths_union_their_reviewer_sets(change, dependency_index):
    changes = [
        change("plugins/plugin-devkit/skills/plugin-rulebook/SKILL.md"),
        change(".claude-plugin/marketplace.json"),
    ]
    scope = derive_review_scope(changes, dependency_index())
    assert scope.mode == "full"
    assert scope.validate == (
        "consistency-reviewer",
        "dependency-reviewer",
        "plugin-rulebook-checker",
        "plugin-validator",
        "security-reviewer",
    )
    assert scope.audit == ("skill-reviewer",)


def test_governance_escalation_is_never_a_subset_of_the_equivalent_delta_scope(
    change, dependency_index
):
    """Regression test for the Critical this design started with: an author
    must never be able to *reduce* reviewer coverage by touching a
    governance path alongside an unrelated risky change."""
    risky_change = change("plugins/demo-kit/skills/x/SKILL.md")
    delta_scope = derive_review_scope([risky_change], dependency_index())
    assert delta_scope.mode == "delta"

    full_scope = derive_review_scope(
        [risky_change, change(".claude-plugin/marketplace.json")], dependency_index()
    )
    assert full_scope.mode == "full"

    delta_reviewers = set(delta_scope.validate) | set(delta_scope.audit)
    full_reviewers = set(full_scope.validate) | set(full_scope.audit)
    assert full_reviewers >= delta_reviewers


def test_governance_path_missing_from_reviewer_map_fails_closed(
    change, dependency_index, monkeypatch
):
    """M1 regression: a path present in FULL_ESCALATION_PATHS but absent
    from FULL_MODE_GOVERNANCE_REVIEWERS must not raise KeyError or silently
    drop the escalation -- derive_review_scope itself must detect the gap
    and return an empty scope for run-codex-review's own guard to catch."""
    import scripts.marketplace_ci.review as review_module

    monkeypatch.setattr(
        review_module, "FULL_ESCALATION_PATHS", (*FULL_ESCALATION_PATHS, "UNDEFINED.md")
    )
    scope = derive_review_scope([change("UNDEFINED.md")], dependency_index())
    assert scope.mode == "full"
    assert scope.validate == ()
    assert scope.audit == ()


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
    # Reuses delta's own baseline reviewer set (this is "delta, but big"),
    # scoped to the full closure rather than only the raw diff.
    assert scope.validate == ("dependency-reviewer", "plugin-rulebook-checker", "security-reviewer")
    assert set(scope.paths) >= {"plugins/demo-kit/skills/x/SKILL.md", "dep-0", "dep-99"}


def test_unbounded_dependency_closure_includes_type_specific_audit(change):
    changes = [change("plugins/demo-kit/skills/x/SKILL.md")]
    deps: list[str] = [f"dep-{i}" for i in range(99)]
    deps.append("plugins/demo-kit/agents/y.md")
    huge_index: dict[str, tuple[str, ...]] = {"plugins/demo-kit/skills/x/SKILL.md": tuple(deps)}
    scope = derive_review_scope(changes, huge_index, dependency_closure_limit=50)
    assert scope.mode == "full"
    assert scope.audit == ("skill-reviewer", "subagent-reviewer")


def test_multiple_component_types_combine_audit_reviewers(change, dependency_index):
    changes = [
        change("plugins/demo-kit/skills/x/SKILL.md"),
        change("plugins/demo-kit/agents/y.md"),
    ]
    scope = derive_review_scope(changes, dependency_index())
    assert scope.audit == ("skill-reviewer", "subagent-reviewer")


def _envelope(reviewer="security-reviewer", findings=None):
    return {
        "contract_version": "1",
        "dispatch": {
            "id": "test-dispatch",
            "reviewer": reviewer,
            "backend": "codex",
            "target_paths": ["plugins/demo-kit/skills/x/SKILL.md"],
        },
        "provenance": {
            "provider": "openai",
            "model": "test-model",
            "cli_version": "0.0.0",
            "execution_profile": "read-only",
        },
        "findings": findings or [],
        "verdict": "pass",
        "inspection_limits": [],
    }


VALID_OUTPUT = _envelope()


def test_validate_review_output_accepts_clean_minor_pass():
    result = validate_review_output(VALID_OUTPUT)
    assert isinstance(result, ReviewResult)
    assert result.blocking is False


def test_validate_review_output_critical_finding_blocks():
    data = _envelope(
        findings=[
            {
                "id": "C1",
                "severity": "critical",
                "axis": "R6",
                "location": "plugins/demo-kit/skills/x/SKILL.md",
                "evidence": "Bash(*) grant",
                "finding": "overly broad tool grant",
                "fix": "scope to Bash(git:*)",
                "confidence": "high",
            }
        ]
    )
    result = validate_review_output(data)
    assert result.blocking is True


def test_validate_review_output_minor_finding_does_not_block():
    data = _envelope(
        findings=[
            {
                "id": "m1",
                "severity": "minor",
                "axis": "R9",
                "location": "x",
                "evidence": "e",
                "finding": "f",
                "fix": "r",
                "confidence": "low",
            }
        ]
    )
    result = validate_review_output(data)
    assert result.blocking is False


def test_validate_review_output_rejects_missing_top_level_field():
    data = {k: v for k, v in VALID_OUTPUT.items() if k != "verdict"}
    with pytest.raises(ReviewOutputError, match="missing required field"):
        validate_review_output(data)


def test_validate_review_output_rejects_malformed_dispatch():
    data = {**VALID_OUTPUT, "dispatch": {"id": "x"}}
    with pytest.raises(ReviewOutputError, match="dispatch missing required field"):
        validate_review_output(data)


def test_validate_review_output_rejects_malformed_finding():
    data = _envelope(findings=[{"id": "x", "severity": "minor"}])
    with pytest.raises(ReviewOutputError, match="finding missing required field"):
        validate_review_output(data)


def test_validate_review_output_rejects_unknown_severity():
    data = _envelope(
        findings=[
            {
                "id": "x",
                "severity": "blocker",
                "axis": "r",
                "location": "p",
                "evidence": "e",
                "finding": "f",
                "fix": "m",
                "confidence": "high",
            }
        ]
    )
    with pytest.raises(ReviewOutputError, match="unknown severity"):
        validate_review_output(data)


def _finding(severity, rule="R9", path="x", line=1):
    location = f"{path}:{line}" if line is not None else path
    return {
        "id": f"{rule}-{path}-{line}",
        "severity": severity,
        "axis": rule,
        "location": location,
        "evidence": "e",
        "finding": "f",
        "fix": "m",
        "confidence": "medium",
    }


def test_aggregate_findings_dedupes_identical_rule_location_using_highest_severity():
    report_a = validate_review_output(
        _envelope(reviewer="plugin-rulebook-checker", findings=[_finding("minor")])
    )
    report_b = validate_review_output(
        _envelope(reviewer="security-reviewer", findings=[_finding("critical")])
    )
    aggregated = aggregate_findings([report_a, report_b])
    assert len(aggregated) == 1
    assert aggregated[0].severity == "Critical"
    assert aggregated[0].reporters == ("plugin-rulebook-checker", "security-reviewer")


def test_aggregate_findings_keeps_distinct_locations_separate():
    report = validate_review_output(
        _envelope(
            reviewer="plugin-rulebook-checker",
            findings=[
                _finding("minor", path="a"),
                _finding("minor", path="b"),
            ],
        )
    )
    aggregated = aggregate_findings([report])
    assert len(aggregated) == 2


def test_validate_review_output_splits_line_number_off_location():
    data = _envelope(findings=[_finding("minor", path="plugins/x/SKILL.md", line=42)])
    result = validate_review_output(data)
    assert result.findings[0].path == "plugins/x/SKILL.md"
    assert result.findings[0].line == 42


def test_validate_review_output_accepts_location_without_line():
    data = _envelope(findings=[_finding("minor", path="plugins/x/SKILL.md", line=None)])
    result = validate_review_output(data)
    assert result.findings[0].path == "plugins/x/SKILL.md"
    assert result.findings[0].line is None
