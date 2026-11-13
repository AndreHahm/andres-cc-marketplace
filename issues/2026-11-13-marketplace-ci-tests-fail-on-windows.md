## Summary
A local Windows run of `tests/marketplace_ci` has 34 failures on an unchanged `main`, so it cannot be used as a pass/fail gate.

## Environment
- **Product/Service**: `tests/marketplace_ci` (pytest via `uv`)
- **Region/Version**: `main` at `9c5d7a74` (2026-11-13)
- **Browser/OS**: Windows 11, Git Bash

## Reproduction Steps
1. Check out `main` at `9c5d7a74` on Windows.
2. Run `uv run pytest tests/marketplace_ci -q -rf -p no:cacheprovider`.
3. Read the short test summary.

## Expected Behavior
The suite passes on Windows, or the tests that need the Linux CI runner are skipped on other platforms with a stated reason.

## Actual Behavior
34 failed, 3447 passed, 174 skipped. Branch `fix/register-codex-agent-exports` gives the same totals.

| File | Test | Failures |
|---|---|---|
| `test_ci_review_delta.py` | `test_the_claude_anchor_lookup` | 7 |
| `test_ci_review_delta.py` | `test_the_anchor_lookup_accepts_only_a_valid_bypass_record` | 7 |
| `test_ci_review_delta.py` | `test_the_anchor_lookup_accepts_a_skipped_review_record` | 4 |
| `test_ci_review_delta.py` | `test_the_anchor_lookup_pairs_a_review_result_with_its_own_head_and_attempt` | 4 |
| `test_ci_review_delta.py` | `test_a_rerun_after_a_newer_run_keeps_its_original_anchor` | 1 |
| `test_ci_review_delta.py` | `test_a_review_result_reused_by_a_rerun_of_only_the_failed_jobs_stays_an_anchor` | 1 |
| `test_ci_review_delta.py` | `test_a_run_complete_before_this_one_was_created_is_its_anchor` | 1 |
| `test_ci_review_delta.py` | `test_no_codex_call_after_a_conversion_to_draft` | 1 |
| `test_claude_review_workflow.py` | `test_a_failed_lookup_is_never_reported_as_a_moved_head` | 6 |
| `test_hooks.py` | `test_staged_converted_agent_export_matching_content_satisfies_parity` | 1 |
| `test_review_verifiers.py` | `test_the_total_bytes_read_are_capped` | 1 |

## Error Details
~~~
assert '' == '1111111111111111111111111111111111111111'    (anchor-lookup tests, 22 cases)
AssertionError: assert 'state=lookup_failed' == 'state=ok' / 'state=head_moved' / 'state=draft'    (6 cases)
::error::the PR is a draft now (or its draft state could not be read): no Codex call    (test_no_codex_call_after_a_conversion_to_draft)
~~~

## Visual Evidence
n/a

## Impact
**Medium** - A Windows developer cannot use a local run as a gate. Every run needs a comparison against `main` to tell existing failures from new ones. CI on Linux is unaffected.

## Additional Context
- Likely cause, not verified: the anchor-lookup and workflow tests run workflow-step shell written for the Linux runner. For example, `test_no_codex_call_after_a_conversion_to_draft` asserts the step calls `/usr/bin/gh`, which does not exist under Git Bash. The `test_hooks.py` and `test_review_verifiers.py` failures may have a different cause, also specific to Windows.
- Found while testing branch `fix/register-codex-agent-exports`.
