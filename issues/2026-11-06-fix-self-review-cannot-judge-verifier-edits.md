## Summary
The fix self-review in `handling-review-findings` can never pass for a fix that edits the verifier driver, the verifiers or their registry, and the skill defines no route for that case

## Environment
- **Product/Service**: git-kit `handling-review-findings` (Workflow step 4a, `references/fix-self-review.md`) and `plugins/git-kit/scripts/git-verify-fix-diff.py`
- **Region/Version**: observed 2026-11-06 on PR #654, head `46127f83`
- **Browser/OS**: Windows 11, Python 3.13

## Reproduction Steps
1. Get a review finding on `plugins/git-kit/scripts/git-verify-fix-diff.py` (on PR #654 it was a CodeRabbit finding on `_git_said`).
2. Apply the fix in the working tree, uncommitted.
3. Run step 4a: `python3 .claude/scripts/git-verify-fix-diff.py --worktree --base "$(git rev-parse HEAD)" --upstream <owner>/<repo>`.

## Expected Behavior
A defined route for a fix the verifiers cannot grade: either the check still runs with the verifiers taken from the target branch, or the skill states a fixed alternative and the wording for the reply.

## Actual Behavior
The script exits 2 with `{"cannot_judge": true, "note": "the fix changes the verifiers, their registry or this script; cannot judge it"}`. It does this whenever the fix touches a path in `_UNJUDGEABLE`:
- `scripts/marketplace_ci/`
- `.claude/marketplace-sync.json`
- `plugins/git-kit/scripts/git-verify-fix-diff.py`
- `.claude/scripts/git-verify-fix-diff.py`

The skill treats exit 2 exactly like a blocking finding (step 4a, budget rule 4d), so there is no push, reply or resolve until the user directs. The session had to stop and ask. The reply could only say the self-review could not judge this change; the wording was improvised.

## Error Details
~~~
the fix changes the verifiers, their registry or this script; cannot judge it
{"cannot_judge": true, "note": "..."}
exit=2
~~~

## Impact
**Low** - Process friction for a narrow class of fixes (any finding on the verifier scripts, their registry or the sync config). No wrong verdict is produced; the refusal is intentional because a fix cannot be graded by the code it edits.

## Additional Context
Directions, none decided:
- Run the verifier modules from the target branch (the trusted merge-base commit the script already uses for them) against the fix's diff even when the driver script is edited.
- Split `_UNJUDGEABLE` so a fix to only the driver's own diagnostics is still checkable by the target-branch verifiers.
- Otherwise document the fallback in `references/fix-self-review.md`: review by another mechanism, record the disposition as `accepted` with the reason, and fix the reply's verification wording.

This is not issue #652, which covers the Windows Codex sandbox failing mid-run.

Related: #578 (closed, introduced the self-review), #568 (umbrella), PR #654.
