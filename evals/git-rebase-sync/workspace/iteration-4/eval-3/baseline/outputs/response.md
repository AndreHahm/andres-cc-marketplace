# Eval 3 baseline: sync PR #640 onto main (simulated)

## Trace (simulated outputs only)
1. `"${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" view 640` -> base main, head patch-1, headRefOid cccc333, isCrossRepository true (fork PR).
2. `git branch --show-current` -> patch-1
3. `git remote get-url origin` -> https://github.com/AndreHahm/andres-cc-marketplace.git (the BASE repo, not the fork)
4. `git rev-parse HEAD` -> cccc333 (equals the PR head, so the local branch is in sync with the PR)
5. `git status` -> clean

## Findings
- Local tree is clean and HEAD matches PR head: a local rebase is safe and reversible.
- The PR is cross-repository. `origin` is the base repo, so `git push --force-with-lease origin patch-1` would push to the wrong place (it would create or overwrite a `patch-1` branch in the base repo, not update the PR).
- Not supplied by the prompt: the fork's owner/URL, whether a remote for the fork is configured, whether "allow edits from maintainers" is enabled, and whether the user has push rights to the fork. I won't invent these.

## Decision
Proceed with the local part only; do not push yet.

Commands I would run (the prompt supplies no output for these, so none is invented):
1. `git fetch origin main`
2. `git rebase origin/main`
   - on conflicts: show the conflicted files and resolve with the user (not simulated here).

Stop before pushing and ask.

## AskUserQuestion (before any push)
Question: "PR #640 comes from a fork, and `origin` points at the base repo, so I can't push the rebased patch-1 there. How should I push the rebased branch to the PR?"
Header: "Push target"
Options:
- "Push to the fork's remote": "You give me the fork URL (or an existing remote name); I add or use it and run a force-with-lease push to the fork's patch-1. Requires push access, or maintainer edits enabled on the PR."
- "Keep it local": "Leave the rebased branch unpushed; you push it yourself."
- "Cancel": "Abort the rebase and leave patch-1 at cccc333."

## Message to user
PR #640 is a fork PR (head patch-1 at cccc333, matching your clean local checkout). I'll fetch and rebase onto origin/main locally now. I will not push to `origin`, since that is the base repo and the PR's branch lives on the fork. Please tell me where to push (see the question), and I'll use --force-with-lease only against that target.
