"""git-kit's git-pr-body-waiver-check.py (merge-pr step 1.6): a PR-body edit must leave the waiver
sections reading the same, as CI's `_section_text` in review.py reads them."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.marketplace_ci import review

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-pr-body-waiver-check.py"


def _load():
    spec = importlib.util.spec_from_file_location("git_pr_body_waiver_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _load()
ARF = check.SECTIONS["Accepted Review Findings"]

WAIVER = "- naming plugins/x.md:12 – deferred #456"
BODY = (
    "## Summary\n\nText.\n\n<!-- guidance -->\n\n## Accepted Review Findings\n\n"
    f"{WAIVER}\n\n## Known CI Failures (Accepted)\n\nNone\n\n## Open Items\n\n- an item\n"
)


def test_the_patterns_are_the_ones_ci_uses():
    assert check.HTML_COMMENT.pattern == review._HTML_COMMENT.pattern
    assert check.HTML_COMMENT.flags == review._HTML_COMMENT.flags
    assert ARF.pattern == review._WAIVER_SECTION.pattern
    assert ARF.flags == review._WAIVER_SECTION.flags
    source = Path(review.__file__).read_text(encoding="utf-8")
    assert 're.search(r"^#{1,2}\\s", rest, re.MULTILINE)' in source
    assert check.SECTION_END.pattern == r"^#{1,2}\s"


@pytest.mark.parametrize(
    "body",
    [
        BODY,
        "",
        "## Open Items\n- x\n",
        "##\n\nAccepted Review Findings\n- a\n## Next\n",
        "<!--\n-->## Accepted Review Findings\n- b\n",
        "## <!--\n-->Accepted Review Findings\n- c\n",
        "##\tAccepted Review Findings\n- d\n",
        "##\u00a0Accepted Review Findings\n- e\n",
        "## accepted review findings\n- f\n### Sub\n- g\n# Top\n",
        "<!-- ## Accepted Review Findings\n- hidden -->\n## Accepted Review Findings\n- h\n",
        "## Accepted Review Findings\n<!-- never closed\n- i\n",
    ],
)
def test_the_section_reads_as_ci_reads_it(body):
    assert check.section_text(body, ARF) == review._section_text(body)


def test_an_open_items_edit_leaves_the_sections_unchanged():
    new = BODY.replace("- an item\n", "- an item\n- a new item\n")
    assert check.changed_sections(BODY, new) == []


@pytest.mark.parametrize(
    "new",
    [
        # A changed waiver line.
        BODY.replace(WAIVER, WAIVER.replace("#456", "#457")),
        # A section that was absent appears through a lower-case heading in Open Items.
        BODY.replace("- an item\n", f"- an item\n## accepted review findings\n{WAIVER}\n").replace(
            f"## Accepted Review Findings\n\n{WAIVER}\n\n", ""
        ),
        # Text after the known-failures heading.
        BODY.replace("None\n", "None\n- ci job x fails\n"),
    ],
)
def test_a_changed_section_is_reported(new):
    assert check.changed_sections(BODY, new) != []


@pytest.mark.parametrize(
    ("base", "new"),
    [
        # Split heading: `##` alone, the heading text further down; a line added below it.
        (
            "## Open Items\n\n##\n\nAccepted Review Findings\n- x\n",
            "## Open Items\n\n##\n\nAccepted Review Findings\n- x\n- y\n",
        ),
        # A heading that exists only once the comment before it is removed.
        (
            "<!--\n-->## Accepted Review Findings\n- x\n",
            "<!--\n-->## Accepted Review Findings\n- x\n- y\n",
        ),
        # Removing a comment opener exposes a commented-out section.
        (
            "<!--\n## Accepted Review Findings\n- x\n-->\n## Open Items\n",
            "\n## Accepted Review Findings\n- x\n-->\n## Open Items\n",
        ),
        # A tab and a non-breaking space after `##`.
        ("##\tAccepted Review Findings\n- x\n", "##\tAccepted Review Findings\n- x\n- y\n"),
        (
            "##\u00a0Known CI Failures (Accepted)\n- x\n",
            "##\u00a0Known CI Failures (Accepted)\n- y\n",
        ),
        # A `###` heading does not end the section.
        (
            "## Accepted Review Findings\n### Notes\n- x\n",
            "## Accepted Review Findings\n### Notes\n- y\n",
        ),
    ],
)
def test_the_security_review_counterexamples_are_caught(base, new):
    assert check.changed_sections(base, new) != []


def _run(tmp_path, base, new):
    base_file, new_file = tmp_path / "base.txt", tmp_path / "new.txt"
    base_file.write_bytes(base.encode())
    new_file.write_bytes(new.encode())
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(base_file), str(new_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_the_jq_newline_and_crlf_do_not_count_as_a_change(tmp_path):
    # --jq .body adds one newline to the base; the new body is written without it.
    base = BODY.rstrip("\n").replace("\n", "\r\n") + "\n"
    result = _run(tmp_path, base, BODY.rstrip("\n"))
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_waiver_change_exits_1_and_names_the_section(tmp_path):
    result = _run(tmp_path, BODY + "\n", BODY.replace("#456", "#457"))
    assert result.returncode == 1
    assert "changed: Accepted Review Findings" in result.stdout


def test_wrong_arguments_exit_2():
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, encoding="utf-8"
    )
    assert result.returncode == 2


@pytest.mark.parametrize(
    "body",
    [
        "## Accepted Review Findings\r\n- a\r\n## Next\r\n",
        "## Accepted Review Findings\n- a\r- b\n",
        "## Accepted Review Findings\n- a\n\r## Next\n- b\n",
    ],
)
def test_cr_bodies_read_as_ci_reads_them(body):
    assert check.section_text(body, ARF) == review._section_text(body)


@pytest.mark.parametrize(
    ("base", "new"),
    [
        # A lone CR splits a waiver line in CI's reader; removing or adding one is a change.
        (
            "## Accepted Review Findings\n- x #1\r- y #2\n",
            "## Accepted Review Findings\n- x #1- y #2\n",
        ),
        # A CR before `##` keeps that line inside CI's section.
        (
            "## Accepted Review Findings\n- x\n\r## Next\n- y\n",
            "## Accepted Review Findings\n- x\n\r## Next\n- z\n",
        ),
    ],
)
def test_a_lone_cr_change_is_reported(base, new):
    assert check.changed_sections(base, new) != []


def test_a_crlf_base_with_the_jq_newline_compares_equal(tmp_path):
    base = BODY.replace("\n", "\r\n") + "\n"
    result = _run(tmp_path, base, BODY)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_known_failures_heading_reads_as_ci_would_read_it(monkeypatch):
    # No CI code parses this section; read it with CI's own function and the same pattern.
    known = check.SECTIONS["Known CI Failures (Accepted)"]
    monkeypatch.setattr(review, "_WAIVER_SECTION", known)
    for body in [
        BODY,
        "##\n\nKnown CI Failures (Accepted)\n- a\n",
        "## known ci failures (accepted)\n- b\n# X\n",
    ]:
        assert check.section_text(body, known) == review._section_text(body)


@pytest.mark.parametrize("which", ["base", "new", "missing"])
def test_an_unreadable_or_missing_file_exits_2(tmp_path, which):
    base, new = tmp_path / "base.txt", tmp_path / "new.txt"
    base.write_bytes(b"\xff\xfe" if which == "base" else b"x")
    new.write_bytes(b"\xff\xfe" if which == "new" else b"x")
    if which == "missing":
        new.unlink()
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(base), str(new)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 2
    assert "cannot read" in result.stderr


_SEPS = ["\n", "\r\n", "\r", "\r\r\n", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", " ", " "]
_LINE = "- naming x.md:1 – accepted"


def _waivers(body):
    section = review.read_waiver_section(body, lambda _issue: True)
    return (section.waivers, section.malformed, section.tracked)


@pytest.mark.parametrize("a", _SEPS)
@pytest.mark.parametrize("b", _SEPS)
def test_an_unchanged_verdict_means_ci_reads_the_same_waivers(a, b):
    # Whenever the script says nothing changed, CI's own reader must agree, for every pair of
    # line separators (CRLF is the one pair the script may treat as LF).
    parts = [
        "## Summary",
        "x",
        "## Accepted Review Findings",
        _LINE,
        "- tracked #7: y",
        "## Open Items",
        "- i",
    ]
    base = a.join(parts) + a
    new = base.replace(a, b)
    if check.changed_sections(base, new) == []:
        assert _waivers(base) == _waivers(new)


@pytest.mark.parametrize(
    ("base", "new"),
    [
        (
            "## Accepted Review Findings\n- naming x.md:1 – \raccepted\n",
            "## Accepted Review Findings\n- naming x.md:1 – accepted\n",
        ),
        (
            "##\rAccepted Review Findings\n- naming x.md:1 – accepted\n",
            "##Accepted Review Findings\n- naming x.md:1 – accepted\n",
        ),
    ],
)
def test_the_security_review_lone_cr_counterexamples_are_caught(base, new):
    assert check.changed_sections(base, new) != []
