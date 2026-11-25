"""Fixture tests for the computed gate and the exceptions registry in use (issue #573):
exception matching, each gate outcome, suppression of script findings only, the envelope
fields a reviewer may return, and the briefing every model reviewer receives."""

from __future__ import annotations

from dataclasses import replace

import pytest

from scripts.marketplace_ci import review_contract as rc
from scripts.marketplace_ci.__main__ import _finding_to_dict
from scripts.marketplace_ci.review import (
    Finding,
    ReviewOutputError,
    ReviewResult,
    ScriptCoverage,
    aggregate_findings,
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


# --- rules a script gate owns (issues #613, #615, #525) ------------------------------------

R37_CLEAN = ScriptCoverage(clean=frozenset({("R37", SKILL)}))
R33_CLEAN = ScriptCoverage(clean_everywhere=frozenset({"R33"}))


def _claim(evidence, rule="plugin-rulebook-compliance", **extra):
    return Finding(
        reviewer=extra.pop("reviewer", "plugin-rulebook-checker"),
        severity=extra.pop("severity", "Major"),
        rule=rule,
        path=extra.pop("path", SKILL),
        evidence=evidence,
        remediation=extra.pop("remediation", "Rename it."),
        line=3,
        **extra,
    )


def _outcome(finding, coverage):
    return gate_decision(finding, in_diff=True, coverage=coverage).outcome


def test_a_checker_claim_a_script_contradicts_is_a_notice():
    r37 = _claim("R37 requires mode 100755 but x.py is 100644", rule="plugin-rulebook:R37")
    assert _outcome(r37, R37_CLEAN) == "notice"
    assert _outcome(_claim("prefix cdx, rename the file", rule="R33"), R33_CLEAN) == "notice"


@pytest.mark.parametrize(
    "rule, evidence",
    [
        ("plugin-rulebook-compliance", "R37 requires mode 100755"),  # id only in the evidence
        ("missing grant", 'the PR adds "<!-- per R35 -->" beside an ungranted tool call'),
        ("plugin-rulebook:R35", "R29 pass/fail subsection deleted"),  # evidence names another rule
        ("plugin-rulebook:R35 and R37", "both sections and modes"),  # more than one rule in `rule`
    ],
)
def test_an_owned_id_outside_the_rule_field_never_qualifies_a_downgrade(rule, evidence):
    """Issue #525 security review M1: evidence quotes PR text, so a PR could plant an owned id."""
    both = ScriptCoverage(clean=frozenset({("R35", SKILL), ("R37", SKILL)}))
    assert _outcome(_claim(evidence, rule=rule), both) == "block"


R35_NO_WORSE = ScriptCoverage(clean=frozenset({("R35", SKILL)}))


def test_a_checker_r35_claim_on_a_skill_no_worse_than_its_base_is_a_notice():
    """Issue #525: a pre-existing missing section, reported on a changed line, does not block."""
    finding = _claim("no ## Quick Start section", rule="plugin-rulebook:R35")
    assert _outcome(finding, R35_NO_WORSE) == "notice"
    assert _outcome(finding, ScriptCoverage()) == "block"  # a new skill or a removed heading
    mixed = _claim("R35 and R29 sections missing", rule="plugin-rulebook:R35")
    assert _outcome(mixed, R35_NO_WORSE) == "block"
    other = _claim("no Quick Start", rule="R35", path="plugins/demo-kit/skills/other/SKILL.md")
    assert _outcome(other, R35_NO_WORSE) == "block"


def test_a_checker_r18_claim_on_a_file_without_a_new_critical_block_is_a_notice():
    """Issue #862: the script measures block sizes, so a model's own count does not block."""
    covered = ScriptCoverage(clean=frozenset({("R18", SKILL)}))
    finding = _claim("25-line block", rule="plugin-rulebook:R18")
    assert _outcome(finding, covered) == "notice"
    assert _outcome(finding, ScriptCoverage()) == "block"
    mixed = _claim("R18 and R6 broken", rule="plugin-rulebook:R18")
    assert _outcome(mixed, covered) == "block"
    other = _claim("25-line block", rule="plugin-rulebook:R18", reviewer="skill-reviewer")
    assert _outcome(other, covered) == "block"
    elsewhere = _claim("big", rule="R18", path="plugins/demo-kit/skills/other/SKILL.md")
    assert _outcome(elsewhere, covered) == "block"


@pytest.mark.parametrize("rule", ["R18", "R35", "R37"])
def test_a_claim_naming_an_uncovered_component_or_a_symlink_blocks(rule):
    covered = ScriptCoverage(clean=frozenset({(rule, SKILL)}))
    claim = f"plugin-rulebook:{rule}"
    inside = _claim("25-line block", rule=claim, components=(f"{SKILL}:12",))
    assert _outcome(inside, covered) == "notice"
    script = _claim("x", rule=claim, components=("plugins/demo-kit/scripts/run.sh:12",))
    assert _outcome(script, covered) == "block"
    assert _outcome(_claim("x", rule=claim, via_symlink=True), covered) == "block"
    odd = _claim("x", rule=claim, components=(SKILL.replace("/", "\\"),))
    assert _outcome(odd, covered) == "block"


def test_an_r33_claim_through_a_symlink_or_an_odd_path_blocks():
    assert _outcome(_claim("x", rule="R33"), R33_CLEAN) == "notice"
    assert _outcome(_claim("x", rule="R33", via_symlink=True), R33_CLEAN) == "block"
    assert _outcome(_claim("x", rule="R33", path="a b.md"), R33_CLEAN) == "block"


# The blocking fixtures below name their rule in `rule`, as the checker does, so each one blocks
# on the condition it is about rather than on a generic axis (PR #855 review).
R37_AXIS = "plugin-rulebook:R37"


def test_without_coverage_nothing_is_downgraded():
    finding = _claim("R37 requires mode 100755", rule=R37_AXIS)
    assert _outcome(finding, R37_CLEAN) == "notice"  # the control: covered, it would be a notice
    assert _outcome(finding, None) == "block"
    assert _outcome(finding, ScriptCoverage()) == "block"


def test_coverage_is_per_rule_and_per_path():
    finding = _claim(
        "R37 requires mode 100755", rule=R37_AXIS, path="plugins/demo-kit/hooks/hooks.json"
    )
    assert _outcome(finding, R37_CLEAN) == "block"  # a hook command is not a covered grant document
    r33 = _claim("R33 prefix", rule="plugin-rulebook:R33")
    assert _outcome(r33, R37_CLEAN) == "block"  # R37 coverage says nothing of R33
    both = _claim("R33 and R37 apply", rule=R37_AXIS)
    assert _outcome(both, R37_CLEAN) == "block"  # every claimed rule must be covered


@pytest.mark.parametrize("path", [f"./{SKILL}", SKILL.replace("/", "//"), f"{SKILL}/../SKILL.md"])
def test_a_lexically_equivalent_path_matches_its_coverage(path):
    """PR #855 review: `./x` and `a//b` name the covered file, so they downgrade like `x`."""
    assert _outcome(_claim("no Quick Start", rule="R35", path=path), R35_NO_WORSE) == "notice"


def test_an_absolute_or_escaping_path_never_matches_coverage():
    """The pure gate cannot resolve an absolute path; an unmatched path keeps blocking."""
    for path in (f"/repo/{SKILL}", f"../{SKILL}"):
        assert _outcome(_claim("no Quick Start", rule="R35", path=path), R35_NO_WORSE) == "block"


@pytest.mark.parametrize(
    "rule, evidence",
    [
        ("plugin-rulebook:R6", "R6 grant is too broad"),
        (R37_AXIS, "R37 is mentioned, but the real defect is R6"),
        ("plugin-rulebook-compliance", "the guard was removed"),  # names no rule id
    ],
)
def test_other_claims_still_block_even_with_coverage(rule, evidence):
    assert _outcome(_claim(evidence, rule=rule), R37_CLEAN) == "block"


def test_only_the_rulebook_checker_can_be_contradicted():
    quoted = _claim("foo(untrusted)  # see R37", rule=R37_AXIS, reviewer="security-reviewer")
    assert _outcome(quoted, R37_CLEAN) == "block"
    shared = replace(
        _claim("R37 requires 100755", rule=R37_AXIS),
        reporters=("plugin-rulebook-checker", "security-reviewer"),
    )
    assert _outcome(shared, R37_CLEAN) == "block"


def test_a_script_finding_about_a_script_owned_rule_still_blocks():
    finding = _claim(
        "R37 requires mode 100755",
        rule="r37-executable-bit",
        source="script",
        rule_class="graph",
        reviewer="script-verifiers",
    )
    assert _outcome(finding, R37_CLEAN) == "block"


def test_a_merge_keeps_the_copy_that_still_blocks():
    downgradable = _claim("R37 requires 100755", rule=R37_AXIS, severity="Critical")
    assert _outcome(downgradable, R37_CLEAN) == "notice"  # the control: alone, it is downgraded
    blocking = _claim("the real defect", rule=R37_AXIS, severity="Major")
    # Same axis, path and line: one copy would be downgraded, the other is not.
    merged = aggregate_findings(
        [
            ReviewResult("plugin-rulebook-checker", "v", (downgradable,)),
            ReviewResult("skill-reviewer", "v", (replace(blocking, reviewer="skill-reviewer"),)),
        ]
    )
    assert len(merged) == 1
    assert _outcome(merged[0], R37_CLEAN) == "block"


def test_an_uncovered_checker_claim_merged_with_a_minor_still_blocks():
    # The checker's Critical is on an uncovered location (it blocks); another reviewer's Minor
    # shares the axis, path and line. The merge must not keep the Minor copy and lose the block.
    critical = _claim(
        "R37 requires 100755",
        rule=R37_AXIS,
        severity="Critical",
        path="plugins/demo-kit/hooks/hooks.json",
    )
    minor = replace(critical, reviewer="skill-reviewer", severity="Minor", evidence="nit")
    merged = aggregate_findings(
        [
            ReviewResult("plugin-rulebook-checker", "v", (critical,)),
            ReviewResult("skill-reviewer", "v", (minor,)),
        ],
        R37_CLEAN,
    )
    assert len(merged) == 1 and merged[0].severity == "Critical"
    assert _outcome(merged[0], R37_CLEAN) == "block"


def test_a_lowercase_or_spaced_rule_id_still_counts_as_another_claim():
    mixed = _claim("rule R37 is cited, but r6 is the real defect", rule=R37_AXIS)
    assert _outcome(mixed, R37_CLEAN) == "block"
