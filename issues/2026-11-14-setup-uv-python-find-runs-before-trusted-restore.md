## Summary
setup-uv runs `uv python find` on the PR checkout before the trusted restore in the Claude review workflows

## Environment
- **Product/Service**: GitHub Actions: `.github/workflows/claude-review-ci.yml`, `.github/workflows/test-headless-claude-review-ci.yml`
- **Region/Version**: `astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2` (v10.3.3), on `main`

## Reproduction Steps
1. Read `getPythonVersion()` in `src/setup-uv.ts` of setup-uv at the pinned SHA. When the action's `python-version` input is empty, it always runs `uv python find --directory <working-directory>` and then executes the interpreter path it gets back with `--version`. This happens whether or not the cache is enabled.
2. In `claude-review-ci.yml`, job `claude-scope` checks out the PR head (line 116) and runs setup-uv (line 127) with only `version` and `enable-cache` set. Only after that does it restore `.python-version`, `.python-versions` and `uv.toml` from the base SHA (line 135).
3. `test-headless-claude-review-ci.yml`, job `headless-scope`, has the same order: head checkout at line 119, setup-uv at line 130, restore at line 138.

## Expected Behavior
No code from the PR runs before the trusted restore in a job that decides scope or policy.

## Actual Behavior
A PR can point `.python-version` at an executable it commits, or commit a `.venv` interpreter. The setup-uv step then runs that file before the restore, and it can write `GITHUB_ENV`/`GITHUB_PATH` for the job's later steps.

## Error Details
~~~
None. There is no error: the step succeeds.
~~~

## Visual Evidence
N/A

## Impact
High. The same exposure was found and fixed in `marketplace-ci.yml` in PR #734. The two scope jobs above match it. Four other jobs in these files run setup-uv without `python-version` after a mixed base/head checkout: `claude-review`, `claude-publish`, `headless-review` and `headless-compare`. Whether their working directory is the PR head still needs to be checked.

## Additional Context
Fix used in PR #734 (commit 591c4ba2): add `python-version: "3.13"` to every setup-uv step. With a non-empty input, the action never runs the lookup. It then exports `UV_PYTHON=3.13`. Other parts of the action were checked at the pinned SHA and read no PR config into the environment: `UV_PYTHON_INSTALL_DIR` and the tool directories come from `RUNNER_TEMP`/`HOME`, and a `cache-dir` read from config is never exported. A structure test like `tests/marketplace_ci/test_marketplace_ci_uv_setup.py` should pin these inputs in both workflows. Related: #641.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/734
- **Head SHA**: a786338c9d2555b44d0948529ed9995e6ba89042
- **Thread**: https://github.com/AndreHahm/andres-cc-marketplace/pull/734#discussion_r4573267506
- **Reviewer**: CodeRabbit (finding on `marketplace-ci.yml`; this sibling exposure was found while verifying it)
- **Severity**: Major

Found in PR #734.
