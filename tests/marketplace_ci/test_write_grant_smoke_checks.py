"""Four skills' smoke tests reject unscoped or inert file-write grants (#587).

A bare `Write` or `Edit` lets a skill overwrite any file without a prompt, and `Write(<glob>)` was
accepted but never matched in a probe (Claude Code 2.1.302, Linux, default permission mode). Each
smoke test's `check_file_write_grants_scoped` must accept only its exact pinned `Edit(...)` set, so
these tests feed it frontmatter variants, including YAML spellings and escapes that hide a tool name
from a plain text match, and check that each unsafe or drifted variant fails.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = "Edit(//tmp/claude-*/*/*/scratchpad/**)"

# (smoke test path, pinned grants, allowed-tools separator, other grants that must not matter)
CASES = {
    "reviewing-analysis-findings": (
        "plugins/analysis-kit/skills/reviewing-analysis-findings/scripts/smoke_test.py",
        [SCRATCH],
        " ",
        "Read Glob AskUserQuestion Bash(python */analysis-kit/scripts/anls_comparator.py:*)",
    ),
    "mining-review-learnings": (
        "plugins/analysis-kit/skills/mining-review-learnings/scripts/smoke_test.py",
        [SCRATCH],
        " ",
        "Read Glob Grep AskUserQuestion Bash(gh pr list:*)",
    ),
    "managing-review-learnings": (
        "plugins/analysis-kit/skills/managing-review-learnings/scripts/smoke_test.py",
        [SCRATCH, "Edit(issues/**)"],
        " ",
        "Read Grep Glob AskUserQuestion Skill(git-kit:github-issue-lifecycle) Bash(date:*)",
    ),
    "github-issue-creator": (
        "plugins/git-kit/skills/github-issue-creator/scripts/smoke_test.py",
        ["Edit(issues/**)"],
        ", ",
        "Read",
    ),
}


def _load(name):
    spec = importlib.util.spec_from_file_location(f"smoke_{name}", ROOT / CASES[name][0])
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _skill(tmp_path, name, grants):
    sep, rest = CASES[name][2], CASES[name][3]
    path = tmp_path / "SKILL.md"
    path.write_text(
        f"---\nname: x\ndescription: y\nallowed-tools: {sep.join([rest, *grants])}\n---\nbody\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("name", CASES)
def test_the_real_skill_passes(name):
    ok, message = _load(name).check_file_write_grants_scoped()
    assert ok, message


@pytest.mark.parametrize("name", CASES)
def test_the_pinned_set_passes_in_any_order(tmp_path, name):
    ok, message = _load(name).check_file_write_grants_scoped(
        _skill(tmp_path, name, list(reversed(CASES[name][1])))
    )
    assert ok, message


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize(
    "extra",
    [
        "Write",
        "Edit",
        "MultiEdit",
        "NotebookEdit",
        "Write(issues/**)",
        "Write(//tmp/claude-*/*/*/scratchpad/**)",
        "Edit(**)",
        "Edit(.claude/**)",
    ],
)
def test_an_added_unscoped_or_inert_grant_fails(tmp_path, name, extra):
    ok, message = _load(name).check_file_write_grants_scoped(
        _skill(tmp_path, name, [*CASES[name][1], extra])
    )
    assert not ok, message


@pytest.mark.parametrize("name", CASES)
def test_a_missing_or_replaced_grant_fails(tmp_path, name):
    module = _load(name)
    pinned = CASES[name][1]
    assert not module.check_file_write_grants_scoped(_skill(tmp_path, name, pinned[1:]))[0]
    assert not module.check_file_write_grants_scoped(_skill(tmp_path, name, ["Write"]))[0]


@pytest.mark.parametrize("name", CASES)
def test_a_bare_write_in_place_of_the_scoped_rule_fails(tmp_path, name):
    ok, message = _load(name).check_file_write_grants_scoped(_skill(tmp_path, name, ["Write"]))
    assert not ok
    assert "differ from the pinned set" in message


def _raw(tmp_path, frontmatter):
    path = tmp_path / "SKILL.md"
    path.write_text(f"---\nname: x\ndescription: y\n{frontmatter}\n---\nbody\n", encoding="utf-8")
    return path


def _pinned(name):
    return " ".join(CASES[name][1])


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize(
    "spelling",
    [
        "allowed-tools: [Read, {pinned}, Write]",
        "allowed-tools: [Read, {pinned}, 'Write']",
        'allowed-tools: "Read {pinned} Write"',
        "allowed-tools: Read {pinned}\n  Write",
        "allowed-tools: Read {pinned}\n  Edit",
        "allowed-tools:\n  - Read\n  - Write",
        "allowed-tools:\n- Read\n- Write",
        "allowed-tools: >-\n  Read {pinned}\n  Write",
        "allowed-tools: Read {pinned}\nallowed-tools: Read",
        'allowed-tools: "Read {pinned} Wri\\u0074e"',
        'allowed-tools: "Read {pinned} \\u0057rite"',
        'allowed-tools: "Read {pinned} Ed\\u0069t(**)"',
        'allowed-tools: "Read {pinned} \\x57rite"',
        'allowed-tools: Read {pinned}\n  "Wri\\u0074e"',
        "allowed-tools: Read {pinned}\n\n  Write",
        "allowed-tools: >-\n  Read {pinned}\n\n  Write",
        "allowed-tools: Read {pinned}\n\n\n  Edit(**)",
        "allowed-tools: [Read, {pinned}, *x]",
        "allowed-tools: Read {pinned} &x Write",
        "allowed-tools: Read {pinned} !!str Write",
        # A multi-line value is unsupported even when the pinned set alone would pass.
        "allowed-tools: Read {pinned}\n  AskUserQuestion",
        "allowed-tools: >-\n  Read {pinned}",
    ],
)
def test_a_hidden_extra_grant_in_another_yaml_spelling_fails(tmp_path, name, spelling):
    ok, message = _load(name).check_file_write_grants_scoped(
        _raw(
            tmp_path,
            spelling.format(
                pinned=_pinned(name).replace(" ", ", ")
                if spelling.startswith("allowed-tools: [")
                else _pinned(name)
            ),
        )
    )
    assert not ok, message


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize(
    "spelling",
    [
        "allowed-tools: [Read, {pinned}]",
        'allowed-tools: "Read {pinned}"',
        "allowed-tools: Read {pinned}\nargument-hint: [x]",
        "allowed-tools: Read {pinned}\n\nargument-hint: [x]",
    ],
)
def test_the_pinned_set_passes_in_other_yaml_spellings(tmp_path, name, spelling):
    ok, message = _load(name).check_file_write_grants_scoped(
        _raw(
            tmp_path,
            spelling.format(
                pinned=_pinned(name).replace(" ", ", ")
                if spelling.startswith("allowed-tools: [")
                else _pinned(name)
            ),
        )
    )
    assert ok, message


@pytest.mark.parametrize("name", CASES)
def test_a_skill_without_allowed_tools_fails(tmp_path, name):
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: x\ndescription: y\n---\nbody\n", encoding="utf-8")
    ok, _ = _load(name).check_file_write_grants_scoped(path)
    assert not ok
