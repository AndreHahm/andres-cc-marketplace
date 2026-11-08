## Summary
The unsandboxed fallback's snapshot file list comes from the branch, not from the base tip's own dependency closure.

## Environment
- **Product/Service**: `run-codex-review` fallback snapshot (`snapshot_fallback_files` and `FALLBACK_FILES` in `scripts/marketplace_ci/review.py`)
- **Region/Version**: found in PR #681, head `f55c605f98d0616afd8c2430119818d74473424b` (follow-up to #676)
- **Browser/OS**: Windows, local parity run with the unsandboxed fallback

## Reproduction Steps
1. Branch off `main`, then let `main` add a new import to `guarded-dispatch.mjs` (or a new data file it reads).
2. Run the parity review with the unsandboxed fallback on the older branch.
3. Observe which files the snapshot writes.

## Expected Behavior
The snapshot contains everything the base tip's dispatcher needs, so the fallback can start its reviewers.

## Actual Behavior
`snapshot_fallback_files` writes the entries of `SNAPSHOT_FILES`, which is the branch's own `FALLBACK_FILES` list. The hash checks still pass, but a file the newer base dispatcher imports is missing from the snapshot, so the fallback cannot start. Not reproduced; reasoned from the code.

## Impact
**Low** - It fails safe: the fallback does not start and nothing runs with `danger-full-access`. The cost is a could-not-run result in a rare case. Fixing it means deriving the closure from the base tip's imports at run time, which is a design change.

## Additional Context
- Found in PR #681 (https://github.com/AndreHahm/andres-cc-marketplace/pull/681), head `f55c605f98d0616afd8c2430119818d74473424b`.
- Reviewer: CodeRabbit, severity Minor, rated "Poor tradeoff" by the reviewer. Thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/681#discussion_r4507579266
- A test already derives the import closure from the branch's `guarded-dispatch.mjs`, so a new import on the branch cannot escape the list; only an import added on the base after the branch was cut can.
