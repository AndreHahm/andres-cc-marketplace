---
name: "source-command-create-git-kit-local-json"
description: "Create or update .Codex/git-kit.local.json, seeded from git-kit's git-tracked default settings, so commit, push, and merge behavior can be overridden per project."
---

# source-command-create-git-kit-local-json

Use this skill when the user asks to run the migrated source command `create-git-kit-local-json`.

## Command Template

# Create git-kit Local Settings File

Create `.Codex/git-kit.local.json` in the project root, seeded from git-kit's git-tracked defaults, so the user can edit it locally to override git-kit's commit/push/merge behavior (see `commit`'s and `merge-pr`'s Settings sections for what each field does).

## Instructions

1. Check whether `.Codex/git-kit.local.json` already exists. If it does, show its current contents and use `AskUserQuestion` to confirm before overwriting — don't silently clobber an existing local override.
2. Read the git-tracked defaults from `${CLAUDE_PLUGIN_ROOT}/git-kit.settings.json`.
3. Write that content to `.Codex/git-kit.local.json`, creating the `.Codex/` directory if it doesn't exist.
4. **Gitignore check**: run `git check-ignore -q .Codex/git-kit.local.json`. If it exits non-zero (the file is NOT ignored), warn clearly: this file is currently trackable by git, which means the `commit` skill's trust-boundary check will refuse to honor `commit_confirm_before_commit: false`, `commit_auto_stage: true`, `commit_auto_push: true`, or `push_auto_pr: true` from it until it's actually gitignored (see `commit`'s Settings "Security note"). Recommend adding `.Codex/*.local.json` (or the broader `.Codex/*.local.*`) to the project's `.gitignore`.
5. Report the created/updated file path, and remind the user they can now edit `.Codex/git-kit.local.json` directly to change any of the settings documented in `commit`'s SKILL.md.
