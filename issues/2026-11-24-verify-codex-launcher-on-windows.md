## Summary
cross-model-review's Codex launcher has Windows-only code that has never run on Windows

## Environment
- **Product/Service**: git-kit plugin, `cross-model-review` skill (`git-review-codex-kit.py`, `git_review_common.py`)
- **Region/Version**: branch `fix/cross-model-review-secret-filter` (follow-up to #697)
- **Browser/OS**: Windows with Git Bash

## Reproduction Steps
Run these on a Windows machine with git-kit and codex-kit installed:

1. Run `tests/marketplace_ci/test_git_review_codex_kit.py` and `tests/marketplace_ci/test_git_review_scope_script.py`. `test_the_real_windows_profile_ignores_the_environment` is skipped on other systems.
2. Put a harmless `git.exe` at a test repository's root, without adding it to PATH, and run the planner and `git-review-codex-kit.py locate` from that root.
3. Check the PATH that `safe_path()` gives the bridge. codex is normally installed as `codex.cmd`.
4. Run the skill's Preflight in a normal Git Bash session.
5. Make one live Codex dispatch through `git-review-codex-kit.py bridge`, including the guardrails fallback.

## Expected Behavior
- `_windows_profile()` returns the account's profile folder and ignores `USERPROFILE`, `HOME` and `HOMEPATH`.
- The planted `git.exe` never runs.
- codex stays reachable for the bridge, and PATH entries from the repository are dropped.
- The PATH check at the top of Preflight does not stop a normal session.
- The dispatch returns a valid envelope.

## Actual Behavior
Unknown. The code was written and tested on Linux, where the Windows API call is only faked. No failure has been seen.

## Impact
**Medium** - the code is security-relevant and unverified on one supported platform. A failed lookup makes Codex unavailable rather than running the repository's code, as far as the Linux tests show.

## Additional Context
- The Windows job in `.github/workflows/marketplace-ci.yml` does not run `test_git_review_codex_kit.py`. Adding it would cover step 1 and parts of steps 2 and 3.
- The Windows bare-name lookup was found by static review in #697's security reviews and was not reproduced.
- Related: #697.
