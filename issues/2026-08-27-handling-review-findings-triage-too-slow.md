## Summary
Triaging PR review findings via `handling-review-findings` takes too long end-to-end — this run on PR #154 (6 findings) took long enough that the user stopped the review-round loop early due to time.

## Environment
- **Product/Service**: `git-kit` plugin, `handling-review-findings` skill
- **Region/Version**: n/a

## Reproduction Steps
1. Open a PR that draws inline findings from more than one automated reviewer (here: Codex + Devin, 6 findings total, one duplicated across both reviewers).
2. Run `handling-review-findings` to triage: verify each finding, decide fix/defer, then reply-and-resolve (or reply-only) on each finding's own GitHub thread.
3. Observe the wall-clock time from "CI is green, start triage" to "all threads replied/resolved."

## Expected Behavior
Triaging a small batch of findings (6, on one PR) should be fast enough that a user doesn't need to interrupt the loop to save time.

## Actual Behavior
This run was slow enough that the user explicitly asked to stop after round 1 rather than continue to a possible round 2, citing time spent. Two contributing factors observed in this run:
1. **Verification depth before trusting each finding**: each of the 6 findings required an independent check against the actual repo content (reading cited files/lines, cross-checking claims like "this rule triggers on read not on Write") before it could be classified as real vs. a false positive. This is arguably the right amount of rigor, but it's inherently slow and scales linearly with finding count.
2. **Fully sequential GitHub API mechanics with no batching**: per `references/github-api-mechanics.md`, the mechanism is one `gh api .../replies` call per finding (6 calls), a separate `reviewThreads` GraphQL lookup, then one `resolveReviewThread` mutation per resolved thread (4 calls) — each `gh api graphql` call additionally requires its own fresh marker-write (`write-git-kit-marker.sh`) immediately beforehand, since the marker is single-use and consumed by the very next Bash call. That's roughly 6 (replies) + 1 (lookup) + 4 (resolves) + several marker writes = 15+ sequential tool round-trips for a 6-finding batch, none of them batched even though the reference doc itself shows a batch-resolve loop is possible (a `for tid in ...` shape) when the marker-per-call constraint doesn't force a call to stand alone.

## Impact
**Medium** — no functional defect (both fixes and all thread state ended up correct), but the process cost scales badly with finding count and reviewer count, which will get worse as more reviewers are enabled or `max_rounds` is used more fully. Users may start skipping proper triage (or accepting review rounds that were never verified) purely to save time, which defeats the point of `handling-review-findings` existing at all.

## Additional Context
- Filed as trackable feedback per explicit user request, not fixed in this session — the user asked to stop the review-round loop here due to time.
- Possible directions for a fix (not evaluated in depth): batch the `resolveReviewThread` mutations into one `gh api graphql` call with multiple mutation aliases (avoiding N separate marker-gated calls); investigate whether the marker guard could accept a single marker covering a short burst of `gh api graphql` calls instead of exactly one; or make the per-finding verification step optionally lighter for low-severity/duplicate findings so the wall-clock cost concentrates on the higher-severity ones.
- Related file: `plugins/git-kit/skills/handling-review-findings/references/github-api-mechanics.md` (mechanics), `plugins/git-kit/hooks/scripts/guard-raw-pr-review.sh` (the marker guard forcing per-call markers).
