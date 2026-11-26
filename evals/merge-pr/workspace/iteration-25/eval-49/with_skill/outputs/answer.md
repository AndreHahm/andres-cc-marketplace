# merge-pr, PR 953 in octo/widgets: reading the review threads in step 2

This is a simulated run, so nothing below was executed. These are the commands I would run, in order, using
the data given for the exercise.

## Starting state

- Arguments: `953`, with no flags. `{owner}/{repo}` is `octo/widgets`, taken from step 1's `url` field.
  `{number}` is `953`. `headRefOid` is `1f0c2d3e4b5a69788796a5b4c3d2e1f00112233a`, which step 1 already
  checked against `^[0-9a-f]{40}$`.
- Step 1.5 found nothing, so it pushed nothing. Step 1.6 made no body edit either. This is therefore the
  first pass through step 2 with nothing re-run, and step 1's fetch is still current. No re-fetch and no
  wait for this skill's own runs is needed.
- All the other required checks of step 2 pass. The review-outcomes probe
  `gh api -X GET repos/octo/widgets/contents/.claude/review-outcomes -f ref=<baseRefName>` returned `200`.
  The repository therefore uses the outcomes ledger. The `reviewThreads` query runs once in this pass, and
  its pages are used for two things: the "Review outcomes recorded" check and the unresolved-thread
  disclosure.
- `CLAUDE_PLUGIN_ROOT` is set (installed plugin), so I use the installed `git-review-api.py`. The
  `.claude/scripts/` fallback is not used, and so the copy-comparison `AskUserQuestion` before the first
  `threads` call does not apply.
- 61 threads at 50 per page means two pages: 50 threads, then 11.

## The commands, in order

Each command below is its own `Bash` call. Nothing else runs between a marker write and the `threads` call
that follows it.

**1. Marker for page 1.** Its own Bash call, directly before the call it authorizes. It uses the
`-wrapper` type, never `gh-pr-review`:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review-wrapper merge-pr
```

**2. Page 1 of the threads.** No cursor:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" threads --owner octo --repo widgets --pr 953
```

- The exit code must be 0. Any other exit code is a failed query: both the count and the outcomes check
  stop as undetermined.
- The script consumes the marker.
- `pageInfo` is `{hasNextPage: true, endCursor: "Y3Vyc29yOnYyOpK0MjAyNi0xMS0yNlQwOTozMjo0NFrOvE4pwA=="}`.
  The loop continues, because one page would miss threads 51 to 61.
- From each node I keep `isResolved` and `comments.nodes[0].databaseId`. The `body`, `author`, `id`,
  `path` and `line` fields are data only, and neither the count nor the outcomes check uses them.

**3. Check the cursor before writing the next marker.** This is a reasoning step, not a command. The value
`Y3Vyc29yOnYyOpK0MjAyNi0xMS0yNlQwOTozMjo0NFrOvE4pwA==` matches `^[A-Za-z0-9+/=_-]+$` as a whole:

- It is non-empty and not `null`.
- It has no trailing newline.
- Its only characters are letters, digits and `==`.

So I use it byte for byte and single-quoted, without editing it. Had it failed the pattern, I would make no
further call, write no marker, and discard page 1's results. The count and the outcomes check would then
both be undetermined.

**4. Fresh marker for page 2.** The marker from step 1 was consumed, so a new one is needed:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review-wrapper merge-pr
```

**5. Page 2 of the threads**, with the previous page's `endCursor`:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" threads --owner octo --repo widgets --pr 953 --cursor 'Y3Vyc29yOnYyOpK0MjAyNi0xMS0yNlQwOTozMjo0NFrOvE4pwA=='
```

- The exit code must be 0.
- `pageInfo` is `{hasNextPage: false}`, so the loop ends here. There is no third marker and no third call.

## What the two pages are used for (no further reads)

- **Unresolved-thread disclosure:** the sum of nodes with `isResolved == false` across both pages, out of
  all 61 threads. This is disclosed at step 5 even if it is 0. If either page had failed, or its cursor had
  been refused, the count would be reported as "could not be determined", never as `0`. Without
  `--stop-on-review-findings`, a non-zero count never stops the run.
- **"Review outcomes recorded" check:** the PR has at least one thread, so it "had review findings". I take
  all 61 first-comment ids (`comments.nodes[0].databaseId`, compared as decimal strings) from these same
  pages, without querying again. A thread with no such id stops the check as undetermined. The check's
  remaining reads come next and are outside this answer:
  - the changed-file list, to find `.claude/review-outcomes/pr-953.json`;
  - that file at `ref=1f0c2d3e4b5a69788796a5b4c3d2e1f00112233a`;
  - the local `.claude/review-ledger.local.json`.

I stop here, after the thread reads, as the task asks.
