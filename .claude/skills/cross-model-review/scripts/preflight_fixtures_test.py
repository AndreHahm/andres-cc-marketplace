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
        (repo / "f.txt").write_text("line1\n")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "new_untracked.txt").write_text("brand new\n")
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
        (repo / "f.txt").write_text("line1\n")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        run_bash(repo, "rm f.txt")
        result = run_bash(repo, diff_build_chain(scope="f.txt"))
        if "DIFF_BUILD_COMPLETED" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"diff-build aborted on a deletion-only SCOPE {detail}"
        return True, "diff-build tolerates a SCOPE naming only a deletion"


def test_gitignored_tracked_file_reports_modified():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "tracked-fixture.data").write_text("line1\n")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        run_bash(repo, "echo 'tracked-fixture.data' >> .git/info/exclude")
        (repo / "tracked-fixture.data").write_text("line1\nline2\n")
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
        (repo / "a" / "f").write_text("x")
        (repo / "b" / "f").write_text("x")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        run_bash(repo, "git update-index --skip-worktree b/f")
        (repo / "b" / "f").unlink()
        (repo / "a" / "f").write_text("y")
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
        (repo / "f.txt").write_text("line1\n")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "f.txt").write_text("line1\nline2\n")
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
        (repo / "f.txt").write_text("line1\n")
        (repo / "plugins" / "codex-kit" / "scripts").mkdir(parents=True)
        (repo / "plugins" / "codex-kit" / "scripts" / "lib.mjs").write_text("x\n")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "plugins" / "codex-kit" / "scripts" / "lib.mjs").write_text("x\ny\n")
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
        (repo / "f.txt").write_text("line1\n")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "new_untracked.txt").write_text("brand new\n")
        run_bash(repo, preflight_chain())
        status = run_bash(repo, "git status --porcelain")
        if "?? new_untracked.txt" not in status.stdout:
            return False, f"real index was mutated by the throwaway-index trick: {status.stdout!r}"
        return True, "real .git/index is untouched after the run -- file still shows as untracked"


CHECKS = [
    test_untracked_file_included,
    test_deletion_only_scope_does_not_abort,
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
