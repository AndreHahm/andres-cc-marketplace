"""A model's R18 (block size) finding on a skill's references and examples never blocks (#862)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from scripts.marketplace_ci.review import (
    Finding,
    ReviewResult,
    aggregate_findings,
    gate_decision,
)

REFERENCE = "plugins/demo-kit/skills/x/references/a.md"


_BASE = Finding(
    reviewer="plugin-rulebook-checker",
    severity="Critical",
    rule="plugin-rulebook:R18",
    path=REFERENCE,
    evidence="42 content lines, above R18's limit",
    remediation="Split the block.",
    line=3,
    reporters=("plugin-rulebook-checker",),
)


def _finding(**changes):
    return replace(_BASE, **changes)


def _outcome(finding):
    return gate_decision(finding, in_diff=True).outcome


@pytest.mark.parametrize(
    "path",
    [
        REFERENCE,
        "plugins/demo-kit/skills/x/examples/deep/a.md",
        ".claude/skills/x/references/a.md",
        "./plugins/demo-kit//skills/x/references/a.md",
        "plugins/demo-kit/skills/x/REFERENCES/A.MD",
    ],
)
@pytest.mark.parametrize("severity", ["Critical", "Major"])
def test_the_cap_covers_references_and_examples(path, severity):
    assert _outcome(_finding(path=path, severity=severity)) == "notice"


@pytest.mark.parametrize(
    "path",
    [
        "plugins/demo-kit/skills/x/SKILL.md",
        "plugins/demo-kit/commands/a.md",
        "plugins/demo-kit/references/a.md",
        "plugins/demo-kit/skills/x/scripts/a.md",
        "plugins/demo-kit/skills/x/references/../SKILL.md",
        "docs/a.md",
        "/plugins/demo-kit/skills/x/references/a.md",
        "../plugins/demo-kit/skills/x/references/a.md",
        "plugins/demo-kit/skills/x/references/a.py",
        "plugins/demo-kit/agents/x/references/a.md",
    ],
)
def test_other_documents_still_block(path):
    assert _outcome(_finding(path=path)) == "block"


@pytest.mark.parametrize(
    "change",
    [
        {"rule": "R18 and R6"},
        {"rule": "security"},
        {"rule": "R6", "evidence": "R18"},
        {"evidence": "R18; the grant also breaks R6"},
        {"reporters": ("plugin-rulebook-checker", "skill-reviewer")},
        {"reviewer": "security-reviewer", "reporters": ("security-reviewer",)},
        {"source": "script"},
        {"components": ("plugins/demo-kit/skills/x/SKILL.md:3",)},
        {"components": ("plugins/demo-kit/skills/x/references/../SKILL.md",)},
    ],
)
def test_the_guards_keep_everything_else_blocking(change):
    assert _outcome(_finding(**change)) == "block"


def test_a_component_in_another_reference_is_covered():
    assert _outcome(replace(_finding(), components=(f"{REFERENCE}:9",))) == "notice"


@pytest.mark.parametrize(
    "other",
    [
        _finding(evidence="R18, and the grant breaks R6"),
        _finding(components=("plugins/demo-kit/skills/x/SKILL.md",)),
        _finding(reviewer="security-reviewer", reporters=("security-reviewer",)),
        _finding(
            reviewer="security-reviewer",
            reporters=("security-reviewer",),
            path=f"./{REFERENCE}",
            severity="Minor",
        ),
    ],
)
def test_merging_with_a_copy_that_blocks_never_becomes_a_notice(other):
    capped = _finding()
    for order in ((capped, other), (other, capped)):
        merged = aggregate_findings(
            [ReviewResult(reviewer=f.reviewer, verdict="fail", findings=(f,)) for f in order]
        )
        assert len(merged) == 1
        assert _outcome(merged[0]) == "block"
