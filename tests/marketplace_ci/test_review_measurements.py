"""The measurement verifiers (issue #576, #568 Phase 2): R13 (SKILL.md line count) and R21 (skill
description sizes), compared with the base so only a PR that makes a value worse across a blocking
threshold is blocked. Weak and Soft Warning tiers are never reported: they were the noise in #568.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci import review_contract
from scripts.marketplace_ci import review_verifiers as rv
from scripts.marketplace_ci.__main__ import main
from scripts.marketplace_ci.git_state import ChangedPath
from scripts.marketplace_ci.review import gate_decision

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = (
    REPO_ROOT
    / "plugins"
    / "plugin-devkit"
    / "skills"
    / "plugin-rulebook"
    / "assets"
    / "settings.json"
)
SKILL = "plugins/demo-kit/skills/demo/SKILL.md"
GOOD_DESCRIPTION = "x" * 100


def _skill(lines: int = 10, description: str = GOOD_DESCRIPTION, extra: str = "") -> str:
    head = f"---\nname: demo\ndescription: {description}\n{extra}---\n"
    return head + "body\n" * max(lines - head.count("\n"), 0)


def _rules(findings):
    return [f.rule for f in findings]


# --- thresholds equal the rulebook settings (R20) ---------------------------------------------


def test_the_constants_equal_the_rulebook_settings():
    rules = json.loads(SETTINGS.read_text(encoding="utf-8"))["rules"]
    r13 = rules["R13_skillmd_line_limit"]["config"]["thresholds"]
    assert (rv.R13_WARNING, rv.R13_CRITICAL) == (r13["warning"], r13["critical"])
    r21 = rules["R21_skill_description_size"]["config"]
    warning, critical = r21["warning_thresholds"], r21["critical_thresholds"]
    assert (rv.DESCRIPTION_LOW_WARNING, rv.DESCRIPTION_LOW_CRITICAL) == (
        warning["description_low"],
        critical["description_low"],
    )
    assert (rv.DESCRIPTION_HIGH_WARNING, rv.DESCRIPTION_HIGH_CRITICAL) == (
        warning["description_high"],
        critical["description_high"],
    )
    assert (rv.WHEN_TO_USE_WARNING, rv.WHEN_TO_USE_CRITICAL) == (
        warning["when_to_use_high"],
        critical["when_to_use_high"],
    )


@pytest.mark.parametrize(
    "lines,rank", [(100, 0), (300, 0), (490, 0), (491, 1), (500, 1), (501, 2), (900, 2)]
)
def test_the_skillmd_line_tiers(lines, rank):
    assert rv.line_tier(lines) == rank


@pytest.mark.parametrize(
    "length,rank",
    [(0, 2), (19, 2), (20, 1), (79, 1), (80, 0), (1018, 0), (1019, 1), (1024, 1), (1025, 2)],
)
def test_the_description_tiers(length, rank):
    assert rv.description_tier(length) == rank


@pytest.mark.parametrize("length,rank", [(506, 0), (507, 1), (512, 1), (513, 2)])
def test_the_when_to_use_tiers(length, rank):
    assert rv.when_to_use_tier(length) == rank


@pytest.mark.parametrize(
    "text,lines", [("", 0), ("a", 1), ("a\n", 1), ("a\nb", 2), ("a\n\nb\n", 3)]
)
def test_line_count_matches_wc_l_style_counting(text, lines):
    assert rv.count_lines(text) == lines


# --- R13 --------------------------------------------------------------------------------------


def test_a_new_skill_over_the_critical_limit_is_a_critical_measurement_finding():
    (finding,) = rv.check_measurements(SKILL, _skill(lines=520), None)
    assert finding.rule == "r13-skillmd-line-count"
    assert finding.severity == "Critical" and finding.rule_class == "measurement"
    assert finding.source == "script" and finding.line is None
    assert "520" in finding.evidence


def test_a_skill_between_the_warning_and_critical_limits_is_a_major_finding():
    (finding,) = rv.check_measurements(SKILL, _skill(lines=495), None)
    assert finding.severity == "Major"


def test_weak_and_soft_warning_tiers_are_not_reported():
    assert rv.check_measurements(SKILL, _skill(lines=450), None) == ()


def test_a_value_that_does_not_get_worse_is_not_reported():
    same_tier = rv.check_measurements(SKILL, _skill(lines=530), _skill(lines=510))
    assert same_tier == ()
    better = rv.check_measurements(SKILL, _skill(lines=480), _skill(lines=520))
    assert better == ()
    shrunk_but_still_critical = rv.check_measurements(SKILL, _skill(lines=505), _skill(lines=900))
    assert shrunk_but_still_critical == ()


def test_crossing_a_threshold_is_reported_at_the_new_tier():
    (major,) = rv.check_measurements(SKILL, _skill(lines=495), _skill(lines=480))
    assert major.severity == "Major"
    (critical,) = rv.check_measurements(SKILL, _skill(lines=505), _skill(lines=495))
    assert critical.severity == "Critical" and "495" in critical.evidence


def test_a_script_measurement_blocks_where_a_model_one_would_not():
    (finding,) = rv.check_measurements(SKILL, _skill(lines=520), None)
    assert gate_decision(finding, in_diff=True).outcome == "block"


def test_the_line_count_does_not_need_readable_frontmatter():
    text = "---\nname: [unclosed\n---\n" + "body\n" * 520
    assert _rules(rv.check_measurements(SKILL, text, None)) == ["r13-skillmd-line-count"]


# --- R21 --------------------------------------------------------------------------------------


def _description_findings(description, base=None, extra="", base_extra=""):
    head = _skill(description=description, extra=extra)
    old = None if base is None else _skill(description=base, extra=base_extra)
    return rv.check_measurements(SKILL, head, old)


def test_a_too_long_description_is_critical_and_a_near_limit_one_is_major():
    (critical,) = _description_findings("d" * 1030)
    assert critical.rule == "r21-description-length" and critical.severity == "Critical"
    (major,) = _description_findings("d" * 1020)
    assert major.severity == "Major"


def test_a_too_short_description_is_reported():
    (critical,) = _description_findings("short")
    assert critical.severity == "Critical" and "5" in critical.evidence
    (major,) = _description_findings("d" * 50)
    assert major.severity == "Major"


def test_the_description_length_is_the_folded_value_not_the_raw_text():
    folded = "---\nname: demo\ndescription: >-\n  " + "\n  ".join(["x" * 40] * 3) + "\n---\n"
    assert rv.description_length(folded) == 40 * 3 + 2
    assert rv.description_length("---\nname: demo\n---\n") is None
    assert rv.description_length("no frontmatter\n") is None


def test_when_to_use_is_measured():
    (when,) = _description_findings(GOOD_DESCRIPTION, extra=f"when_to_use: {'w' * 520}\n")
    assert when.rule == "r21-description-length" and "when_to_use" in when.evidence
    assert _description_findings("d" * 1000, extra=f"when_to_use: {'w' * 400}\n") == ()


def test_the_combined_limit_adds_nothing_the_individual_limits_miss():
    # description <= 1018 and when_to_use <= 506 cannot pass 1524 together, so a combined overrun
    # always comes with an individual one and is not reported twice.
    findings = _description_findings("d" * 1018, extra=f"when_to_use: {'w' * 513}\n")
    assert [f.severity for f in findings] == ["Critical"]


def test_swapping_too_short_for_too_long_is_reported():
    (long_critical,) = _description_findings("d" * 5000, base="d" * 15)
    assert long_critical.severity == "Critical" and "5000" in long_critical.evidence
    (long_major,) = _description_findings("d" * 1020, base="d" * 50)
    assert long_major.severity == "Major"
    (short_critical,) = _description_findings("d" * 15, base="d" * 5000)
    assert short_critical.severity == "Critical"


def test_an_unchanged_description_tier_is_not_reported():
    assert _description_findings("d" * 1030, base="d" * 1040) == ()
    assert _description_findings("d" * 50, base="d" * 60) == ()


def test_a_skill_without_a_description_is_as_bad_as_an_empty_one():
    text = "---\nname: demo\n---\nbody\n"
    (finding,) = rv.check_measurements(SKILL, text, None)
    assert finding.rule == "r21-description-length" and finding.severity == "Critical"
    assert rv.check_measurements(SKILL, text, text) == ()  # already missing in the base


def test_deleting_the_description_is_reported_not_a_way_to_dodge_the_check():
    (finding,) = rv.check_measurements(SKILL, "---\nname: demo\n---\nbody\n", _skill())
    assert finding.severity == "Critical"


def test_an_unreadable_base_counts_as_clean_so_a_repair_is_still_checked():
    findings = rv.check_measurements(SKILL, _skill(description="d" * 1030), "no frontmatter\n")
    assert _rules(findings) == ["r21-description-length"]


def test_commands_and_agents_are_not_measured():
    big = _skill(lines=600)
    assert rv.check_measurements("plugins/demo-kit/commands/x.md", big, None) == ()
    assert rv.check_measurements("plugins/demo-kit/agents/x.md", big, None) == ()


@pytest.mark.parametrize(
    "extra",
    [
        "description: {again}\n",  # a repeated key
    ],
)
def test_a_repeated_description_key_is_unverifiable_not_clean(git_repo, extra):
    text = (
        "---\nname: demo\ndescription: "
        + "d" * 100
        + "\n"
        + extra.format(again="d" * 3000)
        + "---\nbody\n"
    )
    git_repo.write(SKILL, text)
    _commit(git_repo.root, "add")
    _, measures = rv.run_verifiers(
        git_repo.root, (ChangedPath(status="A", old_path=None, new_path=SKILL),)
    )
    assert _rules(measures.findings) == ["frontmatter-unverifiable"]


def test_a_non_string_description_is_unverifiable_not_clean(git_repo):
    git_repo.write(SKILL, "---\nname: demo\ndescription:\n  - " + "d" * 3000 + "\n---\nbody\n")
    _commit(git_repo.root, "add")
    _, measures = rv.run_verifiers(
        git_repo.root, (ChangedPath(status="A", old_path=None, new_path=SKILL),)
    )
    assert _rules(measures.findings) == ["frontmatter-unverifiable"]


# --- running over a change set ----------------------------------------------------------------


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_run_verifiers_returns_the_grant_and_measurement_outcomes(git_repo):
    git_repo.write(SKILL, _skill())
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, _skill(lines=520))
    _commit(git_repo.root, "grow")
    change = (ChangedPath(status="M", old_path=SKILL, new_path=SKILL),)
    grants, measures = rv.run_verifiers(git_repo.root, change, base)
    assert (grants.name, measures.name) == ("grant-to-body", "measurement")
    assert grants.findings == ()
    assert _rules(measures.findings) == ["r13-skillmd-line-count"]
    assert measures.checked == (SKILL,)


def test_run_verifiers_compares_with_the_base_of_a_renamed_file(git_repo):
    old = "plugins/demo-kit/skills/legacy/SKILL.md"
    git_repo.write(old, _skill(lines=520))
    base = _commit(git_repo.root, "base")
    (git_repo.root / SKILL).parent.mkdir(parents=True)
    (git_repo.root / old).rename(git_repo.root / SKILL)
    _commit(git_repo.root, "rename")
    change = (ChangedPath(status="R", old_path=old, new_path=SKILL),)
    _, measures = rv.run_verifiers(git_repo.root, change, base)
    assert measures.findings == ()


@pytest.mark.parametrize("base", ["--output=x", "HEAD", "main", "abc123", "-" + "a" * 39])
def test_a_base_that_is_not_a_full_object_id_is_refused(git_repo, base):
    git_repo.write(SKILL, _skill())
    _commit(git_repo.root, "add")
    change = (ChangedPath(status="M", old_path=SKILL, new_path=SKILL),)
    with pytest.raises(RuntimeError, match="object id"):
        rv.run_verifiers(git_repo.root, change, base)


def test_a_rename_from_a_large_non_skill_file_is_measured_as_new(git_repo):
    reference = "plugins/demo-kit/skills/demo/references/guide.md"
    git_repo.write(reference, "line\n" * 600)
    base = _commit(git_repo.root, "base")
    target = "plugins/demo-kit/skills/other/SKILL.md"
    (git_repo.root / target).parent.mkdir(parents=True)
    (git_repo.root / reference).rename(git_repo.root / target)
    _commit(git_repo.root, "inline the reference")
    change = (ChangedPath(status="R", old_path=reference, new_path=target),)
    _, measures = rv.run_verifiers(git_repo.root, change, base)
    assert "r13-skillmd-line-count" in _rules(measures.findings)


def test_a_skill_the_verifier_cannot_read_is_not_counted_as_measured(git_repo):
    (git_repo.root / SKILL).parent.mkdir(parents=True)
    git_repo.write("target.md", _skill())
    (git_repo.root / SKILL).symlink_to(git_repo.root / "target.md")
    _commit(git_repo.root, "add")
    change = (ChangedPath(status="A", old_path=None, new_path=SKILL),)
    grants, measures = rv.run_verifiers(git_repo.root, change)
    assert measures.checked == () and grants.checked == ()
    assert _rules(measures.findings) == ["frontmatter-unverifiable"]


def test_a_skill_with_unreadable_frontmatter_is_not_counted_as_measured(git_repo):
    git_repo.write(SKILL, "---\nname: [unclosed\n---\n" + "body\n" * 10)
    _commit(git_repo.root, "add")
    change = (ChangedPath(status="A", old_path=None, new_path=SKILL),)
    grants, measures = rv.run_verifiers(git_repo.root, change)
    assert measures.checked == () and grants.checked == ()
    assert _rules(measures.findings) == ["frontmatter-unverifiable"]


def test_an_unparseable_base_is_treated_as_unmeasured_so_a_bad_head_is_still_flagged():
    unparseable = "---\nname: [unclosed\n---\nbody\n"
    findings = rv.check_measurements(SKILL, _skill(description="d" * 1030), unparseable)
    assert _rules(findings) == ["r21-description-length"]
    assert rv.check_measurements(SKILL, _skill(), unparseable) == ()


def test_a_lone_carriage_return_is_a_line_break_for_the_line_count():
    assert rv.count_lines("a\rb\rc") == 3
    assert rv.count_lines("a\r\nb\r\n") == 2
    assert rv.count_lines("a\rb\n") == 2


def test_run_verifiers_without_a_base_treats_every_file_as_new(git_repo):
    git_repo.write(SKILL, _skill(lines=520))
    _commit(git_repo.root, "add")
    change = (ChangedPath(status="A", old_path=None, new_path=SKILL),)
    _, measures = rv.run_verifiers(git_repo.root, change)
    assert _rules(measures.findings) == ["r13-skillmd-line-count"]


# --- run-codex-review wiring ------------------------------------------------------------------

ROSTER = tuple(r.name for r in review_contract.ROSTER)
CLEAN = json.dumps(
    {
        "contract_version": "1",
        "dispatch": {
            "id": "d",
            "reviewer": "security-reviewer",
            "backend": "codex",
            "target_paths": [SKILL],
        },
        "provenance": {
            "provider": "openai",
            "model": "m",
            "cli_version": "9.9.9",
            "execution_profile": "read-only",
        },
        "findings": [],
        "verdict": "pass",
        "inspection_limits": [],
    }
).encode()


def _review(monkeypatch, git_repo, tmp_path, before: str, after: str):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    git_repo.write(SKILL, before)
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, after)
    _commit(git_repo.root, "change")
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base, "--output", str(out)])
    return rc, json.loads(out.read_text(encoding="utf-8"))


def test_a_pr_that_grows_a_skill_past_the_limit_is_blocked(monkeypatch, git_repo, tmp_path):
    rc, payload = _review(monkeypatch, git_repo, tmp_path, _skill(lines=480), _skill(lines=520))
    assert rc == 1
    (finding,) = payload["findings"]
    assert finding["rule"] == "r13-skillmd-line-count"
    assert finding["rule_class"] == "measurement" and finding["source"] == "script"
    assert finding["gate"] == "block"
    assert [v["name"] for v in payload["verifiers"]] == ["grant-to-body", "measurement"]


def test_a_pr_that_only_touches_an_already_oversized_skill_is_not_blocked(
    monkeypatch, git_repo, tmp_path
):
    before = _skill(lines=520)
    rc, payload = _review(monkeypatch, git_repo, tmp_path, before, before + "one more line\n")
    assert rc == 0 and payload["findings"] == []
