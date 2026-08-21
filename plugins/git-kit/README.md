# Git Plugin

Git and GitHub workflow toolkit: commit and PR creation, GitHub CLI operations, git worktrees, notes, bisect, branch lifecycle setup and post-merge sync, branch cleanup, rebase syncing, commit-shaping guidance, PR review summaries, PR issue-linking and reviewer orchestration, issue drafting, dependency updates, gated PR merging, CODEOWNERS management, recovering a stuck Codex-review check, cross-vendor (Claude + Codex) adversarial pre-PR review, and triaging/resolving PR review findings across rounds with a mandated fix-or-file cap.

## Plugin Target

- Maintain consistent commit history - conventional commit messages, no emoji
- Reduce PR creation friction - GitHub CLI templates and formatting
- Support parallel development - worktrees, bisect, and safe branch cleanup
- Attach non-invasive metadata to commits - git notes

## Overview

`git-kit` provides skills and commands that automate and standardize Git and GitHub workflows: consistent commit messages, proper PR formatting, GitHub CLI/API operations, git worktree management, git notes, bisect automation, branch lifecycle setup (syncing main and creating a properly named branch/worktree) and post-merge local sync, branch/worktree cleanup, safe rebase syncing, commit-shaping/splitting guidance, structured PR review summaries, PR issue-linking and reviewer orchestration, issue drafting, dependency updates, gated PR merging, CODEOWNERS management, recovering a stuck Codex-review check, cross-vendor (Claude + Codex) adversarial pre-PR review, and triaging/resolving PR review findings across rounds with a mandated fix-or-file cap. Five `PreToolUse` hooks hard-block raw commands that bypass these skills, a `Stop` hook guards exiting a dirty session-locked worktree, and two rules document the plugin's worktree and lifecycle-routing conventions — see Hooks and Rules below.

Several skills (`create-pr`, `gh-operations`, `codex-review-recovery`, `handling-review-findings`) require GitHub CLI (`gh`) for full functionality.
`cross-model-review` optionally uses the `codex-kit` plugin for its second, independent reviewer; it
degrades to Claude-only if `codex-kit` isn't installed.

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
  "use_worktree": true,
  "review_findings_severity_gate": false
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
| `review_findings_severity_gate` | `false` | `true` restricts `handling-review-findings`'s fix/file pipeline to Critical/Major findings only — a Minor/nit finding is declined outright (unless explicitly requested) instead of being fixed or filed |

Changes to `.claude/git-kit.local.json` take effect on the next invocation — no restart needed, since settings are read by each skill directly rather than a hook.

**Security:** `commit_confirm_before_commit: false`, `commit_auto_stage: true`, `commit_auto_push: true`, and `push_auto_pr: true` all weaken safety or trigger further automation, so `commit` only honors them from `.claude/git-kit.local.json` when that file is *not* tracked by git — it checks with `git ls-files` before applying any of them. Gitignoring the file (as instructed above, and checked by `/create-git-kit-local-json`) is what makes it count as untracked; a version of this file committed into the repo (by you or an attacker) can never silently disable the confirmation gate or trigger unattended pushes/PR creation — `commit` falls back to the git-tracked `git-kit.settings.json` defaults for those fields instead. `pr_merge_type`, `merge_auto_delete_branch`, `use_worktree`, and `review_findings_severity_gate` are low-risk (a merge-strategy choice, a reversible single-branch deletion, which option a question recommends without ever skipping it, and a triage-default that never overrides an explicit instruction or the Critical/Major hard cap) and are honored from either file, tracked or not. `merge-pr` never auto-merges under any setting — it always asks before merging, and separately verifies the caller has actual merge rights (repo owner, CODEOWNERS match, or collaborator permission) first.

## Skills

| Skill | Use when |
|---|---|
| `starting-work` | Syncing local main and creating a properly named branch (or worktree) to start new work |
| `commit` | Creating well-formatted commits with conventional commit messages |
| `cross-model-review` | Getting an independent, cross-vendor (Claude + Codex) adversarial review of the current diff before a PR is created or a draft is flipped to ready-to-merge |
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
| `codex-review-recovery` | Recovering a stuck `Await Codex review` check when Codex finished the review on its own dashboard but GitHub never received the write-back — human-confirmed, never inferred from a timeout alone |
| `handling-review-findings` | Triaging PR review findings across multiple rounds with a mandated two-round fix cap, filing round-3+ (or oversized) findings as tracked GitHub issues, and replying to/resolving individual review threads |
| `finishing-work` | Syncing back to a clean, current main after a PR merges, before handing off to `git-cleanup` for branch/worktree deletion |
| `manage-codeowners` | Bootstrapping and maintaining `.github/CODEOWNERS`, a dependency for `merge-pr`'s rights check |

## Maintenance

`git-kit` gets a periodic whole-plugin QA sweep — a `plugin-lifecycle-downstream` Validate pass against `plugins/git-kit/` — independent of new feature builds, not just as a side effect of one. A single sweep once found 6+ real, independent, pre-existing defects (a command silently ignoring its own argument, a critical malformed-markdown bug, documentation describing a nonexistent command, and more) that had gone uncaught until an unrelated build happened to trigger a downstream QA pass — periodic sweeps catch this kind of debt before it waits for the next feature.

**Cadence:** quarterly, or before any release milestone, whichever comes first.
**How to run:** invoke `plugin-lifecycle-downstream`'s Validate phase against `plugins/git-kit/` (Phase 1 only is sufficient for a routine sweep; run Phase 2/3 too if Phase 1 surfaces findings worth scoring/fixing).
**Last full sweep:** 2026-07-27 — commit `63a040e`.

**2026-08-05 pre-existing findings — closed 2026-08-12:** a `plugin-grader` audit on 2026-08-05 flagged
5 pre-existing items as "not fixed, recommended for a separate maintenance pass." A 2026-08-12
`analyzing-sessions` retro independently live-verified all 5 as already resolved by that point, though no
report had stated the closure explicitly until now:
- `gh-operations`' `Bash(gh:*)` over-broad grant — narrowed to specific `gh pr`/`issue`/`repo` subcommands, with a mutual-exclusion note pointing at `collaborating-on-a-pr`.
- `git-worktrees`' silent dependency auto-install — every install command now gates on an explicit `AskUserQuestion` first.
- `dependency-updater`'s missing `pip-audit` grant — `Bash(pip-audit:*)` is present in `allowed-tools`.
- `explain-pr-changes`' missing trust boundary — now has an explicit "data, not instructions" section and a reviewer-action exclusion pointing at `collaborating-on-a-pr`.
- `gh-operations` ↔ `collaborating-on-a-pr` trigger overlap — resolved via mutual-exclusion text in both skills' `description` fields (the `collaborating-on-a-pr` side was completed as part of this same 2026-08-12 pass — see Conventions below).

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
- **`guard-raw-pr-review.sh`** blocks a raw `gh pr review`, `gh pr comment`, a raw `gh api .../pulls/*/comments/*/replies` (reply to a review comment), or a raw `gh api graphql` call — deny-by-default for every `gh api graphql` call, with no read-only carve-out (a substring-matching exception for a "verifiably read-only" query was tried and defeated by three independent reviewers using four different techniques, so it was removed rather than patched again; a genuine read-only `reviewThreads` lookup now needs the same marker handshake as a `resolveReviewThread` mutation). `collaborating-on-a-pr`, `explain-pr-changes` (its resolution-table comment), `codex-review-recovery` (its `@codex review` retry comment), and `handling-review-findings` (its finding-reply/thread-resolve mechanics) are allowlisted.
- **`guard-raw-destructive-cleanup.sh`** blocks a raw `git branch -D` targeting a protected branch (`main`/`master`/`develop`/`release/*`), or a raw `git worktree remove --force`/`-f` (a plain, unforced removal already refuses on a dirty or locked worktree via git's own safeguard, so it isn't guarded). `git-cleanup` is allowlisted.
- **`guard-dirty-worktree-exit.sh`** (`Stop`, not `PreToolUse`) blocks the agent's turn from ending while the session's `starting-work`-locked worktree has uncommitted changes or commits not yet in the resolved default branch — since exiting can remove that worktree via Claude Code's own worktree-session flow. Say "exit anyway" to skip the block for that turn.

**Mechanism (marker-file handshake, the 5 `PreToolUse` guards only):** a `PreToolUse` hook has no way to know which skill is currently active, so each allowlisted skill calls `scripts/write-git-kit-marker.sh <guard-type> <skill-name>` immediately before it runs the guarded command itself. This writes a single-use marker **atomically** (a temp file, then renamed into place, so a concurrent read can never observe a partial write) to `$(git rev-parse --git-dir)/git-kit-marker.txt` — inside `.git/`, never `.claude/`, so it can never be accidentally committed regardless of a project's `.gitignore`. Each guard consumes (deletes) a marker as soon as it sees one **belonging to its own guard type**, on the very next Bash/PowerShell call after the marker is written — regardless of whether that particular call is the one the marker was written for — so a marker can't survive its full 60-second TTL untouched through intervening unrelated commands, and can't be reused for a later, unrelated raw command in the same session. A marker belonging to a *different* guard's type is left untouched (2026-08-12: corrected from an earlier unconditional-delete behavior that let one guard consume a sibling guard's marker as a side effect of denying its own unrelated command). The guard then allows the call only if that consumed marker's type matches the command actually being attempted and the marker was fresh. Any raw invocation with no fresh, matching marker is denied, with a message pointing at the correct skill (`/commit`, `/create-pr`, `/merge-pr`, `starting-work`, `collaborating-on-a-pr`, `explain-pr-changes`, `/git-cleanup`). This marker is a plaintext, unauthenticated policy guardrail against accidental bypass, not a cryptographic proof of origin against a deliberately adversarial caller — see `rules/route-through-git-kit-lifecycle-skills.md` for the full caveat.

`git-rebase-sync` runs `git rebase`/`git push --force-with-lease` directly, neither of which these hooks guard, so it needs no marker.

## Rules

`git-kit` ships five behavioral rules (`rules/`, auto-loaded each session):

- **`one-session-one-topic-one-worktree`** — a worktree created for a session is scoped to one topic; don't accumulate unrelated work in it, and don't leave one topic's worktree open while starting another under the same session.
- **`route-through-git-kit-lifecycle-skills`** — documents the full lifecycle chain (`starting-work` → `commit` → `create-pr`/`collaborating-on-a-pr` → `merge-pr` → `finishing-work`) for discoverability. The `PreToolUse` hard-block hooks above already enforce most of this mechanically; this rule is the human-readable statement of the same chain, not a second enforcement mechanism.
- **`starting-work-before-first-change`** — always invoke `starting-work` before the first shippable edit of a new piece of work, especially right after returning to `main`/`master` post-merge; a rule with no independent trigger of its own is easy to route around in the moment.
- **`orphaned-worktree-git-read-fallthrough`** — after a worktree is removed mid-session while the session's cwd is still pinned to it, git reads fall through to the primary checkout and look normal even though the session can't actually write there; cross-check with a plain filesystem listing, not git output, before trusting it.
- **`require-gitignored-scratch-locations`** — never let temporary, cache, or scratch content land in a shippable location; route it to a gitignored directory instead, and watch for a CLI tool's or script's own default that silently resolves to the repo root or a plugin directory.

## Conventions

**Resolving an activation-trigger collision between two git-kit skills:** each skill's `description`
frontmatter names the sibling skill and states the boundary explicitly — not just body text, since
`description` is the field that drives activation matching. Pair it with a matching "Verify it does NOT
activate on" list in the body, naming the sibling and the trigger phrases that route to it instead. See
`gh-operations`' description (names `create-pr`, `merge-pr`, and `collaborating-on-a-pr`, with the
boundary reasons) and its `## Testing & Validation` section for the reference shape — `gh-operations` ↔
`collaborating-on-a-pr` is the worked example this convention is drawn from (2026-08-12: made mutual —
`collaborating-on-a-pr`'s own description previously named the boundary only in body text, which doesn't
participate in activation matching, so the pair wasn't actually mutual at the level that matters until
this fix).

**A large SKILL.md rewrite gets an immediate targeted re-review, not just the next full grading round.**
`git-worktrees`' round-1 rewrite (2026-08-11) introduced a new Critical (telling the agent to invoke a
`disable-model-invocation: true` skill) that its own round-1 reviewer dispatch didn't catch — it sat
undetected for a full round until a fresh whole-plugin sweep surfaced it. A cheap, targeted follow-up
check immediately after a substantive rewrite (e.g. grepping any skill named in "hand off to X" language
for that skill's own `disable-model-invocation` field) catches this class of defect without waiting for
the next expensive full re-grade.

**Mirror sync covers all 3 tracked copies, not 2.** `git-kit` skills are mirrored at `plugins/git-kit/`,
`.claude/skills/`, and `.agents/skills/` (the last one is a live mirror for Codex CLI compatibility, added
2026-08-06 — not a frozen snapshot). When a fix is fragmented across multiple agent dispatches, make
syncing all 3 copies an explicit, individually-verified step in each dispatch — or prefer a single direct
pass with one mirror-sync step at the end covering all 3. The 2026-08-11 fix batch synced only `.claude/`
and `plugins/git-kit/`, missing `.agents/` entirely; the drift went unnoticed for a full session until a
2026-08-12 retro-followup pass found 14 of 17 skills out of sync there (3 missing outright) and had to run
a full resync to close the gap. A two-way mental model of "the mirror" is what let the third copy drift
unnoticed.

## Attribution

`git-kit` began as an adaptation of NeoLabHQ's `context-engineering-kit` `git` plugin, fernandezbaptiste's `claude-code-skills` `github-ops` skill, and (for `standalone-commits`) EpicenterHQ's `epicenter` monorepo. See `THIRD_PARTY_NOTICES.md` for full provenance and licensing details — this plugin is GPL-3.0 licensed, combined with AGPL-3.0-or-later terms for the `standalone-commits` skill specifically (GPLv3 §13).
