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
import shlex
import shutil
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
export CLAUDE_PLUGIN_ROOT={str(SKILL_DIR.parent.parent)!r}
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
export CLAUDE_PLUGIN_ROOT={str(SKILL_DIR.parent.parent)!r}
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


def test_intent_add_refusal_is_disclosed():
    """A refused run directory leaves untracked files out of the diff: the chain continues, but
    the refusal is recorded, unlike git's tolerated failure on a deletion-only scope (#637)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "new_untracked.txt").write_text("brand new\n", encoding="utf-8")
        chain = diff_build_chain(
            extra='echo "REFUSED_VALUE=${INTENT_ADD_REFUSED:-UNSET}"\n'
            'git diff "$MERGE_BASE" | grep -q new_untracked.txt && echo UNTRACKED_IN_DIFF || true'
        )
        marker = "RUN=$(mktemp -d)\n"
        if marker not in chain:
            return False, "could not find the run directory line in the extracted chain"
        result = run_bash(repo, chain.replace(marker, marker + 'chmod 750 "$RUN"\n'))
        if "DIFF_BUILD_COMPLETED" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"chain aborted when the helper refused {detail}"
        if "REFUSED_VALUE=1" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"INTENT_ADD_REFUSED was not set when the helper refused {detail}"
        if "UNTRACKED_IN_DIFF" in result.stdout:
            return False, "the untracked file reached the diff, so nothing was refused"
        return True, "a refused intent-add sets INTENT_ADD_REFUSED=1 instead of vanishing"


def test_an_intent_add_git_failure_is_disclosed():
    """A git failure other than the deletion-only case (here an index lock) sets the flag (#697)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "new_untracked.txt").write_text("brand new\n", encoding="utf-8")
        chain = diff_build_chain(extra='echo "REFUSED_VALUE=${INTENT_ADD_REFUSED:-UNSET}"')
        marker = "|| INDEX_COPY_FAILED=1\n"
        if marker not in chain:
            return False, "could not find the index copy line in the extracted chain"
        result = run_bash(repo, chain.replace(marker, marker + 'touch "$RUN/index.lock"\n'))
        if "REFUSED_VALUE=1" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"a locked index did not set INTENT_ADD_REFUSED {detail}"
        return True, "a git failure in the intent-add sets INTENT_ADD_REFUSED=1"


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
        if "git-review-scope-run.sh" in match.group(1):
            return match.group(1).strip()
    raise RuntimeError("Could not find Preflight step 1's review-scope-planner bash block")


def planner_repo(repo: pathlib.Path) -> None:
    # The planner runs from the installed plugin root (planner_chain exports it), never from a
    # path inside the repository under review, so the scratch repo carries no copy of it.
    init_repo(repo)
    (repo / "f.txt").write_text("line1\n", encoding="utf-8")
    commit_all(repo, "init")
    run_bash(repo, "git checkout -qb feature")


def planner_chain(extra: str, *, scope: str = "", approved: bool = False) -> str:
    inputs_block = extract_inputs_block()
    planner = extract_planner_block()
    plugin_root = SKILL_DIR.parent.parent
    return f"""
set -e
{"PLANNER_APPROVED=1" if approved else ""}
export CLAUDE_PLUGIN_ROOT={str(plugin_root)!r}
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


def test_the_planner_block_joined_with_and_and_still_completes():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        planner_repo(repo)
        lines = [ln for ln in extract_planner_block().splitlines() if ln.strip()]
        plugin_root = str(SKILL_DIR.parent.parent)
        script = (
            f"set -e\nexport CLAUDE_PLUGIN_ROOT={plugin_root!r}\nBASE=main\nSCOPE=\n"
            f"{extract_inputs_block()}\n" + " && ".join(lines) + "\n"
            'echo "CHAIN_DONE"\nls "$RUN/full.diff"\n'
        )
        result = run_bash(repo, script)
        if "CHAIN_DONE" not in result.stdout or "full.diff" not in result.stdout:
            detail = f"(exit={result.returncode}): {result.stdout}\n{result.stderr}"
            return False, f"a planner block joined with && did not reach its closing echo {detail}"
        return True, "a planner block joined with && still reaches its closing echo"


def _empty_variable_run(*, with_mirror: bool) -> str:
    """Run the extracted planner block with CLAUDE_PLUGIN_ROOT unset in a scratch repo, with or
    without a committed .claude mirror of the planner, and return its stdout."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        init_repo(repo)
        if with_mirror:
            mirror = repo / ".claude" / "scripts"
            mirror.mkdir(parents=True)
            for name in (
                "git-review-scope.py",
                "git-review-scope-run.sh",
                "git-review-copy-index.sh",
                "git-review-intent-add.sh",
                "git-review-run-dir.sh",
                "git-review-path.sh",
            ):
                source = SKILL_DIR.parent.parent / "scripts" / name
                (mirror / name).write_bytes(source.read_bytes())
        (repo / "f.txt").write_text("line1\n", encoding="utf-8")
        commit_all(repo, "init")
        run_bash(repo, "git checkout -qb feature")
        (repo / "new_untracked.txt").write_text("brand new\n", encoding="utf-8")
        script = (
            f"set -e\nunset CLAUDE_PLUGIN_ROOT\nBASE=main\nSCOPE=\n{extract_inputs_block()}\n"
            f'{extract_planner_block()}\necho "PLAN=${{PLAN_FAILED:-0}}"\n'
        )
        return run_bash(repo, script).stdout


def test_a_relative_path_entry_stops_the_chain():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        planner_repo(repo)
        for entry in (".", "node_modules/.bin", ""):
            result = run_bash(repo, f'PATH="{entry}:$PATH"\n' + planner_chain("true"))
            stopped = "PATH has an empty or relative entry" in result.stdout
            if not stopped or "PLANNER_CHAIN_COMPLETED" in result.stdout:
                return False, f"PATH entry {entry!r} did not stop the chain: {result.stdout}"
        return True, "an empty or relative PATH entry stops the chain"


def test_a_program_in_the_checkout_is_never_run():
    """Absolute PATH entries inside the checkout, or its main checkout, are dropped (#697)."""
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        repo, linked = base / "re'po", base / "linked"
        repo.mkdir()
        planner_repo(repo)
        run_bash(repo, "git worktree add -q --detach ../linked")
        run_bash(repo, "git worktree add -q --detach ../sibling")
        planted = repo / "bin dir"
        planted.mkdir()
        for name in ("git", "bash", "python3", "mktemp", "grep"):
            (planted / name).write_text('#!/bin/sh\ntouch "$0.ran"\n', encoding="utf-8")
            (planted / name).chmod(0o755)
        (base / "link").symlink_to(planted, target_is_directory=True)
        (repo / "sub").mkdir()
        echo = '\necho "FILTERED=${PATH_FILTERED:-0} PATH=$PATH"'
        outside = base / "outside"
        outside.mkdir()
        (outside / "git").write_text(f'#!/bin/sh\ntouch "{planted}/out.ran"\n', encoding="utf-8")
        (outside / "git").chmod(0o755)
        (repo / "out").symlink_to(outside, target_is_directory=True)
        sibling = base / "sibling" / "bin"
        sibling.mkdir()
        (sibling / "git").write_text(f'#!/bin/sh\ntouch "{planted}/sib.ran"\n', encoding="utf-8")
        (sibling / "git").chmod(0o755)
        entries = [planted, base / "link", base / "link" / ".." / "bin dir", repo / "out", sibling]
        for name, target in (("direct", planted / "git"), ("sib", sibling / "git")):
            (base / name).mkdir()
            (base / name / "git").symlink_to(target)
            entries.append(base / name)
        (base / "hop").mkdir()
        (base / "hop" / "git").symlink_to(pathlib.Path("..") / "direct" / "git")
        entries.append(base / "hop")
        (base / "touch").mkdir()
        (planted / "touch").write_text('#!/bin/sh\n: > "$0.ran"\n', encoding="utf-8")
        (planted / "touch").chmod(0o755)
        (base / "touch" / "touch").symlink_to(planted / "touch")
        entries.append(base / "touch")
        (base / "exe").mkdir()
        (base / "exe" / "git.exe").symlink_to(planted / "git")
        entries.append(base / "exe")
        (base / "through").mkdir()
        (base / "through" / "git").symlink_to(repo / "through_git")
        (repo / "through_git").symlink_to(outside / "git")
        entries.append(base / "through")
        harmless = base / "harmless"
        harmless.mkdir()
        (harmless / "git").symlink_to(shutil.which("git") or "/usr/bin/git")
        kept = run_bash(repo, f'PATH="{harmless}:$PATH"\n' + diff_build_chain(extra=echo))
        if f"PATH={harmless}:" not in kept.stdout:
            return False, f"an outside link to an outside program was dropped: {kept.stdout}"
        for entry in entries:
            for cwd in (repo, repo / "sub", linked):
                script = f'PATH="{entry}:$PATH"\n' + diff_build_chain(extra=echo)
                result = run_bash(cwd, script)
                if list(planted.glob("*.ran")) or "DIFF_BUILD_COMPLETED" not in result.stdout:
                    return False, f"{entry} from {cwd}: {result.stdout}\n{result.stderr}"
                if f"PATH={entry}:" in result.stdout or "PATH_FILTERED=1" not in result.stdout:
                    return False, f"{entry} from {cwd} was kept: {result.stdout}"

        def finished(result):
            return "DIFF_BUILD_COMPLETED" in result.stdout and "PATH_FILTERED=1" in result.stdout

        missing = f'PATH="{repo}/node_modules/.bin:$PATH"\n' + diff_build_chain()
        if "PATH_FILTERED=1" not in run_bash(repo, missing).stdout:
            return False, "a missing entry spelled inside the checkout was not flagged"
        noisy = 'cd() { builtin cd "$@" && echo listing; }\npwd() { echo x; }\n'
        noisy += f'PATH="{planted}:$PATH"\n' + diff_build_chain()
        result = run_bash(repo, noisy)
        if (
            list(planted.glob("*.ran"))
            or f"PATH={planted}" in result.stdout
            or not finished(result)
        ):
            return False, f"a cd function defeated the filter: {result.stdout}"
        (repo / "git").write_text('#!/bin/sh\ntouch "bin dir/git.ran"\n', encoding="utf-8")
        (repo / "git").chmod(0o755)
        result = run_bash(repo, f'PATH="{planted}"\n' + diff_build_chain())
        if list(planted.glob("*.ran")) or "no PATH entry outside" not in result.stdout:
            return False, f"an empty PATH did not stop the chain: {result.stdout}"
        (linked / ".git").write_text(
            (linked / ".git").read_text(encoding="utf-8").strip() + "\r\n",
            encoding="utf-8",
            newline="",
        )
        result = run_bash(linked, f'PATH="{planted}:$PATH"\n' + diff_build_chain())
        if (
            list(planted.glob("*.ran"))
            or f"PATH={planted}" in result.stdout
            or not finished(result)
        ):
            return False, f"a CRLF .git file hid the main checkout: {result.stdout}"
        return True, "programs inside the checkout or the main checkout are never run"


def test_the_path_filter_is_the_helpers_own():
    helper = (SKILL_DIR.parent.parent / "scripts/git-review-path.sh").read_text(encoding="utf-8")
    block = helper.split("# >>> path filter\n")[1].split("# <<< path filter")[0]
    if block not in extract_inputs_block():
        return False, "the chain's PATH filter differs from git-review-path.sh"
    return True, "the chain and the helpers filter PATH with the same lines"


def test_an_empty_plugin_root_never_runs_the_repositorys_own_scripts():
    with_mirror = _empty_variable_run(with_mirror=True)
    without_mirror = _empty_variable_run(with_mirror=False)
    for stdout in (with_mirror, without_mirror):
        if "plugin root is empty" not in stdout or "PLAN=" in stdout:
            return False, f"an empty plugin root did not stop the chain: {stdout}"
    return True, "empty CLAUDE_PLUGIN_ROOT stops the chain, whatever .claude/scripts holds (#697)"


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


def test_planner_check_ignores_other_plugins_mirrored_scripts():
    """Only git-kit's own mirrored scripts (git- or git_ prefix) set PLANNER_TOUCHED (#710)."""
    line = next(
        (ln for ln in extract_inputs_block().splitlines() if "PLANNER_TOUCHED=1 ||" in ln), None
    )
    if line is None:
        return False, "could not find the PLANNER_TOUCHED check in the Inputs block"
    cases = {
        ".claude/scripts/plib_catalog_validate.py": "0",
        ".claude/scripts/anls-run.sh": "0",
        ".claude/scripts/inventory_common/pdk_models.py": "0",
        ".claude/scripts/git-review-scope.py": "1",
        ".claude/scripts/git_review_common.py": "1",
        ".Claude/Scripts/GIT-review-path.sh": "1",
        "plugins/git-kit/scripts/git-review-ledger.py": "1",
        ".claude/skills/cross-model-review/SKILL.md": "1",
        ".claude/scripts/plib_a.py\n.claude/scripts/git_review_common.py": "1",
        ".claude/scripts/git_review_common.py\n.claude/scripts/plib_a.py": "1",
        ".claude/scripts/plib_a.py\n.claude/scripts/anls-run.sh": "0",
    }
    with tempfile.TemporaryDirectory() as tmp:
        for path, want in cases.items():
            # shlex.quote keeps a real newline, so the multi-line cases reach grep as two lines.
            script = (
                f"UNSCOPED_CHANGED_FILES={shlex.quote(path)}\n{line}\n"
                "echo TOUCHED=${PLANNER_TOUCHED:-0}"
            )
            result = run_bash(pathlib.Path(tmp), "set -e\n" + script)
            if f"TOUCHED={want}" not in result.stdout:
                return False, f"{path}: expected TOUCHED={want}, got {result.stdout!r}"
    return True, "only git-kit's own mirrored scripts set PLANNER_TOUCHED, not another plugin's"


def test_review_scripts_load_only_git_prefixed_siblings():
    """The narrowed check (#710) is safe only while every sibling file loaded is git-/git_ named."""
    loads = re.compile(
        r'source "[^"]*/([^"/]+)"|with_name\("([^"]+)"\)|_import_sibling\("([^"]+)"\)'
        # Any quoting: scope-run.sh runs the planner as "$(dirname -- "...")/git-review-scope.py".
        r"|python3 -I [^\n]*?/([A-Za-z0-9_.-]+\.py)\b"
    )
    scripts_dir = SKILL_DIR.parent.parent / "scripts"
    paths = sorted(scripts_dir.glob("git-review-*")) + [scripts_dir / "git_review_common.py"]
    found = set()
    for path in paths:
        for match in loads.finditer(path.read_text(encoding="utf-8")):
            name = next(g for g in match.groups() if g)
            found.add((path.name, name))
            if not re.match(r"git[-_]", name, re.IGNORECASE):
                return False, f"{path.name} loads {name!r}, which PLANNER_TOUCHED does not cover"
    if ("git-review-scope-run.sh", "git-review-scope.py") not in found:
        return False, "the planner launch in git-review-scope-run.sh was not matched"
    return True, f"all {len(found)} sibling loads in the review scripts are git-/git_ named"


def test_planner_check_copies_agree():
    """scoped-review.md repeats SKILL.md's PLANNER_TOUCHED line; only SKILL.md's runs."""
    ref = (SKILL_DIR / "references" / "scoped-review.md").read_text(encoding="utf-8")
    skill = [
        ln
        for ln in SKILL_MD.read_text(encoding="utf-8").splitlines()
        if "PLANNER_TOUCHED=1 ||" in ln
    ]
    copy = [ln for ln in ref.splitlines() if "PLANNER_TOUCHED=1 ||" in ln]
    if len(skill) != 1 or skill != copy:
        return False, f"SKILL.md {skill!r} and scoped-review.md {copy!r} differ"
    return True, "scoped-review.md's PLANNER_TOUCHED line matches SKILL.md's"


def test_a_diff_touching_the_review_scripts_stops_the_chain_until_approved():
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        planner_repo(repo)
        variant = repo / "PLUGINS" / "Git-Kit" / "Scripts"  # a case variant of the planner folder
        variant.mkdir(parents=True)
        (variant / "json.py").write_text("x = 1\n", encoding="utf-8")  # untracked on purpose
        check = (
            'echo "TOUCHED=${PLANNER_TOUCHED:-0} PLAN=${PLAN_FAILED:-0} '
            'COPY=${INDEX_COPY_FAILED:-ok}"'
        )
        stopped = run_bash(repo, planner_chain(check))
        if (
            "PLANNER_TOUCHED=1: ask the user first" not in stopped.stdout
            or "PLANNER_CHAIN_COMPLETED" in stopped.stdout
            or stopped.returncode != 0
        ):
            detail = f"(exit={stopped.returncode}): {stopped.stdout}\n{stopped.stderr}"
            return False, f"a changed review script did not stop the chain before it ran {detail}"
        approved = run_bash(repo, planner_chain(check, approved=True))
        if "TOUCHED=1 PLAN=0 COPY=ok" not in approved.stdout:
            detail = f"(exit={approved.returncode}): {approved.stdout}\n{approved.stderr}"
            return False, f"an approved run did not run the helper and the planner {detail}"
        return (
            True,
            "a changed review-script folder (any case, even untracked) stops the chain "
            "until approved",
        )


CHECKS = [
    test_planner_sees_untracked_files_and_diff_goes_to_a_file,
    test_planner_failure_sets_a_flag_instead_of_aborting_the_chain,
    test_a_diff_touching_the_review_scripts_stops_the_chain_until_approved,
    test_planner_check_ignores_other_plugins_mirrored_scripts,
    test_review_scripts_load_only_git_prefixed_siblings,
    test_planner_check_copies_agree,
    test_the_planner_block_joined_with_and_and_still_completes,
    test_an_empty_plugin_root_never_runs_the_repositorys_own_scripts,
    test_a_relative_path_entry_stops_the_chain,
    test_a_program_in_the_checkout_is_never_run,
    test_the_path_filter_is_the_helpers_own,
    test_an_intent_add_git_failure_is_disclosed,
    test_dispatcher_check_matches_a_case_variant_path,
    test_untracked_file_included,
    test_deletion_only_scope_does_not_abort,
    test_intent_add_refusal_is_disclosed,
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
