# Mutation test plan: trust_boundary (plan only, nothing run)

Nothing has been run or edited. This is a plan for running mutation tests on `scripts/marketplace_ci/trust_boundary.py`.

## What I found (read-only)

- Module: `scripts/marketplace_ci/trust_boundary.py` (84 lines).
- It is registered in `.github/mutation-modules.yml` (line 14) with a single test selection:
  - `tests/marketplace_ci/test_workflow_trusted_restore.py`
- That test file imports `TIER1_FILES` and `find_tier1_touches` from the module, so it does reach the module's code in-process.
- The test file also calls `subprocess.run(["git", ...], cwd=git_repo.root)` inside a temporary git repo (around lines 302-306). Its `cwd` is explicit, not the repo's working directory. The `mutation-modules.yml` header warns that subprocess-launched tests starting from another working directory can stop the whole mutmut run, so this selection should be checked against that warning before the run. I have not verified whether it causes a problem.
- Runner and CI: `docs/ci.md` (section "Mutation testing: weekly mutmut runs") describes the weekly job. The local runner is `plugins/quality-kit/scripts/qlty-mutation-run.py`. It checks a green baseline first, then runs mutmut 3.8.1 and exits with mutmut's own status.

## Proposed plan

1. Confirm the baseline is green: run the selected test file on its own, with no mutation, and check it passes. Verify: exit 0.
2. Run mutmut for this module only, using the registered selection, through the runner. Verify: the runner reports a score, counts, and survivor keys, and its totals reconcile with mutmut's own totals.
3. Check for "not measured" mutants. If many mutants are not measured, the selection is too narrow for this module. Verify: the not-measured count is low.
4. Review survivors with the user before changing anything. Each survivor needs a decision: a new test, or `# pragma: no mutate` with a reason. Nothing is written until the user approves.

## Question for you before I run anything

Which way should the run go?

- **Option A: run locally with the registered selection.** Runs steps 1-3 in this worktree using `test_workflow_trusted_restore.py` only. Lowest cost, and it matches the CI job.
- **Option B: run locally with a wider selection.** Adds `test_workflow_trusted_restore.py` plus other tests that exercise `trust_boundary.py`. Finds more mutants measured, but the extra tests must not launch subprocesses from another cwd.
- **Option C: skip the local run and dispatch the weekly CI job** (`workflow_dispatch` on `mutation-testing.yml`). Uses CI's own runner and selection, with no local run.

I have not run any of these. I will wait for your choice.

## Limits I kept to

- No file in the repository was edited or written.
- No agent was dispatched.
- Neither mutmut, pytest nor the mutation runner was run.
- No skill folder or skill file was read.
