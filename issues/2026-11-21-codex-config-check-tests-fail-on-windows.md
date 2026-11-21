## Summary
Two `test_codex_config_check.py` tests fail locally on Windows on a clean `main`; the step's control check never sees the trusted config applied.

## Environment
- **Product/Service**: `tests/marketplace_ci/test_codex_config_check.py`, testing `.github/workflows/marketplace-ci.yml`'s "Check Codex does not apply the repository's own config" step
- **Region/Version**: `main` at 772f5c26; local codex-cli 0.170.0 (the same version CI pins)
- **Browser/OS**: Windows 11, Git Bash, `uv run pytest`

## Reproduction Steps
1. Check out `main` (reproduced on a detached checkout of `origin/main` at 772f5c26, 2026-11-21).
2. Run `uv run pytest -q -p no:cacheprovider tests/marketplace_ci/test_codex_config_check.py`.

## Expected Behavior
All 6 tests pass, as they presumably do on Linux CI (`main` is green).

## Actual Behavior
2 failed, 4 passed:
- `test_an_unapplied_config_passes_and_the_control_shows_it_is_detectable`
- `test_the_control_trusts_the_base_config_never_the_prs`

The extracted step script exits 1 in both.

## Error Details
~~~
AssertionError: ::error::the base branch's .codex/config.toml changes no feature even when trusted (or the comparison failed, cmp exit 0), so check 1 cannot show whether Codex applied a config -- re-check the control after a Codex pin change
assert 1 == 0
~~~

## Visual Evidence
None.

## Impact
**Low**: a local-only test failure. It makes the full `tests/marketplace_ci` run red on Windows but doesn't affect CI.

## Additional Context
The test extracts the step's `run:` script from `marketplace-ci.yml` and runs it with a fake `codex` (a bash script) on `PATH`. The fake applies a project `.codex/config.toml` only when `$CODEX_HOME/config.toml` contains `[projects."$PWD"]`.

Two hypotheses, neither verified:
- On Windows, the real Codex CLI installed globally may shadow the fake `codex` script on `PATH`.
- `$PWD`'s form (`/c/...` in Git Bash) may not match the `[projects."..."]` key the step writes, so the trusted run never applies the config and the control comparison finds no difference.

Not checked: whether the tests pass on Linux. Found while working issue #774, whose diff doesn't touch this test or its step.
