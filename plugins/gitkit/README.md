# Git Plugin

Git and GitHub workflow toolkit: commit and PR creation, GitHub CLI operations, git worktrees, notes, bisect, and branch cleanup.

## Plugin Target

- Maintain consistent commit history - conventional commit messages, no emoji
- Reduce PR creation friction - GitHub CLI templates and formatting
- Support parallel development - worktrees, bisect, and safe branch cleanup
- Attach non-invasive metadata to commits - git notes

## Overview

`gitkit` provides skills and commands that automate and standardize Git and GitHub workflows: consistent commit messages, proper PR formatting, GitHub CLI/API operations, git worktree management, git notes, bisect automation, and branch/worktree cleanup.

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

# Create a pull request
> /create-pr
```

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

## Commands

- `/git-status` - Show detailed git repository status
- `/sync-branch` - Sync the current feature branch with the latest main branch
- `/update-branch-name` - Update the current branch name to follow naming conventions

## Attribution

`gitkit` began as an adaptation of NeoLabHQ's `context-engineering-kit` `git` plugin and fernandezbaptiste's `claude-code-skills` `github-ops` skill. See `THIRD_PARTY_NOTICES.md` for full provenance and licensing details — this plugin is GPL-3.0 licensed as a result.
