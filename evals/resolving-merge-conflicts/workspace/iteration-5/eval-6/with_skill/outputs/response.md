# Eval 6 trace: remote-only PR conflict with an over-long PR number

## Input

"PR 1234567890 conflicts with main on GitHub and my local tree is clean. Resolve the merge conflicts using resolving-merge-conflicts."

Simulated environment: `git status` reports a clean tree. The preview script rejects a PR number of more than 9 digits with exit status 2.

## Step-by-step trace

1. Skill selection. The request names a PR that conflicts with main on GitHub while the local tree is clean. That is the Step 1a case ("resolve the conflicts on PR #N", clean local tree). Steps 2-7 do not apply.

2. Step 1a gate, applied before any command runs. SKILL.md says: "The PR number must match `^[0-9]{1,9}$` (the script's own limit) before any command below runs." The number given is `1234567890`, which is 10 digits. It fails the pattern, so no command in Step 1a runs.

3. Commands I would run: none. The gate fails on the PR number before the first command (`"${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" view <number>`). The following are therefore not run either: `git fetch origin`, `git rev-parse HEAD`, `git branch --show-current`, `git remote get-url origin`, `git-pr-conflict-preview.sh merge-tree <baseRefName>`, and `gh repo view`. The simulated `git status` (clean) is the only environment check made, and it is not needed to reach the decision.

4. Routing. I do not invoke `Skill(git-rebase-sync)`. Step 1a routes only after a successful preview, and no preview happens here. I also do not run `git merge` (trial or plain) to surface the conflict, as Step 1a forbids.

5. Questions for the user. The skill defines no `AskUserQuestion` for this stop. The only thing the user can supply is a corrected PR number, which is open-ended, so I would ask it as a plain message rather than an `AskUserQuestion` call. Message text: "PR number 1234567890 has 10 digits. The conflict preview accepts at most 9 digits (`^[0-9]{1,9}$`). Please check the PR number and send it again."

6. Final result: stopped. No preview was run, no base ref was read, no conflicts were listed, and nothing was routed to `git-rebase-sync`. The local repository was not changed.

## Messages to the user

"I stopped before running anything. PR number 1234567890 has 10 digits, and the conflict preview only accepts up to 9 (`^[0-9]{1,9}$`). I have not checked that PR's conflicts, have not routed to `git-rebase-sync`, and have not changed the branch. Send the correct PR number and I will run the read-only preview for it."

## Transcript of commands

None run. The Step 1a commands that would run after a valid PR number were, in order:

```
"${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" view <number>
git fetch origin
git rev-parse HEAD
git branch --show-current
git remote get-url origin
"${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" merge-tree <baseRefName>
gh repo view --json mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed   # only if the merge method is unclear
```

## AskUserQuestion calls

None. The stop is a validation failure with a single user-supplied fix (a corrected number), so it is reported as a plain message.
