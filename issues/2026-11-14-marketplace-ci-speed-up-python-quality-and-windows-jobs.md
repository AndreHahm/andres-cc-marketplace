## Summary
Marketplace CI's "Python quality" job takes 4m16s and the informational "Review helpers on Windows Git Bash" job takes 6m0s. Most of that time is avoidable test overhead.

## Environment
- **Product/Service**: `.github/workflows/marketplace-ci.yml`, jobs `python-quality` and `review-helpers-windows`
- **Region/Version**: measured on PR #726 run 43497251664 (head `f3f30230`) and a local run on 2026-11-14
- **Browser/OS**: ubuntu-latest and windows-latest GitHub-hosted runners

## Reproduction Steps
1. Open any PR run of `marketplace-ci.yml` and read the per-step timings of the two jobs.
2. Locally: `uv run pytest -q -p no:cacheprovider --durations=40`.
3. Locally: `uv run pytest -q -p no:cacheprovider --durations=0 plugins/decision-kit/tests` and sum the teardown rows.

## Expected Behavior
Both jobs spend their time running the checks, not waiting in teardown or on serial execution that could run in parallel.

## Actual Behavior
- Python quality: `pytest -q` takes 3m52s of 4m16s (4462 tests, serial; 3m09s locally).
- Windows: the review-helper group takes 3m49s and `plugins/decision-kit/tests` takes 1m10s, out of 6m0s.

Findings, in priority order:

1. **decision-kit test server teardown (biggest single cost).** The two server fixtures in
   `plugins/decision-kit/tests/test_dck_decide.py` (lines 81 and 501) run `HTTPServer.serve_forever()` with the
   default `poll_interval` of 0.5s, so every `httpd.shutdown()` waits about 0.5s. Locally that is 129 teardowns,
   64.5s of a 189s run, and most of the Windows decision-kit step. Fix: `serve_forever(poll_interval=0.01)`.
2. **No parallel test execution.** `pytest-xdist` is not a dev dependency. Public-repo hosted runners have 4 vCPU;
   `pytest -n auto` should cut both jobs' pytest time roughly 2-3x. Needs a `uv.lock` update and a check that
   tests sharing HOME or temp state stay isolated.
3. **Windows process spawning.** `test_git_review_scope_script.py`, `test_git_review_ledger_script.py`,
   `test_git_review_fix_diff_script.py` and `test_git_verify_fix_diff_script.py` (all in `tests/marketplace_ci/`)
   take 3m49s on Windows against 26s locally: each test starts many `git`/`bash` processes (70-81 call sites per
   file), about 9x slower on Windows. xdist, or a session-scoped template repository copied per test, would help.
4. **Deliberately slow timeout tests (lower priority).** `test_exhausted_budget_keeps_warning` (10s),
   `test_run_bridge_timeout_kills_the_whole_process_group` (8s) and
   `test_run_bridge_does_not_block_on_a_descendant_that_escaped_the_group` (7s) exercise real timeouts. Shortening
   them needs configurable timeouts in the scripts under test.
5. **Windows uv cache off.** The Windows job's `setup-uv` step sets `enable-cache: "false"`; `uv sync` takes 26s.
   The job holds no secrets, so a cache is an option.

## Error Details
~~~
None: all checks pass; this is CI latency only.
~~~

## Visual Evidence
None.

## Impact
**Low** - CI latency only; nothing is broken. Every PR push waits about 4-6 minutes on these two jobs.

## Additional Context
Related: #706 (a PR-body-only edit re-runs every job) and #641 (replace `pip install uv` with `setup-uv`).
