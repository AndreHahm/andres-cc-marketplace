# A clean Codex review of a large diff does not show how much of it the reviewers read

## Summary
`run-codex-review` lists every changed path in `reviewed_paths`, but nothing in the result shows how much of a large diff a reviewer actually read. A clean result on a large diff can't be read as coverage. It is still undecided whether model calls need to be bounded (chunked) for that reason.

## Environment
- **Product/Service**: `scripts/marketplace_ci/review.py` (`run-codex-review`, CI's Codex delta review and the local parity review); `codex-review-bridge`
- **Region/Version**: `main` at `772f5c26` (2026-11-21), after #614
- **Browser/OS**: Linux and Windows (measured on both)

## Reproduction Steps
1. Commit a large fixture diff in a scratch clone (for example, 4,500 new 1 KiB files).
2. Run `.claude/scripts/git-codex-parity-review.py --output <scratch>/result.json`.
3. Compare `reviewed_paths` with what the reviewers actually opened.

## Expected Behavior
A result either shows how much of the diff each reviewer inspected, or the review is bounded so that a clean result can stand for the whole diff.

## Actual Behavior
- Linux (2026-10-17): 3,000 files, clean in 72 s; 4,546 paths after #614, clean in 273 s.
- Windows (2026-11-21): 4,500 files, clean in 1,066 s, `reviewed_paths` 4,500.
- `reviewed_paths` is the dispatched scope, not a read record. No run found a failure, and none can show coverage.

## Impact
**Low**: no failure or missed finding is known. The risk is a clean result on a large PR being taken as a full review. Workaround: split large PRs.

## Additional Context
- Carried over from #611 (Phase 5), which closed with this question still open. Records: the 2026-10-17 comments on #611 and https://github.com/AndreHahm/andres-cc-marketplace/issues/611#issuecomment-7059564597
- Related:
  - #689: a pass that could not read the workspace is counted as complete. That covers a narrower case of the same gap.
  - #586: Phase 4, which measures the reviewers.
  - #568: the parent issue.
- Chunking the path list was tried and reverted on #611. The bridge drops a finding whose path is outside that call's own `--target-paths`, so per-chunk calls lose cross-file findings. Any bounded design has to keep the full scope for validation.
- **Owner decision needed:**
  - (a) record per-reviewer read evidence in the result;
  - (b) bound the model calls;
  - (c) document the limit and leave it.
