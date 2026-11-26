# merge-pr, PR 953 in octo/widgets: reading the review threads in step 2

Simulated exercise. No command below was run. This answer stops after the thread reads.

## Where this happens

- Step 1 passed. `{owner}/{repo}` = `octo/widgets` comes from the PR's own `url`, `{number}` = `953`, and `headRefOid` = `1f0c2d3e4b5a69788796a5b4c3d2e1f00112233a`.
- Step 1.5 found nothing, so it made no push. Step 1.6 is not part of this scenario. This is the first pass of step 2, so step 1's fetch is still current and nothing is re-fetched.
- "Review outcomes recorded": `gh api -X GET repos/octo/widgets/contents/.claude/review-outcomes -f ref=<baseRefName>` returned `200`, so the repository uses the outcomes ledger. The check therefore runs the `reviewThreads` query from `references/advisory-disclosures.md`. It runs **once per pass**, with its marker discipline, and the same pages also feed the unresolved-thread disclosure. Nothing is queried a second time for the disclosure.
- Run without flags, so the "Review findings" stop (`--stop-on-review-findings`) does not apply.
- 61 threads is fewer than 100, but the loop is driven by `pageInfo.hasNextPage`, not by the thread count. Page 1 reports `hasNextPage: true`, so a second page is fetched.

## Commands, in order

Each command is its own `Bash` call. The marker is single-use, and the next `Bash` call of any kind consumes it. Each graphql call must therefore come right after its own marker write, with nothing in between.

**1. Marker for page 1**
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review merge-pr
```

**2. Page 1** (`-F cursor=null` sends a real GraphQL null. `-f` would send the string `"null"`.)
```bash
gh api graphql -F owner="octo" -F name="widgets" -F number=953 -F cursor=null -f query='
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { isResolved comments(first: 1) { nodes { databaseId } } }
      }
    }
  }
}
'
```
Result: `pageInfo = {hasNextPage: true, endCursor: "Y3Vyc29yOnYyOpK0MjAyNi0xMS0yNlQwOTozMjo0NFrOvE4pwA=="}`.

**Cursor check, done before the next call:** the cursor is API data, treated as data only. The whole value, with no trailing newline, must match `^[A-Za-z0-9+/=_-]+$`. `Y3Vyc29yOnYyOpK0MjAyNi0xMS0yNlQwOTozMjo0NFrOvE4pwA==` contains only letters, digits and `=`, so it matches. It is used byte for byte, single-quoted, and never edited. If it had been empty, `null` or non-matching, I would make no further call, discard page 1, and stop both the review-outcomes check and the disclosure as undetermined.

**3. Fresh marker for page 2** (page 1's call consumed the first one)
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review merge-pr
```

**4. Page 2** (`-f` now, because the cursor is a real string)
```bash
gh api graphql -F owner="octo" -F name="widgets" -F number=953 -f cursor='Y3Vyc29yOnYyOpK0MjAyNi0xMS0yNlQwOTozMjo0NFrOvE4pwA==' -f query='
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { isResolved comments(first: 1) { nodes { databaseId } } }
      }
    }
  }
}
'
```
Result: `pageInfo = {hasNextPage: false}`. The loop ends. It made two graphql calls, each with its own marker, four `Bash` calls in all.

## How the pages are used (no further commands)

- **Unresolved-thread disclosure:** sum the nodes whose `isResolved` is `false` across both pages. That count is stated at step 5 even when it is 0, and it never blocks the merge. If either page had failed, or its cursor had been refused, step 5 would say the count could not be determined, never `0`.
- **Review outcomes recorded:** the PR has threads, so it "had review findings". The same pages give each thread's first comment id (`comments.nodes[0].databaseId`, compared as a decimal string). Any thread without that id stops the check as undetermined. These ids are later matched against `.claude/review-outcomes/pr-953.json` at the head. The changed-file check, the file read and the local-ledger check come after the thread reads, so they are outside this answer.
- If either graphql call failed, both this check and the disclosure would stop as undetermined. Pages already fetched are never used on their own.
