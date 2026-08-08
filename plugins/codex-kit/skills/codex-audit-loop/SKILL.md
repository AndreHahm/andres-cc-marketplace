---
name: codex-audit-loop
description: "Whole-project multi-lens Codex audit, optionally with independently-verified autonomous fixing. Explicitly opt-in only — do NOT invoke for a single small PR, commit, or uncommitted diff (use /codex-kit:review instead). Use only when the user explicitly asks for a complete multi-lens whole-project review, review-until-convergence, multi-branch comparison, or verify-and-fix across isolated worktrees. This is expensive (15-26 parallel Codex calls) — confirm the user wants that scale before running."
argument-hint: "[--mode audit|compare|fix] [--branches <b1,b2,...>] [--base <ref>]"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "AskUserQuestion", "Agent"]
---

# Whole-project multi-lens audit

Three modes. **Confirm scope and cost with the user via `AskUserQuestion` before launching any mode** — this is not a lightweight command.

## Mode A — Multi-lens checkout audit (default)

1. **Explore**: dispatch 1-3 subagents to survey project structure, invariants, high-risk modules.
2. **Plan lenses**: derive 3-20 independent lenses (distinct failure surfaces/subsystems) from the exploration — score candidates on yield, severity-ceiling, orthogonality, groundability; land where one more lens would just re-read files already covered.
3. **Launch**: fire one Codex review per lens in parallel (via `codex-companion.mjs adversarial-review` per lens, or direct `codex exec` through component #17's primitive), each with a distinct focus prompt.
4. **Synthesize**: deduplicate findings by (file, defect-class); track status new/still-open/fixed-verified/regressed across rounds.
5. **Converge**: repeat up to 10 rounds. Stop when a round returns only trivial findings, or two consecutive rounds add no new substantive findings, or all confirmed substantive findings are fixed/accepted.

## Mode B — Multi-branch comparison (`--branches`)

For each named branch vs. `--base`: switch, verify clean, run `codex-companion.mjs review --base <base>`. Synthesize: dedupe shared findings, mark branch-specific vs. shared.

## Mode C — Verified fix loop (`--mode fix`, extends Mode A)

1. Run Mode A's Phases 1-3 (or reuse a completed Mode A run).
2. **Independently verify** every candidate finding via a blind subagent (never told the finding came from Codex) — returns Agreed / Disagreed / Nuanced / False Positive / Uncited (Wave 2's 5-way taxonomy, per decision #11 — this mode's original CONFIRMED/REFUTED/PARTIAL is retired in favor of the same vocabulary every other codex-kit component uses).
3. **Group** confirmed findings into disjoint fix groups by file/subsystem; create one isolated `git worktree` per group.
4. **Fix**: each group's fixer reconfirms, implements, adds tests, runs the local build/test gate.
5. **Merge**: confirm CI green on the exact pushed SHA; merge groups one at a time; rebuild the integration branch after each batch.
6. **Repeat** with a fresh audit round against the new integration SHA until convergence (same criteria as Mode A).

## Boundaries

Never creates PRs, pushes, merges, deploys, or posts comments without explicit authority. Only Mode C edits anything — Modes A and B are review-only. Never fabricates a finding: every lens is instructed to ground findings in cited `file:line` or fail closed.
