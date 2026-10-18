"""The R37 verifier (issue #576, #568 Phase 2): `r37-executable-bit`.

A script that a skill or command runs directly by path, because its `allowed-tools` grant starts
with `${CLAUDE_PLUGIN_ROOT}/...` or `${CLAUDE_SKILL_DIR}/...`, must be committed with git mode
100755; a shell running a 100644 path fails with `Permission denied`. An interpreter that pins the
script (`bash ${...}/x.sh`) does not need the bit. The real tree has no violation today, so this
guards against a repeat.
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

SKILL = "plugins/demo-kit/skills/demo/SKILL.md"
COMMAND = "plugins/demo-kit/commands/demo-run.md"
PLUGIN_SCRIPT = "plugins/demo-kit/scripts/tool.sh"
SKILL_SCRIPT = "plugins/demo-kit/skills/demo/scripts/local.sh"


def _doc(*grants: str, key: str = "allowed-tools") -> str:
    return (
        "---\nname: demo\ndescription: " + "d" * 100 + f"\n{key}: {' '.join(grants)}\n---\nbody\n"
    )


def _grants(path, text):
    root, block = rv._frontmatter(text)
    return rv.script_grants(path, root, block)


# --- which grants name a directly-run script ----------------------------------------------------


def test_a_plugin_root_and_a_skill_dir_script_are_resolved():
    text = _doc(
        "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(${CLAUDE_SKILL_DIR}/scripts/local.sh --dry-run:*)",
    )
    assert [g.script for g in _grants(SKILL, text)] == [PLUGIN_SCRIPT, SKILL_SCRIPT]
    assert [g.line for g in _grants(SKILL, text)] == [4, 4]


def test_a_command_file_resolves_its_skill_dir_to_nothing_and_its_plugin_root_normally():
    text = _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)")
    assert [g.script for g in _grants(COMMAND, text)] == [PLUGIN_SCRIPT]
    assert _grants(COMMAND, _doc("Bash(${CLAUDE_SKILL_DIR}/scripts/local.sh:*)")) == []


@pytest.mark.parametrize(
    "grant",
    [
        # an interpreter runs these, so no executable bit is needed
        "Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(python3 -I ${CLAUDE_SKILL_DIR}/scripts/local.py:*)",
        "Bash(git:*)",
        "Bash(*/scan.sh:*)",
        "Bash(${CLAUDE_PROJECT_DIR}/.claude/scripts/x.py:*)",
        "Bash(${CLAUDE_PLUGIN_ROOT}/../outside.sh:*)",
        "Read",
    ],
)
def test_other_grants_name_no_directly_run_script(grant):
    assert _grants(SKILL, _doc(grant)) == []


def test_a_script_grant_in_an_agent_or_a_mirror_copy_is_out_of_scope():
    text = _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)")
    assert _grants("plugins/demo-kit/agents/a.md", text) == []
    assert _grants(".claude/skills/demo/SKILL.md", text) == []


def test_a_skill_dir_grant_that_climbs_to_the_plugin_scripts_is_resolved():
    text = _doc("Bash(${CLAUDE_SKILL_DIR}/../../scripts/tool.sh:*)")
    assert [g.script for g in _grants(SKILL, text)] == [PLUGIN_SCRIPT]


@pytest.mark.parametrize(
    "grant",
    [
        'Bash("${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh":*)',
        'Bash("${CLAUDE_PLUGIN_ROOT}"/scripts/tool.sh:*)',
        "Bash($CLAUDE_PLUGIN_ROOT/scripts/tool.sh:*)",
        "Bash(env ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(exec ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh --x:*)",
    ],
)
def test_quoted_unbraced_and_wrapped_forms_of_a_direct_run_are_read(grant):
    assert [g.script for g in _grants(SKILL, _doc(grant))] == [PLUGIN_SCRIPT]


def test_a_glob_grant_names_no_single_script():
    assert _grants(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/*:*)")) == []


# --- findings ----------------------------------------------------------------------------------


def _finding(modes, grants=None):
    text = _doc(*(grants or ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"]))
    return rv.check_executable_bits(SKILL, _grants(SKILL, text), modes)


def test_a_non_executable_script_is_a_critical_graph_finding_on_the_grant_line():
    (finding,) = _finding({PLUGIN_SCRIPT: b"100644"})
    assert finding.rule == "r37-executable-bit" and finding.severity == "Critical"
    assert finding.rule_class == "graph" and finding.source == "script"
    assert finding.line == 4 and finding.components == (PLUGIN_SCRIPT,)
    assert "100755" in finding.remediation and "100644" in finding.evidence
    assert gate_decision(finding, in_diff=True).outcome == "block"


def test_an_executable_script_is_clean():
    assert _finding({PLUGIN_SCRIPT: b"100755"}) == ()


@pytest.mark.parametrize(
    "mode,words",
    [
        (b"120000", "symlink"),
        (b"160000", "submodule"),
        (b"040000", "directory"),
    ],
)
def test_a_granted_path_that_is_not_a_regular_executable_file_is_reported(mode, words):
    (finding,) = _finding({PLUGIN_SCRIPT: mode})
    assert words in finding.evidence and finding.severity == "Critical"


def test_a_granted_script_missing_from_the_tree_is_reported_as_the_rule_says():
    (finding,) = _finding({})
    assert "does not exist" in finding.evidence and finding.components == (PLUGIN_SCRIPT,)


def test_each_grant_line_of_a_bad_script_is_pinned_so_a_new_line_is_never_hidden():
    text = (
        "---\nname: demo\nallowed-tools:\n"
        "  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)\n"
        "  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh --x:*)\n---\n"
    )
    findings = rv.check_executable_bits(SKILL, _grants(SKILL, text), {PLUGIN_SCRIPT: b"100644"})
    assert [f.line for f in findings] == [4, 5]


# --- running over a change set -----------------------------------------------------------------


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _write_script(git_repo, rel, executable):
    path = git_repo.write(rel, "#!/bin/sh\necho hi\n")
    path.chmod(0o755 if executable else 0o644)


def _outcome(git_repo, changed, base=None):
    outcomes = rv.run_verifiers(git_repo.root, changed, base)
    return next(o for o in outcomes if o.name == "structure")


def test_run_verifiers_reports_a_new_skill_whose_script_is_not_executable(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=False)
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    _commit(git_repo.root, "add")
    outcome = _outcome(git_repo, (ChangedPath("A", None, SKILL),))
    assert [f.rule for f in outcome.findings] == ["r37-executable-bit"]
    assert outcome.checked == (SKILL,)


def test_run_verifiers_is_clean_when_the_script_is_executable(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    _commit(git_repo.root, "add")
    assert _outcome(git_repo, (ChangedPath("A", None, SKILL),)).findings == ()


def test_dropping_the_executable_bit_is_caught_even_though_the_skill_is_untouched(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    base = _commit(git_repo.root, "base")
    (git_repo.root / PLUGIN_SCRIPT).chmod(0o644)
    _commit(git_repo.root, "chmod")
    outcome = _outcome(git_repo, (ChangedPath("M", PLUGIN_SCRIPT, PLUGIN_SCRIPT),), base)
    (finding,) = outcome.findings
    assert finding.path == SKILL and finding.components == (PLUGIN_SCRIPT,)


def test_a_command_file_and_a_skill_local_script_are_checked_too(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=False)
    _write_script(git_repo, SKILL_SCRIPT, executable=False)
    git_repo.write(COMMAND, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_SKILL_DIR}/scripts/local.sh:*)"))
    _commit(git_repo.root, "add")
    outcome = _outcome(git_repo, (ChangedPath("A", None, SKILL), ChangedPath("A", None, COMMAND)))
    assert sorted(f.path for f in outcome.findings) == [COMMAND, SKILL]


def test_running_out_of_the_read_budget_fails_closed_instead_of_skipping_docs(
    monkeypatch, git_repo
):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    for index in range(3):
        git_repo.write(
            f"plugins/demo-kit/skills/s{index}/SKILL.md",
            _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"),
        )
    _commit(git_repo.root, "add")
    monkeypatch.setattr(rv, "MAX_TOTAL_BYTES", 300)
    with pytest.raises(RuntimeError, match="budget"):
        rv.run_verifiers(git_repo.root, (ChangedPath("M", PLUGIN_SCRIPT, PLUGIN_SCRIPT),), "0" * 40)


def test_an_unreadable_doc_in_a_touched_plugin_is_reported_not_skipped(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    git_repo.write("elsewhere.md", "x")
    (git_repo.root / "plugins/demo-kit/skills/linked").mkdir(parents=True)
    (git_repo.root / "plugins/demo-kit/skills/linked/SKILL.md").symlink_to(
        git_repo.root / "elsewhere.md"
    )
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    _commit(git_repo.root, "add")
    outcome = _outcome(git_repo, (ChangedPath("A", None, SKILL),))
    paths = [f.path for f in outcome.findings]
    assert paths == ["plugins/demo-kit/skills/linked/SKILL.md"]
    assert outcome.findings[0].line is None


def test_a_path_segment_of_dots_does_not_widen_the_enumeration(git_repo):
    git_repo.write("README.md", "x")
    _commit(git_repo.root, "add")
    changed = (ChangedPath("A", None, "plugins/../README.md"),)
    assert _outcome(git_repo, changed).checked == ()


def test_a_pr_that_touches_no_plugin_reads_nothing(git_repo):
    git_repo.write("README.md", "x")
    _commit(git_repo.root, "add")
    outcome = _outcome(git_repo, (ChangedPath("A", None, "README.md"),))
    assert outcome.findings == () and outcome.checked == ()


def test_an_unreadable_skill_in_a_touched_plugin_does_not_hide_the_others(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=False)
    git_repo.write("plugins/demo-kit/skills/broken/SKILL.md", "---\nname: [unclosed\n---\n")
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    _commit(git_repo.root, "add")
    outcome = _outcome(git_repo, (ChangedPath("A", None, SKILL),))
    assert sorted(f.path for f in outcome.findings) == [
        "plugins/demo-kit/skills/broken/SKILL.md",
        SKILL,
    ]
    assert {f.rule for f in outcome.findings} == {"r37-executable-bit"}


# A security pass found that a chmod-only PR passed unseen when an unchanged grant document of the
# plugin could not be read: the skipped document might hold the very grant the chmod breaks.

BROKEN = "plugins/demo-kit/skills/broken/SKILL.md"


def _broken_doc(git_repo, symlink=False):
    if symlink:
        git_repo.write("elsewhere.md", "x")
        (git_repo.root / "plugins/demo-kit/skills/broken").mkdir(parents=True)
        (git_repo.root / BROKEN).symlink_to(git_repo.root / "elsewhere.md")
    else:
        git_repo.write(BROKEN, "---\nname: [unclosed\n---\n")


@pytest.mark.parametrize("symlink", [False, True])
def test_an_unreadable_unchanged_doc_is_reported_and_cites_the_plugins_changed_paths(
    git_repo, symlink
):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    _broken_doc(git_repo, symlink)
    base = _commit(git_repo.root, "base")
    (git_repo.root / PLUGIN_SCRIPT).chmod(0o644)
    _commit(git_repo.root, "chmod")
    outcome = _outcome(git_repo, (ChangedPath("M", PLUGIN_SCRIPT, PLUGIN_SCRIPT),), base)
    (finding,) = outcome.findings
    assert finding.rule == "r37-executable-bit" and finding.path == BROKEN
    assert finding.line is None and finding.components == (f"{PLUGIN_SCRIPT}:*",)
    assert BROKEN not in outcome.checked


def test_a_changed_doc_the_grant_verifier_already_refuses_is_not_reported_twice(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    _broken_doc(git_repo)
    _commit(git_repo.root, "add")
    outcome = _outcome(git_repo, (ChangedPath("A", None, BROKEN),))
    assert outcome.findings == ()


def test_a_plugin_with_too_many_changes_to_cite_fails_closed_when_a_doc_is_unreadable(git_repo):
    _broken_doc(git_repo)
    _commit(git_repo.root, "add")
    changed = tuple(
        ChangedPath("M", f"plugins/demo-kit/scripts/s{n}.sh", f"plugins/demo-kit/scripts/s{n}.sh")
        for n in range(rv.MAX_CITED_PATHS + 1)
    )
    with pytest.raises(RuntimeError, match="too many"):
        rv.run_verifiers(git_repo.root, changed, "0" * 40)


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


def test_a_chmod_alone_blocks_the_run(monkeypatch, git_repo, tmp_path):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    base = _commit(git_repo.root, "base")
    (git_repo.root / PLUGIN_SCRIPT).chmod(0o644)
    _commit(git_repo.root, "chmod")
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base, "--output", str(out)])
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 1
    (finding,) = [f for f in payload["findings"] if f["rule"] == "r37-executable-bit"]
    assert finding["gate"] == "block" and finding["severity"] == "Critical"


def test_a_chmod_alone_blocks_the_run_even_when_an_unchanged_doc_cannot_be_read(
    monkeypatch, git_repo, tmp_path
):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    _broken_doc(git_repo)
    base = _commit(git_repo.root, "base")
    (git_repo.root / PLUGIN_SCRIPT).chmod(0o644)
    _commit(git_repo.root, "chmod")
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base, "--output", str(out)])
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 1
    (finding,) = [f for f in payload["findings"] if f["rule"] == "r37-executable-bit"]
    assert finding["gate"] == "block" and finding["path"] == BROKEN


def test_an_unreadable_unchanged_doc_blocks_even_when_the_plugin_change_is_an_ordinary_edit(
    monkeypatch, git_repo, tmp_path
):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    _broken_doc(git_repo)
    base = _commit(git_repo.root, "base")
    edited = git_repo.write(PLUGIN_SCRIPT, "#!/bin/sh\necho an ordinary content edit\n")
    edited.chmod(0o755)
    _commit(git_repo.root, "edit the script's content only")
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base, "--output", str(out)])
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 1
    (finding,) = [f for f in payload["findings"] if f["rule"] == "r37-executable-bit"]
    assert finding["gate"] == "block" and finding["path"] == BROKEN


# --- wrappers, trailing colons and `:N` names ----------------------------------------------------


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(env FOO=1 ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(env -i ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(command -p ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(exec -a name ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(env exec ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(FOO=1 ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:)",
    ],
)
def test_stacked_wrappers_options_and_assignments_do_not_hide_a_direct_run(grant):
    assert [g.script for g in _grants(SKILL, _doc(grant))] == [PLUGIN_SCRIPT]


def test_a_wrapper_with_an_interpreter_after_it_still_names_no_script():
    text = _doc("Bash(env FOO=1 bash ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)")
    assert _grants(SKILL, text) == []


def test_a_script_name_ending_in_a_colon_and_digits_is_cited_as_a_whole_path():
    script = "plugins/demo-kit/scripts/run.sh:7"
    (finding,) = rv.check_executable_bits(SKILL, [rv.ScriptGrant(script, 4)], {script: b"100644"})
    assert finding.components == (f"{script}{rv.ANY_CHANGE_SUFFIX}",)


def test_an_ordinary_script_name_is_cited_bare():
    (finding,) = rv.check_executable_bits(
        SKILL, [rv.ScriptGrant(PLUGIN_SCRIPT, 4)], {PLUGIN_SCRIPT: b"100644"}
    )
    assert finding.components == (PLUGIN_SCRIPT,)


# --- a grant inside a multi-line scalar ------------------------------------------

_MULTILINE_GRANT = (
    "---\nname: demo\ndescription: " + "d" * 100 + "\nallowed-tools:\n  Read,\n"
    "  Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)\n---\n"
)


def test_a_multi_line_grant_the_pr_did_not_touch_is_not_blamed_on_an_unrelated_edit(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=False)
    git_repo.write(SKILL, _MULTILINE_GRANT + "body\n")
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, _MULTILINE_GRANT + "changed body\n")
    _commit(git_repo.root, "edit")
    assert _outcome(git_repo, (ChangedPath("M", SKILL, SKILL),), base).findings == ()


def test_a_multi_line_grant_is_reported_when_the_pr_drops_the_scripts_bit(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=True)
    git_repo.write(SKILL, _MULTILINE_GRANT + "body\n")
    base = _commit(git_repo.root, "base")
    (git_repo.root / PLUGIN_SCRIPT).chmod(0o644)
    git_repo.write(SKILL, _MULTILINE_GRANT + "changed body\n")
    _commit(git_repo.root, "chmod and edit")
    changed = (ChangedPath("M", SKILL, SKILL), ChangedPath("M", PLUGIN_SCRIPT, PLUGIN_SCRIPT))
    assert len(_outcome(git_repo, changed, base).findings) == 1


def test_a_multi_line_grant_added_by_the_pr_is_reported(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=False)
    git_repo.write(SKILL, _doc("Read") + "body\n")
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, _MULTILINE_GRANT + "body\n")
    _commit(git_repo.root, "add grant")
    assert len(_outcome(git_repo, (ChangedPath("M", SKILL, SKILL),), base).findings) == 1


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(env --unset NAME ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(env --chdir DIR ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(env --unset=NAME ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(nohup ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(nice -n 5 ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
    ],
)
def test_long_options_with_a_separate_value_and_more_wrappers_do_not_hide_a_direct_run(grant):
    assert [g.script for g in _grants(SKILL, _doc(grant))] == [PLUGIN_SCRIPT]


def test_a_new_multi_line_grant_of_a_script_the_base_already_granted_is_reported(git_repo):
    _write_script(git_repo, PLUGIN_SCRIPT, executable=False)
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)") + "body\n")
    base = _commit(git_repo.root, "base")
    git_repo.write(
        SKILL,
        "---\nname: demo\ndescription: " + "d" * 100 + "\nallowed-tools:\n  Read,\n"
        "  Bash(env ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)\n---\nbody\n",
    )
    _commit(git_repo.root, "add a second grant")
    assert len(_outcome(git_repo, (ChangedPath("M", SKILL, SKILL),), base).findings) == 1


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(/usr/bin/env ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(/usr/bin/env FOO=1 ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
        "Bash(/bin/nice -n 5 ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)",
    ],
)
def test_a_wrapper_given_by_its_absolute_path_does_not_hide_a_direct_run(grant):
    assert [g.script for g in _grants(SKILL, _doc(grant))] == [PLUGIN_SCRIPT]


def test_a_plugin_script_that_is_named_like_a_wrapper_is_still_a_direct_run():
    text = _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/env:*)")
    assert [g.script for g in _grants(SKILL, text)] == ["plugins/demo-kit/scripts/env"]


def test_a_quoted_wrapper_name_does_not_hide_a_direct_run():
    text = _doc('Bash("env" ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)')
    assert [g.script for g in _grants(SKILL, text)] == [PLUGIN_SCRIPT]


def test_a_wrapper_option_that_hides_the_program_makes_the_grant_unverifiable():
    text = _doc("Bash(env -S ${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)")
    with pytest.raises(rv.VerifierError):
        _grants(SKILL, text)


# --- script_coverage: what the gate may weigh a model R37 claim against (#613, #615) -------------


def _commit_with_mirrors(root: Path) -> str:
    """Like `_commit`, but forces `.claude/` in: a global gitignore can exclude it."""
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    return _commit(root, "add")


CMD_MIRROR = ".claude/commands/demo-run.md"
SKILL_MIRROR = ".claude/skills/demo/SKILL.md"
GOOD_GRANT = "Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tool.py:*)"


def _coverage(git_repo, *paths):
    outcomes = rv.run_verifiers(git_repo.root, tuple(ChangedPath("A", None, p) for p in paths))
    return rv.script_coverage(git_repo.root, outcomes)


def test_a_fully_resolved_clean_document_and_its_identical_mirror_are_covered(git_repo):
    text = _doc(GOOD_GRANT)
    git_repo.write(SKILL, text)
    git_repo.write(SKILL_MIRROR, text)
    _commit_with_mirrors(git_repo.root)
    coverage = _coverage(git_repo, SKILL)
    assert coverage.covers("R37", SKILL) and coverage.covers("R37", SKILL_MIRROR)


def test_a_mirror_that_differs_from_its_canonical_file_is_not_covered(git_repo):
    git_repo.write(SKILL, _doc(GOOD_GRANT))
    git_repo.write(SKILL_MIRROR, _doc("Bash(${CLAUDE_PROJECT_DIR}/.claude/scripts/x.sh:*)"))
    _commit_with_mirrors(git_repo.root)
    coverage = _coverage(git_repo, SKILL)
    assert coverage.covers("R37", SKILL) and not coverage.covers("R37", SKILL_MIRROR)


def test_a_command_mirror_is_covered_under_dot_claude_commands(git_repo):
    text = _doc(GOOD_GRANT)
    git_repo.write(COMMAND, text)
    git_repo.write(CMD_MIRROR, text)
    _commit_with_mirrors(git_repo.root)
    assert _coverage(git_repo, COMMAND).covers("R37", CMD_MIRROR)


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(${CLAUDE_PROJECT_DIR}/.claude/scripts/x.sh:*)",  # a path form the scan skips
        "Bash(./local.sh:*)",
        "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/*.sh:*)",  # a glob
        "Bash(${CLAUDE_PLUGIN_ROOT}/../other/x.sh:*)",  # leaves its plugin
    ],
)
def test_a_document_with_a_grant_the_scan_cannot_resolve_is_not_covered(git_repo, grant):
    git_repo.write(SKILL, _doc(GOOD_GRANT, grant))
    _commit_with_mirrors(git_repo.root)
    assert not _coverage(git_repo, SKILL).covers("R37", SKILL)


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(timeout 30 ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",  # a wrapper the scan does not know
        "Bash(sudo ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
        "Bash(xargs ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
        "Bash(bash -c ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",  # a command string runs the path
        "Bash(sh -c ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
    ],
)
def test_a_wrapper_or_command_string_that_runs_a_path_leaves_no_coverage(git_repo, grant):
    git_repo.write(SKILL, _doc(grant))
    _commit_with_mirrors(git_repo.root)
    assert not _coverage(git_repo, SKILL).covers("R37", SKILL)


@pytest.mark.parametrize(
    "grant",
    [
        'Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/demo/scripts/x.py":*)',  # the #615 shape
        "Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/x.py:*)",
        "Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
        "Bash(node ${CLAUDE_PLUGIN_ROOT}/scripts/x.js:*)",
        "Bash(git status:*)",
    ],
)
def test_a_plain_interpreter_grant_keeps_the_document_covered(git_repo, grant):
    git_repo.write(SKILL, _doc(grant))
    _commit_with_mirrors(git_repo.root)
    assert _coverage(git_repo, SKILL).covers("R37", SKILL)


def test_a_frontmatter_hooks_key_leaves_no_coverage(git_repo):
    text = _doc(GOOD_GRANT).replace("\n---\nbody", "\nhooks:\n  Stop: []\n---\nbody")
    assert "hooks:" in text
    git_repo.write(SKILL, text)
    _commit_with_mirrors(git_repo.root)
    assert not _coverage(git_repo, SKILL).covers("R37", SKILL)


def test_a_document_with_an_r37_finding_is_not_covered(git_repo):
    git_repo.write(SKILL, _doc("Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh:*)"))
    _write_script(git_repo, "plugins/demo-kit/scripts/tool.sh", executable=False)
    _commit_with_mirrors(git_repo.root)
    assert not _coverage(git_repo, SKILL).covers("R37", SKILL)


def test_a_hook_manifest_is_never_covered(git_repo):
    git_repo.write(SKILL, _doc(GOOD_GRANT))
    _commit_with_mirrors(git_repo.root)
    assert not _coverage(git_repo, SKILL).covers("R37", "plugins/demo-kit/hooks/hooks.json")
