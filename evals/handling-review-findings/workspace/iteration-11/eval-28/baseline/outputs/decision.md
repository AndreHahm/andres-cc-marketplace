# PR #613: ledger promotion decision

## Caveat
This is a baseline answer. I did not read the repo's skill or ledger docs, so the file names and paths below are assumptions to check against the real convention.

## When I promote
- Step 7 found that no further review round will be triggered, because the round budget is spent. The review loop is over, so the 4 ledger entries are final.
- I promote the ledger after that point and before the last push. The owner decided promotion happens before the last push.
- The pending fix commit has not been pushed yet. So the promotion lands in the same push as the final fix.

## How I promote
1. Re-read the local ledger and confirm it holds exactly the 4 entries for PR #613 and that none are half-finished. Fix any entry that is incomplete before copying.
2. Copy or convert those 4 entries from the local, untracked ledger into the tracked, in-repo ledger file. Append only. Do not overwrite or reorder entries from other PRs. Do not move entries that belong to other PRs.
3. Commit the tracked ledger as its own small commit (for example `docs(review-ledger): promote PR 613 entries`). It goes next to the pending fix commit. I do not fold it into the fix commit, so the fix and the record stay separate.
4. Push once, with the fix commit and the promotion commit together. The tracked ledger then reaches the PR branch and is merged with the PR. I do not ask for the push separately.

## Where the tracked file ends up
- The tracked ledger is the repository's tracked review-ledger file (for example under a `docs/` or `evals/` review-ledger path). Its exact path is an assumption.
- It is on the PR branch, in the PR's own diff. After the merge it is in `main` with everything else in the PR.
- The local ledger stays as the working copy. The tracked file is the durable record.

## If there were no pending fix commit
- Nothing is waiting to be pushed, so there is no "last push" to attach the promotion to.
- I would still promote. I make the promotion commit by itself and push it, as the final push on the branch.
- This must still happen before merging. The promotion is a commit that has to go through the PR, so it needs one more push.

## Why I do not promote after merging
- After the merge the PR branch is done. A ledger commit would have no PR to ride on.
- Landing it would need a new branch and PR, or a direct commit to `main`. That is extra overhead and may break branch protection.
- The tracked record would then be missing from the PR that produced it, and the merge could finish without it. If someone forgot, the ledger would never be promoted.
- Promoting before the last push means the PR is complete when it merges.
