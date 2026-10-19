# Ledger promotion decision, PR #613

## When
Step 7 only reports and explicitly says not to promote there. Promotion happens when step 8 ends without posting a trigger. Here the round budget (`max_rounds`) is spent, so no trigger is posted. That is the promotion moment. The same trigger would apply if the user declined another round or no reviewer survived validation (`references/next-round-trigger.md` 8a). It happens before the final push, and not before step 8 has concluded.

## How
Run the ledger script (a promote call, one invocation, no marker needed):

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" promote --pr 613`

It moves PR #613's 4 local ledger entries out of the local, gitignored working ledger (`.claude/review-ledger.local.json`) into the tracked file.

## Where the tracked file ends up
`.claude/review-outcomes/pr-613.json`: one git-tracked file per PR, so two PRs promoting at once cannot conflict. It is the corpus Phase 4 builds its evals from.

I stage that file together with the round's final fix commit. The pending fix commit is committed via `Skill(commit) --push` (never raw git), with `pr-613.json` in the same commit, so the promoted record lands in the single last push.

## If there were no pending fix commit
Commit the promoted file alone via `Skill(commit) --push`, and say plainly that it is a records-only commit, not a fix. It still changes the head SHA, so CI runs again. It is not a fix-driven push, so it does not advance the round counter.

## Failure handling
A failed promote is reported to the user, never silently skipped. It does not block the merge.

## Why not after merging
A merged PR leaves `main` unable to take a direct commit, so there would be no place to land the tracked file. Promotion must therefore ride along with the last push on the PR branch, before the merge.
