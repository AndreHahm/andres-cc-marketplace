## Summary
`run-codex-review` checks the unsandboxed fallback's files once, before dispatch, but each fallback attempt then starts `guarded-dispatch.mjs` from the live working tree, so a protected file changed after the check runs unchecked with full account access.

## Environment
- **Product/Service**: `scripts/marketplace_ci/__main__.py` and `scripts/marketplace_ci/review.py` (`fallback_files_changed`, the guarded launch in `_dispatch_one`)
- **Region/Version**: PR #646 head `2ae7461e`
- **Browser/OS**: Windows 11 (the fallback is Windows only)

## Reproduction Steps
1. Run `run-codex-review --allow-unsandboxed-fallback` (or the git-kit parity wrapper) on a branch where none of `FALLBACK_FILES` differs from the merge-base, so the eligibility check passes.
2. While the reviewers run (10 to 40 minutes), edit one of those files in the working tree, for example `guarded-dispatch.mjs` or a file it imports.
3. Let a reviewer fall back: its next unsandboxed launch starts the edited file.

## Expected Behavior
Whatever the fallback executes is exactly what was checked: the file set is snapshotted, verified, and every unsandboxed launch uses the snapshot.

## Actual Behavior
`fallback_files_changed` runs once before the sandbox probe and the reviewer launches. Each unsandboxed attempt later starts `guarded-dispatch.mjs` from the live working tree. A re-check before each launch would narrow the window but not close it: only a snapshot or a lock closes the gap between the check and Node reading the file.

## Error Details
~~~
No error: this is a time-of-check to time-of-use gap, not a failure.
~~~

## Visual Evidence
None.

## Impact
**Low** - The window needs someone with write access to the same working tree during a run, which is a local attacker or the user's own concurrent edit. It is real but narrow, and the fix is a heavy lift (copy the closure of `guarded-dispatch.mjs` and the data files it reads into a private directory, verify it against the base, launch from there).

## Additional Context
- **Why this is a follow-up:** it needs snapshot-and-launch machinery that does not exist yet, which is too large for the PR that introduces the fallback. This PR does re-check state in the places it can: it refuses the fallback when the files differ from the base, treats an unanswerable comparison as changed, and starts nothing when the probe reports the sandbox down and the fallback is refused.
- **Repository rule cited by the reviewer:** a script that observes state it does not control must re-check it immediately before a side-effecting action (`.claude/rules/recheck-state-before-side-effecting-action.md`).
- **Suggested direction:** snapshot the `FALLBACK_FILES` closure to a private temp directory outside the checkout, hash-verify it against the merge-base copy, run `guarded-dispatch.mjs` from there, and keep `.codex/config.toml` handling in mind (it is read from the working directory).
- **Related:** #644, PR #646.

## Review Finding Source
- **PR:** https://github.com/AndreHahm/andres-cc-marketplace/pull/646
- **Head SHA the finding was raised against:** 2ae7461e72d0eba0b719370546f828ea41d207c0
- **Review comment:** https://github.com/AndreHahm/andres-cc-marketplace/pull/646#discussion_r4483391125 (comment id 4483391125)
- **Reviewer:** CodeRabbit
- **Severity as stated:** Minor (heavy lift)
