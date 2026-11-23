"""Grant findings never block (issue #862): the `allowed-tools-grant` category a model chooses, the
guards around it, and the mislabelled cases those guards must keep blocking."""

from __future__ import annotations

import json
import os
import subprocess
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
    mark_symlinked,
    relative_citations,
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


@pytest.mark.parametrize("spelling", ["./{}", "plugins//demo-kit/{}", "plugins/x/../demo-kit/{}"])
@pytest.mark.parametrize("category", [None, rc.CATEGORY_OTHER])
def test_a_differently_spelled_copy_still_has_to_agree(spelling, category):
    """PR #865: `./x` was grouped apart from `x`, so the other reviewer's label was never seen."""
    tail = SKILL if spelling == "./{}" else SKILL.removeprefix("plugins/demo-kit/")
    grant = _finding("Major", reviewer="a")
    differs = _finding("Minor", reviewer="b", category=category, path=spelling.format(tail))
    for order in ((grant, differs), (differs, grant)):
        (merged,) = _agg(*order)
        assert _outcome(merged) == "block"


def test_a_merge_keeps_the_spelling_that_may_pass_through_a_symlink():
    climbing = "plugins/x/../demo-kit/skills/x/SKILL.md"
    plain = _finding("Critical", reviewer="a")
    other = _finding("Major", reviewer="b", path=climbing)
    for order in ((plain, other), (other, plain)):
        (merged,) = _agg(*order)
        assert merged.path == climbing and merged.severity == "Critical"
        assert merged.components == (f"{SKILL}:3",)


def _relative(root, path, **extra):
    result = ReviewResult(reviewer="r", verdict="fail", findings=(_finding(path=path, **extra),))
    return relative_citations(result, root).findings[0]


@pytest.mark.skipif(os.name == "nt", reason="POSIX path spellings")
@pytest.mark.parametrize("prefix", ["{root}/", "{root}//", "/{root}/", "{root}/./"])
def test_an_absolute_citation_in_the_checkout_is_capped_like_the_relative_one(tmp_path, prefix):
    start = prefix.format(root=tmp_path)
    finding = _relative(tmp_path, f"{start}{SKILL}", components=(f"{start}{SKILL}:9", "a.md:3"))
    assert finding.path == SKILL and finding.components == (f"{SKILL}:9", "a.md:3")
    assert _outcome(_relative(tmp_path, f"{start}{SKILL}")) == "notice"


@pytest.mark.skipif(os.name == "nt", reason="POSIX path spellings")
def test_a_citation_through_a_symlinked_root_is_relative_too(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    assert _relative(link, f"{real}/{SKILL}").path == SKILL
    assert _relative(link, f"{link}/{SKILL}").path == SKILL


@pytest.mark.skipif(os.name == "nt", reason="POSIX path spellings")
def test_every_other_citation_keeps_its_spelling(tmp_path):
    root = tmp_path / "repo"
    for path in (
        f"{tmp_path}/repo-evil/{SKILL}",
        f"{root}/../{SKILL}",
        f"{root}/x/../{SKILL}",
        str(root),
        f"/{SKILL}",
        f"./{SKILL}",
        f"../{SKILL}",
        "",
    ):
        assert _relative(root, path).path == path


@pytest.mark.skipif(os.name == "nt", reason="POSIX path spellings")
def test_an_absolute_copy_still_has_to_agree(tmp_path):
    grant = _finding("Major", reviewer="a")
    differs = _relative(
        tmp_path, f"{tmp_path}/{SKILL}", severity="Minor", reviewer="b", category=rc.CATEGORY_OTHER
    )
    (merged,) = _agg(grant, differs)
    assert _outcome(merged) == "block"


def _marked(root, path, **extra):
    result = ReviewResult(reviewer="r", verdict="fail", findings=(_finding(path=path, **extra),))
    return mark_symlinked([result], root)[0].findings[0]


@pytest.fixture
def linked_repo(git_repo):
    git_repo.write("tool.sh", "x\n")
    git_repo.write(SKILL, "x\n")
    root = git_repo.root
    (root / "plugins/demo-kit/commands").mkdir(parents=True)
    (root / "plugins/demo-kit/commands/a.md").symlink_to("../../../tool.sh")
    (root / "plugins/demo-kit/skills/linked").symlink_to("x")
    git_repo.write("plugins/demo-kit/commands/b.md", "x\n")
    (root / "plugins/demo-kit/commands/b.md:5").symlink_to("../../../tool.sh")
    (root / "plugins/demo-kit/commands/c\\d.md").symlink_to("../../../tool.sh")
    git_repo.write("plugins/demo-kit/commands/e.md", "x\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "links"], cwd=root, check=True)
    return root


@pytest.mark.parametrize(
    "path",
    [
        "plugins/demo-kit/commands/a.md",
        "./plugins/demo-kit//commands/a.md",
        "plugins/demo-kit/skills/linked/SKILL.md",
        "plugins/demo-kit/skills/linked/../x/SKILL.md",
        "plugins/demo-kit/commands/b.md",  # what a citation of the link `b.md:5` parses to
    ],
)
@pytest.mark.parametrize("on_disk", [True, False])
@pytest.mark.skipif(os.name == "nt", reason="symlink creation")
def test_a_symlink_named_like_a_document_is_never_capped(linked_repo, path, on_disk):
    if not on_disk:  # core.symlinks=false checks a link out as a plain file
        for link in ("plugins/demo-kit/commands/a.md", "plugins/demo-kit/skills/linked"):
            (linked_repo / link).unlink()
            (linked_repo / link).write_text("target", encoding="utf-8")
    assert _outcome(_finding(path=path)) == "notice"  # by name alone
    assert _outcome(_marked(linked_repo, path)) == "block"
    assert _outcome(_marked(linked_repo, SKILL, components=(f"{path}:2",))) == "block"


@pytest.mark.skipif(os.name == "nt", reason="symlink creation")
def test_a_link_with_a_backslash_in_its_name_is_never_capped(linked_repo):
    path = "plugins/demo-kit/commands/c\\d.md"
    assert _marked(linked_repo, path).via_symlink
    assert _outcome(_finding(path=path)) == "block"  # not a plain name
    assert _outcome(_finding(components=(f"{path}:3",))) == "block"


@pytest.mark.skipif(os.name == "nt", reason="symlink creation")
def test_a_regular_document_stays_capped(linked_repo):
    assert _outcome(_marked(linked_repo, SKILL)) == "notice"
    assert _outcome(_marked(linked_repo, "plugins/demo-kit/commands/e.md")) == "notice"
    assert mark_symlinked([], linked_repo) == ()


@pytest.mark.skipif(os.name == "nt", reason="symlink creation")
def test_a_symlinked_copy_keeps_a_merged_finding_blocking(linked_repo):
    plain = _finding(reviewer="a")
    other = _marked(
        linked_repo,
        "plugins/demo-kit/skills/linked/../x/SKILL.md",
        reviewer="b",
        severity="Minor",  # so the plain copy is the one kept
    )
    for order in ((plain, other), (other, plain)):
        (merged,) = _agg(*order)
        assert merged.via_symlink and _outcome(merged) == "block"


def test_a_failing_git_raises(tmp_path):
    with pytest.raises(RuntimeError):
        _marked(tmp_path, SKILL)


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


# Cleared by R18's own cap, whatever the category (test_review_size_cap.py).
_SIZE_FINDINGS = {("81db31b9", index) for index in range(6)}


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
    assert cleared == _GRANT_FINDINGS | _SIZE_FINDINGS


def test_a_tool_scoping_rule_name_alone_never_clears_an_injection_finding():
    """c666bfed: security-reviewer named a shell argument injection `tool-scoping`."""
    finding = _saved("c666bfed", 1, rc.CATEGORY_OTHER)
    assert finding.rule == "tool-scoping" and _outcome(finding) == "block"
    assert _outcome(replace(finding, category=None)) == "block"


def test_a_mislabelled_injection_finding_in_a_skill_document_is_the_accepted_residual():
    """The model's label decides inside the covered documents (issue #862, the owner's choice): this
    pins the residual so a later change to it is deliberate."""
    assert _outcome(_saved("c666bfed", 1, GRANT)) == "notice"
