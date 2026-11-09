## Summary
`git-stage-selected-files.sh` aborts the whole staging batch, staging nothing, when its list contains a rename that is already staged and has further edits.

## Environment
- **Product/Service**: git-kit, `plugins/git-kit/scripts/git-stage-selected-files.sh` (called from the `commit` skill, step 6: interactive staging by index)
- **Region/Version**: main at 913d7738
- **Browser/OS**: Windows 11, Git Bash

## Reproduction Steps
1. Run `git mv <old-path> <new-path>` (the rename is now staged).
2. Edit `<new-path>` again, so `git status --short` shows `RM <old-path> -> <new-path>`.
3. Run `git-stage-selected-files.sh --list`. The rename appears as one numbered entry: `N  <old-path> -> <new-path>`.
4. Run the script with that index plus other indices, e.g. `git-stage-selected-files.sh 1 2 3 N`.

## Expected Behavior
An entry whose rename is already staged (status column X is `R` or `C`) stages only the new path, because the old path's deletion is already staged. Only a rename seen in the working tree (X blank, Y = `R`) needs the old path added.

At minimum, an old path that matches nothing is skipped with a clear message instead of aborting the batch, and the script never leaves everything unstaged silently.

## Actual Behavior
The final `git add` fails and nothing at all is staged:

~~~
fatal: pathspec ':(top,literal)<old-path>' did not match any files
~~~

All matched paths go to one `git add --pathspec-from-file` call, so a single unmatched pathspec aborts the whole batch. The `commit` skill then carries on with its checks, and a later `check-all --staged` reports a missing generated mirror counterpart for a staged canonical source. That downstream symptom hides the real cause. The repo's own rulebook-enforcement doc already warns that a batched add with one failing pathspec stages nothing.

## Root cause
`list_candidates` emits the original path for any entry with `R` or `C` in either status column. The staging loop always appends it to the pathspec list. This is deliberate: a comment in the script documents a bug where staging only the new path of a rename seen in the working tree recorded a duplicate instead of a rename, so both halves are staged together.

That holds when the old path is still tracked in the index (X blank, Y = `R`). When the rename is already staged (X = `R` or `C`), `git mv` has already removed the old path from the index. It then exists neither in the working tree nor in the index, so `:(top,literal)<old-path>` matches nothing.

## Constraint to keep
Filenames must never be composed into shell command strings. The script receives only digit indices and passes paths via `--pathspec-from-file` with NUL separators and the `:(top,literal)` pathspec magic. Any fix must keep that.

## Impact
**Medium** - Interactive staging fails for any commit containing a `git mv` rename with further edits. No data loss, and a workaround exists: the `commit` skill's fixed-literal `git add -A` after asking the user (used here), or staging that file separately.

## Additional Context
Related but different, checked before filing: #158 (TOCTOU race in index-based staging, closed), #218 (untracked directory collapsed into one candidate), #219 (control-byte spoofing in the displayed list). None covers a rename that is already staged.
