## Summary
Phase 5 of #568: send a large diff to Codex in bounded chunks instead of one long call, in the local parity review, and make the parity review state every way it differs from CI. `cross-model-review` already plans a scoped review, so there the work is to verify it against a large diff, not to build it.

## Environment
- **Product/Service**: `.claude/scripts/git-codex-parity-review.py` (local CI-parity Codex review), the shared CI review code in `scripts/marketplace_ci/review.py`, and git-kit's `cross-model-review` skill
- **Region/Version**: `main` at `bb06e180` (2026-10-17)
- **Browser/OS**: not relevant

## Reproduction Steps
Not reproduced yet; this is the first task.
1. Build a deliberately large diff (fixtures, not a real PR).
2. Run the parity review against it, then a `cross-model-review` pass against it.
3. Record diff size, duration and failure kind for each path.

## Expected Behavior
A large diff does not make one model call carry the whole review: work is split into bounded chunks, one chunk failing does not lose the others, and the merged result keeps the single result-file shape and the computed gate. When the parity run's chunking differs from CI's, the run says so and does not present a clean result as a CI prediction.

## Actual Behavior
Checked on `main` on 2026-10-17:
- `cross-model-review` plans a scoped review (slices, dispatch batches, one Codex dispatch per batch; `references/scoped-review.md`, planner `scripts/git-review-scope.py`, budgets `cross_model_review_budget_bytes` 250000 and `cross_model_review_max_slice_bytes` 80000 in `git-kit.settings.json`). #541 is still open, so this may not be everything it intends.
- The parity wrapper does no chunking of its own. It runs `python -m scripts.marketplace_ci run-codex-review` once, with one instruction set, and checks the result file.
- `review.py` caps the diff it reads at 64 MiB, dispatches reviewers with a pool of 2 workers, 2 timeout retries and 1 empty retry, and has no per-size splitting of the model call.
- Whether CI itself ever fails on a large diff, at what size, and whether `helper_unknown_error` is Windows-only are not established. No incident is claimed.

## Impact
**Medium** - A very large PR may time out or lose its whole review in one failure; no incident is known and splitting the PR is a workaround.

## Additional Context
- Parent: #568. Definition: section 6 (Roadmap) of the comment "Solution concept v2" on #568 (comment 6173765036), plus its section 7 (RC3 "parity honest about differences", RC5 "chunking and `helper_unknown_error` remain") and #568's scope item 6. Gate to start: Phase 1 (#573, merged). Relates to #572 (Phase 0, timeout and result status), #586 (Phase 4, measures the reviewers), #541 (`cross-model-review` scope and optional models).
- Chunking "in the parity wrapper" means one of two things, because the wrapper only calls the shared CI path. Either change `scripts/marketplace_ci/review.py` (Tier-1: the PR needs a maintainer bypass attestation and the Tier-1 lists in `docs/ci.md` stay in sync), so parity matches CI. Or split the diff in the wrapper alone, which makes parity differ from CI and cuts against RC3.

### Proposed Solution
1. Reproduce first, as above, for both paths.
2. Decide with the owner where chunking lives: the shared `run-codex-review` path, or the wrapper only.
3. If chunking is needed: split by file groups within a size budget, merge findings through the existing computed gate, keep one result file shape.
4. Extend the parity run's existing difference note (it already covers timeout and model) to cover chunking.

### Acceptance Criteria
- [ ] A reproduction record (size, duration, failure kind) for a large diff on both paths.
- [ ] The owner's decision on where chunking lives is recorded in this issue before code is written.
- [ ] Tests first, using fixtures, not live runs.
- [ ] If a Tier-1 file changes, the PR carries the maintainer bypass attestation and the cross-check test passes.
- [ ] `plugin-rulebook` run for any changed component; `security-reviewer` run on any new gate.

### Out of scope
- Changing any reviewer prompt, model pin or weight (Phase 4 measures first).
- The refuted-finding briefing injection.
- Whole-diff behaviour of the optional agy, pi and devin reviewers (#541).
