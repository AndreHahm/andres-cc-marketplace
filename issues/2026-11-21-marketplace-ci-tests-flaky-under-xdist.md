## Summary
Several `tests/marketplace_ci` tests fail only under a parallel `pytest -n auto` run on Windows, and pass when rerun serially.

## Environment
- **Product/Service**: `tests/marketplace_ci` (pytest-xdist)
- **Region/Version**: `main` at 772f5c26 plus an unrelated CI version-pin change (issue #774)
- **Browser/OS**: Windows 11, Git Bash, `uv run pytest`

## Reproduction Steps
1. Run `uv run pytest -q -p no:cacheprovider tests/marketplace_ci -n auto`.
2. Rerun the failing tests on their own, without `-n`.

## Expected Behavior
The same results in parallel and serial runs.

## Actual Behavior
The full parallel run (2026-11-21, about 11 minutes) reported 8 failed, 3643 passed, 204 skipped and 2 errors. Two of those failures are `test_codex_config_check.py`, which also fails serially and is tracked separately. All of the following failed in parallel and passed when rerun serially:
- `test_git_guard_dirty_worktree_exit_script.py`: `test_rebase_merged_branch_does_not_block`, `test_squash_merge_with_merged_pr_at_head_does_not_block`, `test_branch_pushed_to_origin_does_not_block`
- `test_review_call_graph.py`: `test_the_findings_pass_checks_the_deadline_and_builds_the_graph_once`, `test_a_skill_and_an_agent_with_the_same_name_calling_each_other_are_a_cycle`
- `test_review_paths.py`: `test_scanning_for_the_new_forms_stays_fast`
- `test_git_verify_fix_diff_script.py`: `test_no_temporary_directory_is_left_behind[mode0]` and `[mode1]` (errors)

An earlier parallel run with `-x` also hit two more, which passed serially:
- `test_cli.py::test_check_prefix_permanence_no_inventory_at_base_is_ok` (failure)
- `test_codex_review_result_status.py::test_a_failed_dispatch_reports_could_not_run` (error)

## Error Details
~~~
fatal: failed to write commit object
~~~
(git, seen in the parallel run's output)

## Visual Evidence
None.

## Impact
**Low**: local parallel runs report false failures, which makes a real regression harder to spot. Serial runs are unaffected.

## Additional Context
Hypotheses, not verified:
- The git-backed tests contend for resources or share temporary state under load, as `failed to write commit object` suggests.
- The timing tests ("stays fast", "checks the deadline") exceed their bounds when the machine is loaded.

Related, not a duplicate: #729 (Marketplace CI speed), which proposes parallel test execution. If CI adopts xdist, these failures would matter there too.
