"""Diff-scoped blocking for `run-codex-review` (issue #525).

A finding blocks the job only when it sits on a line the PR changed. These
tests pin the three pieces that decide that: parsing `git diff -U0` into
changed new-side line ranges, splitting findings into in-diff / out-of-diff,
and the blocking verdict built on that split.

Fixtures reproduce PR #506 (run 38117400285), whose only Major findings sat on
lines 45, 93 and 113 of `skill-development/SKILL.md` while the PR added line 42.
"""

import pytest

from scripts.marketplace_ci.review import (
    Finding,
    has_blocking_findings,
    parse_changed_line_ranges,
    split_findings_by_diff,
)

SKILL = "plugins/plugin-devkit/skills/skill-development/SKILL.md"
SKILL_MIRROR = ".claude/skills/skill-development/SKILL.md"
SCRIPT = "plugins/analysis-kit/scripts/anls_redact_secrets.py"


def _finding(severity="Major", path=SKILL, line=42, rule="activation", reviewer="skill-reviewer"):
    return Finding(
        reviewer=reviewer,
        severity=severity,
        rule=rule,
        path=path,
        evidence="e",
        remediation="r",
        line=line,
    )


# --- parse_changed_line_ranges -------------------------------------------------


def test_parse_single_added_line_without_count():
    diff = (
        f"diff --git a/{SKILL} b/{SKILL}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{SKILL}\n"
        f"+++ b/{SKILL}\n"
        "@@ -41,0 +42 @@ Identify the entry path and jump in:\n"
        "+- **Plain reusable instruction text** -> run /prompt-library\n"
    )
    assert parse_changed_line_ranges(diff) == {SKILL: ((42, 42),)}


def test_parse_hunk_with_counts_covers_new_side_inclusive():
    diff = (
        f"--- a/{SCRIPT}\n"
        f"+++ b/{SCRIPT}\n"
        "@@ -32 +37,6 @@ _PATTERNS = [\n"
        "-old\n" + "+new\n" * 6 + "@@ -50 +65,4 @@ _PATTERNS = [\n"
        "-old\n" + "+new\n" * 4
    )
    assert parse_changed_line_ranges(diff) == {SCRIPT: ((37, 42), (65, 68))}


def test_parse_pure_deletion_touches_the_join_point():
    # `+10,0` means nothing remains on the new side; the lines on either side
    # of the removal (10 and 11) are the ones whose context changed.
    diff = f"--- a/{SKILL}\n+++ b/{SKILL}\n@@ -10,2 +10,0 @@\n"
    assert parse_changed_line_ranges(diff) == {SKILL: ((10, 11),)}


def test_parse_new_file_covers_every_line():
    diff = (
        "diff --git a/plugins/x/new.md b/plugins/x/new.md\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/plugins/x/new.md\n"
        "@@ -0,0 +1,3 @@\n"
    )
    assert parse_changed_line_ranges(diff) == {"plugins/x/new.md": ((1, 3),)}


def test_parse_deleted_file_has_no_new_side_entry():
    diff = (
        "diff --git a/plugins/x/old.md b/plugins/x/old.md\n"
        "deleted file mode 100644\n"
        "--- a/plugins/x/old.md\n"
        "+++ /dev/null\n"
        "@@ -1,3 +0,0 @@\n"
    )
    assert parse_changed_line_ranges(diff) == {}


def test_parse_rename_keys_on_the_new_path():
    diff = (
        "diff --git a/plugins/x/old.md b/plugins/x/new.md\n"
        "similarity index 90%\n"
        "rename from plugins/x/old.md\n"
        "rename to plugins/x/new.md\n"
        "--- a/plugins/x/old.md\n"
        "+++ b/plugins/x/new.md\n"
        "@@ -5 +5 @@\n"
    )
    assert parse_changed_line_ranges(diff) == {"plugins/x/new.md": ((5, 5),)}


def test_parse_keeps_files_separate_and_mirror_paths_independent():
    diff = (
        f"--- a/{SKILL}\n+++ b/{SKILL}\n@@ -41,0 +42 @@\n+x\n"
        f"--- a/{SKILL_MIRROR}\n+++ b/{SKILL_MIRROR}\n@@ -41,0 +42 @@\n+x\n"
        f"--- a/{SCRIPT}\n+++ b/{SCRIPT}\n@@ -68,0 +87 @@\n+x\n"
    )
    assert parse_changed_line_ranges(diff) == {
        SKILL: ((42, 42),),
        SKILL_MIRROR: ((42, 42),),
        SCRIPT: ((87, 87),),
    }


def test_parse_empty_diff_gives_empty_mapping():
    assert parse_changed_line_ranges("") == {}


def test_parse_quoted_path_header_raises_so_the_caller_can_fail_closed():
    diff = '--- a/"x\\303\\244.md"\n+++ "b/x\\303\\244.md"\n@@ -1 +1 @@\n'
    with pytest.raises(ValueError):
        parse_changed_line_ranges(diff)


def test_parse_ignores_added_content_that_looks_like_a_header():
    # A changed line whose text starts with "+++ b/" or "@@ " must not be read
    # as structure: -U0 body lines are prefixed with "+" or "-", so the added
    # text below begins "++++ b/" and "+@@ ".
    diff = f"--- a/{SKILL}\n+++ b/{SKILL}\n@@ -1,0 +2,2 @@\n++++ b/other.md\n+@@ -9 +9 @@\n"
    assert parse_changed_line_ranges(diff) == {SKILL: ((2, 3),)}


# --- split_findings_by_diff ----------------------------------------------------

PR506_RANGES = {SKILL: ((42, 42),), SKILL_MIRROR: ((42, 42),), SCRIPT: ((37, 42), (87, 87))}


def test_split_puts_a_finding_on_a_changed_line_in_diff():
    on_line = _finding(line=42)
    in_diff, out_of_diff = split_findings_by_diff([on_line], PR506_RANGES)
    assert in_diff == (on_line,)
    assert out_of_diff == ()


@pytest.mark.parametrize("line", [41, 43, 45, 93, 113])
def test_split_match_is_exact_with_no_slack_window(line):
    # PR #506: line 45 is only 3 lines from the added line 42 and must stay
    # out-of-diff, so any slack of 3+ lines would defeat the fix.
    finding = _finding(line=line)
    in_diff, out_of_diff = split_findings_by_diff([finding], PR506_RANGES)
    assert in_diff == ()
    assert out_of_diff == (finding,)


def test_split_range_bounds_are_inclusive():
    first, last, past = (_finding(path=SCRIPT, line=n) for n in (37, 42, 43))
    in_diff, out_of_diff = split_findings_by_diff([first, last, past], PR506_RANGES)
    assert in_diff == (first, last)
    assert out_of_diff == (past,)


def test_split_finding_on_a_file_the_pr_did_not_touch_is_out_of_diff():
    untouched = _finding(severity="Critical", path="plugins/other-kit/skills/x/SKILL.md", line=1)
    in_diff, out_of_diff = split_findings_by_diff([untouched], PR506_RANGES)
    assert in_diff == ()
    assert out_of_diff == (untouched,)


def test_split_finding_without_a_line_on_a_changed_file_stays_in_diff():
    # No line to compare: fail toward blocking rather than hiding a file-level
    # finding (size, missing section) on a file the PR did change.
    file_level = _finding(path=SKILL, line=None, rule="size")
    in_diff, _ = split_findings_by_diff([file_level], PR506_RANGES)
    assert in_diff == (file_level,)


def test_split_finding_without_a_line_on_an_untouched_file_is_out_of_diff():
    file_level = _finding(path="plugins/other-kit/README.md", line=None, rule="size")
    _, out_of_diff = split_findings_by_diff([file_level], PR506_RANGES)
    assert out_of_diff == (file_level,)


def test_split_preserves_input_order_in_both_groups():
    a, b, c, d = (
        _finding(line=42, rule="a"),
        _finding(line=45, rule="b"),
        _finding(line=42, rule="c"),
        _finding(line=93, rule="d"),
    )
    in_diff, out_of_diff = split_findings_by_diff([a, b, c, d], PR506_RANGES)
    assert in_diff == (a, c)
    assert out_of_diff == (b, d)


def test_split_mirror_copy_is_judged_by_its_own_ranges():
    only_plugin_changed = {SKILL: ((42, 42),)}
    mirror = _finding(path=SKILL_MIRROR, line=42)
    in_diff, out_of_diff = split_findings_by_diff([mirror], only_plugin_changed)
    assert in_diff == ()
    assert out_of_diff == (mirror,)


# --- has_blocking_findings -----------------------------------------------------


def test_pr506_majors_outside_the_diff_do_not_block():
    findings = [
        _finding("Major", SKILL, 45, "activation", "skill-reviewer"),
        _finding("Major", SKILL, 93, "injection-surface", "security-reviewer"),
        _finding("Major", SKILL, 113, "tool-scoping", "skill-reviewer"),
        _finding("Minor", SCRIPT, 59, "credential-pii-leakage", "security-reviewer"),
    ]
    assert has_blocking_findings(findings, PR506_RANGES) is False


@pytest.mark.parametrize("severity", ["Critical", "Major"])
def test_critical_or_major_on_a_changed_line_blocks(severity):
    assert has_blocking_findings([_finding(severity, SKILL, 42)], PR506_RANGES) is True


def test_minor_on_a_changed_line_does_not_block():
    assert has_blocking_findings([_finding("Minor", SKILL, 42)], PR506_RANGES) is False


def test_one_in_diff_major_blocks_even_among_many_out_of_diff_ones():
    findings = [_finding("Major", SKILL, n) for n in (45, 93, 113)] + [_finding("Major", SKILL, 42)]
    assert has_blocking_findings(findings, PR506_RANGES) is True


def test_no_findings_does_not_block():
    assert has_blocking_findings([], PR506_RANGES) is False


def test_unavailable_ranges_fall_back_to_severity_only_blocking():
    # If the changed-line ranges could not be computed (None), every
    # Critical/Major keeps blocking exactly as before: a failed diff parse must
    # never turn into a silent pass.
    assert has_blocking_findings([_finding("Major", SKILL, 113)], None) is True
    assert has_blocking_findings([_finding("Minor", SKILL, 113)], None) is False


def test_empty_ranges_mean_nothing_changed_not_unavailable():
    assert has_blocking_findings([_finding("Critical", SKILL, 1)], {}) is False
