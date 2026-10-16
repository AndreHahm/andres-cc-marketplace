# Decision: promoting the PR #613 review ledger

## When
Step 7 found that no further review round will be triggered, because the round budget is spent. That makes the review process final. The ledger holds 4 entries for PR #613 and will not grow. A final fix commit is pending and has not been pushed.

I promote the ledger at this point, before the last push, as the owner decided. I do not wait for the merge.

## How
1. Do not push yet.
2. Run the ledger promotion step on the 4 local entries for PR #613. Promotion turns the local, untracked ledger into a tracked file in the repository.
3. Stage the promoted tracked file together with the pending fix commit's changes, or commit it as a small commit just before the push. It must be in the branch history that gets pushed.
4. Push once. The fix and the promoted ledger go up in the same push, so the PR carries both and they are reviewed and merged together.

## Where the tracked file ends up
The tracked ledger file lives in the repository on the PR branch, and it reaches `main` when the PR merges. I have not read the script or skill in this exercise, so I do not name an exact path. The path is whatever the promotion step defines. It should be a per-PR record for #613 that holds the 4 entries.

## If there were no pending fix commit
Promotion would still need a commit, because a tracked file must be committed and pushed to count. I would make a small standalone commit containing only the promoted ledger and push it. This is the only reason that last push would happen. It must still be done before merge.

## Why not promote after merging
- After the merge, the PR branch is done. Promoting then would require a new branch and PR, or a direct commit to `main`, which bypasses review.
- The ledger would reach `main` separately from the PR it documents, or not at all. The PR's history and the ledger could drift apart.
- Local ledger entries could be lost or go stale if the worktree or branch is cleaned up after the merge (finishing-work and git-cleanup remove branches and worktrees).
- The round budget is spent, so the ledger is complete now. Nothing is gained by waiting.
- The owner's decision is to promote before the last push.
