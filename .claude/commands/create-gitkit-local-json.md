---
description: >-
  Create or update .claude/gitkit.local.json, seeded from gitkit's git-tracked default settings, so commit behavior can be overridden per project.
allowed-tools: Read, Write, Bash(git check-ignore:*)
---

# Create gitkit Local Settings File

Create `.claude/gitkit.local.json` in the project root, seeded from the `commit` skill's git-tracked defaults, so the user can edit it locally to override commit behavior (see `commit`'s Settings section for what each field does).

## Instructions

1. Check whether `.claude/gitkit.local.json` already exists. If it does, show its current contents and use `AskUserQuestion` to confirm before overwriting — don't silently clobber an existing local override.
2. Read the git-tracked defaults from `${CLAUDE_PLUGIN_ROOT}/skills/commit/assets/settings.json`.
3. Write that content to `.claude/gitkit.local.json`, creating the `.claude/` directory if it doesn't exist.
4. **Gitignore check**: run `git check-ignore -q .claude/gitkit.local.json`. If it exits non-zero (the file is NOT ignored), warn clearly: this file is currently trackable by git, which means the `commit` skill's trust-boundary check will refuse to honor `commit_confirm_before_commit: false` or `commit_auto_stage: true` from it until it's actually gitignored (see `commit`'s Settings "Security note"). Recommend adding `.claude/*.local.json` (or the broader `.claude/*.local.*`) to the project's `.gitignore`.
5. Report the created/updated file path, and remind the user they can now edit `.claude/gitkit.local.json` directly to change any of the settings documented in `commit`'s SKILL.md.
