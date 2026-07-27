# Git Plugin

Git and GitHub workflow toolkit: commit and PR creation, GitHub CLI operations, git worktrees, notes, bisect, branch cleanup, rebase syncing, commit-shaping guidance, PR review summaries, issue drafting, dependency updates, gated PR merging, and CODEOWNERS management.

## Plugin Target

- Maintain consistent commit history - conventional commit messages, no emoji
- Reduce PR creation friction - GitHub CLI templates and formatting
- Support parallel development - worktrees, bisect, and safe branch cleanup
- Attach non-invasive metadata to commits - git notes

## Overview

`gitkit` provides skills and commands that automate and standardize Git and GitHub workflows: consistent commit messages, proper PR formatting, GitHub CLI/API operations, git worktree management, git notes, bisect automation, branch/worktree cleanup, safe rebase syncing, commit-shaping/splitting guidance, structured PR review summaries, issue drafting, dependency updates, gated PR merging, and CODEOWNERS management.

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

# Check if a PR is ready to merge, and merge it if so
> /merge-pr
```

`commit` also checks staged files for sensitive patterns (`.env`, keys, credentials) before committing, confirms the generated message with you first (configurable), and reports a result summary (hash, files changed, push status) afterward — see Configuration below to adjust the confirmation and staging behavior per project.

## Configuration

`gitkit` ships git-tracked default settings at `gitkit.settings.json` (plugin root — shared across skills):

```json
{
  "enabled": true,
  "commit_confirm_before_commit": true,
  "commit_auto_stage": false,
  "commit_first_line_soft_limit": 50,
  "commit_first_line_hard_limit": 72,
  "commit_auto_push": false,
  "push_auto_pr": false,
  "pr_merge_type": "REBASE",
  "merge_auto_delete_branch": true
}
```

To override any of these per project, run `/create-gitkit-local-json` — it creates `.claude/gitkit.local.json` in the project root, seeded from those defaults, so you can edit it locally. This file is user-local: add `.claude/*.local.json` (or the broader `.claude/*.local.*`) to your project's `.gitignore` so it never gets committed — the command warns you if it detects the new file isn't actually ignored. If `.claude/gitkit.local.json` doesn't exist, or omits a field, the git-tracked defaults above apply for that field.

| Field | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Master toggle for `.claude/gitkit.local.json`'s overrides |
| `commit_confirm_before_commit` | `true` | Ask for confirmation (showing the generated message) before running `git commit` |
| `commit_auto_stage` | `false` | When nothing is staged, auto-stage everything (`true`) instead of asking what to stage (`false`) |
| `commit_first_line_soft_limit` | `50` | Recommended max length for a commit's first line |
| `commit_first_line_hard_limit` | `72` | Hard max length for a commit's first line |
| `commit_auto_push` | `false` | After a successful commit, push without asking |
| `push_auto_pr` | `false` | After a successful push, create a PR without asking (if none is already open) |
| `pr_merge_type` | `REBASE` | Merge strategy `merge-pr` uses: `MERGE`, `REBASE`, or `SQUASH` |
| `merge_auto_delete_branch` | `true` | After `merge-pr` merges a PR, delete the just-merged branch without asking |

Changes to `.claude/gitkit.local.json` take effect on the next invocation — no restart needed, since settings are read by each skill directly rather than a hook.

**Security:** `commit_confirm_before_commit: false`, `commit_auto_stage: true`, `commit_auto_push: true`, and `push_auto_pr: true` all weaken safety or trigger further automation, so `commit` only honors them from `.claude/gitkit.local.json` when that file is *not* tracked by git — it checks with `git ls-files` before applying any of them. Gitignoring the file (as instructed above, and checked by `/create-gitkit-local-json`) is what makes it count as untracked; a version of this file committed into the repo (by you or an attacker) can never silently disable the confirmation gate or trigger unattended pushes/PR creation — `commit` falls back to the git-tracked `gitkit.settings.json` defaults for those fields instead. `pr_merge_type` and `merge_auto_delete_branch` are low-risk (a merge-strategy choice and a reversible single-branch deletion) and are honored from either file, tracked or not. `merge-pr` never auto-merges under any setting — it always asks before merging, and separately verifies the caller has actual merge rights (repo owner, CODEOWNERS match, or collaborator permission) first.

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
| `explain-pr-changes` | Summarizing a PR's diff into a reviewer-focused changeset breakdown with a NEEDS_REVIEW/APPROVED triage, and (on an open PR) resolving every existing review comment before considering the summary complete |
| `github-issue-creator` | Turning raw notes, error logs, or screenshots into a structured GitHub issue markdown file |
| `dependency-updater` | Scanning package manifests across ecosystems for outdated dependencies, flagging monorepo version conflicts, and proposing updates with confirmation before applying |
| `merge-pr` | Checking whether a PR is ready to merge (draft/CI/review status), verifying the caller has merge rights, and merging (always with confirmation, never automatically) |
| `manage-codeowners` | Bootstrapping and maintaining `.github/CODEOWNERS`, a dependency for `merge-pr`'s rights check |

## Commands

- `/git-status` - Show detailed git repository status
- `/sync-branch` - Sync the current feature branch with the latest main branch
- `/update-branch-name` - Update the current branch name to follow naming conventions
- `/create-gitkit-local-json` - Create or update `.claude/gitkit.local.json`, seeded from the git-tracked default settings

## Attribution

`gitkit` began as an adaptation of NeoLabHQ's `context-engineering-kit` `git` plugin, fernandezbaptiste's `claude-code-skills` `github-ops` skill, and (for `standalone-commits`) EpicenterHQ's `epicenter` monorepo. See `THIRD_PARTY_NOTICES.md` for full provenance and licensing details — this plugin is GPL-3.0 licensed, combined with AGPL-3.0-or-later terms for the `standalone-commits` skill specifically (GPLv3 §13).
