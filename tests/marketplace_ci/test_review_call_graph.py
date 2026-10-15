"""The call-graph verifier (issue #576, #568 Phase 2): `skill-agent-dependency-cycle`.

A call is a literal `Skill(name)` or `Agent(subagent_type: name)` in the body of a skill, agent or
command, outside code blocks; a grant in the frontmatter, a prose mention and a component naming
itself are not calls. A call to a component that does not exist, and a call that closes a cycle,
are blocking findings, but only for a call the PR introduces: a cycle or a dangling call already in
the base never blocks (the real tree has an intentional `commit` <-> `create-pr` cycle). External
`plugin:skill` targets and placeholders such as `...` are skipped.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci import review_verifiers as rv
from scripts.marketplace_ci.git_state import ChangedPath

RULE = "skill-agent-dependency-cycle"


def _skill(name):
    return f"plugins/demo-kit/skills/{name}/SKILL.md"


def _agent(name):
    return f"plugins/demo-kit/agents/{name}.md"


def _command(name):
    return f"plugins/demo-kit/commands/{name}.md"


def _doc(name, body="", grants=""):
    return (
        f"---\nname: {name}\ndescription: {'d' * 100}\n"
        + (f"allowed-tools: {grants}\n" if grants else "")
        + "---\n"
        + body
    )


# --- which text is a call ------------------------------------------------------------------------


def _calls(text):
    return [(c.kind, c.target, c.line) for c in rv.extract_calls(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Run `Skill(commit)` first.", [("skill", "commit", 1)]),
        ("Run Skill(commit) first.", [("skill", "commit", 1)]),
        ('Use Skill(skill: "commit", args: "x").', [("skill", "commit", 1)]),
        ("Use Skill( create-pr , --draft).", [("skill", "create-pr", 1)]),
        (
            'Agent(subagent_type: "security-reviewer", prompt: "x")',
            [("agent", "security-reviewer", 1)],
        ),
        (
            "Agent({ subagent_type: 'security-reviewer', description: 'x' })",
            [("agent", "security-reviewer", 1)],
        ),
        ("a\n\nb `Skill(one)` and Skill(two)\n", [("skill", "one", 3), ("skill", "two", 3)]),
    ],
)
def test_literal_calls_are_found(text, expected):
    assert _calls(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "```\nSkill(commit)\n```\n",
        "~~~bash\nAgent(subagent_type: x)\n~~~\n",
        "    Skill(commit)\n",
        "Use the commit skill, or Skill without parens.",
        "Agent(prompt: only)",
        "Skill()",
        "<!-- Skill(commit) -->",
    ],
)
def test_code_blocks_comments_and_non_calls_are_not_calls(text):
    assert _calls(text) == []


def test_a_grant_in_the_frontmatter_is_not_a_call():
    text = _doc("a", "No calls here.\n", grants="Skill(commit) Read")
    assert _calls(text) == []


def test_a_call_after_the_frontmatter_keeps_its_file_line():
    text = _doc("a", "intro\n\nCall Skill(commit) now.\n", grants="Read")
    assert _calls(text) == [("skill", "commit", 8)]


# --- running over a change set -----------------------------------------------------------------


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _outcome(git_repo, changed, base):
    outcomes = rv.run_verifiers(git_repo.root, changed, base)
    return next(o for o in outcomes if o.name == "call-graph")


def _modify(path):
    return ChangedPath("M", path, path)


def test_a_call_that_closes_a_new_cycle_is_a_blocking_finding_on_its_own_line(git_repo):
    git_repo.write(_skill("a"), _doc("a", "See Skill(b).\n"))
    git_repo.write(_skill("b"), _doc("b", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("b"), _doc("b", "Nothing.\n\nBack to Skill(a).\n"))
    _commit(git_repo.root, "close the cycle")
    outcome = _outcome(git_repo, (_modify(_skill("b")),), base)
    (finding,) = outcome.findings
    assert finding.rule == RULE and finding.severity == "Major" and finding.source == "script"
    assert finding.rule_class == "graph" and finding.path == _skill("b")
    assert finding.line is None and "line 7" in finding.evidence
    assert "b -> a -> b" in finding.evidence or "a -> b -> a" in finding.evidence
    assert outcome.checked == (_skill("b"),)


def test_a_cycle_already_in_the_base_never_blocks(git_repo):
    git_repo.write(_skill("a"), _doc("a", "See Skill(b).\n"))
    git_repo.write(_skill("b"), _doc("b", "Back to Skill(a).\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "See Skill(b). Reworded.\n"))
    _commit(git_repo.root, "edit")
    assert _outcome(git_repo, (_modify(_skill("a")),), base).findings == ()


def test_a_new_call_to_a_missing_component_is_a_blocking_finding(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n\nCall Skill(nope).\n"))
    _commit(git_repo.root, "add call")
    (finding,) = _outcome(git_repo, (_modify(_skill("a")),), base).findings
    assert finding.rule == RULE and finding.severity == "Major" and finding.line is None
    assert "line 7" in finding.evidence
    assert "nope" in finding.evidence and "does not exist" in finding.evidence


def test_a_missing_component_already_called_in_the_base_does_not_block(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Call Skill(nope).\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Call Skill(nope). Reworded.\n"))
    _commit(git_repo.root, "edit")
    assert _outcome(git_repo, (_modify(_skill("a")),), base).findings == ()


def test_deleting_a_component_is_the_removed_identifier_check_not_this_one(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Call Skill(b).\n"))
    git_repo.write(_skill("b"), _doc("b", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    (git_repo.root / _skill("b")).unlink()
    _commit(git_repo.root, "delete b")
    change = (ChangedPath("D", _skill("b"), None),)
    assert _outcome(git_repo, change, base).findings == ()


def test_creating_the_target_of_an_old_dangling_call_can_close_a_cycle(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Call Skill(b).\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("b"), _doc("b", "Back to Skill(a).\n"))
    _commit(git_repo.root, "add b")
    outcome = _outcome(git_repo, (ChangedPath("A", None, _skill("b")),), base)
    by_path = {f.path: f for f in outcome.findings}
    assert set(by_path) == {_skill("a"), _skill("b")}
    assert _skill("b") in by_path[_skill("a")].components  # creating b makes a's call the PR's


def test_with_no_base_every_call_problem_counts_as_new(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Call Skill(b) and Skill(nope).\n"))
    git_repo.write(_skill("b"), _doc("b", "Back to Skill(a).\n"))
    _commit(git_repo.root, "add")
    outcome = _outcome(git_repo, (_modify(_skill("a")), _modify(_skill("b"))), None)
    assert sorted((f.path, "nope" in f.evidence) for f in outcome.findings) == [
        (_skill("a"), False),
        (_skill("a"), True),
        (_skill("b"), False),
    ]


@pytest.mark.parametrize(
    "body",
    [
        "Call Skill(codex:rescue).",
        "Call Skill(...).",
        "Call Skill(a) itself.",
        "```\nSkill(nope)\n```\n",
        "Call Skill(<name>) and Skill({x}).",
    ],
)
def test_external_targets_placeholders_self_calls_and_code_are_skipped(git_repo, body):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", body + "\n"))
    _commit(git_repo.root, "edit")
    assert _outcome(git_repo, (_modify(_skill("a")),), base).findings == ()


def test_a_grant_is_not_an_edge_so_a_grant_and_a_call_do_not_make_a_cycle(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n", grants="Skill(b)"))
    git_repo.write(_skill("b"), _doc("b", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("b"), _doc("b", "Call Skill(a).\n"))
    _commit(git_repo.root, "edit")
    assert _outcome(git_repo, (_modify(_skill("b")),), base).findings == ()


def test_a_skill_call_resolves_to_a_command_and_an_agent_call_only_to_an_agent(git_repo):
    git_repo.write(_command("run"), _doc("run", "Nothing.\n"))
    git_repo.write(_agent("rev"), _doc("rev", "Nothing.\n"))
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    body = "Skill(run) then Agent(subagent_type: rev) then Agent(subagent_type: run).\n"
    git_repo.write(_skill("a"), _doc("a", body))
    _commit(git_repo.root, "edit")
    (finding,) = _outcome(git_repo, (_modify(_skill("a")),), base).findings
    assert "run" in finding.evidence and "agent" in finding.evidence


def test_an_agent_that_calls_a_skill_that_calls_it_back_is_a_cycle(git_repo):
    git_repo.write(_agent("rev"), _doc("rev", "Nothing.\n"))
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_agent("rev"), _doc("rev", "Use Skill(a).\n"))
    git_repo.write(_skill("a"), _doc("a", "Use Agent(subagent_type: rev).\n"))
    _commit(git_repo.root, "add both edges")
    outcome = _outcome(git_repo, (_modify(_agent("rev")), _modify(_skill("a"))), base)
    assert sorted(f.path for f in outcome.findings) == [_agent("rev"), _skill("a")]


def test_a_changed_component_that_cannot_be_read_is_a_finding_not_a_skip(git_repo):
    git_repo.write("elsewhere.md", "Call Skill(a).\n")
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    (git_repo.root / _skill("b")).parent.mkdir(parents=True)
    (git_repo.root / _skill("b")).symlink_to(git_repo.root / "elsewhere.md")
    _commit(git_repo.root, "add a symlinked skill")
    outcome = _outcome(git_repo, (ChangedPath("A", None, _skill("b")),), base)
    (finding,) = outcome.findings
    assert finding.rule == RULE and finding.path == _skill("b") and finding.line is None
    assert "symlink" in finding.evidence and _skill("b") not in outcome.checked


def test_a_pr_that_touches_no_component_reads_nothing(git_repo):
    git_repo.write("README.md", "x")
    git_repo.write(_skill("a"), _doc("a", "Call Skill(nope).\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write("README.md", "y")
    _commit(git_repo.root, "docs")
    outcome = _outcome(git_repo, (_modify("README.md"),), base)
    assert outcome.findings == () and outcome.checked == ()


def test_running_out_of_the_scan_budget_fails_the_run_closed(monkeypatch, git_repo):
    git_repo.write(_skill("a"), _doc("a", "Call Skill(b).\n"))
    git_repo.write(_skill("b"), _doc("b", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    monkeypatch.setattr(rv, "MAX_PARSE_SECONDS", -1.0)
    with pytest.raises(RuntimeError, match="budget"):
        rv.run_verifiers(git_repo.root, (_modify(_skill("a")),), base)


def test_the_same_head_gives_the_same_call_graph_findings(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Call Skill(b) and Skill(nope).\n"))
    git_repo.write(_skill("b"), _doc("b", "Back to Skill(a).\n"))
    _commit(git_repo.root, "add")
    change = (_modify(_skill("a")), _modify(_skill("b")))
    assert rv.run_verifiers(git_repo.root, change, None) == rv.run_verifiers(
        git_repo.root, tuple(reversed(change)), None
    )


def test_hostile_call_syntax_stays_fast():
    import time

    started = time.perf_counter()
    # under the 250,000-character parse cap that run_verifiers applies before any parse
    rv.extract_calls("Skill(" * 40_000 + "\n")
    rv.extract_calls("Agent(" * 40_000 + "subagent_type\n")
    rv.extract_calls(("Skill(a" + " " * 300 + "\n") * 700)
    assert time.perf_counter() - started < 10


# A security pass (static) found these. Each is a way for a PR to add a call problem unseen, or a
# call the extractor missed, in a form the real tree actually uses.


def test_a_prefixed_call_to_a_plugin_of_this_marketplace_is_resolved_and_can_close_a_cycle(
    git_repo,
):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    git_repo.write(_skill("b"), _doc("b", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Call Skill(demo-kit:b).\n"))
    git_repo.write(_skill("b"), _doc("b", "Call Skill(demo-kit:a).\n"))
    _commit(git_repo.root, "prefixed cycle")
    outcome = _outcome(git_repo, (_modify(_skill("a")), _modify(_skill("b"))), base)
    assert sorted(f.path for f in outcome.findings) == [_skill("a"), _skill("b")]


def test_a_typo_behind_a_marketplace_prefix_is_a_dangling_call(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Call Skill(demo-kit:nope).\n"))
    _commit(git_repo.root, "typo")
    (finding,) = _outcome(git_repo, (_modify(_skill("a")),), base).findings
    assert "demo-kit:nope" in finding.evidence and "does not exist" in finding.evidence


def test_a_prefixed_call_is_resolved_against_the_named_plugin_only(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    git_repo.write("plugins/other-kit/skills/z/SKILL.md", _doc("z", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Call Skill(other-kit:a).\n"))
    _commit(git_repo.root, "wrong plugin")
    assert len(_outcome(git_repo, (_modify(_skill("a")),), base).findings) == 1


def test_a_prefixed_agent_call_is_resolved(git_repo):
    git_repo.write(_agent("rev"), _doc("rev", "Nothing.\n"))
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", 'Agent(subagent_type: "demo-kit:rev")\n'))
    _commit(git_repo.root, "call")
    assert _outcome(git_repo, (_modify(_skill("a")),), base).findings == ()


def test_a_skill_and_an_agent_with_the_same_name_calling_each_other_are_a_cycle(git_repo):
    git_repo.write(_skill("audit"), _doc("audit", "Nothing.\n"))
    git_repo.write(_agent("audit"), _doc("audit", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("audit"), _doc("audit", "Use Agent(subagent_type: audit).\n"))
    git_repo.write(_agent("audit"), _doc("audit", "Use Skill(audit).\n"))
    _commit(git_repo.root, "same-name cycle")
    outcome = _outcome(git_repo, (_modify(_skill("audit")), _modify(_agent("audit"))), base)
    assert sorted(f.path for f in outcome.findings) == [_agent("audit"), _skill("audit")]


def test_a_call_made_live_by_an_edit_on_another_line_is_reported_for_the_whole_file(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Intro.\n\n    Skill(nope) is only an example.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Intro.\nThen:\n    Skill(nope) is only an example.\n"))
    _commit(git_repo.root, "turn the code block into a paragraph")
    (finding,) = _outcome(git_repo, (_modify(_skill("a")),), base).findings
    assert finding.line is None and "line 7" in finding.evidence


def test_a_multi_line_call_reports_the_line_of_its_target():
    text = _doc("a", 'Dispatch Agent({\n  subagent_type: "nope",\n})\n')
    assert _calls(text) == [("agent", "nope", 6)]


def test_a_lone_carriage_return_makes_the_line_unknown_instead_of_wrong():
    assert [(c.target, c.line) for c in rv.extract_calls("Intro\rSee Skill(b).\r")] == [("b", None)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<details>\nRun Skill(x)\n</details>\n", [("skill", "x", 2)]),
        ("<div>\n<!-- Skill(a) -->\nSkill(b)\n</div>\n", [("skill", "b", 3)]),
        ("Text[^1]\n\n[^1]: Skill(x)\n", [("skill", "x", 3)]),
        ("Text[^1]\n\n[^1]: Note.\n\n    Then Agent(subagent_type: x).\n", [("agent", "x", 5)]),
        ('Agent(description: "Audit (phase 5)", subagent_type: "x")', [("agent", "x", 1)]),
        ('Agent(prompt: "' + "p" * 600 + '", subagent_type: "x")', [("agent", "x", 1)]),
        ('Agent({"subagent_type": "x"})', [("agent", "x", 1)]),
        ('Skill(args: "y", skill: x)', [("skill", "x", 1)]),
        ("Skill({ skill: x })", [("skill", "x", 1)]),
        ("Skill(name: x)", []),
    ],
)
def test_calls_in_html_blocks_footnotes_and_other_argument_shapes_are_found(text, expected):
    assert _calls(text) == expected


def test_a_call_key_far_from_its_call_is_not_borrowed():
    text = "Agent(prompt: only)\n" + "filler " * 800 + "\nsubagent_type: nope\n"
    assert _calls(text) == []


def test_a_file_name_is_not_a_skill_target(git_repo):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Open Skill(notes.md).\n"))
    _commit(git_repo.root, "edit")
    assert _outcome(git_repo, (_modify(_skill("a")),), base).findings == ()


def test_more_call_problems_than_the_cap_fail_the_run_closed(monkeypatch, git_repo):
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "Skill(n1) Skill(n2) Skill(n3)\n"))
    _commit(git_repo.root, "three dangling calls")
    monkeypatch.setattr(rv, "MAX_CALL_FINDINGS", 2)
    with pytest.raises(RuntimeError, match="call problems"):
        rv.run_verifiers(git_repo.root, (_modify(_skill("a")),), base)


def test_the_findings_pass_checks_the_deadline_and_builds_the_graph_once(monkeypatch):
    import time

    monkeypatch.setattr(rv, "MAX_CALL_FINDINGS", 100_000)

    nodes = [("skill", f"s{n}") for n in range(120)]
    paths = {node: f"plugins/demo-kit/skills/{node[1]}/SKILL.md" for node in nodes}
    edges = [
        rv._Edge(paths[src], src, rv.Call("skill", dst[1], 1), dst)
        for src in nodes
        for dst in nodes
        if src != dst
    ]
    started = time.perf_counter()
    findings = rv.check_call_graph(
        edges, [], paths, frozenset(paths.values()), time.monotonic() + 60
    )
    assert len(findings) == 120 * 119 and time.perf_counter() - started < 10
    with pytest.raises(RuntimeError, match="budget"):
        rv.check_call_graph(edges, [], paths, frozenset(paths.values()), time.monotonic() - 1)


def test_a_parser_fault_in_a_changed_doc_is_a_finding_and_in_an_unchanged_doc_is_ignored(
    monkeypatch, git_repo
):
    real = rv.extract_calls

    def faulty(text):
        if "BOOM" in text:
            raise RecursionError("deep")
        return real(text)

    git_repo.write(_skill("old"), _doc("old", "BOOM\n"))
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    git_repo.write(_skill("a"), _doc("a", "BOOM and Skill(b)\n"))
    _commit(git_repo.root, "edit")
    monkeypatch.setattr(rv, "extract_calls", faulty)
    outcome = _outcome(git_repo, (_modify(_skill("a")),), base)
    (finding,) = outcome.findings
    assert (
        finding.path == _skill("a")
        and finding.rule == RULE
        and "RecursionError" in finding.evidence
    )
    assert _skill("a") not in outcome.checked


def test_a_symlinked_component_directory_is_a_blocking_finding(git_repo):
    git_repo.write("elsewhere/foo/SKILL.md", _doc("foo", "Skill(a)\n"))
    git_repo.write(_skill("a"), _doc("a", "Nothing.\n"))
    base = _commit(git_repo.root, "base")
    link = git_repo.root / "plugins/demo-kit/skills/foo"
    link.symlink_to(git_repo.root / "elsewhere/foo")
    _commit(git_repo.root, "link a skill directory")
    outcome = _outcome(git_repo, (ChangedPath("A", None, "plugins/demo-kit/skills/foo"),), base)
    (finding,) = outcome.findings
    assert finding.rule == RULE and finding.path == "plugins/demo-kit/skills/foo"
    assert "symlink" in finding.evidence


def test_a_call_after_a_fence_with_a_leading_space_is_a_call_because_that_is_not_frontmatter():
    assert _calls(" ---\nSkill(nope)\n---\n") == [("skill", "nope", 2)]


def test_a_call_inside_real_frontmatter_after_a_bom_is_not_a_call():
    text = "﻿---\nname: x\ndescription: 'Use Skill(nope)'\n---\nBody.\n"
    assert _calls(text) == []


def test_a_call_in_the_body_after_bom_frontmatter_keeps_its_file_line():
    text = "﻿---\nname: x\ndescription: d\n---\nSee Skill(b).\n"
    assert _calls(text) == [("skill", "b", 5)]


def test_a_fence_made_of_lone_carriage_returns_does_not_hide_a_call():
    assert _calls("---\rSkill(evil)\r---\n") == [("skill", "evil", None)]
