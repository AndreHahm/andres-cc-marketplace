## Summary
About 39 review-helper tests are skipped on native Windows, so the scope helper scripts' run-directory, symlink, index-copy and write-helper guards have no Windows test coverage

## Environment
- **Product/Service**: git-kit review helper scripts (`plugins/git-kit/scripts/`) and their tests (`tests/marketplace_ci/`)
- **Region/Version**: after PR #654
- **Browser/OS**: Windows 11, Git for Windows, Python 3.13, uv

## Reproduction Steps
1. On native Windows, run `uv run pytest -rs tests/marketplace_ci/test_git_review_scope_script.py tests/marketplace_ci/test_git_review_fix_diff_script.py`.
2. Read the skip reasons: `needs POSIX modes, symlinks, case-sensitive names or shell helpers` and `needs POSIX shell scripts, symlinks or a ':'-separated PATH`.
3. Check the `review-helpers-windows` job in `.github/workflows/marketplace-ci.yml`.

## Expected Behavior
The guards in `git-review-scope-run.sh`, `git-review-copy-index.sh`, `git-review-intent-add.sh` and `git-review-write-run-file.sh` are exercised on Windows, either by running these tests there or by an equivalent Windows-native test. A Windows-only regression fails a check.

## Actual Behavior
PR #654 made the suite pass on Windows by marking tests that need POSIX mechanisms with `posix_only` (`pytest.mark.skipif(os.name == "nt")`):
- 29 tests in `test_git_review_scope_script.py`
- about 10 in `test_git_review_fix_diff_script.py`
- a few in `test_git_review_ledger_script.py` and `test_git_verify_fix_diff_script.py`

They rely on shell scripts standing in for git, symlinks, file owners, mode bits (0600/0700), a colon in a path, case-distinct names, and `mktemp` run directories used with bash helper scripts. The `review-helpers-windows` job runs only three test files and is informational, so a regression in these guards would not be noticed.

## Impact
**Medium** - a test coverage gap only. No known user-facing failure; the helper scripts run under Git Bash and issue #637 fixed the mode check there.

## Additional Context
Proposed scope:
1. A Windows-native run-directory fixture so the helper-script tests can run on Windows.
2. Decide which skipped tests have a faithful Windows equivalent and which are genuinely POSIX-only.
3. Decide whether to add these test files to the `review-helpers-windows` job.

Two ledger tests that use the `_other_owner_git` stub (`test_git_review_ledger_script.py`) still run on Windows but pass without exercising the stub, because a `#!/bin/sh` file named `git` is never executed there. Worth fixing as part of item 2.

Related: #416, #305, #421, #596, #637, PR #654.
