## Summary
`handling-review-findings`'s documented `reviewThreads` GraphQL recipe passes `-f cursor=null` on the first page, which silently returns zero threads even when real ones exist

## Environment
- **Product/Service**: `plugins/git-kit/skills/handling-review-findings/references/github-api-mechanics.md` — the "Resolving a review thread" section's `reviewThreads` query example
- **Region/Version**: this repo (`andres-cc-marketplace`)

## Reproduction Steps
1. Open a real PR with at least one unresolved inline review comment (e.g. PR #311 in this repo at the time of filing).
2. Run the doc's documented first-page recipe exactly as written:
   ```
   gh api graphql -F owner="<owner>" -F name="<repo>" -F number=<pr> -f cursor=null -f query='
   query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
     repository(owner: $owner, name: $name) {
       pullRequest(number: $number) {
         reviewThreads(first: 50, after: $cursor) {
           pageInfo { hasNextPage endCursor }
           nodes { id isResolved path line comments(first: 1) { nodes { databaseId body author { login } } } }
         }
       }
     }
   }
   '
   ```
3. Observe the response.

## Expected Behavior
The query should return the PR's real review threads, including the known unresolved one.

## Actual Behavior
Returns an empty thread list even though a real, unresolved thread exists:
```
{"data":{"repository":{"pullRequest":{"reviewThreads":{"pageInfo":{"hasNextPage":false,"endCursor":null},"nodes":[]}}}}}
```

Root cause: `gh api`'s `-f`/`--raw-field` flag always sends its value as a literal string, never JSON `null` (only `-F`/`--field` supports typed values, and even that has no native `null`). So `-f cursor=null` sends the GraphQL `$cursor` variable as the string `"null"`, not an actual null — the query's `after: $cursor` argument then treats `"null"` as a real (bogus) pagination cursor, and the connection returns an empty page instead of starting from the beginning.

Confirmed fix: re-running the identical query with the `$cursor` variable declaration and `-f cursor=null` dropped entirely (`reviewThreads(first: 50)`, no `after:` argument) correctly returns the real thread, including its `id`, `isResolved: false`, `path`, and `comments`. A later page should only ever pass a real `-f cursor="<endCursor>"` value taken from a prior response's own `pageInfo.endCursor` — never a placeholder on the first call.

## Error Details
~~~
{"data":{"repository":{"pullRequest":{"reviewThreads":{"pageInfo":{"hasNextPage":false,"endCursor":null},"nodes":[]}}}}}
~~~

## Visual Evidence
N/A

## Impact
**High** — this is the exact recipe `handling-review-findings`'s own Workflow step 8 ("Resolving a review thread") tells an agent to follow verbatim when triaging PR review threads. Following it as written against a real PR silently returns "no review threads found" even when threads exist, since `hasNextPage: false` / `endCursor: null` both read as a normal "nothing more to fetch" signal rather than indicating the query itself malfunctioned. A session following the doc as-is would either wrongly conclude there's nothing to resolve on a PR that has real, unresolved findings, or have to independently rediscover this exact fix — which is what happened when this bug was found.

## Additional Context
Found 2026-09-11 while triaging a real Codex review finding on PR #311 via the `handling-review-findings` skill itself — the documented recipe returned zero threads on the first attempt; omitting the cursor variable/flag entirely on a retry surfaced the real thread correctly.

Suggested fix (not prescriptive): remove the `$cursor` variable declaration and the `-f cursor=null` flag from the documented first-page example in `references/github-api-mechanics.md`; only introduce `$cursor` and a real `-f cursor="<endCursor>"` value in a follow-up call once pagination is actually needed (i.e. a prior response's `pageInfo.hasNextPage` was `true`).
