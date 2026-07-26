# Git Plugin

Git and GitHub workflow toolkit: commit and PR creation, GitHub CLI operations, git worktrees, notes, bisect, branch cleanup, rebase syncing, commit-shaping guidance, PR review summaries, and issue drafting.

## Plugin Target

- Maintain consistent commit history - conventional commit messages, no emoji
- Reduce PR creation friction - GitHub CLI templates and formatting
- Support parallel development - worktrees, bisect, and safe branch cleanup
- Attach non-invasive metadata to commits - git notes

## Overview

`gitkit` provides skills and commands that automate and standardize Git and GitHub workflows: consistent commit messages, proper PR formatting, GitHub CLI/API operations, git worktree management, git notes, bisect automation, branch/worktree cleanup, safe rebase syncing, commit-shaping/splitting guidance, structured PR review summaries, and issue drafting.

Several skills (`create-pr`, `gh-operations`) require GitHub CLI (`gh`) for full functionality.

## Installation

```bash
/plugin install gitkit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/gitkit
```

## Quick Start

```bash
# Create a well-formatted commit
> /commit

# Amend the last commit
> /commit --amend

# Commit and push in one step
> /commit --push

# Create a pull request
> /create-pr
```

`commit` also checks staged files for sensitive patterns (`.env`, keys, credentials) before committing, confirms the generated message with you first (configurable), and reports a result summary (hash, files changed, push status) afterward — see Configuration below to adjust the confirmation and staging behavior per project.

## Configuration

The `commit` skill reads optional per-project settings from `.claude/gitkit.local.md` in the project root (YAML frontmatter, no required body). This file is user-local — add `.claude/*.local.md` to your project's `.gitignore` so it never gets committed. If the file is absent, or a field is omitted, the defaults below apply.

```markdown
---
enabled: true
commit_confirm_before_commit: true
commit_auto_stage: false
commit_first_line_soft_limit: 50
commit_first_line_hard_limit: 72
---
```

| Field | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Master toggle for this file's overrides |
| `commit_confirm_before_commit` | `true` | Ask for confirmation (showing the generated message) before running `git commit` |
| `commit_auto_stage` | `false` | When nothing is staged, auto-stage everything (`true`) instead of asking what to stage (`false`) |
| `commit_first_line_soft_limit` | `50` | Recommended max length for a commit's first line |
| `commit_first_line_hard_limit` | `72` | Hard max length for a commit's first line |

Changes to this file take effect on the next `/commit` invocation — no restart needed, since it's read by the skill itself rather than a hook.

**Security:** `commit_confirm_before_commit: false` and `commit_auto_stage: true` both weaken safety, so `commit` only honors them when this file is *not* tracked by git — it checks with `git ls-files` before applying either. Gitignoring the file (as instructed above) is what makes it count as untracked; a version of this file committed into the repo (by you or an attacker) can never silently disable the confirmation gate or turn on auto-staging.

## Skills

| Skill | Use when |
|---|---|
| `commit` | Creating well-formatted commits with conventional commit messages |
| `create-pr` | Creating pull requests using GitHub CLI with proper templates and formatting |
| `gh-operations` | Working with pull requests, issues, repositories, workflows, or the GitHub API via `gh` |
| `git-worktrees` | Working on multiple branches simultaneously without stashing |
| `git-notes` | Attaching metadata to commits without changing history |
| `git-bisect` | Guiding an automated or manual git bisect session to find a regression commit |
| `git-cleanup` | Safely analyzing and cleaning up local git branches and worktrees |
| `git-rebase-sync` | Syncing a feature branch onto the latest base branch via rebase, with backup tags and safe force-with-lease pushing |
| `standalone-commits` | Deciding whether a commit is reviewable on its own, and ordering multi-file changes into dependency-ordered waves |
| `explain-pr-changes` | Summarizing a PR's diff into a reviewer-focused changeset breakdown with a NEEDS_REVIEW/APPROVED triage |
| `github-issue-creator` | Turning raw notes, error logs, or screenshots into a structured GitHub issue markdown file |

## Commands

- `/git-status` - Show detailed git repository status
- `/sync-branch` - Sync the current feature branch with the latest main branch
- `/update-branch-name` - Update the current branch name to follow naming conventions

## Attribution

`gitkit` began as an adaptation of NeoLabHQ's `context-engineering-kit` `git` plugin, fernandezbaptiste's `claude-code-skills` `github-ops` skill, and (for `standalone-commits`) EpicenterHQ's `epicenter` monorepo. See `THIRD_PARTY_NOTICES.md` for full provenance and licensing details — this plugin is GPL-3.0 licensed, combined with AGPL-3.0-or-later terms for the `standalone-commits` skill specifically (GPLv3 §13).
