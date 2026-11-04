## Summary
`cross-model-review` cannot run on Windows: `git-review-write-run-file.sh` rejects the scratch run directory because it cannot be given mode 0700, so no reviewer instruction file or findings file can be written.

## Environment
- **Product/Service**: git-kit, `plugins/git-kit/skills/cross-model-review/SKILL.md` and `plugins/git-kit/scripts/git-review-write-run-file.sh` (the helper introduced for #541)
- **Region/Version**: Windows 11, Git Bash (MSYS), Python 3.13, observed 2026-11-04 on branch `fix/git-review-api-windows-body-file` while preparing the PR for #623

## Reproduction Steps
1. On Windows (Git Bash), run the skill's Preflight chain from its Inputs block: `umask 077`, `RUN=$(mktemp -d)`, then the index copy, intent-add and scope planner steps. All of these succeed (`manifest-1.json` was written: 5 files in 4 slices).
2. Build the first Codex instruction file with the write helper:
   `bash .claude/scripts/git-review-write-run-file.sh "$RUN" review_for_codex.1.md @review.md - @diffs-1/<slice>.codex.diff`
3. Observe the exit code and message.

## Expected Behavior
The helper writes the file into `$RUN` and the review proceeds, as on Linux.

## Actual Behavior
The helper exits 2 before writing anything:

```
git-review-write-run-file.sh: run directory must have mode 0700
```

Probe on the affected machine, with `$RUN` being `/tmp/tmp.<random>` from `mktemp -d` under `umask 077`:

- `stat -c %a "$RUN"` prints `755`, while `ls -la` shows `-rw-------` on files inside it.
- `chmod 700 "$RUN"` does not change the reported mode (still `755`).
- `find "$RUN" -maxdepth 0 -perm 700` matches nothing.

The failing check is the helper's own line 53: `[ -n "$(find "$run_dir" -maxdepth 0 -perm 700 2>/dev/null)" ] || fail "run directory must have mode 0700"`.

## Impact
**Medium** - the whole cross-model review cannot run on Windows, before any Codex dispatch. The skill's design says a refused write must stop the run and must never fall back to another way of writing the file, so every Phase 1 and Phase 2 file (both Codex instruction files and both Claude findings files) is blocked. The skill is a pre-PR gate that `create-pr` and `merge-to-completion` route through, so a Windows contributor has to skip it or review some other way. The Preflight scripts themselves work on Windows; only the write helper fails.

## Additional Context
- Cause: Git Bash on NTFS does not represent POSIX mode bits on directories the way the helper assumes. The helper's directory check (and the skill's no-`Write`-grant design that depends on it) is POSIX-only, with no Windows branch and no fallback.
- It is the same class of problem as #623 (`git-review-api.py` refused on Windows after PR #583) and #538 (`O_NOFOLLOW` assumed available).
- The Codex side is not the problem here: the local Windows guardrails fallback is enabled and `codex` is installed. The run stopped before reaching it.
- Possible directions, not decided:
  - A `win32` branch in the helper that replaces the mode check with a check that the directory sits in the per-user temp directory, as is being done for `git-review-api.py` in #623.
  - Have the skill create `$RUN` under a directory it controls and verify ownership by another means.
  - Document the limit and offer an explicit single-vendor fallback when the helper refuses.

## Related
- #541 (introduced the helper)
- #623 (Windows body-file support for `git-review-api.py`)
- #538 (a similar platform assumption)
- #305 (git-kit scripts on Windows)
