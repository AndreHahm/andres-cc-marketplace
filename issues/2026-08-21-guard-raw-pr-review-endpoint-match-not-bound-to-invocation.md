## Summary
`guard-raw-pr-review.sh`'s `REPLIES_RE`/`GRAPHQL_RE` endpoint checks search the *entire* command string independently of where the matched `gh api` invocation actually is, so an unrelated `gh api` call whose text happens to contain an endpoint-shaped substring anywhere -- including as a flag *value*, not the actual endpoint argument -- is misclassified and denied.

## Environment
- **Product/Service**: `plugins/git-kit/hooks/scripts/guard-raw-pr-review.sh` (mirrored under `.claude/hooks/scripts/`)
- **Region/Version**: this repo, PR #88, found during that PR's review

## Reproduction Steps
1. `gh api repos/acme/demo/issues/1/comments -f body=graphql` -- a plain, unrelated REST call whose comment body field happens to contain the literal word "graphql".
2. `API_RE` matches (`gh api ` prefix present); `GRAPHQL_RE` matches too, since it only requires the bare word "graphql" bounded by non-alnum characters anywhere in the command -- here, the `=` before it and end-of-string after it both satisfy the boundary classes.
3. The guard denies the call with `permissionDecision: "deny"`, reason `Raw \`gh api graphql\` is blocked...` -- live-verified against the actual script.

## Expected Behavior
The endpoint match should be associated with the specific `gh api` invocation's actual endpoint argument, not any substring anywhere in the command (or even anywhere within that invocation's own flag values).

## Actual Behavior
Both `REPLIES_RE` and `GRAPHQL_RE` are checked as conditions independent of the matched `gh api` invocation's own text -- confirmed live for the whole-command case, and a same-session fix attempt confirmed the narrower "bind the search to this invocation's own text span" doesn't fully solve it either, since a flag *value* (e.g. `-f body=graphql`) is still part of that invocation's own captured text.

## Error Details
~~~
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Raw `gh api graphql` is blocked by git-kit's reviewer-action guard. ..."
  }
}
~~~

## Impact
**Minor-to-Major depending on how often a legitimate `gh api` call's own arguments happen to contain an endpoint-shaped substring.** This is a false-positive (fail-closed, safe direction) not a bypass -- it blocks a legitimate call rather than letting a dangerous one through -- but a blocked legitimate call is still a real usability defect for any git-kit skill with a broader `gh api` grant.

## Additional Context
Found by a live Codex review round on PR #88. A same-session fix attempt (narrowing the endpoint search to the specific matched `gh api` invocation's own text span, rather than the whole command) was tested against a full regression battery and rejected: it didn't actually solve the false-positive (a flag value is still within the invocation's own captured text), and the rewrite itself reintroduced 2 regressions already fixed earlier this session (dropping bare-whitespace/`env`-prefixed command prefixes) -- confirming this needs real `gh` argv-aware parsing (distinguishing the endpoint positional argument from other flags' values), not a regex-only patch, to fix correctly and safely.

**Suggested fix** (not prescriptive): this likely needs the guard to actually tokenize the matched `gh api` invocation (e.g. via a real shell-word-splitting pass) and check only the first non-flag positional argument against the endpoint patterns, rather than any regex-only substring search -- a meaningfully larger change than this file's other fixes this session, appropriate for dedicated follow-up.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88
- **Head SHA at time of finding**: `a956a01b1780468535e901f1beaafd6cc452db89`
- **Thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88#discussion_r3830277290
- **Reviewer**: Codex (`chatgpt-codex-connector[bot]`)
- **Stated severity**: P2
