## Summary
`git-verify-fix-diff.py --worktree` cannot run on Windows: it writes git's `alternates` files with CRLF line endings, so `git read-tree` fails and the verifier self-review reports "could not run".

## Environment
- **Product/Service**: git-kit, `plugins/git-kit/scripts/git-verify-fix-diff.py` (mirrored at `.claude/scripts/git-verify-fix-diff.py`)
- **Region/Version**: current `main`; Python 3.13, Git for Windows
- **Browser/OS**: Windows 11

## Reproduction Steps
1. On Windows, in any repository that has `scripts/marketplace_ci/`, make an uncommitted change.
2. Run `python3 .claude/scripts/git-verify-fix-diff.py --worktree --base "$(git rev-parse HEAD)" --upstream <owner>/<repo>`.
3. Read the output: exit status 2, "Verifiers could not run".
4. To see the real cause, run the same `git read-tree <sha>` with `GIT_OBJECT_DIRECTORY` pointing at a directory whose `info/alternates` the script wrote. Compare the file's bytes with the same file written with `newline=""`.

## Expected Behavior
`_snapshot()` builds its throwaway index, commit and clone, and the verifiers run on the fix's own diff, as they do on Linux.

## Actual Behavior
`_snapshot()` writes `objects/info/alternates` with `open(..., "w", encoding="utf-8")` (line 292) and appends to the clone's alternates with `alternates.open("a", encoding="utf-8")` (line 311). On Windows text mode turns LF into CRLF. Git splits an alternates file on LF only, so the object directory path ends in a carriage return and `git read-tree` exits 128. Written with `newline=""`, the same call exits 0.

The script's own message hides the cause: `_git()` runs `subprocess.run(..., check=True, capture_output=True)`, and `CalledProcessError` carries the argument list and the exit status but not git's stderr.

## Error Details
~~~
Verifiers could not run: Command [... 'read-tree', '<sha>'] returned non-zero exit status 128.

git's own stderr, captured by reproducing the call:
error: object directory [LOCAL_PATH]/.git/objects? does not exist; check .git/objects/info/alternates
fatal: failed to unpack tree object <sha>

Bytes of the alternates file as the script writes it end in 0d 0a (CRLF); with newline="" they end in 0a.
~~~

## Visual Evidence
None.

## Impact
**Medium** - Step 4a (the verifier self-review) of the `handling-review-findings` skill cannot succeed on Windows when it uses `--worktree`, so a Windows session can never pass that gate. 6 of the 8 tests with "worktree_mode" in `tests/marketplace_ci/test_git_verify_fix_diff_script.py` fail on Windows (6 failed, 2 passed). Linux is unaffected, and the script fails closed (exit 2), so nothing wrong is accepted.

## Additional Context
- **Why CI missed it:** the full pytest run is Ubuntu-only (job "Python quality" in `.github/workflows/marketplace-ci.yml`), where text mode writes LF. The `windows-latest` job "review-helpers-windows" runs only `test_git_review_run_dir.py`, `test_git_review_api_script.py` and one `test_reviewer_dispatch.py` case, not this test file. That job's own comment already says text mode writes CRLF only on Windows.
- **Suggested fix:** write both alternates files with `newline=""` (or as bytes); include git's stderr in the failure message so a git error is not reduced to an exit status; run this file's `--worktree` tests, or a small CRLF regression test, in the Windows job.
- **Separate note, not part of this bug:** even when it runs, a fix that edits `scripts/marketplace_ci/` is unjudgeable by design (`_UNJUDGEABLE`) and the script exits 2.
- **Unverified:** `plugins/git-kit/scripts/git-review-ledger.py` line 281 appends to `.git/info/exclude` in text mode on Windows. Whether git tolerates the carriage return there was not checked.
- **Related, not duplicates:** #151 (use `newline=""` when script-editing tracked files), #588 and #626 (git guard gaps in the same scripts).
- Found while working PR #646; not caused by it (the code is unchanged on `main`).
