---
description: Sync feature branch with main via git-rebase-sync.
argument-hint: [target]
allowed-tools: Skill(git-kit:git-rebase-sync)
disable-model-invocation: true
---

1. Identify target branch: $ARGUMENTS if given, otherwise let `git-rebase-sync` resolve the repository's default branch itself.
2. Invoke `Skill(git-kit:git-rebase-sync)`, passing the target branch identified in step 1 as its `args` (omit `args` when no explicit target was given, so the skill falls back to the GitHub default branch). `git-rebase-sync` performs the actual rebase, conflict resolution, and force-with-lease push — including its own `AskUserQuestion` confirmations and pre-rebase backup ref — this command no longer runs `git rebase`/`git push` directly.
