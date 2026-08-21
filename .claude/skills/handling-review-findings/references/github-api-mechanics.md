# GitHub API Mechanics

## Replying to an inline PR review comment

```
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies -f body="..."
```

The shorter, more-intuitive-looking `repos/{owner}/{repo}/pulls/comments/{comment_id}/replies` (no
`pull_number` segment) 404s — this exact pitfall is already documented in
`.claude/rules/verify-tool-behavior-before-instructing.md`'s PR #51 row. Always include `pull_number`.

For a long or multi-line reply body, write it to a scratchpad file first rather than inline shell
quoting — avoids shell-escaping failures on backtick- or quote-heavy finding text:

```
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies \
  -f body="$(cat "<scratchpad-path>/reply.txt")" --silent
```

## Resolving a review thread

There is no REST endpoint for this at all. It requires GitHub's GraphQL API — first a `reviewThreads`
query on the PR to obtain the thread's opaque node `id`, then the `resolveReviewThread` mutation keyed
by that `id`. Both calls go through `gh api graphql -f query=...`.

The `reviewThreads` query form actually needed, including the field that bridges a thread node back to
the REST `comment_id` the reply endpoint above requires:

```
reviewThreads(first: 50) {
  nodes {
    id
    isResolved
    path
    line
    comments(first: 1) {
      nodes { databaseId body author { login } }
    }
  }
}
```

`comments.nodes[0].databaseId` is the REST `comment_id` — the missing link between the GraphQL thread
list and the REST reply endpoint above.

**The `gh-pr-review` marker (SKILL.md's Workflow / GitHub API Mechanics) goes immediately before the
`resolveReviewThread` mutation call, never before this read-only `reviewThreads` lookup.** The lookup
is itself a `Bash` call and would consume a live marker on its own if one were already written,
leaving the mutation call right after it denied for lack of a marker — confusing, though not unsafe
(it fails closed). If the lookup and the mutation happen as two separate `Bash` calls, write the
marker again right before the mutation specifically.

Resolving one thread:

```
gh api graphql -f query='mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { id isResolved } } }' -f id="$tid"
```

Batch resolution — several threads in one shot beats N separate calls (Bash-tool syntax, POSIX `for`;
this repo's agent shell is PowerShell-primary, but the `Bash` tool is a separate, always-available
surface for exactly this kind of POSIX scripting):

```
for tid in PRRT_xxx PRRT_yyy; do
  gh api graphql -f query='mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { id isResolved } } }' -f id="$tid"
done
```

## Leaving a thread unresolved on purpose

For a deferred (round-3+, scope-deferred, or declined) finding, reply with the tracking-issue link (or
the decline acknowledgment) and state explicitly that the thread is being left open until the issue is
addressed — then simply never call `resolveReviewThread` for it. This is the mechanical counterpart to
`references/round-and-dedup-rules.md`'s "deferred findings don't get resolved" rule.

## Fetching all reviewers together

Pull every reviewer's inline comments in one call and triage as one batch, rather than per-tool —
consistent with "the round counter is per-PR, not per-reviewer":

```
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments
```

## Issue traceability payload

Every issue filed from the Issue path (SKILL.md Workflow step 5) must include, beyond
`github-issue-creator`'s standard template fields:

- The PR URL.
- The head SHA the finding was raised against.
- The review thread/comment URL or ID.
- The reviewer that raised it (tool name, or human reviewer's handle).
- Its stated severity.

This is the payload a reader needs to act on the issue without re-opening the PR. Add it as its own
`## Review Finding Source` section in the drafted issue file, after `## Additional Context`.

## Issue-filing convention

Use a plain, non-closing reference in the PR body/comment — "Found in PR #N" — never
"Fixes #N"/"Closes #N". A merge must not auto-close a still-open, still-unaddressed issue.

## Scratchpad path

Any placeholder path above (e.g. `<scratchpad-path>/reply.txt`) means the session's actual scratchpad
directory — never a literal path to type as-is, and never a bare relative filename, which would
silently resolve to the current working directory instead (see CLAUDE.md's "No Scratch Files at Repo
Root" and `.claude/rules/require-gitignored-scratch-locations.md`).
