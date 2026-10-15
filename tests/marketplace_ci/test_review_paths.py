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
        f"See [x][ref] and\n\n[ref]: {ESCAPE}",
        f'<a href="{ESCAPE}">guide</a>',
        f"<img src='{ESCAPE}'>",
        "See `${CLAUDE_SKILL_DIR}/../../docs/guide.md`.",
        "See ${CLAUDE_SKILL_DIR}/../../docs/guide.md.",
        "See **${CLAUDE_SKILL_DIR}/../../docs/guide.md**, then more",
        "See ${CLAUDE_SKILL_DIR}/../../docs/guide.md: it explains.",
        "See [x](%2E%2E/%2E%2E/docs/guide.md).",
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


# --- a security pass found these evasions; each one renders as a live link under CommonMark -----
# (checked against markdown-it-py, a CommonMark parser, before the cases were written).

DESTINATION = "plugins/demo-kit/docs/guide.md"


def _escapes(findings):
    return [f for f in findings if f.rule == "r34-escaping-path"]


@pytest.mark.parametrize(
    "fenced_line",
    [
        'cat "${CLAUDE_SKILL_DIR}/../../docs/guide.md"',
        "cat ${CLAUDE_SKILL_DIR}/../../docs/guide.md",
        'cat "${CLAUDE_SKILL_DIR}"/../../docs/guide.md',
        "cat $CLAUDE_SKILL_DIR/../../docs/guide.md",
        'cat "$CLAUDE_SKILL_DIR"/../../docs/guide.md',
    ],
)
def test_a_skill_dir_path_is_read_inside_a_fenced_block(fenced_line):
    text = _lines("```bash", fenced_line, "```")
    (finding,) = _check(text)
    assert finding.line == 2


@pytest.mark.parametrize(
    "line",
    [
        "See ${CLAUDE_SKILL_DIR}/../../docs/guide.md.",
        'See "${CLAUDE_SKILL_DIR}"/../../docs/guide.md.',
        "See $CLAUDE_SKILL_DIR/../../docs/guide.md.",
    ],
)
def test_the_quoted_and_unbraced_skill_dir_forms_are_read_in_prose(line):
    assert len(_check(_lines(line))) == 1


def test_a_fenced_link_is_still_skipped_but_a_fenced_skill_dir_path_inside_the_skill_passes():
    text = _lines("```bash", "cat ${CLAUDE_SKILL_DIR}/references/other.md", f"[x]({ESCAPE})", "```")
    assert _check(text) == ()


@pytest.mark.parametrize(
    "text",
    [
        "[x](" + " " * 25 + ESCAPE + ")",
        "[x](" + ESCAPE + " " * 25 + ")",
        "[x](" + "./" * 160 + ESCAPE + ")",
        "[x](\n" + ESCAPE + ")",
        "[x](   \n   " + ESCAPE + ")",
        "[r]:\n  " + ESCAPE + "\n\n[r]",
        "> [r]: " + ESCAPE + "\n\n[r]",
        "- [r]: " + ESCAPE + "\n\n[r]",
        "> > [r]: " + ESCAPE + "\n\n[r]",
        '<a href="' + "./" * 160 + ESCAPE + '">x</a>',
    ],
)
def test_links_in_the_forms_a_pattern_scanner_misses_are_read(text):
    assert len(_check(_lines(text))) >= 1


def test_a_destination_with_parentheses_is_read_whole():
    tree_extra = ["plugins/demo-kit/docs/x(1).md"]
    findings = _check(_lines("[x](../../docs/x(1).md)"), extra=tree_extra)
    (finding,) = findings
    assert "plugins/demo-kit/docs/x(1).md" in finding.evidence


def test_a_document_the_parser_fails_on_is_a_blocking_finding_not_a_pass(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(rv._MARKDOWN, "parse", fail)
    (finding,) = _escapes(_check(_lines(f"[x]({ESCAPE})")))
    assert finding.severity == "Major" and finding.line is None
    assert "could not be read" in finding.evidence and "ValueError" in finding.evidence


@pytest.mark.parametrize("text", ["> " * 3000 + "x", "![" * 100_000])
def test_nesting_deep_enough_to_overflow_the_parser_is_a_blocking_finding(text):
    (finding,) = _escapes(_check(text + "\n"))
    assert finding.severity == "Major" and "RecursionError" in finding.evidence


def test_a_document_over_the_parse_size_cap_is_a_blocking_finding_and_is_not_parsed(monkeypatch):
    monkeypatch.setattr(rv, "MAX_PARSE_BYTES", 50)
    (finding,) = _escapes(_check(_lines(f"[x]({ESCAPE})", "x" * 60)))
    assert finding.severity == "Major" and "larger than" in finding.evidence


def test_a_document_after_the_parse_time_budget_is_a_blocking_finding():
    (finding,) = _escapes(
        rv.check_escaping_paths(SKILL, _lines("fine"), _tree(), frozenset(), parse=False)
    )
    assert finding.severity == "Major" and "budget" in finding.evidence


def test_the_parse_time_budget_is_enforced_across_the_docs_of_a_run(monkeypatch, git_repo):
    git_repo.stage(".claude/marketplace-sync.json", json.dumps({"scripts_mirrors": []}))
    other = "plugins/demo-kit/skills/demo/references/other.md"
    git_repo.write(other, _lines("Fine."))
    git_repo.write(REFERENCE, _lines("Fine."))
    base = _commit(git_repo.root, "base")
    monkeypatch.setattr(rv, "MAX_PARSE_SECONDS", -1.0)
    # reference files only: a changed SKILL.md also starts the call-graph scan (its own budget)
    change = (ChangedPath("M", other, other), ChangedPath("M", REFERENCE, REFERENCE))
    outcome = rv.run_verifiers(git_repo.root, change, base)[2]
    assert sorted(f.path for f in outcome.findings) == sorted([other, REFERENCE])
    assert all(f.severity == "Major" for f in outcome.findings)


@pytest.mark.parametrize(
    "text",
    [
        "Read \\`[guide](" + ESCAPE + ")\\` now.",
        'Read <b title="`">[guide](' + ESCAPE + ')<b title="`"> now.',
    ],
)
def test_backticks_that_do_not_open_a_code_span_do_not_hide_a_link(text):
    assert len(_check(_lines(text))) == 1


def test_a_real_code_span_still_hides_its_link_after_the_escape_handling():
    assert _check(_lines(f"Read `[guide]({ESCAPE})` now.")) == ()
    assert _check(_lines(f"Read \\\\`[guide]({ESCAPE})` now.")) == ()


def test_a_fence_inside_an_html_comment_does_not_hide_the_rest_of_the_file():
    text = _lines("<!--", "```", "-->", f"[x]({ESCAPE})")
    (finding,) = _check(text)
    assert finding.line == 4


def test_a_fence_that_never_closes_is_code_to_the_end_as_a_renderer_shows_it():
    assert _check(_lines("```", f"[x]({ESCAPE})", "more")) == ()


def test_the_finding_cites_the_resolved_target_so_creating_it_makes_the_finding_the_prs():
    (finding,) = _check(_lines(f"[x]({ESCAPE})"))
    assert DESTINATION in finding.components


def test_the_finding_cites_the_fence_lines_above_it_so_editing_them_makes_it_the_prs():
    text = _lines("```", "code", "```", f"[x]({ESCAPE})")
    (finding,) = _check(text)
    assert f"{SKILL}:1" in finding.components and f"{SKILL}:3" in finding.components


def test_scanning_for_the_new_forms_stays_fast():
    import time

    started = time.perf_counter()
    _check("](" + " " * 30 + "\n" + ("](\n" * 50_000))
    _check(("> " * 5000) + "[r]:" + "\n")
    _check("[r]:\n" * 50_000)
    _check("$CLAUDE_SKILL_DIR/" * 50_000 + "\n")
    _check("\\`" * 100_000 + "\n")
    assert time.perf_counter() - started < 5


# A second security pass (static) claimed these. Each renders as a live link under CommonMark, so
# the scanner must read it; a pattern scanner could not, which is why R34 now uses a parser.


@pytest.mark.parametrize(
    "text",
    [
        "`a\\` [x](" + ESCAPE + ") `",
        '`<b x="`"> [x](' + ESCAPE + ") `",
        "Write comments as `<!--`.\n\n```\n-->\n```\n[x](" + ESCAPE + ")\n```\n```",
        "<div>\n```\n</div>\n\n[x](" + ESCAPE + ")\n\n<div>\n```\n</div>",
        '<div>\n```\n<a href="' + ESCAPE + '">z</a>\n```\n</div>',
        "   ```\n      ```\nx\n```\n[x](" + ESCAPE + ")\n```\n```",
        "intro ` text\nmore ` [x](" + ESCAPE + ") `",
        "[x](" + ESCAPE + "#((y)))",
        "[x](" + ESCAPE + "#\\()",
        "[x](<" + ESCAPE + "#\\>>)",
        "[x](" + ESCAPE + ' "a\\"b")',
        "[x](" + ESCAPE + '\n"title")',
        "[x]:" + " " * 21 + ESCAPE + "\n\n[x]",
        "- a\n  - b\n\n    [x]: " + ESCAPE + "\n\n[x]",
        "[foo\nbar]: " + ESCAPE + "\n\n[foo bar]",
        "[a\\]b]: " + ESCAPE + "\n\n[a\\]b]",
        '<a HREF="' + ESCAPE + '">x</a>',
        '<a   href  =  "' + ESCAPE + '">x</a>',
        '<video poster="' + ESCAPE + '"></video>',
        "[x](&#46;&#46;/&#46;&#46;/docs/guide.md)",
        "[x](&period;&period;/&period;&period;/docs/guide.md)",
        '<a href="&#46;&#46;/&#46;&#46;/docs/guide.md">x</a>',
        "[x](\\.\\./\\.\\./docs/guide.md)",
    ],
)
def test_every_form_a_commonmark_renderer_shows_as_a_link_is_read(text):
    findings = _escapes(_check(_lines(text)))
    assert findings and all(DESTINATION in f.components for f in findings)


def test_a_destination_on_the_next_line_is_reported_where_it_is_and_cites_its_paragraph():
    text = _lines("Intro line", "See [guide](", "../../docs/guide.md)")
    (finding,) = _check(text)
    assert finding.line == 3 and {f"{SKILL}:1", f"{SKILL}:2"} <= set(finding.components)


def test_a_long_external_url_is_not_a_finding():
    url = "https://img.shields.io/badge/" + "a-b" * 200
    assert _check(_lines(f"![badge]({url})", f"[r]: {url}", f'<img src="{url}">')) == ()


def test_the_finding_cap_fails_closed_with_a_file_level_finding():
    text = "\n\n".join(f"[x{n}]({ESCAPE})" for n in range(rv._MAX_PATH_FINDINGS + 5)) + "\n"
    findings = _escapes(_check(text))
    assert len(findings) == rv._MAX_PATH_FINDINGS + 1
    assert findings[-1].line is None and findings[-1].severity == "Major"


def test_a_paragraph_too_long_to_cite_gives_one_file_level_finding_not_a_pass():
    text = _lines(*[f"[x{n}]({ESCAPE})" for n in range(rv.MAX_CONTEXT_LINES + 5)])
    (finding,) = _escapes(_check(text))
    assert finding.line is None and finding.severity == "Critical"


def test_html_in_a_comment_is_not_a_link():
    assert _check(_lines(f'<!-- <a href="{ESCAPE}">x</a> -->', f"<!-- [x]({ESCAPE}) -->")) == ()


def test_hostile_html_blocks_stay_fast():
    import time

    started = time.perf_counter()
    _check("<div>\n" + "<a " * 80_000 + "\n")
    _check("<div>\n" + '<a href="' * 40_000 + "\n")
    _check("<div>\n" + "<!--" * 80_000 + "\n")
    assert time.perf_counter() - started < 10


def test_a_document_just_under_the_parse_cap_parses_in_bounded_time():
    import time

    started = time.perf_counter()
    _check("[a](x" * (rv.MAX_PARSE_BYTES // 5) + "\n")
    assert time.perf_counter() - started < 10


# A third security pass (static) found places where a renderer shows a link that a plain CommonMark
# parse does not: GFM footnotes and tables, YAML frontmatter, HTML raw-text and CDATA modes.


@pytest.mark.parametrize(
    "text",
    [
        "See note.[^1]\n\n[^1]: [guide](" + ESCAPE + ")\n",
        "See note.[^1]\n\n[^1]: Note.\n\n    More [guide](" + ESCAPE + ").\n",
        '<xmp>\n<a href="' + ESCAPE + '">g</a>\n',
        '<textarea>\n<a href="' + ESCAPE + '">g</a>\n',
        '<script>\n<a href="' + ESCAPE + '">g</a>\n',
        '<title>\n<a href="' + ESCAPE + '">g</a>\n',
        '<plaintext>\n<a href="' + ESCAPE + '">g</a>\n',
        'x <![CDATA[ > <a href="' + ESCAPE + '">g</a> ]]> y',
        "| a | b | c |\n|---|---|---|\n| `x | [doc](" + ESCAPE + ") | y` |\n",
        "---\nnote: |\n  <!--\n---\n[g](" + ESCAPE + ")\n",
        "[g](../../docs/.../../guide.md)",
        "[g](../../docs/*/../guide.md)",
        "[g](../../docs/{x}/../guide.md)",
        "[g](../../docs/$x/../guide.md)",
        "[g](../../docs/%3Cx%3E/../guide.md)",
        '<a href=".&#9;./.&#9;./docs/guide.md">g</a>',
        '<a href=".\t./.\n./docs/guide.md">g</a>',
        '<picture><source srcset="'
        + ESCAPE
        + " 1x, "
        + ESCAPE
        + ' 2x"><img src="ok.png"></picture>',
    ],
)
def test_links_a_renderer_shows_but_a_plain_commonmark_parse_hides_are_read(text):
    findings = _escapes(_check(_lines(text)))
    assert findings and all(DESTINATION in f.components for f in findings)


def test_a_percent_encoded_hash_is_part_of_the_file_name_not_a_fragment():
    extra = ["plugins/demo-kit/docs/x#y.md"]
    (finding,) = _check(_lines("[g](../../docs/x%23y.md)"), extra=extra)
    assert "plugins/demo-kit/docs/x#y.md" in finding.components


@pytest.mark.parametrize(
    "line",
    [
        "[t](references/<topic>.md) and [y](../../docs/*.md)",
        "[t](references/.../x.md)",
        "[t](references/{name}.md)",
        "[t](references/$X.md)",
    ],
)
def test_a_placeholder_that_survives_normalisation_is_still_skipped(line):
    assert _check(_lines(line)) == ()


def test_a_token_without_a_line_map_keeps_its_links_as_file_level_sites(monkeypatch):
    from markdown_it.token import Token

    link = Token("link_open", "a", 1, attrs={"href": ESCAPE})
    inline = Token("inline", "", 0, children=[link], map=None)
    monkeypatch.setattr(rv._MARKDOWN, "parse", lambda text, env=None: [inline])
    (finding,) = _check(_lines("anything"))
    assert finding.line is None


def test_nesting_past_the_old_limit_is_not_silently_dropped():

    nested = "".join("  " * depth + "- item\n" for depth in range(60))
    text = nested + "\n" + "  " * 60 + f"- [x]({ESCAPE})\n"
    findings = _check(text)
    assert findings and findings[0].rule == "r34-escaping-path"


def test_the_parser_hardening_is_pinned_to_the_installed_python():
    assert rv._html_urls('<noembed><a href="x.md">') == ["x.md"]
    assert rv._html_urls("<![CDATA[ > <a href='y.md'> ]]>") == ["y.md"]
    assert rv._html_urls('<TEXTAREA><a HREF="z.md">') == ["z.md"]


# --- a finding is the PR's when the change ALTERS what is live, wherever the edit sits ----------

INDENTED = "Example:\n\n    [g](" + ESCAPE + ")\n"


def _known(base_text, path=SKILL):
    return rv.check_escaping_paths(path, base_text, _tree(), frozenset())


def test_a_link_exposed_by_an_edit_elsewhere_is_a_file_level_finding():
    head = "- Example:\n\n    [g](" + ESCAPE + ")\n"
    (finding,) = rv.check_escaping_paths(SKILL, head, _tree(), frozenset(), known=_known(INDENTED))
    assert finding.line is None and finding.severity == "Critical"


def test_a_reference_definition_exposed_by_an_inserted_blank_line_is_file_level():
    base = "<div>\n[g]: " + ESCAPE + "\n</div>\n\n[g]\n"
    head = "<div>\n\n[g]: " + ESCAPE + "\n</div>\n\n[g]\n"
    findings = rv.check_escaping_paths(SKILL, head, _tree(), frozenset(), known=_known(base))
    assert findings and all(f.line is None for f in findings)


def test_a_finding_that_was_already_there_keeps_its_line():
    text = _lines("Intro.", "", f"[g]({ESCAPE})")
    (finding,) = rv.check_escaping_paths(SKILL, text, _tree(), frozenset(), known=_known(text))
    assert finding.line == 3


def test_with_no_base_text_every_finding_is_file_level():
    (finding,) = rv.check_escaping_paths(
        SKILL, _lines(f"[g]({ESCAPE})"), _tree(), frozenset(), known=()
    )
    assert finding.line is None


def test_run_verifiers_reads_the_base_of_a_modified_doc_and_flags_an_exposure(git_repo):
    git_repo.stage(".claude/marketplace-sync.json", json.dumps({"scripts_mirrors": []}))
    git_repo.write("plugins/demo-kit/docs/guide.md", "guide")
    git_repo.write(SKILL, _skill_text("Example:", "", f"    [g]({ESCAPE})"))
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, _skill_text("- Example:", "", f"    [g]({ESCAPE})"))
    _commit(git_repo.root, "head")
    outcome = rv.run_verifiers(git_repo.root, (ChangedPath("M", SKILL, SKILL),), base)[2]
    (finding,) = outcome.findings
    assert finding.rule == "r34-escaping-path" and finding.line is None


def test_run_verifiers_keeps_the_line_of_a_finding_the_base_already_had(git_repo):
    git_repo.stage(".claude/marketplace-sync.json", json.dumps({"scripts_mirrors": []}))
    git_repo.write("plugins/demo-kit/docs/guide.md", "guide")
    git_repo.write(SKILL, _skill_text("Bad: [g](" + ESCAPE + ")."))
    base = _commit(git_repo.root, "base")
    git_repo.write(SKILL, _skill_text("Bad: [g](" + ESCAPE + ").", "", "Added line."))
    _commit(git_repo.root, "head")
    outcome = rv.run_verifiers(git_repo.root, (ChangedPath("M", SKILL, SKILL),), base)[2]
    (finding,) = outcome.findings
    assert finding.line is not None


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
    # The reference file's link was already in the base, so it keeps its line; the skill's new link
    # is reported for the whole file, with its line in the evidence.
    assert sorted((f.path, f.line) for f in outcome.findings) == [(SKILL, None), (REFERENCE, 1)]
    (new,) = [f for f in outcome.findings if f.path == SKILL]
    assert "at line 6" in new.evidence
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
