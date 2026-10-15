"""The removed-identifier verifier (issue #576, #568 Phase 2): `removed-identifier-leftover`.

A skill, agent or command that the PR deletes or renames (its (kind, name) is in the base and not in
the head) must not stay referenced in the live tree: `Skill(name)`, `subagent_type: name`, or the
name in backticks (only when no other component still has that name). The scan covers `plugins/`,
`docs/`, `scripts/`, `.github/` and root files; the `.claude/`, `.agents/` and `.codex/` copies are
the mirror family's business, and `evals/` and `issues/` are history. One finding per removed
component, on the deleted or renamed path, so it is the PR's. With no base nothing is known to be
removed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci import review_verifiers as rv
from scripts.marketplace_ci.git_state import ChangedPath

RULE = "removed-identifier-leftover"


def _skill(name, plugin="demo-kit"):
    return f"plugins/{plugin}/skills/{name}/SKILL.md"


def _agent(name, plugin="demo-kit"):
    return f"plugins/{plugin}/agents/{name}.md"


def _command(name, plugin="demo-kit"):
    return f"plugins/{plugin}/commands/{name}.md"


def _doc(name, body=""):
    return f"---\nname: {name}\ndescription: {'d' * 100}\n---\n{body}"


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _outcome(git_repo, changed, base):
    outcomes = rv.run_verifiers(git_repo.root, changed, base)
    return next(o for o in outcomes if o.name == "removed-identifier")


def _delete(git_repo, rel):
    (git_repo.root / rel).unlink()
    return ChangedPath("D", rel, None)


def _setup(
    git_repo, *, doc="Run Skill(gone) first.\n", where="plugins/demo-kit/skills/user/SKILL.md"
):
    git_repo.write(_skill("gone"), _doc("gone", "Nothing.\n"))
    git_repo.write(where, _doc("user", doc))
    return _commit(git_repo.root, "base")


def test_a_deleted_skill_that_a_call_still_names_is_a_blocking_finding(git_repo):
    base = _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    (finding,) = _outcome(git_repo, (change,), base).findings
    assert finding.rule == RULE and finding.severity == "Major" and finding.source == "script"
    assert finding.rule_class == "graph" and finding.path == _skill("gone")
    assert finding.line is None
    assert (
        "gone" in finding.evidence and "plugins/demo-kit/skills/user/SKILL.md" in finding.evidence
    )


@pytest.mark.parametrize(
    "body",
    [
        "Run `Skill(gone)` first.",
        'Call Skill(skill: "gone").',
        "Use `demo-kit:gone` here.",
        'Call Skill({"skill": "gone"}).',
        "Use `/gone` to start.",
    ],
)
def test_each_reference_form_counts(git_repo, body):
    base = _setup(git_repo, doc=body + "\n")
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    assert len(_outcome(git_repo, (change,), base).findings) == 1


def test_a_deleted_agent_is_found_by_its_subagent_type(git_repo):
    git_repo.write(_agent("rev"), _doc("rev"))
    git_repo.write(_skill("user"), _doc("user", 'Agent(subagent_type: "rev", prompt: "x")\n'))
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _agent("rev"))
    _commit(git_repo.root, "delete")
    (finding,) = _outcome(git_repo, (change,), base).findings
    assert finding.path == _agent("rev") and "agent" in finding.evidence


def test_no_leftover_means_no_finding(git_repo):
    base = _setup(git_repo, doc="Nothing to see.\n")
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    outcome = _outcome(git_repo, (change,), base)
    assert outcome.findings == ()


def test_a_pr_that_updates_the_references_in_the_same_change_is_clean(git_repo):
    base = _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    git_repo.write("plugins/demo-kit/skills/user/SKILL.md", _doc("user", "Updated.\n"))
    _commit(git_repo.root, "delete and update")
    assert _outcome(git_repo, (change,), base).findings == ()


def test_a_rename_reports_the_old_name_on_the_old_path(git_repo):
    base = _setup(git_repo)
    old, new = _skill("gone"), _skill("fresh")
    (git_repo.root / new).parent.mkdir(parents=True)
    (git_repo.root / old).rename(git_repo.root / new)
    _commit(git_repo.root, "rename")
    (finding,) = _outcome(git_repo, (ChangedPath("R", old, new),), base).findings
    assert finding.path == old and "gone" in finding.evidence


def test_a_component_moved_to_another_plugin_keeps_its_name(git_repo):
    base = _setup(git_repo)
    old, new = _skill("gone"), _skill("gone", "other-kit")
    (git_repo.root / new).parent.mkdir(parents=True)
    (git_repo.root / old).rename(git_repo.root / new)
    _commit(git_repo.root, "move")
    assert _outcome(git_repo, (ChangedPath("R", old, new),), base).findings == ()


@pytest.mark.parametrize(
    "where",
    [
        ".claude/skills/user/SKILL.md",
        ".agents/skills/user/SKILL.md",
        ".codex/agents/user.toml",
        "evals/user/evals.json",
        "issues/draft.md",
    ],
)
def test_mirrors_exports_evals_and_issue_drafts_are_not_scanned(git_repo, where):
    base = _setup(git_repo, where=where)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    assert _outcome(git_repo, (change,), base).findings == ()


@pytest.mark.parametrize(
    "where", ["docs/guide.md", "scripts/tool.py", ".github/workflows/x.yml", "README.md"]
)
def test_docs_scripts_workflows_and_root_files_are_scanned(git_repo, where):
    base = _setup(git_repo, where=where)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    (finding,) = _outcome(git_repo, (change,), base).findings
    assert where in finding.evidence


def test_a_backticked_name_does_not_count_while_another_component_keeps_the_name(git_repo):
    git_repo.write(_skill("gone"), _doc("gone"))
    git_repo.write(_agent("gone"), _doc("gone"))
    git_repo.write(_skill("user"), _doc("user", "Use the `/gone` helper.\n"))
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete the skill, keep the agent")
    assert _outcome(git_repo, (change,), base).findings == ()


def test_a_call_naming_the_removed_kind_still_counts_when_another_kind_keeps_the_name(git_repo):
    git_repo.write(_skill("gone"), _doc("gone"))
    git_repo.write(_agent("gone"), _doc("gone"))
    git_repo.write(_skill("user"), _doc("user", "Run Skill(gone).\n"))
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete the skill, keep the agent")
    assert len(_outcome(git_repo, (change,), base).findings) == 1


def test_the_reference_in_the_removed_components_own_plugin_counts(git_repo):
    base = _setup(git_repo, where="plugins/demo-kit/skills/gone/references/notes.md")
    # the skill's own reference file survives while the SKILL.md is deleted
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete only SKILL.md")
    assert len(_outcome(git_repo, (change,), base).findings) == 1


def test_the_evidence_gives_a_count_and_at_most_five_sorted_paths(git_repo):
    git_repo.write(_skill("gone"), _doc("gone"))
    for index in range(8):
        git_repo.write(f"docs/g{index}.md", "See `/gone`.\n")
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    (finding,) = _outcome(git_repo, (change,), base).findings
    assert "8 reference" in finding.evidence and "8 file" in finding.evidence
    assert finding.evidence.count("docs/g") == 5
    assert "docs/g0.md" in finding.evidence and "docs/g7.md" not in finding.evidence


def test_a_name_with_regex_characters_is_matched_literally(git_repo):
    git_repo.write(_command("a.b"), _doc("a.b"))
    git_repo.write("docs/x.md", "Use `/a.b` and `/axb`.\n")
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _command("a.b"))
    _commit(git_repo.root, "delete")
    (finding,) = _outcome(git_repo, (change,), base).findings
    assert "1 reference" in finding.evidence


def test_with_no_base_nothing_is_known_to_be_removed(git_repo):
    _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    assert _outcome(git_repo, (change,), None).findings == ()


def test_a_pr_that_touches_no_component_scans_nothing(git_repo):
    git_repo.write("README.md", "x")
    base = _commit(git_repo.root, "base")
    git_repo.write("README.md", "y")
    _commit(git_repo.root, "docs")
    outcome = _outcome(git_repo, (ChangedPath("M", "README.md", "README.md"),), base)
    assert outcome.findings == () and outcome.checked == ()


def test_removing_more_components_than_the_cap_fails_the_run_closed(monkeypatch, git_repo):
    for name in ("a", "b", "c"):
        git_repo.write(_skill(name), _doc(name))
    base = _commit(git_repo.root, "base")
    changes = tuple(_delete(git_repo, _skill(name)) for name in ("a", "b", "c"))
    _commit(git_repo.root, "delete three")
    monkeypatch.setattr(rv, "MAX_REMOVED_COMPONENTS", 2)
    with pytest.raises(RuntimeError, match="removed"):
        rv.run_verifiers(git_repo.root, changes, base)


def test_the_same_head_gives_the_same_findings(git_repo):
    base = _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    first = rv.run_verifiers(git_repo.root, (change,), base)
    assert first == rv.run_verifiers(git_repo.root, (change,), base)


def test_a_git_grep_that_times_out_fails_the_run_closed(monkeypatch, git_repo):
    base = _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    real_run = subprocess.run

    def hang(argv, **kw):
        if argv[:2] == ["git", "grep"]:
            raise subprocess.TimeoutExpired(argv, kw.get("timeout", 0))
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", hang)
    with pytest.raises(RuntimeError, match="timed out"):
        rv.run_verifiers(git_repo.root, (change,), base)


def test_a_git_grep_error_other_than_no_match_fails_the_run_closed(monkeypatch, git_repo):
    base = _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    real_run = subprocess.run

    def broken(argv, **kw):
        if argv[:2] == ["git", "grep"]:
            return subprocess.CompletedProcess(argv, returncode=2, stdout=b"", stderr=b"fatal")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", broken)
    with pytest.raises(RuntimeError, match="git grep failed"):
        rv.run_verifiers(git_repo.root, (change,), base)


@pytest.mark.parametrize(
    ("name", "reference", "expected"),
    [
        ("gone-away", "Use `gone-away` here.", 1),
        ("gone", "Use `gone` here.", 0),
        ("commit", "See the `commit` docstring.", 0),
        ("gone", "Use `/gone` here.", 1),
        ("gone", "Use `demo-kit:gone` here.", 1),
    ],
)
def test_a_bare_backticked_name_counts_only_when_it_is_hyphenated(
    git_repo, name, reference, expected
):
    git_repo.write(_skill(name), _doc(name))
    git_repo.write("docs/x.md", reference + "\n")
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _skill(name))
    _commit(git_repo.root, "delete")
    assert len(_outcome(git_repo, (change,), base).findings) == expected


def test_a_changelog_is_history_and_is_not_scanned(git_repo):
    git_repo.write(_skill("gone"), _doc("gone"))
    git_repo.write("plugins/demo-kit/CHANGELOG.md", "- added Skill(gone)\n")
    git_repo.write("CHANGELOG.md", "- added Skill(gone)\n")
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    assert _outcome(git_repo, (change,), base).findings == ()


def test_a_gitattributes_in_the_pr_cannot_hide_the_references(git_repo):
    base = _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    git_repo.write(".gitattributes", "* -diff\n*.md binary\n")
    _commit(git_repo.root, "delete and mark everything binary")
    assert len(_outcome(git_repo, (change,), base).findings) == 1


def test_converting_a_skill_to_a_command_of_the_same_name_is_not_a_removal(git_repo):
    base = _setup(git_repo)
    old, new = _skill("gone"), _command("gone")
    (git_repo.root / new).parent.mkdir(parents=True, exist_ok=True)
    (git_repo.root / old).rename(git_repo.root / new)
    _commit(git_repo.root, "skill to command")
    assert _outcome(git_repo, (ChangedPath("R", old, new),), base).findings == ()


def test_converting_a_command_to_a_skill_of_the_same_name_is_not_a_removal(git_repo):
    git_repo.write(_command("gone"), _doc("gone"))
    git_repo.write("plugins/demo-kit/skills/user/SKILL.md", _doc("user", "Run Skill(gone).\n"))
    base = _commit(git_repo.root, "base")
    old, new = _command("gone"), _skill("gone")
    (git_repo.root / new).parent.mkdir(parents=True)
    (git_repo.root / old).rename(git_repo.root / new)
    _commit(git_repo.root, "command to skill")
    assert _outcome(git_repo, (ChangedPath("R", old, new),), base).findings == ()


@pytest.mark.parametrize(
    "body",
    ['Call Skill({"skill": "gone"}).', 'Agent({"subagent_type": "gone"})'],
)
def test_json_style_keys_are_found(git_repo, body):
    kind_is_agent = "subagent_type" in body
    target = _agent("gone") if kind_is_agent else _skill("gone")
    git_repo.write(target, _doc("gone"))
    git_repo.write("docs/x.md", body + "\n")
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, target)
    _commit(git_repo.root, "delete")
    assert len(_outcome(git_repo, (change,), base).findings) == 1


def test_a_name_the_search_cannot_match_safely_is_a_finding_not_a_skip(git_repo):
    git_repo.write(_command("odd name"), _doc("odd name"))
    base = _commit(git_repo.root, "base")
    change = _delete(git_repo, _command("odd name"))
    _commit(git_repo.root, "delete")
    (finding,) = _outcome(git_repo, (change,), base).findings
    assert finding.path == _command("odd name") and "cannot be searched" in finding.evidence


def test_the_total_search_time_has_a_budget(monkeypatch, git_repo):
    base = _setup(git_repo)
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    monkeypatch.setattr(rv, "MAX_PARSE_SECONDS", -1.0)
    with pytest.raises(RuntimeError, match="budget"):
        rv.run_verifiers(git_repo.root, (change,), base)


def test_checked_lists_the_removed_components_that_were_searched(git_repo):
    base = _setup(git_repo, doc="Nothing to see.\n")
    change = _delete(git_repo, _skill("gone"))
    _commit(git_repo.root, "delete")
    outcome = _outcome(git_repo, (change,), base)
    assert outcome.findings == () and outcome.checked == (_skill("gone"),)
