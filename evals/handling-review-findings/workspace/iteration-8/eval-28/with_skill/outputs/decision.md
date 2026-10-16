# PR #613: ledger promotion decision

## When
Step 7 finds no further review round will be triggered (round budget spent). That is the trigger: promote
now, before the last push, not later. The final fix commit is pending and unpushed, so the timing is right.
The fix has already passed verification and the 4a-4d self-review (or the user directed otherwise); each
finding's disposition is recorded in the local ledger first (4e), which holds 4 entries for PR #613.

## How
Run (nothing is executed in this simulation):

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" promote --pr 613

This moves PR #613's 4 entries out of the local, gitignored working ledger
(`.claude/review-ledger.local.json`) into the git-tracked `.claude/review-outcomes.json`. A corrupt ledger is
refused with exit 2 and never overwritten; I would report that rather than continue without a record.

## Where the tracked file ends up
`.claude/review-outcomes.json` is staged together with the round's final fix commit. It is committed through
`Skill(commit) --push` (never a raw git commit), after the push-destination check. So it lands in the PR's
last push, in the same commit as the final fix, and merges with the PR. It is the corpus Phase 4 builds its
evals from.

## If there were no pending fix commit
Commit `.claude/review-outcomes.json` alone via `Skill(commit) --push` and say plainly that it is a
records-only commit, not a fix. It still changes the head SHA, so CI runs again. It is not a fix-driven push,
so it does not advance the round counter.

## Why not promote after merging
A merged PR leaves `main` unable to take a direct commit, so a post-merge promotion would have nowhere to be
committed. The tracked file must ride in the PR's last push instead.

## Failure handling
A failed promote is reported to the user, never silently skipped, and does not block the merge. Merge
readiness stays with `merge-pr`.
