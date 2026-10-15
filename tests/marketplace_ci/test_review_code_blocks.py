"""The R18 verifier (issue #576, #568 Phase 2): fenced code blocks over 20 lines (Major) or 30
(Critical) in a skill, command or agent file, reported only when the PR adds or worsens one. The
repo already holds hundreds of blocks over 20 lines, so the comparison with the base is what keeps
the check from blocking PRs that never wrote them. Weak-warning blocks (11 to 20 lines) are not
reported, and a block with a recorded R18 exception note above it is exempt.
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
COMMAND = "plugins/demo-kit/commands/demo-run.md"
AGENT = "plugins/demo-kit/agents/demo-agent.md"
REFERENCE = "plugins/demo-kit/skills/demo/references/notes.md"


def _block(lines: int, fence: str = "```", info: str = "bash", tag: str = "x") -> str:
    body = "".join(f"{tag} {i}\n" for i in range(lines))
    return f"{fence}{info}\n{body}{fence}\n"


def _doc(*parts: str) -> str:
    return "# Title\n\n" + "\n".join(parts)


def _rules(findings):
    return [f.rule for f in findings]


def test_the_thresholds_equal_the_rulebook_settings():
    thresholds = json.loads(SETTINGS.read_text(encoding="utf-8"))["rules"][
        "R18_code_block_line_limit"
    ]["config"]["thresholds"]
    assert (rv.R18_WARNING, rv.R18_CRITICAL) == (thresholds["warning"], thresholds["critical"])


@pytest.mark.parametrize("lines,rank", [(10, 0), (20, 0), (21, 1), (30, 1), (31, 2), (200, 2)])
def test_the_block_tiers(lines, rank):
    assert rv.block_tier(lines) == rank


# --- the fence parser -------------------------------------------------------------------------


def test_a_backtick_and_a_tilde_block_are_found_with_their_content_size():
    blocks = rv.fenced_blocks(_doc(_block(3), _block(5, fence="~~~", info="")))
    assert [(b.start, b.size) for b in blocks] == [(3, 3), (9, 5)]


def test_a_longer_fence_holds_shorter_fences_as_content():
    text = "````markdown\n```bash\nls\n```\n````\n"
    (block,) = rv.fenced_blocks(text)
    assert block.size == 3 and block.end == 5


def test_a_closing_fence_must_be_long_enough_and_carry_no_text():
    text = "```bash\na\n``\n``` not a closer\nb\n```  \nafter\n"
    (block,) = rv.fenced_blocks(text)
    assert block.size == 4 and block.end == 6


def test_a_backtick_fence_whose_info_string_has_a_backtick_is_not_a_fence():
    # Line 1 is not an opener; the bare fence on line 3 is one, and CommonMark reads it that way.
    assert [b.start for b in rv.fenced_blocks("```a`b\ntext\n```\n")] == [3]
    assert rv.fenced_blocks("```a`b\ntext\n") == []


def test_an_unclosed_block_runs_to_the_end_of_the_file():
    (block,) = rv.fenced_blocks("```bash\na\nb\nc\n")
    assert block.size == 3 and block.closed is False


def test_an_indented_fence_inside_a_list_is_found_and_crlf_is_read():
    text = "- item\r\n    ```bash\r\n    a\r\n    b\r\n    ```\r\n"
    (block,) = rv.fenced_blocks(text)
    assert block.size == 2


def test_a_file_without_fences_has_no_blocks():
    assert rv.fenced_blocks("plain\ntext\n") == []


def test_a_closer_indented_four_or_more_columns_past_the_opener_is_content():
    text = "```\n" + "a\n" * 19 + "    ```\n    ```\n" + "b\n" * 19 + "```\n"
    (block,) = rv.fenced_blocks(text)
    assert block.size == 40


def test_a_fence_in_a_blockquote_is_a_block_closed_at_the_same_depth():
    text = "> ```bash\n" + "> x\n" * 40 + "> ```\n"
    (block,) = rv.fenced_blocks(text)
    assert block.size == 40
    other = "> ```bash\n> a\n```\n> b\n> ```\n"
    first = rv.fenced_blocks(other)[0]
    assert first.size == 1 and first.closed is False  # the unquoted line ended the quote


def test_a_fence_after_a_list_marker_is_a_block():
    text = "- ```bash\n" + "  x\n" * 40 + "  ```\n"
    (block,) = rv.fenced_blocks(text)
    assert block.size == 40


def test_a_lone_carriage_return_is_a_line_break():
    text = "```\r" + "x\r" * 40 + "```\n"
    (block,) = rv.fenced_blocks(text)
    assert block.size == 40


def test_a_quoted_fence_that_never_closes_does_not_swallow_the_blocks_after_it():
    """Once the quote ends the fence ends, so later real blocks are still counted."""
    before = _doc(_block(40))
    after = _doc("> ```", "", _block(40), _block(40, tag="n"), _block(40, tag="m"))
    (finding,) = rv.check_code_blocks(SKILL, after, before)
    assert finding.severity == "Critical" and "(40 lines)" in finding.evidence
    assert finding.evidence.startswith("2 fenced")


def test_a_list_item_fence_that_never_closes_ends_with_its_list_item():
    before = _doc(_block(40))
    after = _doc("- ~~~", "", _block(40), _block(40, tag="n"))
    (finding,) = rv.check_code_blocks(SKILL, after, before)
    assert finding.evidence.startswith("1 fenced") or finding.evidence.startswith("2 fenced")
    assert finding.severity == "Critical"


def test_the_parser_stays_linear_on_hostile_input():
    import time

    started = time.perf_counter()
    rv.fenced_blocks(" " * 200_000 + "x\n")
    rv.fenced_blocks(("```\n" + "a\n" * 21 + "```\n") * 20_000)
    rv.fenced_blocks("> " * 100_000 + "```\n")
    assert time.perf_counter() - started < 5


# --- findings ---------------------------------------------------------------------------------


def test_a_new_block_over_20_lines_is_a_major_measurement_finding():
    (finding,) = rv.check_code_blocks(SKILL, _doc(_block(25)), None)
    assert finding.rule == "r18-code-block-line-count" and finding.severity == "Major"
    assert finding.rule_class == "measurement" and finding.source == "script"
    assert finding.line is None and "line 3" in finding.evidence and "25" in finding.evidence
    assert gate_decision(finding, in_diff=True).outcome == "block"


def test_a_block_over_30_lines_is_critical():
    (finding,) = rv.check_code_blocks(SKILL, _doc(_block(31)), None)
    assert finding.severity == "Critical"


def test_weak_warning_blocks_are_not_reported():
    assert rv.check_code_blocks(SKILL, _doc(_block(11), _block(20)), None) == ()


def test_one_finding_per_file_lists_every_reported_block_at_the_worst_tier():
    doc = _doc(_block(25), _block(35, tag="y"), _block(12, tag="z"))
    (finding,) = rv.check_code_blocks(SKILL, doc, None)
    assert finding.severity == "Critical" and finding.line is None and finding.components == ()
    assert "line 3 (25 lines)" in finding.evidence and "(35 lines)" in finding.evidence
    assert "12 lines" not in finding.evidence


def test_an_identical_block_in_the_base_is_not_reported_even_when_it_moved():
    before = _doc("intro", _block(25))
    after = _doc("intro", "new paragraph", "another", _block(25))
    assert rv.check_code_blocks(SKILL, after, before) == ()


def test_a_block_edited_without_changing_its_tier_is_not_reported():
    assert rv.check_code_blocks(SKILL, _doc(_block(26)), _doc(_block(24, tag="y"))) == ()


def test_a_block_promoted_across_a_threshold_is_reported_at_the_new_tier():
    (finding,) = rv.check_code_blocks(SKILL, _doc(_block(35, tag="y")), _doc(_block(25)))
    assert finding.severity == "Critical"


def test_adding_a_second_large_block_is_reported_for_the_new_one_only():
    before = _doc(_block(25))
    after = _doc(_block(25), _block(24, tag="n"))
    (finding,) = rv.check_code_blocks(SKILL, after, before)
    assert "line 31" in finding.evidence and "line 3 " not in finding.evidence


def test_duplicating_a_block_is_reported_whichever_copy_is_matched():
    before = _doc("P", _block(40))
    after = _doc(_block(40), "P", _block(40))
    (finding,) = rv.check_code_blocks(SKILL, after, before)
    assert finding.line is None and gate_decision(finding, in_diff=True).outcome == "block"


def test_a_block_filled_in_the_middle_is_the_prs_even_if_its_fences_are_untouched(
    monkeypatch, git_repo, tmp_path
):
    before = _skill(_doc(_block(25)))
    inner = "".join(f"added {i}\n" for i in range(230))
    after = before.replace("x 12\n", "x 12\n" + inner)
    rc, payload = _review(monkeypatch, git_repo, tmp_path, before, after)
    assert rc == 1
    (finding,) = [f for f in payload["findings"] if f["rule"] == "r18-code-block-line-count"]
    assert finding["gate"] == "block" and finding["severity"] == "Critical"


def test_the_count_comparison_is_linear_in_the_number_of_blocks():
    import time

    text = _doc(*[_block(21, tag=str(i)) for i in range(20_000)])
    started = time.perf_counter()
    rv.check_code_blocks(SKILL, text, None)
    assert time.perf_counter() - started < 5


def test_removing_or_shrinking_blocks_is_never_reported():
    assert rv.check_code_blocks(SKILL, _doc(_block(5)), _doc(_block(40))) == ()


# --- a note typed by the PR cannot waive the check ---------------------------------------------


def test_a_note_typed_above_a_new_block_does_not_exempt_it():
    """Honoring the rulebook's in-file `R18 exception` note would let a PR waive its own finding.
    Only the Tier-1 exceptions registry may suppress a script finding."""
    note = "**Output** (R18 exception: a worked before/after pair; splitting it breaks it)"
    assert len(rv.check_code_blocks(SKILL, _doc(note, "", _block(40)), None)) == 1


def test_an_existing_noted_block_that_is_edited_is_not_reported_as_worse():
    note = "R18 exception: intentional whole example"
    before = _doc(note, "", _block(40))
    after = _doc(note, "", _block(45, tag="z"))
    assert rv.check_code_blocks(SKILL, after, before) == ()


def test_the_remediation_points_at_the_registry_not_at_a_note():
    (finding,) = rv.check_code_blocks(SKILL, _doc(_block(40)), None)
    assert "review_exceptions.yaml" in finding.remediation


# --- scope ------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", [SKILL, COMMAND, AGENT])
def test_skills_commands_and_agents_are_measured(path):
    assert len(rv.check_code_blocks(path, _doc(_block(40)), None)) == 1


@pytest.mark.parametrize("path", [REFERENCE, "docs/ci.md", "plugins/demo-kit/README.md"])
def test_other_files_are_not_measured(path):
    assert rv.check_code_blocks(path, _doc(_block(40)), None) == ()


# --- running over a change set ----------------------------------------------------------------


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _skill(body: str) -> str:
    return "---\nname: demo\ndescription: " + "d" * 100 + "\n---\n" + body


def test_run_verifiers_measures_commands_and_agents_too(git_repo):
    git_repo.write(COMMAND, _doc(_block(40)))
    git_repo.write(AGENT, _doc(_block(25)))
    _commit(git_repo.root, "add")
    change = tuple(ChangedPath("A", None, p) for p in (AGENT, COMMAND))
    _, measures, _ = rv.run_verifiers(git_repo.root, change)
    assert sorted(_rules(measures.findings)) == ["r18-code-block-line-count"] * 2
    assert measures.checked == (AGENT, COMMAND)


def test_a_rename_from_a_non_component_file_has_no_block_base(git_repo):
    git_repo.write(REFERENCE, _doc(_block(40)))
    base = _commit(git_repo.root, "base")
    (git_repo.root / SKILL).parent.mkdir(parents=True, exist_ok=True)
    (git_repo.root / REFERENCE).rename(git_repo.root / SKILL)
    _commit(git_repo.root, "inline")
    change = (ChangedPath("R", REFERENCE, SKILL),)
    _, measures, _ = rv.run_verifiers(git_repo.root, change, base)
    assert "r18-code-block-line-count" in _rules(measures.findings)


def test_a_rename_between_components_keeps_the_block_base(git_repo):
    legacy = "plugins/demo-kit/skills/legacy/SKILL.md"
    git_repo.write(legacy, _skill(_doc(_block(40))))
    base = _commit(git_repo.root, "base")
    (git_repo.root / SKILL).parent.mkdir(parents=True, exist_ok=True)
    (git_repo.root / legacy).rename(git_repo.root / SKILL)
    _commit(git_repo.root, "move")
    change = (ChangedPath("R", legacy, SKILL),)
    _, measures, _ = rv.run_verifiers(git_repo.root, change, base)
    assert "r18-code-block-line-count" not in _rules(measures.findings)


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


def test_editing_only_inside_a_block_to_push_it_past_30_lines_blocks(
    monkeypatch, git_repo, tmp_path
):
    before = _skill(_doc(_block(25)))
    after = _skill(_doc(_block(35, tag="y")))
    rc, payload = _review(monkeypatch, git_repo, tmp_path, before, after)
    assert rc == 1
    (finding,) = [f for f in payload["findings"] if f["rule"] == "r18-code-block-line-count"]
    assert finding["severity"] == "Critical" and finding["gate"] == "block"


def test_touching_a_file_that_already_has_a_large_block_does_not_block(
    monkeypatch, git_repo, tmp_path
):
    before = _skill(_doc(_block(40)))
    after = before + "one more line of prose\n"
    rc, payload = _review(monkeypatch, git_repo, tmp_path, before, after)
    assert rc == 0 and payload["findings"] == []
