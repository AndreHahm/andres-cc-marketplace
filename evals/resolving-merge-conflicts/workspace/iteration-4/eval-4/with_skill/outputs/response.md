# Eval 4 - resolving-merge-conflicts (with_skill)

## Trace
1. Read SKILL.md. Request = PR #579 conflicts on GitHub, clean local tree -> Step 1a (remote-only). Steps 2-7 do not apply.
2. Validated PR number "579" matches ^[0-9]+$ -> ok.
3. Read references/remote-only-conflicts.md (the skill sends there for exit-status handling/procedure).

## Commands (in order, with simulated output)
1. "${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" view 579 -> CONFLICTING / DIRTY, base main, head fix/example-branch @ dddd444, isCrossRepository false, url .../AndreHahm/andres-cc-marketplace/pull/579
   - baseRefName "main" matches ^[A-Za-z0-9_][A-Za-z0-9._/-]*$ -> ok to use/pass on.
2. git status -> clean (no commit/stash request needed)
3. git fetch origin -> succeeds
4. git rev-parse HEAD -> dddd444 == headRefOid -> ok
5. git branch --show-current -> scratch-alias != headRefName fix/example-branch -> MISMATCH
6. git remote get-url origin -> AndreHahm/andres-cc-marketplace == PR url repo; isCrossRepository false -> fork check passes

NOT run: `git-pr-conflict-preview.sh merge-tree main` and `gh repo view --json ...` (the skill's decision gate stops before them; the prompt also supplies no output for either, so none is invented).

## Decision
Do NOT preview (merge-tree) and do NOT route to git-rebase-sync yet. Stop and confirm the local branch is the intended one: the local branch is an alias (scratch-alias) at the PR's exact commit. git-rebase-sync pushes `origin HEAD:<branch>`, so it would push to "scratch-alias", creating/rewriting a different remote branch and leaving PR #579 unchanged.

## AskUserQuestion (would be called)
Question: "PR #579's head branch is `fix/example-branch`, but your local branch is `scratch-alias` (same commit dddd444). Rebasing and pushing from here would push to `scratch-alias` on origin and leave PR #579 unchanged. How do you want to proceed?"
Header: "Local branch"
Options:
- "Switch to fix/example-branch" - You check out `fix/example-branch` yourself (the skill does not), then I re-run the preview and route to git-rebase-sync.
- "scratch-alias is intended" - Confirm this alias is deliberate; I will not route on without further confirmation since the push target would differ from the PR branch.
- "Cancel" - Stop here; nothing has been changed.

## Message to user
Conflicts on PR #579 exist only on GitHub (mergeable: CONFLICTING, DIRTY); your working tree is clean and HEAD matches the PR head (dddd444), and origin is the PR's own repository. However your current branch is `scratch-alias`, not the PR's head branch `fix/example-branch`. I've stopped before previewing the conflicted files or handing off to git-rebase-sync, because the rebase would push to the wrong remote branch name. Nothing was changed. Please confirm or switch branches.

## Result
Stopped at the Step 1a branch-name check; no merge-tree preview, no routing, no files changed.
