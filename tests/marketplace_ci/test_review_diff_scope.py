"""Diff-scoped blocking for `run-codex-review` (issue #525).

A finding blocks the job only when it sits on a line the PR changed. These
tests pin the three pieces that decide that: parsing `git diff -U0` into
changed new-side line ranges, splitting findings into in-diff / out-of-diff,
and the blocking verdict built on that split.

Fixtures reproduce PR #506 (run 38117400285), whose only Major findings sat on
lines 45, 93 and 113 of `skill-development/SKILL.md` while the PR added line 42.
"""

import json
import subprocess
import sys

import pytest

import scripts.marketplace_ci.review as review_module
from scripts.marketplace_ci.__main__ import _diff_scope, _finding_to_dict, main
from scripts.marketplace_ci.review import (
    Finding,
    blocking_findings,
    compute_changed_line_ranges,
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


# --- compute_changed_line_ranges (real git repo) ---------------------------------


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.md").write_text("".join(f"line {n}\n" for n in range(1, 11)))
    (tmp_path / "gone.md").write_text("x\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _base(repo):
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_compute_ranges_reports_added_and_edited_lines(repo):
    base = _base(repo)
    lines = [f"line {n}\n" for n in range(1, 11)]
    lines[2] = "edited\n"
    lines.insert(5, "inserted\n")
    (repo / "a.md").write_text("".join(lines))
    (repo / "new.md").write_text("one\ntwo\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "change")
    assert compute_changed_line_ranges(repo, base) == {
        "a.md": ((3, 3), (6, 6)),
        "new.md": ((1, 2),),
    }


def test_compute_ranges_leaves_out_a_deleted_file(repo):
    base = _base(repo)
    (repo / "gone.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "delete")
    assert compute_changed_line_ranges(repo, base) == {}


def test_compute_ranges_handles_a_non_ascii_filename(repo):
    base = _base(repo)
    (repo / "k\u00e4se.md").write_text("one\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "umlaut")
    assert compute_changed_line_ranges(repo, base) == {"k\u00e4se.md": ((1, 1),)}


def test_compute_ranges_is_unavailable_for_an_unresolvable_base(repo):
    assert compute_changed_line_ranges(repo, "0" * 40) is None


# --- _finding_to_dict ----------------------------------------------------------


def test_finding_to_dict_carries_the_in_diff_flag():
    finding = _finding(line=42)
    assert _finding_to_dict(finding, in_diff=True)["in_diff"] is True
    assert _finding_to_dict(finding, in_diff=False)["in_diff"] is False


def test_finding_to_dict_in_diff_is_null_when_ranges_are_unavailable():
    assert _finding_to_dict(_finding(line=42), in_diff=None)["in_diff"] is None


# --- Hardening from the security review of the gate (issue #525) --------------

HEADER = "--- a/{p}\n+++ b/{p}\n"


def test_parse_added_form_feed_does_not_desync_hunk_counting():
    # str.splitlines() splits on \x0c; git counts hunk lines by \n only. The
    # second added line looks like a file header and must stay hunk content.
    diff = (
        HEADER.format(p=SKILL)
        + "@@ -10,0 +11,2 @@\n+a\x0cb\n+++ b/README.md\n"
        + "@@ -200 +201 @@\n-old\n+new\n"
    )
    # The form feed also marks the file changed in full (a reviewer may count by it);
    # the point here is that the second hunk stays under SKILL and README.md never appears.
    assert parse_changed_line_ranges(diff) == {SKILL: ((11, 12), (201, 201), (1, sys.maxsize))}


def test_parse_unicode_line_separator_in_a_path_is_kept_whole():
    path = "plugins/x/ev\u2028il.sh"
    diff = HEADER.format(p=path) + "@@ -1 +1 @@\n-a\n+b\n"
    assert parse_changed_line_ranges(diff) == {path: ((1, 1),)}


def test_parse_strips_the_tab_git_appends_to_a_path_with_a_space():
    diff = "--- a/my hook.sh\t\n+++ b/my hook.sh\t\n@@ -1 +1 @@\n-a\n+b\n"
    assert parse_changed_line_ranges(diff) == {"my hook.sh": ((1, 1),)}


def test_parse_raises_when_a_non_header_line_follows_a_finished_hunk():
    diff = HEADER.format(p=SKILL) + "@@ -1 +1 @@\n-a\n+b\nstray line outside any hunk\n"
    with pytest.raises(ValueError):
        parse_changed_line_ranges(diff)


def test_parse_accepts_no_newline_marker_and_binary_and_mode_lines():
    diff = (
        "diff --git a/a.sh b/a.sh\nold mode 100644\nnew mode 100755\n"
        "diff --git a/b.bin b/b.bin\nBinary files a/b.bin and b/b.bin differ\n"
        + HEADER.format(p="c.md")
        + "@@ -1 +1 @@\n-a\n\\ No newline at end of file\n+b\n"
    )
    assert parse_changed_line_ranges(diff) == {"c.md": ((1, 1),)}


def test_compute_ranges_sees_hunks_despite_a_gitattributes_minus_diff(repo):
    base = _base(repo)
    (repo / ".gitattributes").write_text("* -diff\n")
    (repo / "a.md").write_text("changed\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "attrs")
    ranges = compute_changed_line_ranges(repo, base)
    assert ranges is not None
    assert ranges["a.md"] == ((1, 1),)


def test_compute_ranges_is_unavailable_when_git_cannot_start(tmp_path):
    assert compute_changed_line_ranges(tmp_path / "does-not-exist", "0" * 40) is None


def test_split_changed_path_without_hunks_is_in_diff_with_or_without_a_line():
    # A pure rename, mode change or empty file produces no hunk at all.
    no_hunk = "plugins/x/hooks/run.sh"
    with_line = _finding(path=no_hunk, line=3)
    without_line = _finding(path=no_hunk, line=None)
    in_diff, out = split_findings_by_diff([with_line, without_line], {}, changed_paths=(no_hunk,))
    assert in_diff == (with_line, without_line)
    assert out == ()


@pytest.mark.parametrize(
    "raw",
    [
        "./" + SKILL,
        "plugins/plugin-devkit//skills/skill-development/SKILL.md",
        SKILL + "/../SKILL.md",
    ],
)
def test_split_normalises_the_finding_path_before_lookup(raw):
    finding = _finding(path=raw, line=42)
    in_diff, _ = split_findings_by_diff([finding], PR506_RANGES)
    assert in_diff == (finding,)


def test_split_resolves_an_absolute_path_under_the_repo_root(tmp_path):
    target = tmp_path / SKILL
    target.parent.mkdir(parents=True)
    target.write_text("x\n")
    finding = _finding(path=str(target), line=42)
    in_diff, _ = split_findings_by_diff([finding], PR506_RANGES, repo_root=tmp_path)
    assert in_diff == (finding,)


def test_split_resolves_a_symlink_to_a_changed_file(tmp_path):
    target = tmp_path / SKILL
    target.parent.mkdir(parents=True)
    target.write_text("x\n")
    (tmp_path / "alias.md").symlink_to(target)
    finding = _finding(path="alias.md", line=42)
    in_diff, _ = split_findings_by_diff([finding], PR506_RANGES, repo_root=tmp_path)
    assert in_diff == (finding,)


def test_split_path_escaping_the_repo_root_stays_out_of_diff(tmp_path):
    finding = _finding(path="../../etc/passwd", line=1)
    _, out = split_findings_by_diff([finding], PR506_RANGES, repo_root=tmp_path)
    assert out == (finding,)


def test_critical_in_a_touched_file_blocks_even_outside_the_changed_lines():
    # A PR can delete a guard on one line and leave the exposed use elsewhere.
    critical = _finding("Critical", SKILL, 93, "injection-surface")
    assert blocking_findings([critical], PR506_RANGES) == (critical,)
    assert has_blocking_findings([critical], PR506_RANGES) is True


def test_major_outside_the_changed_lines_of_a_touched_file_does_not_block():
    assert blocking_findings([_finding("Major", SKILL, 93)], PR506_RANGES) == ()


def test_critical_in_a_file_the_pr_did_not_touch_does_not_block():
    other = _finding("Critical", "plugins/other-kit/skills/x/SKILL.md", 1)
    assert blocking_findings([other], PR506_RANGES) == ()


def test_critical_on_a_changed_path_without_hunks_blocks():
    critical = _finding("Critical", "plugins/x/run.sh", None)
    assert blocking_findings([critical], {}, changed_paths=("plugins/x/run.sh",)) == (critical,)


def test_blocking_findings_with_unavailable_ranges_keeps_every_critical_and_major():
    major, minor = _finding("Major", SKILL, 113), _finding("Minor", SKILL, 113)
    assert blocking_findings([major, minor], None) == (major,)


def test_finding_to_dict_carries_the_blocking_flag():
    assert _finding_to_dict(_finding(), in_diff=False, blocking=True)["blocking"] is True
    assert _finding_to_dict(_finding())["blocking"] is None


# --- Changed symlinks expose existing content as new (second security review) ---


def _symlink_repo(tmp_path):
    (tmp_path / "plugins/y/scripts").mkdir(parents=True)
    (tmp_path / "plugins/y/scripts/existing.sh").write_text("a\n" * 20)
    (tmp_path / "plugins/trusted/lib").mkdir(parents=True)
    (tmp_path / "plugins/trusted/lib/a.py").write_text("a\n" * 20)
    (tmp_path / "plugins/x/hooks").mkdir(parents=True)
    (tmp_path / "plugins/x/hooks/run.sh").symlink_to("../../y/scripts/existing.sh")
    (tmp_path / "plugins/evil").mkdir(parents=True)
    (tmp_path / "plugins/evil/lib").symlink_to("../trusted/lib")
    return tmp_path


LINK = "plugins/x/hooks/run.sh"
DIR_LINK = "plugins/evil/lib"
LINK_RANGES = {LINK: ((1, 1),), DIR_LINK: ((1, 1),)}
LINK_PATHS = (LINK, DIR_LINK)


@pytest.mark.parametrize(
    "cited",
    [LINK + "", "plugins/y/scripts/existing.sh"],
    ids=["link spelling", "target spelling"],
)
@pytest.mark.parametrize("severity", ["Major", "Critical"])
def test_finding_in_a_changed_file_symlink_blocks_whichever_spelling_it_cites(
    tmp_path, cited, severity
):
    root = _symlink_repo(tmp_path)
    finding = _finding(severity, cited, 7)
    found = blocking_findings([finding], LINK_RANGES, changed_paths=LINK_PATHS, repo_root=root)
    assert found == (finding,)


@pytest.mark.parametrize("cited", [DIR_LINK + "/a.py", "plugins/trusted/lib/a.py"])
def test_finding_under_a_changed_directory_symlink_blocks_whichever_spelling_it_cites(
    tmp_path, cited
):
    root = _symlink_repo(tmp_path)
    finding = _finding("Major", cited, 3)
    found = blocking_findings([finding], LINK_RANGES, changed_paths=LINK_PATHS, repo_root=root)
    assert found == (finding,)


def test_target_of_a_symlink_the_pr_did_not_change_stays_untouched(tmp_path):
    root = _symlink_repo(tmp_path)
    finding = _finding("Critical", "plugins/y/scripts/existing.sh", 7)
    assert blocking_findings([finding], {SKILL: ((42, 42),)}, repo_root=root) == ()


# --- _diff_scope: the handler's classification, in one place ------------------


def test_diff_scope_returns_blocking_and_in_diff_sets_from_a_real_diff(repo):
    base = _base(repo)
    lines = [f"line {n}\n" for n in range(1, 11)]
    lines[2] = "edited\n"
    (repo / "a.md").write_text("".join(lines))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "change")
    on_line = _finding("Major", "a.md", 3)
    off_line_major = _finding("Major", "a.md", 8)
    off_line_critical = _finding("Critical", "a.md", 9)
    blocking, in_diff, scoped = _diff_scope(
        (on_line, off_line_major, off_line_critical), repo, base, ("a.md",)
    )
    assert blocking == {on_line, off_line_critical}
    assert in_diff == {on_line}
    assert scoped is True


def test_diff_scope_falls_back_to_every_critical_and_major_when_git_fails(repo):
    major, minor = _finding("Major", "a.md", 8), _finding("Minor", "a.md", 8)
    blocking, in_diff, scoped = _diff_scope((major, minor), repo, "0" * 40, ("a.md",))
    assert blocking == {major}
    assert in_diff is None
    assert scoped is False


# --- Third security review: root symlink, odd line breaks, repo root, exit 2 ---


def test_finding_under_a_changed_symlink_to_the_filesystem_root_blocks(tmp_path):
    # The link target "/" must not turn the containment prefix into "//".
    inside = tmp_path / "plugins/foo/x.py"
    inside.parent.mkdir(parents=True)
    inside.write_text("x\n" * 20)
    link = tmp_path / "plugins/evil/root"
    link.parent.mkdir(parents=True)
    link.symlink_to("/")
    finding = _finding("Major", f"plugins/evil/root{inside}", 10)
    found = blocking_findings(
        [finding],
        {"plugins/evil/root": ((1, 1),)},
        changed_paths=("plugins/evil/root",),
        repo_root=tmp_path,
    )
    assert found == (finding,)


@pytest.mark.parametrize(
    "added",
    ["a\rb", "a\x0bb", "a\x0cb", "a\x1cb", "a\x1db", "a\x1eb", "a\x85b", "a\u2028b", "a\u2029b"],
)
def test_parse_marks_a_file_changed_in_full_when_a_diff_line_has_a_non_newline_break(added):
    # A reviewer may count lines by these breaks while git counts only "\n", so
    # the exact line match cannot be trusted for this file.
    diff = HEADER.format(p=SKILL) + f"@@ -3 +3 @@\n-old\n+{added}\n"
    ranges = parse_changed_line_ranges(diff)
    major_far_away = _finding("Major", SKILL, 500)
    assert split_findings_by_diff([major_far_away], ranges)[0] == (major_far_away,)


def test_parse_keeps_line_scoping_for_crlf_content():
    diff = HEADER.format(p=SKILL) + "@@ -3 +3 @@\n-old\r\n+new\r\n"
    ranges = parse_changed_line_ranges(diff)
    assert ranges == {SKILL: ((3, 3),)}
    assert split_findings_by_diff([_finding("Major", SKILL, 500)], ranges)[0] == ()


def test_parse_full_file_marker_only_applies_to_the_file_with_the_odd_break():
    diff = (
        HEADER.format(p=SKILL)
        + "@@ -3 +3 @@\n-old\n+a\u2028b\n"
        + HEADER.format(p=SCRIPT)
        + "@@ -3 +3 @@\n-old\n+new\n"
    )
    ranges = parse_changed_line_ranges(diff)
    assert split_findings_by_diff([_finding("Major", SCRIPT, 500)], ranges)[0] == ()
    assert len(split_findings_by_diff([_finding("Major", SKILL, 500)], ranges)[0]) == 1


def test_diff_scope_finds_symlinks_from_the_git_root_not_the_working_directory(repo):
    base = _base(repo)
    (repo / "link.md").symlink_to("a.md")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "link")
    (repo / "sub").mkdir()
    target_spelling = _finding("Major", "a.md", 3)
    blocking, _, _ = _diff_scope((target_spelling,), repo / "sub", base, ("link.md",))
    assert blocking == {target_spelling}


def _handler_repo(git_repo, hooks_lines):
    for name in ("plugin-rulebook-checker", "dependency-reviewer", "security-reviewer"):
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    git_repo.write("README.md", "original")
    git_repo.write("plugins/demo-kit/hooks/hooks.json", "".join(f"line {n}\n" for n in range(1, 8)))
    for args in (("add", "-A"), ("commit", "-q", "-m", "base")):
        subprocess.run(["git", *args], cwd=git_repo.root, check=True, capture_output=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()
    git_repo.write("plugins/demo-kit/hooks/hooks.json", "".join(hooks_lines))
    for args in (("add", "-A"), ("commit", "-q", "-m", "change")):
        subprocess.run(["git", *args], cwd=git_repo.root, check=True, capture_output=True)
    return base_sha


def _envelope(severity, line):
    return json.dumps(
        {
            "contract_version": "1",
            "dispatch": {
                "id": "d",
                "reviewer": "security-reviewer",
                "backend": "codex",
                "target_paths": ["plugins/demo-kit/hooks/hooks.json"],
            },
            "provenance": {
                "provider": "openai",
                "model": "m",
                "cli_version": "0",
                "execution_profile": "read-only",
            },
            "findings": [
                {
                    "id": "F1",
                    "severity": severity,
                    "axis": "R6",
                    "location": f"plugins/demo-kit/hooks/hooks.json:{line}",
                    "evidence": "e",
                    "finding": "f",
                    "fix": "m",
                    "confidence": "high",
                }
            ],
            "verdict": "reject",
            "inspection_limits": [],
        }
    ).encode()


def _run_handler(monkeypatch, git_repo, base_sha, envelope, tmp_path):
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=envelope, stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base_sha, "--output", str(out)])
    return rc, json.loads(out.read_text(encoding="utf-8"))


EDIT_LINE_2 = ["line 1\n", "EDITED\n"] + [f"line {n}\n" for n in range(3, 8)]


def test_handler_does_not_fail_on_a_major_outside_the_changed_lines(
    monkeypatch, git_repo, tmp_path
):
    base = _handler_repo(git_repo, EDIT_LINE_2)
    rc, result = _run_handler(monkeypatch, git_repo, base, _envelope("major", 6), tmp_path)
    assert rc == 0
    assert result["blocking"] is False
    assert result["diff_scoped"] is True
    assert result["findings"][0]["in_diff"] is False
    assert result["findings"][0]["blocking"] is False


def test_handler_fails_on_a_major_on_a_changed_line(monkeypatch, git_repo, tmp_path):
    base = _handler_repo(git_repo, EDIT_LINE_2)
    rc, result = _run_handler(monkeypatch, git_repo, base, _envelope("major", 2), tmp_path)
    assert rc == 1
    assert result["findings"][0]["in_diff"] is True
    assert result["findings"][0]["blocking"] is True


def test_handler_fails_on_a_critical_outside_the_changed_lines_of_a_touched_file(
    monkeypatch, git_repo, tmp_path
):
    base = _handler_repo(git_repo, EDIT_LINE_2)
    rc, result = _run_handler(monkeypatch, git_repo, base, _envelope("critical", 6), tmp_path)
    assert rc == 1
    assert result["findings"][0]["in_diff"] is False
    assert result["findings"][0]["blocking"] is True


def test_handler_exits_2_and_rewrites_the_output_when_classification_raises(
    monkeypatch, git_repo, tmp_path
):
    import scripts.marketplace_ci.__main__ as cli

    def boom(*args, **kwargs):
        raise RuntimeError("classification exploded")

    monkeypatch.setattr(cli, "_diff_scope", boom)
    base = _handler_repo(git_repo, EDIT_LINE_2)
    rc, result = _run_handler(monkeypatch, git_repo, base, _envelope("major", 6), tmp_path)
    assert rc == 2
    assert result["blocking"] is True
    assert "classification exploded" in result["error"]


# --- Open findings closed after the third review (items 2, 3, 4) -----------------


def test_symlink_recorded_in_git_is_found_when_the_checkout_holds_a_plain_file(repo):
    # core.symlinks=false checks a link out as a plain file holding its target
    # text, so os.path.islink is False; the git tree still says mode 120000.
    base = _base(repo)
    blob = (
        subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=repo,
            input=b"a.md",
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    _git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},link.md")
    _git(repo, "commit", "-q", "-m", "link")
    (repo / "link.md").write_text("a.md")
    assert not (repo / "link.md").is_symlink()
    ranges = compute_changed_line_ranges(repo, base)
    assert ranges is not None
    target_spelling = _finding("Major", "a.md", 3)
    found = blocking_findings([target_spelling], ranges, changed_paths=("link.md",), repo_root=repo)
    assert found == (target_spelling,)


def test_relative_git_symlink_target_resolves_from_the_links_directory(repo):
    (repo / "sub").mkdir()
    (repo / "sub/x.md").write_text("x\n" * 5)
    _git(repo, "add", ".")
    blob = (
        subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=repo,
            input=b"x.md",
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    _git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},sub/link.md")
    _git(repo, "commit", "-q", "-m", "link")
    (repo / "sub/link.md").write_text("x.md")
    cited = _finding("Major", "sub/x.md", 4)
    found = blocking_findings(
        [cited], {"sub/link.md": ((1, 1),)}, changed_paths=("sub/link.md",), repo_root=repo
    )
    assert found == (cited,)


def test_compute_ranges_is_unavailable_when_the_diff_exceeds_the_size_cap(repo, monkeypatch):
    base = _base(repo)
    (repo / "a.md").write_text("changed\n" * 50)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "big")
    assert compute_changed_line_ranges(repo, base) is not None
    monkeypatch.setattr(review_module, "_MAX_DIFF_BYTES", 10)
    assert compute_changed_line_ranges(repo, base) is None


def test_path_match_ignores_case_and_unicode_form_off_linux(monkeypatch):
    monkeypatch.setattr(review_module, "_FOLD_PATHS", True)
    ranges = {"plugins/Demo/Caf\u00e9.md": ((5, 5),)}
    case_variant = _finding("Major", "plugins/demo/caf\u00e9.md", 5)
    nfd_variant = _finding("Major", "plugins/Demo/Cafe\u0301.md", 5)
    in_diff, out = split_findings_by_diff([case_variant, nfd_variant], ranges)
    assert in_diff == (case_variant, nfd_variant)
    assert out == ()


def test_path_match_is_case_sensitive_on_linux(monkeypatch):
    monkeypatch.setattr(review_module, "_FOLD_PATHS", False)
    ranges = {"plugins/Demo/x.md": ((5, 5),)}
    other_case = _finding("Major", "plugins/demo/x.md", 5)
    assert split_findings_by_diff([other_case], ranges)[0] == ()


def test_fold_also_applies_to_changed_paths_and_blocking(monkeypatch):
    monkeypatch.setattr(review_module, "_FOLD_PATHS", True)
    critical = _finding("Critical", "PLUGINS/X/run.sh", None)
    assert blocking_findings([critical], {}, changed_paths=("plugins/x/run.sh",)) == (critical,)
