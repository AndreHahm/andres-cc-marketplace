# Ledger promotion for PR #613 (simulated, nothing executed)

## When
Step 8 ended with no trigger posted (the round budget is spent). That is the promotion point, per Workflow step 7 and `references/fix-self-review.md` 4e. I do not promote in step 7 itself, and not earlier while a trigger might still be posted. The final fix commit is still pending and unpushed, so promotion comes before that last push, as the owner decided.

## How
1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" promote --pr 613`.
2. This moves PR #613's 4 entries from the local, gitignored working ledger (`.claude/review-ledger.local.json`) into the git-tracked `.claude/review-outcomes.json`. That file is the corpus Phase 4 builds its evals from.
3. A failed promote is reported to the user, never silently skipped. It does not block the merge.
4. Notes in the entries get copied into a tracked file, so I check that none contains a secret or a quoted credential.

## Where the tracked file ends up
`.claude/review-outcomes.json` is staged together with the round's final fix commit. I commit through `Skill(commit) --push`, after the usual push-destination check. It then lands on the PR branch in the same push as the fix. The ledger records travel with the last push, and no extra commit is needed.

## If there were no pending fix commit
I commit `.claude/review-outcomes.json` alone via `Skill(commit) --push`. I say plainly that it is a records-only commit, not a fix. It still changes the head SHA, so CI runs again. It is not a fix-driven push, so it does not advance the round counter.

## Why not after merging
A merged PR leaves `main` unable to take a direct commit. Promoting after the merge would have nowhere to land the tracked file, so the entries would be lost or would need a new branch and PR. Promotion therefore has to ride on the PR branch, before the last push. This skill also never merges. Merging belongs to `merge-pr`, so promotion cannot wait for a merge this skill does not perform.
