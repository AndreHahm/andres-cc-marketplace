---
description: Sync feature branch with the latest main branch.
argument-hint: [target]
allowed-tools: Bash(git fetch:*), Bash(git rebase:*), Bash(git push:*), Bash(git branch:*)
disable-model-invocation: true
---

1. Fetch latest upstream refs: `git fetch origin --prune`.
2. Identify target branch: $ARGUMENTS if given, otherwise `main`.
3. Rebase current branch onto the target identified in step 2 (substitute the actual branch name — do not use shell parameter expansion like `${target:-main}`, since `$ARGUMENTS` is a literal text substitution, not a shell environment variable):
   ```bash
   git rebase origin/<target-branch>
   ```
4. Resolve any conflicts
5. Force-with-lease push to update the PR:
   ```bash
   git push --force-with-lease origin $(git branch --show-current)
   ```
