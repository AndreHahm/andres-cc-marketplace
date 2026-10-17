# PR #613: ledger promotion decision

## When
Promotion happens at Workflow step 8, once it ends without posting a trigger. Here the round budget is spent (`max_rounds` reached), so no trigger is posted. That is the condition in `references/fix-self-review.md` 4e. It happens before the last push, not after the merge. Step 7 says the ledger is promoted only once step 8 ends with no trigger posted, never earlier. The owner's decision (promote before the last push) matches the skill.

## How
Run the ledger script for PR 613 after the final fix is verified, and before `Skill(commit) --push`:

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" promote --pr 613`

This moves PR #613's 4 working-ledger entries (local, gitignored `.claude/review-ledger.local.json`) into the git-tracked file. Notes are copied into a tracked file, so none may contain a secret or a quoted credential.

## Where the tracked file ends up
`.claude/review-outcomes.json` is the tracked corpus that Phase 4 builds its evals from. Stage it together with the round's final fix commit, so the pending fix and the promoted records go through `Skill(commit) --push` as one commit and one push. The commit goes through the commit skill, never a hand-run git command.

## If there were no pending fix commit
Commit `.claude/review-outcomes.json` alone via `Skill(commit) --push`, and say plainly that it is a records-only commit, not a fix. It still changes the head SHA, so CI runs again. It is not a fix-driven push, so it does not advance the round counter.

## Why not promote after merging
A merged PR leaves `main` unable to take a direct commit, so a post-merge promotion has nowhere to land. The records must ride on the PR branch before its last push.

## Failure handling
A failed promote is reported to the user, never silently skipped, and does not block the merge. The merge decision still belongs entirely to `merge-pr`.
