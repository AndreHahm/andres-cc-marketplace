#!/usr/bin/env python3
"""Execution-based fixture tests for cross-model-review's Preflight logic.

Unlike scripts/smoke_test.py (structural checks on SKILL.md's own text), this suite extracts the
actual bash commands the skill documents and runs them for real against constructed scratch git
repositories, asserting on exit codes and output. This exists because a reasoning-only check --
"read the skill and explain what happens in scenario X" -- is structurally unable to catch a bug
where the skill's prose *accurately* describes broken behavior: an agent faithfully reading it just
confirms the buggy behavior as correct, since "what the text says happens" and "what actually
happens" are the same wrong thing. Two real bugs (a grep -E no-match aborting the whole chained
Preflight invocation, and git add -N aborting on a deletion-only SCOPE) survived 10 rounds of
100%-passing reasoning-based skill-tester evals for exactly this reason -- this suite is the second,
execution-based check that catches what those can't.

Extraction, not reimplementation: the Inputs section's canonical diff-build bash block and Preflight
step 6's grep pattern are pulled directly out of SKILL.md's own text via regex, not hand-copied --
if the skill's actual commands change, these fixtures exercise the new commands automatically rather
than silently testing stale logic.
"""

import pathlib
import re
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
BASH = "bash"


def extract_inputs_block() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("## Inputs")
    end = text.find("## Preflight")
    if start == -1 or end == -1:
        raise RuntimeError("Could not locate the Inputs..Preflight span in SKILL.md")
    section = text[start:end]
    match = re.search(r"```bash\n(.*?)```", section, re.DOTALL)
    if not match:
        raise RuntimeError("Could not find the Inputs section's fenced bash block")
    return match.group(1)


def extract_dispatcher_check_command() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    for match in re.finditer(r"```bash\n(.*?)```", text, re.DOTALL):
        block = match.group(1)
        if "DISPATCHER_TOUCHED" in block:
            return block.strip()
    raise RuntimeError("Could not find Preflight step 6's dispatcher-trust check bash block")


def run_bash(repo_dir: pathlib.Path, script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, "-c", script],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def init_repo(repo_dir: pathlib.Path) -> None:
    # core.excludesFile="" isolates fixtures from whatever global gitignore the machine running
    # this test happens to have configured -- without it, a global rule (e.g. a personal "*.log"
    # exclude) can silently contaminate a fixture in a way that has nothing to do with the skill
    # itself, exactly as happened during this suite's own development.
    run_bash(
        repo_dir,
        "git init -q -b main && git config user.email a@a.com && git config user.name a "
        '&& git config core.excludesFile ""',
    )


def commit_all(repo_dir: pathlib.Path, message: str) -> None:
    run_bash(repo_dir, f"git add -A && git commit -q -m {message!r}")


def diff_build_chain(base: str = "main", scope: str = "", extra: str = "") -> str:
    """Reconstruct just the Inputs section's canonical diff-build, from the actually-extracted
    command block, plus a scenario-specific assertion appended at the end. Isolated from the
    dispatcher-trust grep (see preflight_chain below) so a diff-build scenario isn't confounded
    by a separate, unrelated bug in step 6."""
    inputs_block = extract_inputs_block()
    scope_line = f"SCOPE={scope!r}\n" if scope else "SCOPE=\n"
    return f"""
set -e
BASE={base!r}
{scope_line}
{inputs_block}
echo "DIFF_BUILD_COMPLETED"
{extra}
"""


def preflight_chain(base: str = "main", scope: str = "", extra: str = "") -> str:
    """Reconstruct the *full* single &&-chained Preflight invocation SKILL.md's own intro
    mandates -- diff-build through the dispatcher-trust check -- for scenarios specifically about
    whether the whole chain reaches its closing echo, not just the diff-build portion. The
    dispatcher-trust check itself is extracted verbatim (extract_dispatcher_check_command), not
    reimplemented, so a change to its actual command is exercised automatically."""
    inputs_block = extract_inputs_block()
    dispatcher_check = extract_dispatcher_check_command()
    scope_line = f"SCOPE={scope!r}\n" if scope else "SCOPE=\n"
    return f"""
set -e
BASE={base!r}
{scope_line}
{inputs_block}
UNSCOPED_CHANGED_FILES=$(git diff --name-only "$MERGE_BASE")
{dispatcher_check}
echo "PREFLIGHT_CHAIN_COMPLETED"
{extra}
"""


def test_untracked_file_included():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "new_untracked.txt").write_text("brand new\n", encoding="utf-8")
        marker = "UNTRACKED_VISIBLE=yes"
        check = f'git diff "$MERGE_BASE" | grep -q new_untracked.txt && echo {marker}'
        result = run_bash(repo, diff_build_chain(extra=check))
        if marker not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"untracked file not visible in diff {detail}"
        return True, "untracked file correctly appears in the diff"


def test_deletion_only_scope_does_not_abort():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        run_bash(repo, "rm f.txt")
        result = run_bash(repo, diff_build_chain(scope="f.txt"))
        if "DIFF_BUILD_COMPLETED" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"diff-build aborted on a deletion-only SCOPE {detail}"
        return True, "diff-build tolerates a SCOPE naming only a deletion"


def test_index_copy_failure_is_disclosed():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        run_bash(
            repo, 'mv "$(git rev-parse --git-path index)" "$(git rev-parse --git-path index).bak"'
        )
        result = run_bash(
            repo,
            diff_build_chain(extra='echo "INDEX_COPY_FAILED_VALUE=${INDEX_COPY_FAILED:-UNSET}"'),
        )
        if "DIFF_BUILD_COMPLETED" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"chain aborted when the real index couldn't be copied {detail}"
        if "INDEX_COPY_FAILED_VALUE=1" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"INDEX_COPY_FAILED was not set when the copy failed {detail}"
        return True, "a failed index copy sets INDEX_COPY_FAILED=1 instead of continuing silently"


def test_gitignored_tracked_file_reports_modified():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "tracked-fixture.data").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        run_bash(repo, "echo 'tracked-fixture.data' >> .git/info/exclude")
        (repo / "tracked-fixture.data").write_text("line1\nline2\n", encoding="utf-8")
        result = run_bash(
            repo,
            diff_build_chain(extra='git diff --name-status "$MERGE_BASE" -- tracked-fixture.data'),
        )
        status_line = next(
            (line for line in result.stdout.splitlines() if "tracked-fixture.data" in line), ""
        )
        if status_line.startswith("M"):
            return True, "gitignored-but-tracked file correctly reports as Modified"
        detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
        return False, f"expected 'M\\ttracked-fixture.data', got {status_line!r} {detail}"


def test_sparse_checkout_entry_not_reported_deleted():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "a").mkdir()
        (repo / "b").mkdir()
        (repo / "a" / "f").write_text("x", encoding="utf-8")
        (repo / "b" / "f").write_text("x", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        run_bash(repo, "git update-index --skip-worktree b/f")
        (repo / "b" / "f").unlink()
        (repo / "a" / "f").write_text("y", encoding="utf-8")
        result = run_bash(
            repo,
            diff_build_chain(extra='git diff --name-status "$MERGE_BASE"'),
        )
        lines = result.stdout.splitlines()
        b_reported = any("b/f" in line for line in lines)
        a_modified = any(line.startswith("M") and "a/f" in line for line in lines)
        if b_reported:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"sparse-excluded b/f incorrectly appeared in the diff {detail}"
        if not a_modified:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"expected 'M a/f' in the diff {detail}"
        return True, "sparse-checkout skip-worktree entry is not misreported as deleted"


MARKER_ECHO = 'echo "DISPATCHER_TOUCHED_VALUE=${DISPATCHER_TOUCHED:-UNSET}"'


def test_dispatcher_grep_no_match_does_not_abort_chain():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "f.txt").write_text("line1\nline2\n", encoding="utf-8")
        result = run_bash(repo, preflight_chain(extra=MARKER_ECHO))
        if "PREFLIGHT_CHAIN_COMPLETED" not in result.stdout:
            return False, (
                "chain aborted on the NORMAL no-match case (the common case for nearly every "
                f"review) -- (exit={result.returncode}): {result.stdout}\n{result.stderr}"
            )
        if "DISPATCHER_TOUCHED_VALUE=UNSET" not in result.stdout:
            return False, f"DISPATCHER_TOUCHED was set despite no match: {result.stdout!r}"
        return (
            True,
            "chain completes and DISPATCHER_TOUCHED stays unset when the grep finds no match",
        )


def test_dispatcher_grep_match_detected():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        (repo / "plugins" / "codex-kit" / "scripts").mkdir(parents=True)
        (repo / "plugins" / "codex-kit" / "scripts" / "lib.mjs").write_text("x\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "plugins" / "codex-kit" / "scripts" / "lib.mjs").write_text(
            "x\ny\n", encoding="utf-8"
        )
        result = run_bash(repo, preflight_chain(extra=MARKER_ECHO))
        if "PREFLIGHT_CHAIN_COMPLETED" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"chain should complete when the grep matches {detail}"
        if "DISPATCHER_TOUCHED_VALUE=1" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"DISPATCHER_TOUCHED was not set to 1 despite a match {detail}"
        return True, "chain completes and DISPATCHER_TOUCHED=1 is set when the grep matches"


def test_real_index_untouched_after_run():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "new_untracked.txt").write_text("brand new\n", encoding="utf-8")
        run_bash(repo, preflight_chain())
        status = run_bash(repo, "git status --porcelain")
        if "?? new_untracked.txt" not in status.stdout:
            return False, f"real index was mutated by the throwaway-index trick: {status.stdout!r}"
        return True, "real .git/index is untouched after the run -- file still shows as untracked"


def extract_planner_block() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    for match in re.finditer(r"```bash\n(.*?)```", text, re.DOTALL):
        if "git-review-scope.py" in match.group(1):
            return match.group(1).strip()
    raise RuntimeError("Could not find Preflight step 1's review-scope-planner bash block")


def planner_repo(repo: pathlib.Path) -> None:
    # The planner is run by its repo-relative path, so the scratch repo carries a copy of it on
    # main, committed before the branch, so it is not part of the diff under review.
    init_repo(repo)
    script = SKILL_DIR.parent.parent / "scripts" / "git-review-scope.py"
    dest = repo / "plugins" / "git-kit" / "scripts"
    dest.mkdir(parents=True)
    (dest / "git-review-scope.py").write_bytes(script.read_bytes())
    (repo / "f.txt").write_text("line1\n", encoding="utf-8")
    commit_all(repo, "init")
    run_bash(repo, "git checkout -qb feature")


def planner_chain(extra: str, *, scope: str = "") -> str:
    inputs_block = extract_inputs_block()
    planner = extract_planner_block()
    return f"""
set -e
BASE=main
SCOPE={scope!r}
{inputs_block}
{planner}
echo "PLANNER_CHAIN_COMPLETED"
{extra}
"""


def test_planner_sees_untracked_files_and_diff_goes_to_a_file():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        planner_repo(repo)
        (repo / "new_untracked.txt").write_text("brand new\n", encoding="utf-8")
        check = (
            'grep -q new_untracked.txt "$RUN/manifest-1.json" && '
            'grep -q new_untracked.txt "$RUN/full.diff" && echo PLANNER_SAW_UNTRACKED'
            ' && grep -rq new_untracked.txt "$RUN/diffs-1" && echo SLICE_DIFF_WRITTEN'
            ' && echo "STATUS=$DIFF_STATUS PLAN=${PLAN_FAILED:-0} TOUCHED=${PLANNER_TOUCHED:-0}"'
        )
        result = run_bash(repo, planner_chain(check))
        ok = "PLANNER_SAW_UNTRACKED" in result.stdout and "SLICE_DIFF_WRITTEN" in result.stdout
        if not ok or "STATUS=0 PLAN=0 TOUCHED=0" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"planner/diff-file step wrong {detail}"
        return (
            True,
            "planner lists the untracked file, writes slice diffs, diff text goes to a file",
        )


def test_planner_failure_sets_a_flag_instead_of_aborting_the_chain():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        planner_repo(repo)
        (repo / "new_untracked.txt").write_text("brand new\n", encoding="utf-8")
        # A scope starting with ':' (pathspec magic) is valid for git but refused by the planner.
        result = run_bash(repo, planner_chain('echo "PLAN=${PLAN_FAILED:-0}"', scope=":/"))
        if "PLANNER_CHAIN_COMPLETED" not in result.stdout or "PLAN=1" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"chain aborted or PLAN_FAILED unset {detail}"
        return True, "an unplannable scope sets PLAN_FAILED=1 and the chain still completes"


def test_dispatcher_check_matches_a_case_variant_path():
    with tempfile.TemporaryDirectory() as tmp:
        script = (
            'UNSCOPED_CHANGED_FILES="Plugins/Codex-Kit/Assets/x.json"\n'
            + extract_dispatcher_check_command()
            + '\necho "TOUCHED=${DISPATCHER_TOUCHED:-0}"\n'
        )
        result = run_bash(pathlib.Path(tmp), "set -e\n" + script)
        if "TOUCHED=1" not in result.stdout:
            return (
                False,
                f"case-variant dispatcher path not matched: {result.stdout} {result.stderr}",
            )
        return (
            True,
            "a case-variant dispatcher path (case-insensitive filesystem) sets DISPATCHER_TOUCHED",
        )


def test_a_diff_touching_the_planner_skips_it_and_sets_the_flag():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        planner_repo(repo)
        variant = repo / "PLUGINS" / "Git-Kit" / "Scripts"  # a case variant of the planner folder
        variant.mkdir(parents=True)
        (variant / "json.py").write_text("x = 1\n", encoding="utf-8")
        check = (
            'echo "TOUCHED=${PLANNER_TOUCHED:-0} PLAN=${PLAN_FAILED:-0}"; ls "$RUN/manifest-1.json"'
        )
        result = run_bash(repo, planner_chain(check))
        bad = "TOUCHED=1 PLAN=0" not in result.stdout or "manifest-1.json" in result.stdout
        if bad or result.returncode == 0 and "No such file" not in result.stderr:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"planner ran or flag unset despite a changed planner folder {detail}"
        return (
            True,
            "a changed planner folder (any case) sets PLANNER_TOUCHED and the planner does not run",
        )


CHECKS = [
    test_planner_sees_untracked_files_and_diff_goes_to_a_file,
    test_planner_failure_sets_a_flag_instead_of_aborting_the_chain,
    test_a_diff_touching_the_planner_skips_it_and_sets_the_flag,
    test_dispatcher_check_matches_a_case_variant_path,
    test_untracked_file_included,
    test_deletion_only_scope_does_not_abort,
    test_index_copy_failure_is_disclosed,
    test_gitignored_tracked_file_reports_modified,
    test_sparse_checkout_entry_not_reported_deleted,
    test_dispatcher_grep_no_match_does_not_abort_chain,
    test_dispatcher_grep_match_detected,
    test_real_index_untouched_after_run,
]


def main():
    failed = False
    for check in CHECKS:
        try:
            ok, message = check()
        except Exception as exc:  # noqa: BLE001 -- report any fixture-setup error as a failure, not a crash
            ok, message = False, f"fixture raised {exc!r}"
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
