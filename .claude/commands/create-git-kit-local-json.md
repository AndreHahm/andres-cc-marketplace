---
description: >-
  Create or update .claude/git-kit.local.json, seeded from git-kit's git-tracked default settings, so commit, push, and merge behavior can be overridden per project.
allowed-tools: Read, Write, Bash(git check-ignore:*)
---

# Create git-kit Local Settings File

Create `.claude/git-kit.local.json` in the project root, seeded from git-kit's git-tracked defaults, so the user can edit it locally to override git-kit's commit/push/merge behavior (see `commit`'s and `merge-pr`'s Settings sections for what each field does).

## Instructions

1. Check whether `.claude/git-kit.local.json` already exists. If it does, show its current contents and use `AskUserQuestion` to confirm before overwriting — don't silently clobber an existing local override.
2. Read the git-tracked defaults from `${CLAUDE_PLUGIN_ROOT}/git-kit.settings.json`.
3. **Gitignore check**: run `git check-ignore -q .claude/git-kit.local.json`. If it exits non-zero (the file is NOT ignored), warn clearly: this file would be trackable by git, which means the trust-boundary checks in both `commit` and `handling-review-findings` will refuse to honor certain fields from it until it's actually gitignored. Nine fields total are affected: `commit`'s `commit_confirm_before_commit: false`, `commit_auto_stage: true`, `commit_auto_push: true`, and `push_auto_pr: true` (see `commit`'s Settings "Security note"); and `handling-review-findings`'s a `review_findings_reviewers` entry's `enabled: false`, `review_findings_max_rounds` set lower than the tracked default, `review_findings_generate_issues: true`, `review_findings_severity_gate: true`, and a reviewer's `default_review_trigger`/`full_review_trigger` (see `references/settings-and-round-budget.md`'s "Read order and trust boundary" section). Recommend adding `.claude/*.local.json` (or the broader `.claude/*.local.*`) to the project's `.gitignore`.
4. Write that content to `.claude/git-kit.local.json`, creating the `.claude/` directory if it doesn't exist.
5. Report the created/updated file path, and remind the user they can now edit `.claude/git-kit.local.json` directly to change any of the settings documented in `commit`'s SKILL.md or `handling-review-findings`'s Settings section.
