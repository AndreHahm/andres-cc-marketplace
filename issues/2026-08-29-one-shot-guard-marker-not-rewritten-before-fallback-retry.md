## Summary
A one-shot guard-marker mechanism consumed by the first attempt of a multi-step operation isn't automatically valid for a documented fallback retry — `guard-raw-pr-ops.sh` consumes git-kit's one-shot marker on the first `gh pr merge --rebase` attempt, and a fallback retry after that attempt fails is unconditionally blocked by the same guard, regardless of the marker's own TTL.

## Environment
- **Product/Service**: `git-kit` plugin — `merge-pr` skill / `guard-raw-pr-ops.sh`
- **Region/Version**: this repo, found during PR #148 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. `merge-pr`'s step 7 writes a one-shot marker via `write-git-kit-marker.sh` and runs `gh pr merge --rebase`.
2. `guard-raw-pr-ops.sh` consumes (deletes/invalidates) that marker the moment the guarded command runs — regardless of whether the command itself succeeds or fails.
3. If the rebase merge fails, step 7(d)'s documented fallback path runs (readiness checks, user confirmation, retry) and attempts the merge again — but writes no new marker first.
4. The retry is blocked by `guard-raw-pr-ops.sh`, which finds no valid marker, even though the fallback path is a legitimate, intended continuation of the same guarded operation.

## Expected Behavior
A one-shot guard-marker mechanism must be rewritten immediately before *every* attempt of the guarded operation, not just the first — including inside any documented fallback/retry branch.

## Actual Behavior
The fallback retry path had no marker-rewrite step, so it was unconditionally blocked by the guard every time, independent of the marker's 60-second TTL (the TTL never got a chance to matter, since the marker was already fully consumed rather than merely expired).

## Impact
[Severity: High] This broke the skill's own documented recovery path — a rebase-merge failure followed by the documented fallback would always fail a second time for a reason unrelated to the actual merge conflict. Fixed in `git-kit`'s PR #148 (commit `d9bfdc1`): step 7(d)'s rejection fallback now re-writes the git-kit marker (`write-git-kit-marker.sh gh-pr-merge merge-pr`) immediately before the retry. Verified: `check_step7_rejection_fallback` in `scripts/smoke_test.py` was strengthened to assert the marker-rewrite text is present specifically within sub-step (d), and passes.

## Additional Context
Mined from PR #148's own review history (`chatgpt-codex-connector[bot]`; 12 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #148` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/148#discussion_r3872420051
