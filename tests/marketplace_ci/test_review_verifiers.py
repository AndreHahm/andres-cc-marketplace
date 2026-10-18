"""The script verifiers behind the review gate (issue #576, #568 Phase 2), starting with
`r6-bash-scope`: a skill or command may not grant unrestricted Bash, and an agent may not scope it.

The verifier is deterministic and reads the PR's committed blobs as data. Its findings are
`source="script"`, so the computed gate can block on them and the exceptions registry can suppress
them, unlike a model finding.
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
from scripts.marketplace_ci.prefix_check import find_prefix_violations
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


def _doc(key: str, value: str) -> str:
    description = (
        "A demo component used only by the verifier tests, long enough for R21 to accept it."
    )
    return f"---\nname: demo\ndescription: {description}\n{key}: {value}\n---\n\n# Body\n"


def _skill(value: str) -> str:
    return _doc("allowed-tools", value)


def _rules(findings):
    return [f.rule for f in findings]


# --- skills and commands: allowed-tools -------------------------------------------------------


@pytest.mark.parametrize("grant", ["Bash", "Bash(*)", "Read Bash", "Read Bash(*) Grep"])
def test_unrestricted_bash_is_a_critical_script_finding(grant):
    (finding,) = rv.check_bash_scope(SKILL, _skill(grant))
    assert finding.rule == "r6-bash-scope"
    assert finding.severity == "Critical"
    assert finding.source == "script"
    assert finding.rule_class == "line"
    assert finding.path == SKILL
    assert finding.line == 4
    assert finding.reviewer == rv.VERIFIER_REVIEWER


@pytest.mark.parametrize("interpreter", ["sh", "bash", "cmd", "powershell"])
def test_a_shell_interpreter_grant_is_a_finding(interpreter):
    (finding,) = rv.check_bash_scope(SKILL, _skill(f"Read Bash({interpreter}:*)"))
    assert finding.rule == "r6-bash-scope"


@pytest.mark.parametrize("grant", ["Bash(bash -c:*)", "Bash(sh -c 'x':*)", "Bash(bash:*)"])
def test_an_interpreter_grant_is_a_finding_whatever_its_arguments(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
        "Bash(bash ./scripts/x.sh --dry-run:*)",
        "Bash(sh scripts/x.sh:*)",
        "Bash(bash x.sh:*)",
        "Bash(powershell ${CLAUDE_SKILL_DIR}/scripts/x.ps1:*)",
    ],
)
def test_an_interpreter_that_pins_one_script_passes(grant):
    assert rv.check_bash_scope(SKILL, _skill(grant)) == ()


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(bash scripts/*.sh:*)",
        "Bash(bash -x ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
        "Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/?.sh:*)",
    ],
)
def test_an_interpreter_that_does_not_pin_one_script_is_a_finding(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(git:*)",
        "Bash(git status:*) Bash(git diff:*)",
        "Bash(python3 -I ${CLAUDE_SKILL_DIR}/scripts/x.py --dry-run:*)",
        "Bash(gh api repos/*/issues/*:*)",
        "Read Grep Glob",
        "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",  # the standard form of a script grant
        "Bash(${CLAUDE_SKILL_DIR}/scripts/x.py --dry-run:*)",
        "Bash(${CLAUDE_PROJECT_DIR}/.claude/scripts/x.py:*)",
        "Bash(*/scan.sh:*)",  # a wildcard directory still pins the script by name
        "Bash(*/git-kit/skills/git-cleanup/scripts/phase1-analysis.sh:*)",
        "Bash(shellcheck:*)",
        "Bash(basename:*)",
    ],
)
def test_a_named_scoped_tool_passes(grant):
    assert rv.check_bash_scope(SKILL, _skill(grant)) == ()


def test_each_violating_grant_is_reported_once():
    findings = rv.check_bash_scope(SKILL, _skill("Bash(git:*) Bash(sh:*) Bash(*)"))
    assert [f.evidence for f in findings] == [
        "`allowed-tools` grants `Bash(sh:*)`, a shell interpreter with no pinned script",
        "`allowed-tools` grants `Bash(*)`, unrestricted Bash",
    ]


def test_a_comma_separated_list_is_read():
    assert len(rv.check_bash_scope(SKILL, _skill("Read, Bash, Grep"))) == 1
    assert rv.check_bash_scope(SKILL, _skill("Read, Bash(git log --format=a,b:*), Grep")) == ()


def test_a_yaml_block_list_reports_the_line_of_the_item():
    text = "---\nname: demo\nallowed-tools:\n  - Read\n  - Bash\n  - Grep\n---\n"
    (finding,) = rv.check_bash_scope(SKILL, text)
    assert finding.line == 5


def test_a_yaml_flow_list_and_a_folded_scalar_are_read():
    flow = "---\nname: demo\nallowed-tools: [Read, Bash]\n---\n"
    assert len(rv.check_bash_scope(SKILL, flow)) == 1
    folded = "---\nname: demo\nallowed-tools: >-\n  Read\n  Bash(*)\n---\n"
    (finding,) = rv.check_bash_scope(SKILL, folded)
    assert finding.line is None


def test_a_command_file_is_checked_like_a_skill():
    (finding,) = rv.check_bash_scope(COMMAND, _skill("Bash"))
    assert finding.path == COMMAND


def test_a_disallowed_tools_entry_is_not_a_grant():
    assert rv.check_bash_scope(SKILL, _doc("disallowed-tools", "Bash")) == ()


def test_a_file_without_an_allowed_tools_field_has_no_finding():
    assert rv.check_bash_scope(SKILL, "---\nname: demo\n---\n") == ()


def test_a_command_without_any_frontmatter_grants_nothing():
    assert rv.check_bash_scope(COMMAND, "# Just a command\n\nDo the thing.\n") == ()


# --- agents: tools ----------------------------------------------------------------------------


@pytest.mark.parametrize("tools", ["Read, Grep, Bash", "Read, Bash, Grep", "Bash"])
def test_bare_bash_is_correct_for_an_agent(tools):
    assert rv.check_bash_scope(AGENT, _doc("tools", tools)) == ()


@pytest.mark.parametrize("tools", ["Read, Bash(git:*)", "Bash(*)", "Read, Bash(python3 -I x.py:*)"])
def test_a_scoped_bash_entry_in_an_agent_is_a_finding(tools):
    (finding,) = rv.check_bash_scope(AGENT, _doc("tools", tools))
    assert finding.rule == "r6-bash-scope"
    assert finding.severity == "Critical"
    assert "bare `Bash`" in finding.remediation


def test_an_agent_yaml_list_is_read():
    text = "---\nname: demo-agent\ntools:\n  - Read\n  - Bash(git:*)\n---\n"
    (finding,) = rv.check_bash_scope(AGENT, text)
    assert finding.line == 5


def test_agent_tool_grants_such_as_agent_with_a_type_are_not_bash():
    assert rv.check_bash_scope(AGENT, _doc("tools", "Read, Agent(reviewer), Grep")) == ()


# --- evasions, spellings and line attribution ------------------------------------------------


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(/bin/bash:*)",
        "Bash(/bin/sh:*)",
        "Bash(bash.exe:*)",
        "Bash(cmd.exe:*)",
        "Bash(powershell.exe:*)",
        "Bash(BASH:*)",
        "Bash(b''ash:*)",
        "Bash(\\bash:*)",
        "Bash(C:\\Windows\\System32\\cmd.exe:*)",
        "Bash(**)",
        "Bash(* *)",
        "Bash(*:*)",
        "Bash(?:*)",
    ],
)
def test_other_spellings_of_unrestricted_bash_are_findings(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


@pytest.mark.parametrize(
    "entry,line",
    [
        ("'allowed-tools': Bash", 3),
        ('"allowed-tools": Bash', 3),
        ("? allowed-tools\n: Bash", 4),
    ],
)
def test_a_quoted_or_explicit_key_is_still_read_and_located(entry, line):
    (finding,) = rv.check_bash_scope(SKILL, f"---\nname: demo\n{entry}\n---\n")
    assert finding.line == line


def test_a_flow_mapping_frontmatter_is_read():
    (finding,) = rv.check_bash_scope(SKILL, "---\n{name: demo, allowed-tools: Bash}\n---\n")
    assert finding.line == 2


def test_a_comment_mentioning_bash_does_not_take_the_attribution():
    text = "---\nname: demo\nallowed-tools:\n  # Bash is discussed here\n  - Read\n  - Bash\n---\n"
    (finding,) = rv.check_bash_scope(SKILL, text)
    assert finding.line == 6


def test_a_grant_in_a_multi_line_scalar_has_no_line():
    text = "---\nname: demo\nallowed-tools: Read\n  Bash\n  Grep\n---\n"
    (finding,) = rv.check_bash_scope(SKILL, text)
    assert finding.line is None


def test_a_decoy_on_the_header_line_does_not_take_the_attribution():
    text = "---\nname: demo\nallowed-tools: >- # Bash is not granted here\n  Read\n  Bash\n---\n"
    (finding,) = rv.check_bash_scope(SKILL, text)
    assert finding.line is None


def test_a_bom_and_crlf_line_endings_do_not_hide_the_frontmatter():
    bom = "\ufeff---\nname: demo\nallowed-tools: Bash\n---\n"
    (finding,) = rv.check_bash_scope(SKILL, bom)
    assert finding.line == 3
    crlf = "---\r\nname: demo\r\nallowed-tools: Bash\r\n---\r\n"
    (finding,) = rv.check_bash_scope(SKILL, crlf)
    assert finding.line == 3


@pytest.mark.parametrize("char", ["\r", "\x85", "\u2028", "\u2029"])
def test_a_line_break_git_does_not_count_makes_the_frontmatter_unverifiable(char):
    text = f"---\nname: demo{char}more\nallowed-tools: Bash\n---\n"
    with pytest.raises(rv.VerifierError, match="line break"):
        rv.check_bash_scope(SKILL, text)


def test_an_odd_timestamp_or_integer_is_not_a_crash():
    text = (
        "---\nname: demo\ncreated: 2026-13-01\nbig: " + "9" * 5000 + "\nallowed-tools: Read\n---\n"
    )
    assert rv.check_bash_scope(SKILL, text) == ()


def test_the_evidence_quotes_a_long_or_odd_token_as_data():
    token = "Bash(bash -c `rm`\n" + "x" * 500 + ")"
    (finding,) = rv.check_bash_scope(SKILL, _skill("'" + token.replace("'", "''") + "'"))
    assert len(finding.evidence) < 400
    assert "\n" not in finding.evidence and finding.evidence.count("`") == 4


def test_a_file_with_thousands_of_entries_is_bounded():
    many = "---\nname: demo\nallowed-tools:\n" + "  - Bash\n" * (rv.MAX_ENTRIES + 1) + "---\n"
    with pytest.raises(rv.VerifierError, match="entries"):
        rv.check_bash_scope(SKILL, many)


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(cmd /c:*)",
        "Bash(cmd.exe /C:*)",
        "Bash(cmd /k:*)",
        "Bash(sh +x:*)",
        "Bash(bash +o posix:*)",
        "Bash(b\\ash:*)",
        "Bash(bas\\h:*)",
        "Bash(bash /dev/stdin:*)",
        "Bash(bash /dev/fd/0:*)",
        "Bash(bash /proc/self/fd/0:*)",
        "Bash(bash //dev/stdin:*)",
        "Bash(bash /./dev/stdin:*)",
        "Bash(bash ${IFS}:*)",
        "Bash(bash $X:*)",
        "Bash(bash x:*)",
        "Bash(bash ${OTHER}/scripts/x.sh:*)",
        "Bash($SHELL:*)",
        "Bash(${CLAUDE_PLUGIN_ROOT}/../${X}/bash:*)",
        "Bash(${OTHER}/scripts/x.sh:*)",
        "Bash(${BASH}:*)",
        "Bash(b${X}ash:*)",
        "Bash(`bash`:*)",
        "Bash(bash*)",
        "Bash(b*:*)",
        "Bash(*sh -c *)",
        "'Bash(bash: *)'",
        "Bash(bash:**)",
        "Bash(bash:*:*)",
        "Bash(git*)",
        "Bash(*/bash:*)",  # a wildcard directory does not hide an interpreter
        "Bash(*/sh -c:*)",
    ],
)
def test_options_wildcards_and_escapes_do_not_pin_a_script(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


@pytest.mark.parametrize(
    "text",
    [
        "---\nname: demo\nallowed-tools: Read Bash(bash:*))\n---\n",  # extra parenthesis
        "---\nname: demo\nallowed-tools: !!null Bash\n---\n",  # explicit tag
        "---\nname: demo\nallowed-tools: !!binary Bash\n---\n",
        "---\nname: demo\nallowed-tools:\n  - !!str Bash\n---\n",
        "---\nname: demo\n? [allowed-tools]\n: Bash\n---\n",  # a non-scalar key
        "---yaml\nname: demo\nallowed-tools: Bash\n---\n",  # a fence variant
        '---\nname: demo\nx: "foo\nallowed-tools: Bash"\nallowed-tools: Read\n---\n',
        "---\nname: demo\n...\nallowed-tools: Bash\n---\n",  # a second document
    ],
)
def test_other_ambiguous_frontmatter_is_unverifiable(text):
    with pytest.raises(rv.VerifierError):
        rv.check_bash_scope(SKILL, text)


def test_a_finding_cites_the_fences_and_the_lines_between_the_key_and_the_entry():
    text = "---\nname: demo\nallowed-tools:\n  - Read\n  # note\n  - Bash\n---\nbody\n"
    (finding,) = rv.check_bash_scope(SKILL, text)
    assert finding.line == 6
    assert finding.components == tuple(f"{SKILL}:{n}" for n in (1, 3, 4, 5, 7))


def test_a_finding_without_a_line_cites_nothing_extra():
    (finding,) = rv.check_bash_scope(SKILL, "---\nallowed-tools: Read\n  Bash\n---\n")
    assert finding.line is None and finding.components == ()


def test_an_over_long_context_gives_the_finding_no_line():
    pad = "  - Read\n" * (rv.MAX_CONTEXT_LINES + 1)
    (finding,) = rv.check_bash_scope(SKILL, f"---\nallowed-tools:\n{pad}  - Bash\n---\n")
    assert finding.line is None and finding.components == ()


def test_deeply_nested_flow_collections_are_refused_before_parsing():
    text = "---\nname: demo\nx: " + "[" * 200 + "\nallowed-tools: Read\n---\n"
    with pytest.raises(rv.VerifierError, match="nest"):
        rv.check_bash_scope(SKILL, text)


# --- parsing failures and path classification -------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "---\nname: [unclosed\n---\n",
        "---\n- a\n- b\n---\n",
        "---\nname: demo\nallowed-tools: Read\n",  # never closed
        "\n---\nname: demo\nallowed-tools: Bash\n---\n",  # leading blank line
        "---\nname: demo\n<<: {allowed-tools: Bash}\n---\n",  # merge key
        "---\nname: demo\nallowed-tools: Read\nallowed-tools: Bash\n---\n",  # duplicate key
        "---\nname: demo\nallowed-tools:\n  nested: Bash\n---\n",  # a mapping, not a list
        "---\nname: demo\nallowed-tools: [Read, [Bash]]\n---\n",  # nested sequence
        "---\nname: demo\nallowed-tools: Read Bash(git:*\n---\n",  # unbalanced parenthesis
        "---\nname: demo\nallowed-tools: Bash(git:*)extra\n---\n",  # malformed Bash entry
    ],
)
def test_unreadable_frontmatter_is_reported_not_swallowed(text):
    with pytest.raises(rv.VerifierError):
        rv.check_bash_scope(SKILL, text)


@pytest.mark.parametrize(
    "text",
    [
        "---\nname: demo\nx: &a Bash\nallowed-tools: *a\n---\n",
        "---\nname: &k allowed-tools\nx: &v Bash\n*k : *v\n---\n",  # an alias as the key
    ],
)
def test_a_yaml_alias_is_unverifiable(text):
    with pytest.raises(rv.VerifierError, match="alias"):
        rv.check_bash_scope(SKILL, text)


def test_a_billion_laughs_block_is_refused_without_being_expanded():
    levels = ["a: &a0 [x, x, x, x, x, x, x, x, x]"]
    levels += [f"{chr(98 + i)}: &a{i + 1} [{', '.join([f'*a{i}'] * 9)}]" for i in range(9)]
    text = "---\nname: demo\n" + "\n".join(levels) + "\nallowed-tools: Read\n---\n"
    with pytest.raises(rv.VerifierError, match="alias"):
        rv.check_bash_scope(SKILL, text)


def test_an_oversized_frontmatter_block_is_refused():
    big = "---\nname: demo\nallowed-tools: " + "Read " * 40_000 + "\n---\n"
    with pytest.raises(rv.VerifierError, match="larger than"):
        rv.check_bash_scope(SKILL, big)


def test_a_deeply_nested_block_is_refused_not_a_crash():
    deep = "---\nname: demo\nallowed-tools: " + "[" * 5000 + "\n---\n"
    with pytest.raises(rv.VerifierError):
        rv.check_bash_scope(SKILL, deep)
    nested = "---\nname: demo\nx: " + "[" * 3000 + "]" * 3000 + "\n---\n"
    with pytest.raises(rv.VerifierError):
        rv.check_bash_scope(SKILL, nested)


@pytest.mark.parametrize(
    "path,kind",
    [
        ("plugins/demo-kit/skills/demo/SKILL.md", "skill"),
        (".claude/skills/demo/SKILL.md", "skill"),
        ("plugins/demo-kit/commands/demo-run.md", "command"),
        ("plugins/demo-kit/commands/ns/demo-run.md", "command"),
        ("plugins/demo-kit/agents/team/demo-agent.md", "agent"),
        (".claude/commands/demo-run.md", "command"),
        ("plugins/demo-kit/agents/demo-agent.md", "agent"),
        (".claude/agents/demo-agent.md", "agent"),
        ("plugins/demo-kit/skills/demo/references/notes.md", None),
        ("docs/commands/x.md", None),
        ("plugins/demo-kit/skills/demo/SKILL.txt", None),
        ("plugins/demo-kit/skills/demo/skill.md", "skill"),
        ("plugins/demo-kit/commands/demo-run.MD", "command"),
        ("plugins/demo-kit/rules/x.md", None),
    ],
)
def test_component_kind(path, kind):
    assert rv.component_kind(path) == kind


def test_the_interpreter_list_equals_the_rulebook_setting():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    forbidden = settings["rules"]["R6_tool_scoping_least_privilege"]["config"][
        "forbidden_bash_scopes"
    ]
    names = {s.removeprefix("Bash(").removesuffix(":*)") for s in forbidden if s.endswith(":*)")}
    assert set(rv.SHELL_INTERPRETERS) == names


# --- the gate ---------------------------------------------------------------------------------


def test_a_script_finding_blocks_on_a_changed_line_and_is_a_notice_elsewhere():
    (finding,) = rv.check_bash_scope(SKILL, _skill("Bash"))
    assert gate_decision(finding, in_diff=True).outcome == "block"
    assert gate_decision(finding, in_diff=False).outcome == "notice"


def test_the_findings_are_deterministic():
    text = _skill("Bash(sh:*) Bash Bash(*)")
    assert rv.check_bash_scope(SKILL, text) == rv.check_bash_scope(SKILL, text)


# --- reading the committed tree ---------------------------------------------------------------


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _changes(*paths: str, status: str = "A") -> tuple[ChangedPath, ...]:
    return tuple(ChangedPath(status=status, old_path=None, new_path=p) for p in paths)


def test_run_verifiers_reads_the_committed_blob_not_the_working_tree(git_repo):
    git_repo.write(SKILL, _skill("Bash"))
    _commit(git_repo.root, "add")
    git_repo.write(SKILL, _skill("Read"))  # uncommitted, must be ignored
    outcome, *_ = rv.run_verifiers(git_repo.root, _changes(SKILL))
    assert _rules(outcome.findings) == ["r6-bash-scope"]


def test_run_verifiers_reports_the_verifier_name_and_what_it_checked(git_repo):
    git_repo.write(SKILL, _skill("Read"))
    git_repo.write("README.md", "x")
    _commit(git_repo.root, "add")
    outcome, *_ = rv.run_verifiers(git_repo.root, _changes(SKILL, "README.md"))
    assert outcome.name == "grant-to-body"
    assert outcome.findings == ()
    assert outcome.checked == (SKILL,)


def test_run_verifiers_skips_a_deleted_file(git_repo):
    git_repo.write("README.md", "x")
    _commit(git_repo.root, "base")
    deleted = (ChangedPath(status="D", old_path=SKILL, new_path=None),)
    outcome, *_ = rv.run_verifiers(git_repo.root, deleted)
    assert outcome.findings == () and outcome.checked == ()


def test_run_verifiers_does_not_follow_a_symlink(git_repo):
    git_repo.write("outside.md", _skill("Bash"))
    target = git_repo.root / SKILL
    target.parent.mkdir(parents=True)
    target.symlink_to(git_repo.root / "outside.md")
    _commit(git_repo.root, "add")
    outcome, *_ = rv.run_verifiers(git_repo.root, _changes(SKILL))
    (finding,) = outcome.findings
    assert finding.rule == "frontmatter-unverifiable"
    assert "symlink" in finding.evidence


def test_a_file_that_cannot_be_verified_is_a_blocking_finding_not_a_skip(git_repo):
    """An adversarial PR must not be able to keep a Bash grant by making its file unreadable."""
    git_repo.write(SKILL, "---\nname: [unclosed\n---\n")
    _commit(git_repo.root, "add")
    outcome, *_ = rv.run_verifiers(git_repo.root, _changes(SKILL))
    assert outcome.checked == ()
    (finding,) = outcome.findings
    assert finding.rule == "frontmatter-unverifiable"
    assert finding.severity == "Major" and finding.line is None and finding.source == "script"
    assert gate_decision(finding, in_diff=True).outcome == "block"


def test_stray_bytes_in_the_body_do_not_hide_a_grant(git_repo):
    target = git_repo.root / SKILL
    target.parent.mkdir(parents=True)
    target.write_bytes(_skill("Bash").encode() + b"\xff\xfe body bytes\n")
    _commit(git_repo.root, "add")
    outcome, *_ = rv.run_verifiers(git_repo.root, _changes(SKILL))
    assert _rules(outcome.findings) == ["r6-bash-scope"]


def test_a_file_over_the_size_cap_is_unverifiable_and_never_fully_read(git_repo):
    git_repo.write(SKILL, _skill("Read") + "x" * (rv.MAX_BLOB_BYTES + 1))
    _commit(git_repo.root, "add")
    outcome, *_ = rv.run_verifiers(git_repo.root, _changes(SKILL))
    (finding,) = outcome.findings
    assert finding.rule == "frontmatter-unverifiable" and "bytes" in finding.evidence


def test_the_total_bytes_read_are_capped(monkeypatch, git_repo):
    monkeypatch.setattr(rv, "MAX_TOTAL_BYTES", len(_skill("Read")) * 2 + 1)
    paths = [f"plugins/demo-kit/skills/s{i}/SKILL.md" for i in range(4)]
    for path in paths:
        git_repo.write(path, _skill("Read"))
    _commit(git_repo.root, "add")
    texts, problems = rv._read_blobs(git_repo.root, paths)
    assert len(texts) == 2 and len(problems) == 2
    assert all("total size" in why for why in problems.values())


def test_a_run_whose_files_overflow_the_budget_never_passes_quietly(monkeypatch, git_repo):
    """The component pass reports the overflow as unverifiable findings; the structure pass, which
    reads every skill of a touched plugin, fails the whole run closed."""
    monkeypatch.setattr(rv, "MAX_TOTAL_BYTES", len(_skill("Read")) * 2 + 1)
    paths = [f"plugins/demo-kit/skills/s{i}/SKILL.md" for i in range(4)]
    for path in paths:
        git_repo.write(path, _skill("Read"))
    _commit(git_repo.root, "add")
    with pytest.raises(RuntimeError, match="budget"):
        rv.run_verifiers(git_repo.root, _changes(*paths))


def test_a_changed_path_missing_from_head_is_an_error_not_a_silent_drop(git_repo):
    git_repo.write("README.md", "x")
    _commit(git_repo.root, "base")
    with pytest.raises(RuntimeError, match="not in HEAD"):
        rv.run_verifiers(git_repo.root, _changes(SKILL))


def test_run_verifiers_checks_both_sides_of_a_rename(git_repo):
    git_repo.write(SKILL, _skill("Bash"))
    _commit(git_repo.root, "add")
    renamed = (
        ChangedPath(status="R", old_path="plugins/demo-kit/skills/legacy/SKILL.md", new_path=SKILL),
    )
    outcome, *_ = rv.run_verifiers(git_repo.root, renamed)
    assert outcome.checked == (SKILL,)
    assert len(outcome.findings) == 1


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


def _review_repo(git_repo, skill_text: str):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    git_repo.write("README.md", "original")
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, skill_text)
    _commit(git_repo.root, "change")
    return git_repo.root, base


def _run(monkeypatch, root, base, tmp_path):
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base, "--output", str(out)])
    return rc, json.loads(out.read_text(encoding="utf-8"))


def test_a_script_finding_blocks_the_run_and_is_recorded(monkeypatch, git_repo, tmp_path):
    root, base = _review_repo(git_repo, _skill("Read Bash"))
    rc, payload = _run(monkeypatch, root, base, tmp_path)
    assert rc == 1
    assert payload["status"] == "findings" and payload["blocking"] is True
    (finding,) = payload["findings"]
    assert finding["rule"] == "r6-bash-scope"
    assert finding["source"] == "script" and finding["rule_class"] == "line"
    assert finding["gate"] == "block" and finding["in_diff"] is True
    assert finding["suppressed"] is False


def test_a_clean_skill_leaves_the_run_clean_and_records_the_verifier(
    monkeypatch, git_repo, tmp_path
):
    root, base = _review_repo(git_repo, _skill("Read Grep"))
    rc, payload = _run(monkeypatch, root, base, tmp_path)
    assert rc == 0
    assert payload["status"] == "clean" and payload["findings"] == []
    assert payload["verifiers"] == [
        {"name": "grant-to-body", "status": "clean", "findings": 0, "checked": 1},
        {"name": "measurement", "status": "clean", "findings": 0, "checked": 1},
        {"name": "path-and-mirror", "status": "clean", "findings": 0, "checked": 1},
        {"name": "structure", "status": "clean", "findings": 0, "checked": 1},
        {"name": "call-graph", "status": "clean", "findings": 0, "checked": 1},
        {"name": "removed-identifier", "status": "clean", "findings": 0, "checked": 0},
    ]


def test_an_unverifiable_file_blocks_the_run(monkeypatch, git_repo, tmp_path):
    root, base = _review_repo(git_repo, "---\nname: [unclosed\n---\n")
    rc, payload = _run(monkeypatch, root, base, tmp_path)
    assert rc == 1 and payload["blocking"] is True
    (finding,) = payload["findings"]
    assert finding["rule"] == "frontmatter-unverifiable" and finding["gate"] == "block"
    grants, measures, *_ = payload["verifiers"]
    assert grants["status"] == "findings" and grants["checked"] == 0
    assert measures["status"] == "findings"  # the same unverifiable finding, kept once overall


def test_a_grant_added_to_an_existing_file_blocks_even_in_an_unusual_form(
    monkeypatch, git_repo, tmp_path
):
    """The finding's line must be one the PR changed: a quoted key moved the finding to line 1."""
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    git_repo.write(
        SKILL, "---\nname: demo\n# note: Bash is unrelated\nallowed-tools: Read\n---\nbody\n"
    )
    base = _commit(git_repo.root, "base")
    git_repo.write(
        SKILL, "---\nname: demo\n# note: Bash is unrelated\n'allowed-tools': Bash\n---\nbody\n"
    )
    _commit(git_repo.root, "change")
    rc, payload = _run(monkeypatch, git_repo.root, base, tmp_path)
    assert rc == 1
    (finding,) = payload["findings"]
    assert finding["rule"] == "r6-bash-scope" and finding["line"] == 4
    assert finding["gate"] == "block"


def test_a_crashing_verifier_makes_the_run_could_not_run(monkeypatch, git_repo, tmp_path):
    def boom(*args, **kwargs):
        raise RuntimeError("verifier exploded")

    monkeypatch.setattr(rv, "run_verifiers", boom)
    root, base = _review_repo(git_repo, _skill("Read"))
    rc, payload = _run(monkeypatch, root, base, tmp_path)
    assert rc == 2
    assert payload["status"] == "could_not_run" and payload["blocking"] is True
    assert "verifier" in payload["error"]


def _edit_existing(monkeypatch, git_repo, tmp_path, before: str, after: str):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    git_repo.write(SKILL, before)
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, after)
    _commit(git_repo.root, "change")
    return _run(monkeypatch, git_repo.root, base, tmp_path)


def test_renaming_the_key_line_blocks_a_grant_that_sits_on_an_untouched_line(
    monkeypatch, git_repo, tmp_path
):
    before = "---\nname: demo\ndisallowed-tools:\n  - Bash\n---\nbody\n"
    after = "---\nname: demo\nallowed-tools:\n  - Bash\n---\nbody\n"
    rc, payload = _edit_existing(monkeypatch, git_repo, tmp_path, before, after)
    assert rc == 1
    (finding,) = payload["findings"]
    assert (
        finding["rule"] == "r6-bash-scope" and finding["line"] == 4 and finding["gate"] == "block"
    )


def test_deleting_a_line_above_the_fence_blocks_a_grant_it_turns_into_frontmatter(
    monkeypatch, git_repo, tmp_path
):
    before = "# Title\n---\nname: demo\nallowed-tools: Bash\n---\nbody\n"
    after = "---\nname: demo\nallowed-tools: Bash\n---\nbody\n"
    rc, payload = _edit_existing(monkeypatch, git_repo, tmp_path, before, after)
    assert rc == 1
    assert [f["gate"] for f in payload["findings"]] == ["block"]


def test_an_untouched_grant_in_a_file_with_only_a_body_change_is_a_notice(
    monkeypatch, git_repo, tmp_path
):
    before = "---\nname: demo\nallowed-tools: Bash\n---\nbody\n"
    after = "---\nname: demo\nallowed-tools: Bash\n---\nbody changed\n"
    rc, payload = _edit_existing(monkeypatch, git_repo, tmp_path, before, after)
    assert rc == 0
    assert [f["gate"] for f in payload["findings"]] == ["notice"]


def test_a_registry_entry_suppresses_a_script_finding(monkeypatch, git_repo, tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "exceptions:\n"
        "  - rule: r6-bash-scope\n"
        '    path: "plugins/**"\n'
        "    reason: test reason\n"
        "    authority: docs/ci.md\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(review_contract, "EXCEPTIONS_PATH", registry)
    root, base = _review_repo(git_repo, _skill("Bash"))
    rc, payload = _run(monkeypatch, root, base, tmp_path)
    assert rc == 0
    (finding,) = payload["findings"]
    assert finding["gate"] == "suppressed" and finding["suppressed"] is True
    assert finding["exception"]["rule"] == "r6-bash-scope"


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(env bash:*)",
        "Bash(env FOO=1 bash -c:*)",
        "Bash(FOO=1 bash:*)",
        "Bash(/usr/bin/env sh:*)",
        "Bash(exec -a name bash:*)",
        "Bash(nohup bash:*)",
        "Bash(env:*)",
        "Bash(time:*)",
        "Bash(env env:*)",
    ],
)
def test_a_wrapper_in_front_of_an_interpreter_is_still_an_interpreter_grant(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(env bash ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
        "Bash(FOO=1 bash scripts/x.sh:*)",
        "Bash(env git:*)",
        "Bash(env FOO=1 ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)",
    ],
)
def test_a_wrapper_in_front_of_a_pinned_script_or_a_named_tool_passes(grant):
    assert rv.check_bash_scope(SKILL, _skill(grant)) == ()


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(env -S bash:*)",
        "Bash(env -Sbash:*)",
        "Bash(env --split-string=bash:*)",
        "Bash(env -i:*)",
        "Bash(FOO=1:*)",
    ],
)
def test_a_grant_whose_program_cannot_be_read_is_unverifiable_not_clean(grant):
    with pytest.raises(rv.VerifierError):
        rv.check_bash_scope(SKILL, _skill(grant))


@pytest.mark.parametrize(
    "grant",
    [
        'Bash("env" bash:*)',
        "Bash('/usr/bin/env' sh:*)",
        "Bash(\\env bash:*)",
        "Bash(ENV bash:*)",
        "Bash(nice --adjustment 5 bash:*)",
        "Bash(time --format x bash:*)",
        "Bash(time --output f bash:*)",
    ],
)
def test_quoted_escaped_and_case_variant_wrappers_and_long_options_are_read(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


@pytest.mark.parametrize("grant", ["Bash(*\u00a0*)", "Bash(* *)"])
def test_odd_whitespace_between_wildcards_is_a_finding_not_a_crash(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(env '-i' bash:*)",
        "Bash(env \\-i bash:*)",
        "Bash(env 'FOO=1' bash:*)",
        "Bash(FOO='a b' bash:*)",
        "Bash(env -iS bash:*)",
        "Bash(env --split=bash:*)",
        "Bash(env --sp=bash:*)",
        "Bash(env --not-an-option bash:*)",
    ],
)
def test_a_wrapper_word_this_check_cannot_read_makes_the_grant_unverifiable(grant):
    with pytest.raises(rv.VerifierError):
        rv.check_bash_scope(SKILL, _skill(grant))


@pytest.mark.parametrize(
    "grant",
    [
        "Bash(env - bash:*)",
        "Bash(env -P /x bash:*)",
        "Bash(nice -5 bash:*)",
        "Bash(env --ignore-environment bash:*)",
        "Bash(env --unset=NAME bash:*)",
    ],
)
def test_known_wrapper_options_are_skipped_and_the_shell_behind_them_is_found(grant):
    assert len(rv.check_bash_scope(SKILL, _skill(grant))) == 1


def test_a_known_wrapper_option_in_front_of_a_named_tool_passes():
    assert rv.check_bash_scope(SKILL, _skill("Bash(nice -5 git status:*)")) == ()


# --- script_coverage: R33 half (the R37 half is in test_review_exec_bit.py) ----------------------


def test_script_coverage_for_r33_needs_a_run_with_no_violations(tmp_path):
    # No inventory in the fixture: nothing was checked, so nothing is covered.
    assert not rv.script_coverage(tmp_path, []).covers("R33", "plugins/demo-kit/scripts/x.py")


_INVENTORY = ".claude-plugin/marketplace-inventory.json"
_INVENTORY_TEXT = json.dumps(
    {"schema_version": "1.0.0", "marketplace_name": "f", "updated_on": "2026-01-01", "plugins": []}
)
_R33_PATH = "plugins/demo-kit/scripts/x.py"


def test_script_coverage_for_r33_when_the_prefix_check_finds_nothing(git_repo):
    git_repo.write(_INVENTORY, _INVENTORY_TEXT)
    _commit(git_repo.root, "add the inventory")
    assert rv.script_coverage(git_repo.root, []).covers("R33", _R33_PATH)


def test_script_coverage_for_r33_needs_a_tree_that_matches_head(git_repo):
    # The prefix check reads the working tree, the verifiers read committed objects: an uncommitted
    # edit to a tracked file means the two may disagree, so nothing is covered.
    git_repo.write(_INVENTORY, _INVENTORY_TEXT)
    git_repo.write("README.md", "committed\n")
    _commit(git_repo.root, "add the inventory")
    git_repo.write("README.md", "edited, not committed\n")
    assert not rv.script_coverage(git_repo.root, []).covers("R33", _R33_PATH)


def test_script_coverage_for_r33_sees_a_committed_violation_deleted_on_disk(git_repo):
    # The scanner reads the disk, so deleting a committed unprefixed file without committing leaves
    # it clean; only the clean-tree guard stops that silence from reading as "no violation".
    plugin = {"id": "plugin_git-kit", "name": "git-kit", "source": "./git-kit"}
    plugin.update(status="active", prefix="git")
    inventory = {"schema_version": "1.0.0", "marketplace_name": "f", "updated_on": "2026-01-01"}
    git_repo.write(_INVENTORY, json.dumps({**inventory, "plugins": [plugin]}))
    manifest = {"name": "f", "plugins": [{"name": "git-kit", "source": "./git-kit"}]}
    git_repo.write(".claude-plugin/marketplace.json", json.dumps(manifest))
    git_repo.write("git-kit/scripts/other.py", "")
    _commit(git_repo.root, "a committed violation")
    assert not rv.script_coverage(git_repo.root, []).covers("R33", _R33_PATH)
    (git_repo.root / "git-kit/scripts/other.py").unlink()
    assert find_prefix_violations(git_repo.root) == []  # the scanner alone is now blind to it
    assert not rv.script_coverage(git_repo.root, []).covers("R33", _R33_PATH)


def test_script_coverage_for_r33_needs_a_git_repository(tmp_path):
    inventory = tmp_path / _INVENTORY
    inventory.parent.mkdir(parents=True)
    inventory.write_text(_INVENTORY_TEXT, encoding="utf-8")
    assert not rv.script_coverage(tmp_path, []).covers("R33", _R33_PATH)


def test_script_coverage_for_r33_ignores_an_untracked_file(git_repo):
    # An untracked file can only add a prefix violation, never hide one: coverage is unaffected.
    git_repo.write(_INVENTORY, _INVENTORY_TEXT)
    _commit(git_repo.root, "add the inventory")
    git_repo.write("scratch.txt", "untracked\n")
    assert rv.script_coverage(git_repo.root, []).covers("R33", _R33_PATH)
