# Transcript: eval 3, git-rebase-sync (with_skill)

User message: "PR #640 conflicts with main on GitHub and my local tree is clean. Sync it onto main using git-rebase-sync, go ahead."

Skill read in full. This is a PR-triggered call (the user names PR #640), so Step 1's PR preflight applies.

## Commands (in order, simulated output)

1. `gh pr view 640 --json baseRefName,headRefName,headRefOid,isCrossRepository,url`
   (PR number 640 matches `^[0-9]+$`)
   -> {"baseRefName":"main","headRefName":"patch-1","headRefOid":"cccc333","isCrossRepository":true,"url":"https://github.com/AndreHahm/andres-cc-marketplace/pull/640"}
2. `git branch --show-current` -> patch-1
3. `git remote get-url origin` -> https://github.com/AndreHahm/andres-cc-marketplace.git
4. `git rev-parse HEAD` -> cccc333
5. `git status` -> nothing to commit, working tree clean

## Preflight evaluation

- isCrossRepository: **true** -> the skill says to stop and report, without rebasing.
- origin matches owner/repo in url: yes (AndreHahm/andres-cc-marketplace)
- current branch == headRefName: yes (patch-1)
- HEAD == headRefOid: yes (cccc333)

Only the fork check fails, but it is a stop condition on its own. I do NOT run `git fetch origin`,
create a backup tag, call AskUserQuestion for a rebase command, rebase, or push. No AskUserQuestion
calls were made (stopping and reporting is what the skill prescribes here, not asking to proceed).

## Message to the user

I did not rebase PR #640. The PR preflight stopped me: `gh pr view` reports `isCrossRepository: true`,
so the PR comes from a fork. This skill only syncs same-repository PR branches. Rebasing and then
force-pushing `patch-1` to `origin` would not update the fork's branch that the PR actually tracks,
and the local `patch-1` may not be the fork's branch at all.

The other checks passed: `origin` is AndreHahm/andres-cc-marketplace, the local branch is `patch-1`
(the PR's `headRefName`), and HEAD `cccc333` equals `headRefOid`. The tree is clean. I have changed
nothing: no fetch, no backup tag, no rebase, no push.

Options: the fork owner (or you, if you have push access to their branch) rebases the PR onto main in
the fork, or you tell me explicitly how you want to proceed and I will reconsider.

## Decision: STOP (do not proceed)
