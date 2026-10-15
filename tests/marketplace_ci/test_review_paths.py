"""The R34 path verifier (issue #576, #568 Phase 2): `r34-escaping-path`. A relative link or
`${CLAUDE_SKILL_DIR}` path in a skill's SKILL.md or references/*.md that resolves outside the skill
folder may land only in the plugin-root references/ or assets/ folder, or in scripts/ for a plugin
the base's `.claude/marketplace-sync.json` lists under `scripts_mirrors`. Dead links are NOT checked
here: on the real tree 10 of 11 were illustrative examples only a human can tell from a real miss.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci import review_verifiers as rv
from scripts.marketplace_ci.git_state import ChangedPath
from scripts.marketplace_ci.review import gate_decision

SKILL = "plugins/demo-kit/skills/demo/SKILL.md"
REFERENCE = "plugins/demo-kit/skills/demo/references/notes.md"
EXISTING = [
    SKILL,
    REFERENCE,
    "plugins/demo-kit/skills/demo/references/other.md",
    "plugins/demo-kit/skills/sibling/SKILL.md",
    "plugins/demo-kit/skills/sibling/references/x.md",
    "plugins/demo-kit/references/shared.md",
    "plugins/demo-kit/assets/logo.png",
    "plugins/demo-kit/scripts/tool.sh",
    "plugins/demo-kit/docs/guide.md",
    "plugins/other-kit/references/shared.md",
    "docs/ci.md",
    ".github/pull_request_template.md",
    "README.md",
]


def _tree(extra=()):
    return rv.RepoTree([*EXISTING, *extra])


def _check(text, path=SKILL, mirrors=(), extra=()):
    return rv.check_escaping_paths(path, text, _tree(extra), frozenset(mirrors))


def _lines(*lines):
    return "\n".join(lines) + "\n"


# --- allowed targets ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    [
        "references/other.md",
        "./references/other.md",
        "../../references/shared.md",
        "../../assets/logo.png",
        "../../references/shared.md#heading",
        "SKILL.md",
        "${CLAUDE_SKILL_DIR}/references/other.md",
        "${CLAUDE_SKILL_DIR}/../../references/shared.md",
    ],
)
def test_targets_inside_the_skill_or_the_shared_plugin_folders_pass(target):
    assert _check(_lines(f"See [x]({target}) for more.")) == ()
    assert _check(_lines(f"Read `{target}` first.")) == ()


def test_scripts_are_allowed_only_for_a_plugin_listed_in_scripts_mirrors():
    text = _lines("Run [tool](../../scripts/tool.sh).")
    assert _check(text, mirrors=["demo-kit"]) == ()
    (finding,) = _check(text, mirrors=["other-kit"])
    assert finding.rule == "r34-escaping-path"


# --- escaping targets --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    [
        "../../docs/guide.md",
        "../sibling/references/x.md",
        "../sibling/SKILL.md",
        "../../../other-kit/references/shared.md",
        "../../../../docs/ci.md",
        "../../../../README.md",
    ],
)
def test_paths_that_leave_the_skill_for_anything_else_are_critical_findings(target):
    (finding,) = _check(_lines("Intro.", f"See [guide]({target})."))
    assert finding.rule == "r34-escaping-path" and finding.severity == "Critical"
    assert finding.rule_class == "graph" and finding.source == "script"
    assert finding.line == 2 and finding.path == SKILL
    assert gate_decision(finding, in_diff=True).outcome == "block"
    assert gate_decision(finding, in_diff=False).outcome == "notice"


def test_a_path_that_resolves_only_at_the_repo_root_still_leaves_the_skill():
    (finding,) = _check(_lines("Template: [t](.github/pull_request_template.md)."))
    assert finding.rule == "r34-escaping-path"


def test_an_obfuscated_path_that_comes_back_inside_the_skill_is_a_finding():
    (finding,) = _check(_lines("See [me](references/../SKILL.md)."))
    assert "obfuscated" in finding.evidence or ".." in finding.evidence


def test_a_variable_path_that_escapes_is_a_finding():
    (finding,) = _check(_lines("Read `${CLAUDE_SKILL_DIR}/../../docs/guide.md` first."))
    assert finding.line == 1


def test_every_escaping_target_on_a_line_is_reported():
    text = _lines("See [a](../../docs/guide.md) and [b](../sibling/SKILL.md).")
    assert len(_check(text)) == 2


# --- other forms of the same links --------------------------------------------------------------

ESCAPE = "../../docs/guide.md"


@pytest.mark.parametrize(
    "line",
    [
        f'See [x]({ESCAPE} "a title").',
        f"See [x]({ESCAPE} 'a title').",
        f"See [x](  {ESCAPE}  ).",
        f"See [x](<{ESCAPE}>).",
        f"See [x]({ESCAPE}#heading).",
        f"See [x]({ESCAPE}#*).",
        f"[![badge](../../assets/logo.png)]({ESCAPE})",
        f"See [a [b] c]({ESCAPE}).",
        f"See [x][ref] and\n[ref]: {ESCAPE}",
        f'<a href="{ESCAPE}">guide</a>',
        f"<img src='{ESCAPE}'>",
        "See `${CLAUDE_SKILL_DIR}/../../docs/guide.md`.",
        "See ${CLAUDE_SKILL_DIR}/../../docs/guide.md.",
        "See **${CLAUDE_SKILL_DIR}/../../docs/guide.md**, then more",
        "See ${CLAUDE_SKILL_DIR}/../../docs/guide.md: it explains.",
        "See [x](%2E%2E/%2E%2E/docs/guide.md).",
        "See [x](..\\..\\docs\\guide.md).",
        "See [x](/plugins/demo-kit/docs/guide.md).",
    ],
)
def test_the_other_ways_to_write_a_link_are_read(line):
    findings = _check(_lines(line))
    assert len(findings) >= 1 and findings[0].rule == "r34-escaping-path"


def test_an_escape_inside_a_longer_code_span_run_is_read_as_live_text():
    text = _lines(f"A `` ` `` B [x]({ESCAPE}) C `y`")
    assert len(_check(text)) == 1
    quoted = _lines(f"Quoted ``[x]({ESCAPE})`` is code.")
    assert _check(quoted) == ()


def test_a_four_space_indented_fence_does_not_switch_the_check_off_for_the_file():
    text = _lines("Intro", "", "    ```", "", f"[x]({ESCAPE})")
    assert len(_check(text)) == 1


def test_a_fenced_example_after_a_normal_fence_is_still_skipped():
    text = _lines("```markdown", f"[x]({ESCAPE})", "```", f"[y]({ESCAPE})")
    (finding,) = _check(text)
    assert finding.line == 4


@pytest.mark.parametrize(
    "target",
    [
        "references/./../SKILL.md",
        "references/../references/other.md",
        "../../references/../assets/logo.png",
        "${CLAUDE_SKILL_DIR}/../demo/SKILL.md",
    ],
)
def test_more_obfuscated_paths_are_findings(target):
    assert len(_check(_lines(f"See [x]({target})."))) >= 1


def test_skill_files_in_other_letter_cases_are_in_scope():
    text = _lines(f"[x]({ESCAPE})")
    assert len(_check(text, path="plugins/demo-kit/skills/demo/skill.md")) == 1
    deeper = _lines("[x](../../../docs/guide.md)")
    assert len(_check(deeper, path="plugins/demo-kit/skills/demo/references/NOTES.MD")) == 1


def test_hostile_link_syntax_stays_fast():
    import time

    started = time.perf_counter()
    _check("[" * 300_000 + "](\n")
    _check("[](" * 100_000 + "\n")
    _check("](" * 100_000 + "\n")
    _check("`" * 200_000 + "\n" + ("`a" * 100_000) + "\n")
    assert time.perf_counter() - started < 5


def test_the_tree_answers_existence_for_files_and_folders_without_storing_prefixes():
    tree = rv.RepoTree(["a/b/c.md", "a/d.md", "e.md"])
    assert tree.exists("a/b/c.md") and tree.exists("a/b") and tree.exists("a")
    assert not tree.exists("a/b/c") and not tree.exists("a/bc") and not tree.exists("x")


# --- what is skipped ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "See [site](https://example.com/docs/guide.md).",
        "Mail [me](mailto:a@b.c).",
        "Jump to [top](#heading).",
        "Placeholder [x](references/<topic>.md) and [y](../../docs/*.md).",
        "Path [z](${CLAUDE_SKILL_DIR}/...) elided.",
        "Template [t]({{ url }}) rendered.",
        "Missing [m](references/nope.md) is a dead link, not this rule's business.",
        "Dead variable `${CLAUDE_SKILL_DIR}/references/nope.md` too.",
        "Absolute [a](/docs/guide.md) is a site path.",
        "Inline code `[x](../../docs/guide.md)` quotes a link.",
    ],
)
def test_urls_anchors_placeholders_dead_links_and_quoted_links_are_not_findings(line):
    assert _check(_lines(line)) == ()


def test_links_inside_fenced_blocks_are_not_checked():
    text = _lines("```markdown", "[x](../../docs/guide.md)", "```", "[ok](references/other.md)")
    assert _check(text) == ()


def test_a_link_after_a_fenced_block_is_checked_and_numbered():
    text = _lines("```", "code", "```", "[x](../../docs/guide.md)")
    (finding,) = _check(text)
    assert finding.line == 4


def test_only_skill_files_and_their_references_are_in_scope():
    text = _lines("[x](../../docs/guide.md)")
    from_reference = _lines("[x](../../../docs/guide.md)")
    assert _check(text, path="plugins/demo-kit/commands/run.md") == ()
    assert _check(text, path="plugins/demo-kit/skills/demo/scripts/note.md") == ()
    assert _check(text, path="docs/ci.md") == ()
    assert _check(text, path=".claude/skills/demo/SKILL.md") == ()
    assert len(_check(from_reference, path=REFERENCE)) == 1


def test_a_reference_file_resolves_links_from_its_own_folder():
    ok = _lines("[a](other.md) [b](../SKILL.md) [c](../../../references/shared.md)")
    assert _check(ok, path=REFERENCE) == ()
    bad = _lines("[a](../../sibling/SKILL.md)")
    assert len(_check(bad, path=REFERENCE)) == 1


def test_a_lone_carriage_return_does_not_hide_a_link_and_drops_the_line():
    (finding,) = _check("intro\r[x](../../docs/guide.md)\r")
    assert finding.line is None


def test_hostile_input_stays_fast():
    import time

    started = time.perf_counter()
    _check("[" * 100_000 + "\n" + "(" * 100_000 + "\n" + "`" * 100_000 + "\n")
    _check(("[a](references/other.md) " * 200 + "\n") * 500)
    assert time.perf_counter() - started < 5


# --- running over a change set -----------------------------------------------------------------


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo(git_repo, skill_text, mirrors=("demo-kit",)):
    git_repo.stage(".claude/marketplace-sync.json", json.dumps({"scripts_mirrors": list(mirrors)}))
    git_repo.write("docs/guide.md", "guide")
    git_repo.write("plugins/demo-kit/scripts/tool.sh", "#!/bin/sh\n")
    git_repo.write(SKILL, skill_text)
    git_repo.write(REFERENCE, _lines("[up](../../../../../docs/guide.md)"))
    return _commit(git_repo.root, "base")


def _skill_text(*lines):
    return "---\nname: demo\ndescription: " + "d" * 100 + "\n---\n" + _lines(*lines)


def test_run_verifiers_reports_escaping_paths_in_skills_and_their_references(git_repo):
    base = _repo(git_repo, _skill_text("Fine: [t](../../scripts/tool.sh)."))
    git_repo.write(
        SKILL,
        _skill_text("Fine: [t](../../scripts/tool.sh).", "Bad: [g](../../../../docs/guide.md)."),
    )
    _commit(git_repo.root, "change")
    change = (
        ChangedPath("M", SKILL, SKILL),
        ChangedPath("M", REFERENCE, REFERENCE),
    )
    outcome = rv.run_verifiers(git_repo.root, change, base)[2]
    assert outcome.name == "path-and-mirror"
    assert sorted((f.path, f.line) for f in outcome.findings) == [(SKILL, 6), (REFERENCE, 1)]
    assert outcome.checked == (SKILL, REFERENCE)


def test_the_allowed_scripts_folder_comes_from_the_base_not_the_pr(git_repo):
    """A PR that adds its plugin to scripts_mirrors must not widen its own allowed folders."""
    base = _repo(git_repo, _skill_text("Fine."), mirrors=())
    git_repo.stage(".claude/marketplace-sync.json", json.dumps({"scripts_mirrors": ["demo-kit"]}))
    git_repo.write(SKILL, _skill_text("Run [t](../../scripts/tool.sh)."))
    _commit(git_repo.root, "widen and link")
    outcome = rv.run_verifiers(git_repo.root, (ChangedPath("M", SKILL, SKILL),), base)[2]
    assert [f.rule for f in outcome.findings] == ["r34-escaping-path"]


def test_an_unreadable_mirror_config_in_the_base_allows_no_scripts_folder(git_repo):
    git_repo.stage(".claude/marketplace-sync.json", "{not json")
    git_repo.write("plugins/demo-kit/scripts/tool.sh", "#!/bin/sh\n")
    git_repo.write(SKILL, _skill_text("Run [t](../../scripts/tool.sh)."))
    base = _commit(git_repo.root, "base")
    outcome = rv.run_verifiers(git_repo.root, (ChangedPath("A", None, SKILL),), base)[2]
    assert [f.rule for f in outcome.findings] == ["r34-escaping-path"]


def test_a_doc_file_that_cannot_be_read_is_a_finding_not_a_pass(git_repo):
    git_repo.stage(".claude/marketplace-sync.json", json.dumps({"scripts_mirrors": []}))
    (git_repo.root / REFERENCE).parent.mkdir(parents=True, exist_ok=True)
    git_repo.write("elsewhere.md", "[x](../../docs/guide.md)\n")
    (git_repo.root / REFERENCE).symlink_to(git_repo.root / "elsewhere.md")
    git_repo.write(SKILL, _skill_text("Fine."))
    base = _commit(git_repo.root, "base")
    outcome = rv.run_verifiers(
        git_repo.root, (ChangedPath("A", None, REFERENCE), ChangedPath("A", None, SKILL)), base
    )[2]
    unreadable = [f for f in outcome.findings if f.path == REFERENCE]
    assert len(unreadable) == 1 and unreadable[0].severity == "Major" and unreadable[0].line is None
    assert "symlink" in unreadable[0].evidence
    assert REFERENCE not in outcome.checked


def test_unchanged_files_are_not_scanned(git_repo):
    base = _repo(git_repo, _skill_text("Bad: [g](../../../../docs/guide.md)."))
    outcome = rv.run_verifiers(git_repo.root, (), base)[2]
    assert outcome.findings == () and outcome.checked == ()
