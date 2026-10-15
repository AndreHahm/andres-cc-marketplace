"""Fixture tests for the computed gate and the exceptions registry in use (issue #573):
exception matching, each gate outcome, suppression of script findings only, the envelope
fields a reviewer may return, and the briefing every model reviewer receives."""

from __future__ import annotations

import pytest

from scripts.marketplace_ci import review_contract as rc
from scripts.marketplace_ci.__main__ import _finding_to_dict
from scripts.marketplace_ci.review import (
    Finding,
    ReviewOutputError,
    blocking_findings,
    gate_decision,
    validate_review_output,
)

SKILL = "plugins/demo-kit/skills/x/SKILL.md"


def _entry(rule="r5-r6-ask-user-question-grant", path="plugins/**", **extra):
    return rc.ExceptionEntry(
        rule=rule,
        path=path,
        reason=extra.get("reason", "A redundant grant is a no-op."),
        authority=extra.get("authority", "docs/ci.md"),
    )


def _finding(severity="Major", rule="r5-r6-ask-user-question-grant", path=SKILL, **extra):
    return Finding(
        reviewer=extra.pop("reviewer", "skill-reviewer"),
        severity=severity,
        rule=rule,
        path=path,
        evidence="e",
        remediation="r",
        line=extra.pop("line", 3),
        **extra,
    )


# --- exception matching ----------------------------------------------------------


@pytest.mark.parametrize(
    "pattern,path,expected",
    [
        ("plugins/**", "plugins/a/b/c.md", True),
        ("plugins/**", "plugins/a.md", True),
        ("plugins/*", "plugins/a/b.md", False),  # one star never crosses a directory
        ("plugins/*/SKILL.md", "plugins/demo/SKILL.md", True),
        ("plugins/**/SKILL.md", "plugins/a/b/SKILL.md", True),
        ("plugins/**/SKILL.md", "plugins/SKILL.md", True),
        ("scripts/a.py", "scripts/a.py", True),
        ("scripts/a.py", "scripts/ab.py", False),
        ("scripts/?.py", "scripts/a.py", True),
        ("scripts/?.py", "scripts/ab.py", False),
        (".claude/**", "./.claude/rules/x.md", True),  # a leading ./ is normalised away
        ("plugins/**", "docs/plugins/x.md", False),  # anchored at the start
        ("plugins/a.b", "plugins/axb", False),  # a dot in a pattern is a dot
    ],
)
def test_path_globs_are_anchored_and_directory_aware(pattern, path, expected):
    entry = _entry(path=pattern)
    assert (rc.match_exception((entry,), entry.rule, path) is entry) is expected


@pytest.mark.parametrize(
    "path",
    [
        "plugins/x/../../scripts/marketplace_ci/review.py",  # climbs out of the glob's prefix
        "../plugins/x.md",
        "/plugins/x.md",
        "plugins/x/../../../etc/passwd",
        "",
    ],
)
def test_a_path_that_escapes_its_prefix_never_matches(path):
    assert rc.match_exception((_entry(path="**"),), "r5-r6-ask-user-question-grant", path) is None


def test_the_rule_must_match_exactly():
    assert rc.match_exception((_entry(),), "r5-r6-other", SKILL) is None


def test_the_first_matching_entry_wins():
    first, second = _entry(path="plugins/**"), _entry(path="plugins/demo-kit/**", reason="second")
    assert rc.match_exception((first, second), first.rule, SKILL) is first


# --- the briefing every model reviewer receives -----------------------------------------


def test_no_exceptions_means_no_briefing_section():
    assert rc.render_exceptions_briefing(()) == ""


def test_the_briefing_carries_every_field_of_every_entry():
    entries = (
        _entry(reason="first\nreason   spread over lines", authority="docs/ci.md"),
        _entry(rule="mirror-byte-identity", path=".claude/**", authority="docs/ci.md"),
    )
    text = rc.render_exceptions_briefing(entries)
    assert text.startswith("[documented exceptions]")
    assert text.rstrip().endswith("[end documented exceptions]")
    for entry in entries:
        assert entry.rule in text and entry.path in text and entry.authority in text
    assert "first reason spread over lines" in text


# --- gate outcomes ------------------------------------------------------------------------


@pytest.mark.parametrize("severity", ["Critical", "Major"])
def test_a_model_critical_or_major_on_a_changed_line_blocks(severity):
    assert gate_decision(_finding(severity), in_diff=True).outcome == "block"


@pytest.mark.parametrize("severity", ["Critical", "Major"])
def test_a_model_critical_or_major_off_the_diff_is_a_notice(severity):
    assert gate_decision(_finding(severity), in_diff=False).outcome == "notice"


@pytest.mark.parametrize("in_diff", [True, False])
def test_a_minor_never_blocks(in_diff):
    assert gate_decision(_finding("Minor"), in_diff=in_diff).outcome == "notice"


@pytest.mark.parametrize("severity", ["Critical", "Major"])
def test_a_model_measurement_finding_is_a_notice_until_verifiers_exist(severity):
    finding = _finding(severity, rule_class="measurement")
    assert gate_decision(finding, in_diff=True).outcome == "notice"


def test_a_script_measurement_finding_still_blocks():
    finding = _finding("Critical", rule_class="measurement", source="script")
    assert gate_decision(finding, in_diff=True).outcome == "block"


@pytest.mark.parametrize("rule_class", ["line", "graph", "judgment"])
def test_the_other_rule_classes_block_like_before(rule_class):
    assert gate_decision(_finding(rule_class=rule_class), in_diff=True).outcome == "block"


def test_a_script_finding_matching_an_exception_is_suppressed_and_cites_it():
    entry = _entry()
    decision = gate_decision(
        _finding("Critical", source="script"), in_diff=True, exceptions=(entry,)
    )
    assert decision.outcome == "suppressed"
    assert decision.exception is entry


def test_a_suppressed_script_finding_is_suppressed_even_off_the_diff_or_minor():
    entry = _entry()
    for finding, in_diff in [
        (_finding("Minor", source="script"), True),
        (_finding("Critical", source="script"), False),
    ]:
        assert gate_decision(finding, in_diff=in_diff, exceptions=(entry,)).outcome == "suppressed"


def test_a_model_finding_is_never_suppressed_by_an_exception():
    decision = gate_decision(_finding("Critical"), in_diff=True, exceptions=(_entry(),))
    assert decision.outcome == "block"
    assert decision.exception is None


def test_a_script_finding_with_no_matching_exception_is_gated_normally():
    finding = _finding("Critical", rule="some-other-rule", source="script")
    assert gate_decision(finding, in_diff=True, exceptions=(_entry(),)).outcome == "block"
    outside = _finding("Critical", path="docs/ci.md", source="script")
    assert gate_decision(outside, in_diff=True, exceptions=(_entry(),)).outcome == "block"


def test_blocking_findings_honours_exceptions_and_rule_class():
    suppressed = _finding("Critical", source="script")
    measured = _finding("Critical", rule="size", rule_class="measurement")
    real = _finding("Major", rule="activation")
    ranges = {SKILL: ((1, 10),)}
    assert blocking_findings(
        [suppressed, measured, real], ranges, changed_paths=(SKILL,), exceptions=(_entry(),)
    ) == (real,)


def test_blocking_findings_with_unknown_ranges_still_applies_the_gate_classes():
    measured = _finding("Critical", rule="size", rule_class="measurement")
    real = _finding("Critical", rule="activation")
    assert blocking_findings([measured, real], None) == (real,)


# --- envelope fields -------------------------------------------------------------------------


def _envelope(**finding_extra):
    finding = {
        "id": "f1",
        "severity": "major",
        "axis": "activation",
        "location": f"{SKILL}:3",
        "evidence": "e",
        "finding": "f",
        "fix": "x",
        "confidence": "high",
    }
    finding.update(finding_extra)
    return {
        "contract_version": "1",
        "dispatch": {
            "id": "d",
            "reviewer": "skill-reviewer",
            "backend": "codex",
            "target_paths": [],
        },
        "provenance": {},
        "findings": [finding],
        "verdict": "findings",
        "inspection_limits": [],
    }


def test_a_finding_without_the_new_fields_gets_the_defaults():
    (finding,) = validate_review_output(_envelope()).findings
    assert finding.rule_class == "judgment"
    assert finding.source == "model"
    assert finding.evidence_type is None
    assert finding.confidence == "high"
    assert finding.risk == ()


def test_the_new_fields_are_parsed_and_kept():
    risk = {"reachable": True, "exposure": "all users", "mitigation": "none"}
    (finding,) = validate_review_output(
        _envelope(rule_class="graph", evidence_type="repo_policy", risk=risk)
    ).findings
    assert finding.rule_class == "graph"
    assert finding.evidence_type == "repo_policy"
    assert dict(finding.risk) == risk


@pytest.mark.parametrize(
    "extra",
    [
        {"rule_class": "vibes"},
        {"evidence_type": "hunch"},
        {"risk": "high"},
        {"risk": {"reachable": True, "unknown": 1}},
        {"risk": {"exposure": ["list"]}},
    ],
)
def test_an_invalid_new_field_is_refused_not_ignored(extra):
    with pytest.raises(ReviewOutputError):
        validate_review_output(_envelope(**extra))


def test_a_model_reviewer_cannot_claim_to_be_a_script():
    with pytest.raises(ReviewOutputError):
        validate_review_output(_envelope(source="script"))


# --- the result payload ------------------------------------------------------------------------


def test_the_finding_dict_records_gate_class_and_exception():
    entry = _entry()
    finding = _finding("Major", source="script", rule_class="line", confidence="high")
    decision = gate_decision(finding, in_diff=True, exceptions=(entry,))
    out = _finding_to_dict(finding, True, False, decision)
    assert out["gate"] == "suppressed"
    assert out["suppressed"] is True
    assert out["exception"] == {
        "rule": entry.rule,
        "path": entry.path,
        "authority": entry.authority,
    }
    assert out["rule_class"] == "line" and out["source"] == "script"
    assert out["confidence"] == "high" and out["blocking"] is False


def test_the_finding_dict_for_a_blocking_finding_has_no_exception():
    finding = _finding("Critical")
    out = _finding_to_dict(finding, True, True, gate_decision(finding, in_diff=True))
    assert out["gate"] == "block"
    assert out["suppressed"] is False and out["exception"] is None


# --- aggregation and the measurement downgrade (security review M1, M2) -------------------------


def _agg(*findings):
    from scripts.marketplace_ci.review import ReviewResult, aggregate_findings

    reports = [ReviewResult(f.reviewer, "v", (f,)) for f in findings]
    return aggregate_findings(reports)


def test_a_measurement_copy_never_hides_a_blocking_duplicate():
    measured = _finding("Critical", rule_class="measurement", reviewer="a")
    real = _finding("Major", reviewer="b")
    (merged,) = _agg(measured, real)
    assert merged.rule_class == "judgment"
    assert gate_decision(merged, in_diff=True).outcome == "block"


def test_a_tie_is_not_decided_by_dispatch_order():
    measured = _finding("Critical", rule_class="measurement", reviewer="a")
    real = _finding("Critical", reviewer="b")
    for order in ((measured, real), (real, measured)):
        (merged,) = _agg(*order)
        assert gate_decision(merged, in_diff=True).outcome == "block"


def test_a_script_finding_never_absorbs_a_model_finding():
    script = _finding("Critical", source="script", reviewer="verifier")
    model = _finding("Major", reviewer="skill-reviewer")
    merged = _agg(script, model)
    assert {f.source for f in merged} == {"script", "model"}
    decisions = [gate_decision(f, in_diff=True, exceptions=(_entry(),)) for f in merged]
    assert sorted(d.outcome for d in decisions) == ["block", "suppressed"]


def test_the_measurement_downgrade_is_only_safe_while_the_bridge_rejects_rule_class():
    """A model's own `rule_class` can downgrade its finding to a notice. That is safe only
    because the bridge's output schema has no such property, so a model cannot set it. If the
    schema gains one, decide who may assert `measurement` before changing this test."""
    from pathlib import Path

    bridge = Path(__file__).resolve().parents[2] / (
        "plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs"
    )
    assert "rule_class" not in bridge.read_text(encoding="utf-8")
