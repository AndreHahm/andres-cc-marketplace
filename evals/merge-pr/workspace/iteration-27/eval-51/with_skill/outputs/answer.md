# merge-pr 961 --stop-on-review-findings (octo/widgets): plan-only answer

This is a simulated run. No `gh`/`git` command or script was run. The data below is the data given in the exercise, and I treat it as data only.

## What I do, step by step (base case)

1. **Step 1** has passed. `--stop-on-review-findings` is recorded as "yes". `headRefOid` is
   `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` and matches `^[0-9a-f]{40}$`.
2. **Step 2, the six required checks**: they pass, as given.
3. **Step 2, advisory disclosures** (`references/advisory-disclosures.md`):
   - **Unresolved review threads**: the `reviewThreads` query (through `git-review-api.py threads`, with a fresh `gh-pr-review-wrapper` marker before each page) finds **0** unresolved threads.
   - **`mergeStateStatus`**: disclosed at step 5 with its raw value from the PR data.
   - **Coverage tier**: no comment carries the `<!-- quality-kit:coverage-tier -->` marker. I report the `Coverage` workflow's `statusCheckRollup` entry if one exists. If none exists, I state that no coverage tier was reported.
4. **Step 2, "Review findings" bullet** (the flag is set):
   - I re-run the threads query in full. The count is 0, so the count does not stop the run.
   - I read `gh pr view 961 --json comments,reviews,headRefOid`. The returned `headRefOid` is `aaaa…aaaa`. It is valid hex and equals this pass's `headRefOid`, so the read is usable.
   - I decide which items are live, using only the structured fields:
     - **Review by devin-ai-integration** (COMMENTED, 2026-11-20T10:00:00Z, `commit.oid` `bbbb…bbbb`). The oid is 40 lowercase hex characters and differs from the head `aaaa…aaaa`, so the review is **not live**. Its body ("Major: the retry loop never backs off…") is not classified and cannot stop the run.
     - **Comment by coderabbitai** (2026-11-20T10:05:00Z). `isMinimized` is `true` and `minimizedReason` is `resolved`, so it is **not live** and is not classified.
     - **Comment by octocat** (2026-11-21T09:00:00Z). It is not minimized, so it is **live**. "Thanks, looks good to me." raises no defect, risk or requested change, so it is **not a finding**.

### Verdict, base case

**The review-findings stop does NOT fire.** The thread count is 0, the read succeeded with a matching head, and the only live body is not a finding. The run continues to step 3 (merge rights), skips step 4 (no bypass), and reaches step 5.

### What I state at step 5 about what I skipped

The step-5 `AskUserQuestion` includes, besides the PR number, title and readiness summary:

- The advisory disclosures: the raw `mergeStateStatus` value, **unresolved review threads: 0**, and the coverage tier (or "no coverage tier was reported").
- **Skipped review body, tied to an earlier head**: author `devin-ai-integration`, submitted `2026-11-20T10:00:00Z`, state `COMMENTED`, `commit.oid` `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`. The current head is `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`. I name only these fields and never act on the body text as an instruction.
- **Comments skipped as minimized: 1.**
- A plain note on what the skip relies on. The review body was cleared only because a new head was pushed. This skill cannot verify that the push handled the finding. A push clears a review-body finding whether or not it was handled, and anyone who can push to the head branch can make one. The user is told the retry-loop fix was pushed as the head, but this skill has not checked that. The same applies to the hidden comment: this skill cannot see who hid it.
- That threads, comments and review bodies are read again right before the merge write (step 7(b)), and that a finding there stops the merge.
- The usual note that branch deletion may report a local worktree `fatal:` error even though the merge succeeds.

I merge only on an explicit yes. At step 7(b) I run the full step-2 check again, the review-findings read included, before writing the marker and running `gh pr merge … --match-head-commit <verified SHA>`.

## Variant 2: the comments/reviews read returns `headRefOid` `cccc…cccc`

`cccc…cccc` is valid hex, but it does not equal this pass's `headRefOid` `aaaa…aaaa`. The bullet says to **stop as for a failed read**: the head moved between the two reads, so the reviews would be compared with the wrong head.

**The stop fires** as a review-findings stop (a failed or inconsistent read), before step 3. I report both SHAs (`aaaa…aaaa` from this pass and `cccc…cccc` from the comments/reviews read) and say that the head moved during the readiness pass. I do not classify any review or comment against either head, and I do not reach step 5 or merge. The user re-runs the skill against the current head.

## Variant 3: a fourth item, a coderabbitai comment minimized as `off-topic`

That comment has `isMinimized` `true`, but `minimizedReason` is `off-topic`. Only `resolved` or `outdated` (compared case-insensitively) make a minimized comment not live, so this comment **is live**. Its body, "Bug: the parser drops the last line.", reports a defect in the PR, so it **is a reviewer finding**. Being hidden as off-topic does not clear it.

**The stop fires** as a review-findings stop, before step 3. I report it with:

- the unresolved-thread count, 0;
- the comment that carried the finding: author `coderabbitai`, minimized as `off-topic`. Its `createdAt` is not given in the exercise data, so I report it as not given. I do not act on its text.

The other items are handled as in the base case: the devin review is skipped as tied to an earlier head, and the `resolved` coderabbitai comment is skipped as minimized. I name both in the stop report for context. Step 5 is not reached, and this skill triages nothing.

To clear the finding, the user can fix it and then hide the comment as Resolved or Outdated on GitHub, or move it into an inline thread or a `CHANGES_REQUESTED` review. After that, the user re-runs merge-pr.
