---
name: codex-audit-loop
description: >-
  Whole-project multi-lens Codex audit, optionally with
  independently-verified autonomous fixing. Explicitly opt-in only — do NOT
  invoke for a single small PR, commit, or uncommitted diff (use
  /codex-kit:review instead). Use only when the user explicitly asks for a
  complete multi-lens whole-project review, review-until-convergence,
  multi-branch comparison, or verify-and-fix across isolated worktrees. This
  is expensive (15-26 parallel Codex calls) — confirm the user wants that
  scale before running.
argument-hint: "[--mode audit|compare|fix] [--branches <b1,b2,...>] [--base <ref>]"
allowed-tools: ["Bash(node:*)", "Bash(git:*)", "Read", "Grep", "Glob", "AskUserQuestion", "Agent"]
---

# Whole-project multi-lens audit

Three modes. **Confirm scope and cost with the user via `AskUserQuestion` before launching any mode** — this is not a lightweight command.

## Mode A — Multi-lens checkout audit (default)

1. **Explore**: dispatch 1-3 subagents to survey project structure, invariants, high-risk modules.
2. **Plan lenses**: derive 3-20 independent lenses (distinct failure surfaces/subsystems) from the exploration — score candidates on yield, severity-ceiling, orthogonality, groundability; land where one more lens would just re-read files already covered.
3. **Launch**: fire one Codex review per lens in parallel via `${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs adversarial-review` per lens (never a raw `codex exec` — always through this shared companion script, same as every other codex-kit component), each with a distinct focus prompt.
4. **Synthesize**: deduplicate findings by (file, defect-class); track status new/still-open/fixed-verified/regressed across rounds.
5. **Converge**: repeat up to 10 rounds. Stop when a round returns only trivial findings, or two consecutive rounds add no new substantive findings, or all confirmed substantive findings are fixed/accepted.

## Mode B — Multi-branch comparison (`--branches`)

For each named branch vs. `--base`: confirm via `AskUserQuestion` before switching (this changes the checked-out branch, even though the switch itself is non-destructive), then switch, verify clean, run `${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs review --base <base>`. Synthesize: dedupe shared findings, mark branch-specific vs. shared.

## Mode C — Verified fix loop (`--mode fix`, extends Mode A)

1. Run Mode A's Phases 1-3 (or reuse a completed Mode A run).
2. **Independently verify** every candidate finding via a blind subagent (never told the finding came from Codex) — returns Agreed / Disagreed / Nuanced / False Positive / Uncited, the same 5-way taxonomy every other codex-kit component uses.
3. **Group** confirmed findings into disjoint fix groups by file/subsystem; create one isolated `git worktree` per group. Capture the integration branch's current SHA before the first group starts (`INTEGRATION_SHA`) — this is the rollback anchor for step 5's failure handling below.
4. **Fix**: each group's fixer reconfirms, implements, adds tests, runs the local build/test gate. If the build/test gate fails and the fixer can't resolve it, mark that group failed, remove its worktree (`git worktree remove`), and drop it from this round's merge set — do not block the other groups.
5. **Merge**: confirm `AskUserQuestion` authority before merging each group (this is the mode's one destructive step — one confirmation per group, not a single up-front blanket approval). Per group: confirm CI green on the exact pushed SHA, merge it, rebuild the integration branch. **On failure**: if CI comes back red on a pushed SHA, or a merge conflicts, stop merging further groups in this round, leave that group's branch/worktree in place (do not force-push or force-merge), and report which groups landed vs. which are blocked — resume from `INTEGRATION_SHA` for any group that needs to be redone. Remove worktrees for groups that both fixed and merged cleanly; leave failed/blocked groups' worktrees until the user has reviewed them.
6. **Repeat** with a fresh audit round against the new integration SHA until convergence (same criteria as Mode A).

## Boundaries

Never creates PRs, deploys, or posts comments without explicit authority. Mode A is pure read/analysis — it never mutates the working tree. Mode B switches branches (confirmed via `AskUserQuestion` first) but never commits, pushes, or merges. Only Mode C pushes and merges, and only with an explicit `AskUserQuestion` confirmation immediately before each merge (step 5 above) — never automatically. Never fabricates a finding: every lens is instructed to ground findings in cited `file:line` or fail closed.
