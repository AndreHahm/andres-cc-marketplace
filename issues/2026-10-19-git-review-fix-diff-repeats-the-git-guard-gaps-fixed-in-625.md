## Summary
`git-review-fix-diff.py` carries a third copy of the "git is not inside the repository" guard and still has both gaps that PR #625 fixed in `git-review-ledger.py` and `git-verify-fix-diff.py`: it guards only the nearest `.git` ancestor, and it compares paths as case-sensitive strings.

## Environment
- **Product/Service**: `plugins/git-kit/scripts/git-review-fix-diff.py` (run by `handling-review-findings`, step 4, as `python3 -I` against the developer's checkout); guard in `_repository_root` (line 61) and `_find_git` (line 70), with the `guards` list at line 77, the case-sensitive `is_relative_to` comparison at line 80, and the result used at line 187
- **Region/Version**: `main` at `87ef1ef5`; found while working on PR #625 (head `cdcd6af3`)
- **Browser/OS**: Linux for the verification below; the case-sensitivity gap is reasoned from the code only and needs a macOS run

## Reproduction Steps
1. Create a repository `main` with one commit, then `git worktree add --detach ../linked` from it (this repository keeps its own worktrees under `<main checkout>/.claude/worktrees/<name>/`).
2. Put an executable `bin/git` in `main` that does nothing but exit 0.
3. Load `git-review-fix-diff.py`, set the working directory to `linked` and `PATH` to `<main>/bin:/usr/bin:/bin`, and call `_find_git()`.
4. Repeat with a nested repository: an outer repository with `bin/git`, and `vendor/inner` initialised as its own repository; working directory `vendor/inner`.

## Expected Behavior
Both cases return `None` (no usable git): every directory a branch could have written is guarded, namely each ancestor holding a `.git` entry plus a linked worktree's main working tree (follow the `.git` file's `gitdir` pointer and its `commondir`), compared by file identity (`os.path.samestat`) so letter case and aliases cannot hide a match. A `.git` entry that cannot be read fails closed.

## Actual Behavior
Verified against the unmodified script: both cases return the planted `bin/git` (the linked-worktree case and the nested-repository case are each accepted). The same two cases against the fixed `git-review-ledger.py` return `None`.

Second gap, not verified: the comparison is a string comparison, so on a case-insensitive file system a `PATH` entry spelled with different letter case from the on-disk path (for example `cd ~/repos/Proj` when the real directory is `~/Repos/proj`) is not recognised as inside the repository.

## Error Details
None. The guard fails open silently: the planted executable is returned as the git to run.

## Visual Evidence
None.

## Impact
**Medium** - hardening of a local helper. No exploit is known and the review that found this was static. The script runs on a developer's machine against branches that may be contributed by others, so the guard is the only thing between a committed `bin/git` and its execution.

## Additional Context
Fix shape:
- Copy the block now present, byte-identical, in `git-review-ledger.py` and `git-verify-fix-diff.py` (`_main_working_tree`, `_repository_roots`, `_is_inside`, `_find_git`) into this script.
- Add the guard tests that exist in `tests/marketplace_ci/test_git_review_ledger_script.py` and `test_git_verify_fix_diff_script.py` to `tests/marketplace_ci/test_git_review_fix_diff_script.py`: linked worktree, outer repository from a nested one, unreadable `.git` entry, a link outside the repository pointing in, a subdirectory working directory, and a case-insensitive file system test that skips elsewhere. That file already has planted-git tests for the repository root and subdirectories (around lines 317 and 410). Against the old guard, the linked-worktree, nested-repository and unreadable-entry tests are the ones that fail.
- Edit the canonical `plugins/` file only; the `.claude/` mirror is generated.

Design question to decide while fixing: the helper now exists in three copies. A shared module would remove the triplicate, but these scripts are invoked standalone by path (`python3 -I`), so an import needs a deliberate mechanism. The alternative is a third copy, which is what `docs/ci.md` currently describes.

Related minor items from the same security review, same family, not fixed in #625 and worth deciding in the same pass:
1. `git-review-ledger.py`'s `repo_root()` silently falls back to the current directory when git fails. It is still refused later, but with a misleading "could not check whether ... is tracked" message; `git-verify-fix-diff.py` raises an explicit error instead.
2. `-c safe.bareRepository=explicit` is not in the hardening flags (needs git 2.38 or later). A directory laid out as a bare repository and committed on a branch could be used as the repository if the working directory is inside it.
3. `PATH` is cut to git's own directory and `HOME` is dropped, so a version-manager git shim (asdf, mise) stops working. This fails closed, so it is a usability limit.
4. `git-verify-fix-diff.py` removes the script's own directory from `sys.path`; `git-review-ledger.py` does not.

Suggested labels: `t: security`, `a: ai-setup`, `p: medium`.

## References
- Found while working on PR #625: https://github.com/AndreHahm/andres-cc-marketplace/pull/625
- Parent work: #610 (reference only, not closing)
- Same family in `codex-kit`: #508 (planted `node` found through the working directory) and #510 (a bare `git` found through the working directory)
