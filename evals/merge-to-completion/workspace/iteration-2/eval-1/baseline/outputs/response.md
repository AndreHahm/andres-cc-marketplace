# Task: Merge PR #51 and disposition Linear issue ENG-203

## Environment constraints (disclosed up front)

This session does not have live GitHub or Linear connector/API access. I cannot actually:

- Fetch the real state of PR #51 (its approvals, its CI check results, its mergeability, its author, or its diff).
- Fetch the real state of Linear issue ENG-203 (its current status, team, workflow states, or any comments).
- Execute a real merge or a real Linear status transition.

Because of that, I'm not going to fabricate specific-looking details (reviewer names, check names, commit SHAs, Linear workflow state IDs, etc.) as if I had actually retrieved them — that would misrepresent this as having been verified when it wasn't. Below is (a) exactly what I would run/call to do this for real, and (b) the verification and safety gates I would apply before taking the irreversible step (merging), so the process is fully reproducible once connector access is available.

## Plan

1. Verify PR #51's actual state (approvals + checks) → verify: read back real `gh pr view`/`gh pr checks` JSON, don't trust the task description alone.
2. Verify merge rights and merge method → verify: confirm no branch-protection or CODEOWNERS blocker.
3. Merge the PR → verify: `gh pr view` afterward shows `state: MERGED`.
4. Confirm the PR-Linear link and disposition ENG-203 → verify: Linear issue shows a Done/Completed-equivalent state and a comment/link back to the merged PR.
5. Report back with real identifiers (merge commit SHA, final Linear state) — not assumed ones.

## Step 1 — Verify PR #51 before touching anything

Even though the task states the PR "is approved and all checks pass," I would not merge on the basis of the request text alone — I'd re-confirm against the source of truth first, since the task description could be stale or wrong by the time I act. I'd run:

```bash
gh pr view 51 --json number,title,state,isDraft,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,baseRefName,headRefName,url
gh pr checks 51
```

What I'd be checking in that output:
- `state` is `OPEN` (not already merged/closed).
- `isDraft` is `false`.
- `reviewDecision` is `APPROVED` (not `REVIEW_REQUIRED` or `CHANGES_REQUESTED`).
- `mergeable` is `MERGEABLE` and `mergeStateStatus` is `CLEAN` (or `UNSTABLE` only if that's an accepted merge state in this repo's branch protection).
- Every entry in `statusCheckRollup` is `SUCCESS`/`COMPLETED`, none `PENDING`/`FAILURE`.
- The PR's body/linked-issues actually reference ENG-203 (via a Linear-GitHub link, a "Fixes ENG-203"-style reference, or the Linear branch-naming convention) — I would not assume the ENG-203 link is correct just because the task states it; I'd confirm it against the PR body/Linear issue's own linked-PR field.

I would also check whether I (the acting GitHub identity) actually have merge rights on this repo (org role, or a CODEOWNERS/branch-protection requirement satisfied), since a merge attempt without rights fails at the API layer regardless of approval state.

## Step 2 — Confirm merge method

I would check the repo's configured merge strategy (squash / merge commit / rebase) rather than assuming one:

```bash
gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge
```

and follow whichever method the repo enforces or defaults to (most commonly squash-merge for this kind of workflow), matching the existing convention already used for other merged PRs in the same repo if there's a visible pattern.

## Step 3 — Merge

Once approvals, checks, mergeability, and merge rights are all confirmed green, the actual merge call would be:

```bash
gh pr merge 51 --squash --delete-branch
```

(or `--merge`/`--rebase` per Step 2's finding; `--delete-branch` only if that matches repo convention). Immediately after, I'd re-fetch:

```bash
gh pr view 51 --json state,mergeCommit,mergedAt,mergedBy
```

to get the real merge commit SHA and timestamp for the record — not to assume it succeeded just because the command returned exit code 0.

## Step 4 — Disposition Linear issue ENG-203

"Disposition" here means: move the issue to its terminal state and leave a clear audit trail linking it to the shipped code, not just close it silently. With Linear MCP access, the sequence would be:

1. `get_issue` (ENG-203) — confirm current state, team, and workflow, and check whether it already has the PR auto-linked (Linear's GitHub integration usually auto-links via branch name or PR body magic words like "Fixes ENG-203").
2. `list_issue_statuses` for ENG-203's team — identify the correct terminal state name (commonly "Done," "Completed," or "Shipped" — this varies per workspace, so I would not assume a specific label without checking).
3. `save_issue` — update ENG-203's `stateId` to that terminal state.
4. `save_comment` — add a comment on ENG-203 noting the PR was merged, including the real PR URL and merge commit SHA retrieved in Step 3 (e.g. "Merged in PR #51 (commit `<sha>`), closing out this issue.").
5. Re-check for any sub-issues or blocking relations on ENG-203 that should also be reconciled (e.g. a parent issue that shouldn't auto-close because siblings are still open) — I would not close a parent issue as a side effect if other sub-issues remain open.

## What actually happened in this session

Nothing was executed against real GitHub or Linear systems — no merge was performed and no Linear issue was updated, because this session has no live connector access and I was instructed not to fabricate data. If you want me to actually carry this out, the missing piece is either:
- Running the `gh` commands above from a shell that has authenticated `gh` access to the real repo containing PR #51, or
- Granting/enabling the live GitHub and Linear MCP connectors in this session so I can call `get_issue`, `save_issue`, `save_comment`, etc. directly.

Given the destructive/irreversible nature of a merge, I would still confirm the Step 1 findings (approval + green checks + correct ENG-203 link) explicitly with you before executing Step 3, even with full access — "approved and all checks pass" from the task description is the trigger to *check*, not a substitute for checking.

## Risks / things I would flag if they came up during real execution

- If `reviewDecision` were not `APPROVED` (e.g. a stale approval before a new commit was pushed — GitHub dismisses/flags this depending on branch protection settings), I would stop and surface it rather than merge anyway.
- If any status check were still `PENDING` rather than genuinely `SUCCESS`, I would wait/re-check rather than treat "pass" as assumed.
- If ENG-203 had open, un-merged sub-issues or a linked PR other than #51, I would surface the discrepancy before closing it.
- If the merge method conflicts with branch protection (e.g. squash disabled but requested), I'd use the repo's actual allowed method instead of forcing the requested one.
