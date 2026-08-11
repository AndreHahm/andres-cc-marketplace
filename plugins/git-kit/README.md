# Git Plugin

Git and GitHub workflow toolkit: commit and PR creation, GitHub CLI operations, git worktrees, notes, bisect, branch lifecycle setup and post-merge sync, branch cleanup, rebase syncing, commit-shaping guidance, PR review summaries, PR issue-linking and reviewer orchestration, issue drafting, dependency updates, gated PR merging, and CODEOWNERS management.

## Plugin Target

- Maintain consistent commit history - conventional commit messages, no emoji
- Reduce PR creation friction - GitHub CLI templates and formatting
- Support parallel development - worktrees, bisect, and safe branch cleanup
- Attach non-invasive metadata to commits - git notes

## Overview

`git-kit` provides skills and commands that automate and standardize Git and GitHub workflows: consistent commit messages, proper PR formatting, GitHub CLI/API operations, git worktree management, git notes, bisect automation, branch lifecycle setup (syncing main and creating a properly named branch/worktree) and post-merge local sync, branch/worktree cleanup, safe rebase syncing, commit-shaping/splitting guidance, structured PR review summaries, PR issue-linking and reviewer orchestration, issue drafting, dependency updates, gated PR merging, and CODEOWNERS management. Five `PreToolUse` hooks hard-block raw commands that bypass these skills, a `Stop` hook guards exiting a dirty session-locked worktree, and two rules document the plugin's worktree and lifecycle-routing conventions — see Hooks and Rules below.

Several skills (`create-pr`, `gh-operations`) require GitHub CLI (`gh`) for full functionality.

## Installation

```bash
/plugin install git-kit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/git-kit
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

`git-kit` ships git-tracked default settings at `git-kit.settings.json` (plugin root — shared across skills):

```json
{
  "enabled": true,
  "commit_confirm_before_commit": true,
  "commit_auto_stage": false,
  "commit_first_line_soft_limit": 50,
  "commit_first_line_hard_limit": 72,
  "commit_body_max_lines": 5,
  "commit_auto_push": false,
  "push_auto_pr": false,
  "pr_merge_type": "REBASE",
  "merge_auto_delete_branch": true,
  "use_worktree": true
}
```

To override any of these per project, run `/create-git-kit-local-json` — it creates `.claude/git-kit.local.json` in the project root, seeded from those defaults, so you can edit it locally. This file is user-local: add `.claude/*.local.json` (or the broader `.claude/*.local.*`) to your project's `.gitignore` so it never gets committed — the command warns you if it detects the new file isn't actually ignored. If `.claude/git-kit.local.json` doesn't exist, or omits a field, the git-tracked defaults above apply for that field.

| Field | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Master toggle for `.claude/git-kit.local.json`'s overrides |
| `commit_confirm_before_commit` | `true` | Ask for confirmation (showing the generated message) before running `git commit` |
| `commit_auto_stage` | `false` | When nothing is staged, auto-stage everything (`true`) instead of asking what to stage (`false`) |
| `commit_first_line_soft_limit` | `50` | Recommended max length for a commit's first line |
| `commit_first_line_hard_limit` | `72` | Hard max length for a commit's first line |
| `commit_body_max_lines` | `5` | Recommended max lines for the commit body, when one is included |
| `commit_auto_push` | `false` | After a successful commit, push without asking |
| `push_auto_pr` | `false` | After a successful push, create a PR without asking (if none is already open) |
| `pr_merge_type` | `REBASE` | Merge strategy `merge-pr` uses: `MERGE`, `REBASE`, or `SQUASH` |
| `merge_auto_delete_branch` | `true` | After `merge-pr` merges a PR, delete the just-merged branch without asking |
| `use_worktree` | `true` | Which option `starting-work`'s plain-branch-vs-worktree question recommends by default — the question itself always still asks |

Changes to `.claude/git-kit.local.json` take effect on the next invocation — no restart needed, since settings are read by each skill directly rather than a hook.

**Security:** `commit_confirm_before_commit: false`, `commit_auto_stage: true`, `commit_auto_push: true`, and `push_auto_pr: true` all weaken safety or trigger further automation, so `commit` only honors them from `.claude/git-kit.local.json` when that file is *not* tracked by git — it checks with `git ls-files` before applying any of them. Gitignoring the file (as instructed above, and checked by `/create-git-kit-local-json`) is what makes it count as untracked; a version of this file committed into the repo (by you or an attacker) can never silently disable the confirmation gate or trigger unattended pushes/PR creation — `commit` falls back to the git-tracked `git-kit.settings.json` defaults for those fields instead. `pr_merge_type`, `merge_auto_delete_branch`, and `use_worktree` are low-risk (a merge-strategy choice, a reversible single-branch deletion, and which option a question recommends without ever skipping it) and are honored from either file, tracked or not. `merge-pr` never auto-merges under any setting — it always asks before merging, and separately verifies the caller has actual merge rights (repo owner, CODEOWNERS match, or collaborator permission) first.

## Skills

| Skill | Use when |
|---|---|
| `starting-work` | Syncing local main and creating a properly named branch (or worktree) to start new work |
| `commit` | Creating well-formatted commits with conventional commit messages |
| `create-pr` | Creating pull requests using GitHub CLI with proper templates and formatting |
| `collaborating-on-a-pr` | Linking a related issue when creating a PR, or acting as a reviewer — commenting, approving, requesting changes, checking CODEOWNERS context |
| `gh-operations` | Working with pull requests, issues, repositories, workflows, or the GitHub API via `gh` |
| `git-worktrees` | Working on multiple branches simultaneously without stashing |
| `git-notes` | Attaching metadata to commits without changing history |
| `git-bisect` | Guiding an automated or manual git bisect session to find a regression commit |
| `git-cleanup` | Safely analyzing and cleaning up local git branches and worktrees |
| `git-rebase-sync` | Syncing a feature branch onto the latest base branch via rebase, with backup tags and safe force-with-lease pushing |
| `standalone-commits` | Deciding whether a commit is reviewable on its own, ordering multi-file changes into dependency-ordered waves, and prioritizing/filtering which pending change to stage first when several are relevant to a PR |
| `explain-pr-changes` | Summarizing a PR's diff into a reviewer-focused changeset breakdown with a NEEDS_REVIEW/APPROVED triage, and (on an open PR) resolving every existing review comment before considering the summary complete |
| `github-issue-creator` | Turning raw notes, error logs, or screenshots into a structured GitHub issue markdown file |
| `dependency-updater` | Scanning package manifests across ecosystems for outdated dependencies, flagging monorepo version conflicts, and proposing updates with confirmation before applying |
| `merge-pr` | Checking whether a PR is ready to merge (draft/CI/review status), verifying the caller has merge rights, and merging (always with confirmation, never automatically) |
| `finishing-work` | Syncing back to a clean, current main after a PR merges, before handing off to `git-cleanup` for branch/worktree deletion |
| `manage-codeowners` | Bootstrapping and maintaining `.github/CODEOWNERS`, a dependency for `merge-pr`'s rights check |

## Maintenance

`git-kit` gets a periodic whole-plugin QA sweep — a `plugin-lifecycle-downstream` Validate pass against `plugins/git-kit/` — independent of new feature builds, not just as a side effect of one. A single sweep once found 6+ real, independent, pre-existing defects (a command silently ignoring its own argument, a critical malformed-markdown bug, documentation describing a nonexistent command, and more) that had gone uncaught until an unrelated build happened to trigger a downstream QA pass — periodic sweeps catch this kind of debt before it waits for the next feature.

**Cadence:** quarterly, or before any release milestone, whichever comes first.
**How to run:** invoke `plugin-lifecycle-downstream`'s Validate phase against `plugins/git-kit/` (Phase 1 only is sufficient for a routine sweep; run Phase 2/3 too if Phase 1 surfaces findings worth scoring/fixing).
**Last full sweep:** 2026-07-27 — commit `63a040e`.

## Commands

- `/git-status` - Show detailed git repository status
- `/sync-branch` - Sync the current feature branch with the latest main branch
- `/update-branch-name` - Update the current branch name to follow naming conventions
- `/create-git-kit-local-json` - Create or update `.claude/git-kit.local.json`, seeded from the git-tracked default settings

## Hooks

`git-kit` ships five `PreToolUse` hooks and one `Stop` hook (`hooks/hooks.json`):

- **`guard-raw-commit.sh`** blocks a raw `git commit`. `commit` and `standalone-commits` — the two skills that legitimately run `git commit` directly — are allowlisted.
- **`guard-raw-pr-ops.sh`** blocks a raw `gh pr create` or `gh pr merge`. `create-pr`, `merge-pr`, and `explain-pr-changes` (its no-PR-yet publish path) are allowlisted.
- **`guard-raw-branch-create.sh`** blocks a raw `git checkout -b`/`-B`, `git switch -c`/`-C`/`--create`, or `git worktree add -b`/`-B`. `starting-work` and `commit` (its on-`main` branch-check fallback) are allowlisted.
- **`guard-raw-pr-review.sh`** blocks a raw `gh pr review` or `gh pr comment`. `collaborating-on-a-pr` and `explain-pr-changes` (its resolution-table comment) are allowlisted.
- **`guard-raw-destructive-cleanup.sh`** blocks a raw `git branch -D` targeting a protected branch (`main`/`master`/`develop`/`release/*`), or a raw `git worktree remove --force`/`-f` (a plain, unforced removal already refuses on a dirty or locked worktree via git's own safeguard, so it isn't guarded). `git-cleanup` is allowlisted.
- **`guard-dirty-worktree-exit.sh`** (`Stop`, not `PreToolUse`) blocks the agent's turn from ending while the session's `starting-work`-locked worktree has uncommitted changes or commits not yet in the resolved default branch — since exiting can remove that worktree via Claude Code's own worktree-session flow. Say "exit anyway" to skip the block for that turn.

**Mechanism (marker-file handshake, the 5 `PreToolUse` guards only):** a `PreToolUse` hook has no way to know which skill is currently active, so each allowlisted skill calls `scripts/write-git-kit-marker.sh <guard-type> <skill-name>` immediately before it runs the guarded command itself. This writes a single-use marker to `$(git rev-parse --git-dir)/git-kit-marker.txt` — inside `.git/`, never `.claude/`, so it can never be accidentally committed regardless of a project's `.gitignore`. The hook checks the marker is present, matches the guard type being attempted, and is no more than 60 seconds old, then **always deletes it** whether or not it matched — a marker can't be reused for a later, unrelated raw command in the same session. Any raw invocation with no fresh, matching marker is denied, with a message pointing at the correct skill (`/commit`, `/create-pr`, `/merge-pr`, `starting-work`, `collaborating-on-a-pr`, `explain-pr-changes`, `/git-cleanup`). This marker is a plaintext, unauthenticated policy guardrail against accidental bypass, not a cryptographic proof of origin against a deliberately adversarial caller — see `rules/route-through-git-kit-lifecycle-skills.md` for the full caveat.

`git-rebase-sync` runs `git rebase`/`git push --force-with-lease` directly, neither of which these hooks guard, so it needs no marker.

## Rules

`git-kit` ships two behavioral rules (`rules/`, auto-loaded each session):

- **`one-session-one-topic-one-worktree`** — a worktree created for a session is scoped to one topic; don't accumulate unrelated work in it, and don't leave one topic's worktree open while starting another under the same session.
- **`route-through-git-kit-lifecycle-skills`** — documents the full lifecycle chain (`starting-work` → `commit` → `create-pr`/`collaborating-on-a-pr` → `merge-pr` → `finishing-work`) for discoverability. The `PreToolUse` hard-block hooks above already enforce most of this mechanically; this rule is the human-readable statement of the same chain, not a second enforcement mechanism.

## Attribution

`git-kit` began as an adaptation of NeoLabHQ's `context-engineering-kit` `git` plugin, fernandezbaptiste's `claude-code-skills` `github-ops` skill, and (for `standalone-commits`) EpicenterHQ's `epicenter` monorepo. See `THIRD_PARTY_NOTICES.md` for full provenance and licensing details — this plugin is GPL-3.0 licensed, combined with AGPL-3.0-or-later terms for the `standalone-commits` skill specifically (GPLv3 §13).
