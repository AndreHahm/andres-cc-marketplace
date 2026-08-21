## Summary
`guard-raw-pr-review.sh` guards `gh pr review` and `gh pr comment`, but not their equivalent raw `gh api` REST calls — `gh api -X POST repos/{owner}/{repo}/pulls/{n}/reviews` performs the same action as `gh pr review --approve`/`--request-changes`, and `gh api repos/{owner}/{repo}/issues/{n}/comments` performs the same action as `gh pr comment` (GitHub's Issues API backs PR comments). Neither is matched by any existing branch.

## Environment
- **Product/Service**: `plugins/git-kit/hooks/scripts/guard-raw-pr-review.sh` (mirrored under `.claude/hooks/scripts/`)
- **Region/Version**: this repo, found during a `security-reviewer` pass on this file, branch `feat/review-findings-handling`, 2026-08-21

## Reproduction Steps
1. `gh api -X POST repos/{owner}/{repo}/pulls/123/reviews -f event=APPROVE` — approves a PR via the REST API directly.
2. `gh api repos/{owner}/{repo}/issues/123/comments -f body="..."` — posts a PR comment via the REST API directly (PRs share the Issues comments endpoint).
3. Neither matches `REPLIES_RE` (requires `/comments/{id}/replies`, a different, more specific endpoint) or `GRAPHQL_RE`, and neither is the literal `gh pr review`/`gh pr comment` subcommand form — both fall through to `exit 0`, unguarded, with no marker check.

## Expected Behavior
Either these two endpoints are guarded the same way the other two `gh api` write actions already are, or the file's own header comment states plainly and specifically why they're accepted as out of scope (today it names the general residual but not these two endpoints specifically).

## Actual Behavior
Both endpoints are unguarded. The file's header (as of this writing) already discloses a general residual — "a raw `gh api .../pulls/*` write call outside these two shapes remains unguarded, mitigated only by every git-kit skill with a broader `gh api` grant being a reviewed, allowlisted component" — but that mitigation depends entirely on no currently-allowlisted skill (or a skill added later) ever having a broad enough `gh api` grant to reach these two specific endpoints, which isn't independently verified anywhere.

## Impact
**Medium** — these are functional equivalents of the two actions this file was specifically built to guard (`gh pr review`, `gh pr comment`), reachable via the exact same `gh api` mechanism the file already parses for its other two branches. The endpoint-matching machinery to close this already exists in the file (same `REPLIES_RE`/`GRAPHQL_RE` pattern), so this isn't a new mechanism to build, just two more endpoint patterns.

## Suggested Fix (not prescriptive)
Extend the endpoint-matching to cover `/pulls/{n}/reviews` (any write verb) and `/issues/{n}/comments`, using the same `API_RE` + endpoint-regex-as-independent-condition structure the file already uses for `REPLIES_RE`/`GRAPHQL_RE`. Alternatively, if these are deliberately staying out of scope for now, update the header comment to name these two endpoints specifically (not just "a raw `gh api .../pulls/*` write call") so a future reader knows this was a considered decision, not an oversight.

## Additional Context
Found during the same `security-reviewer` pass that found and fixed two other, higher-severity bypasses in this file (both fixed in the same commit) — this one was left unfixed and filed here instead, since closing it means expanding this guard's endpoint coverage beyond what the current branch's own functional need (the reply/resolveReviewThread endpoints `handling-review-findings` actually uses) requires, which is a scope decision worth its own review rather than folding into an unrelated bug-fix commit.
