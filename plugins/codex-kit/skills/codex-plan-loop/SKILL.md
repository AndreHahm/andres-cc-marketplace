---
name: codex-plan-loop
description: >-
  Dual-AI plan-validate-implement-review loop with Codex. Use for (1) complex
  feature development requiring validation, (2) high-quality code with
  security/performance concerns, (3) large-scale refactoring, or (4) an
  explicit request for a codex-claude loop or dual-AI review. Do NOT use for
  simple one-off fixes or prototypes, nor for a single implementation/fix
  task that doesn't need an up-front plan-validation phase — use codex-rescue
  for those.
argument-hint: "feature description [--security-focus] [--performance-focus] [--model SLUG] [--effort LEVEL]"
allowed-tools: ["Bash(node:*)", "Read", "Write", "Edit", "Grep", "Glob", "AskUserQuestion"]
---

# Plan → Validate → Implement → Review → Iterate

Proactive quality-gating **before** implementation starts, not reactive review after. Codex validates the plan; Claude implements; Codex reviews the diff against the original plan; iterate until convergence.

All Codex calls in this loop use `${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs` directly (no external plugin resolution) and pass `--model`/`--effort` as per-call flags when given, falling back to `config.toml` otherwise (decisions #1, #4, #7). Content sent to Codex is framed as evidence, not instructions (scope-expansion #8).

## Phase 1: Plan

Write a detailed implementation plan to `.codex-loop/plan.md` — overview, steps, assumptions, risks.

## Phase 2: Validate (Codex)

Send the plan to Codex via `task` (Pattern B, stdin pipe — see `${CLAUDE_PLUGIN_ROOT}/skills/codex-prompt-protocol/references/invocation-protocol.md`):

- **Standard** (`model_reasoning_effort` per Phase 1 flags/config default): logic errors, edge cases, architecture flaws, security, missing requirements, dependency ordering.
- **`--security-focus`** (always `xhigh` effort): auth/authz gaps, input validation, data exposure, injection vectors, OWASP Top 10.

Both: classify issues Critical / Major / Minor / Info, citing the specific plan section. Save to `.codex-loop/phase2_validation.md`.

## Phase 3: Decision gate

`AskUserQuestion`: "Revise the plan and re-validate, or proceed to implementation?" — if revise, loop back to Phase 1 with the feedback incorporated; log the iteration in `.codex-loop/iterations.md`.

## Phase 4: Implement

Claude implements step-by-step per the approved plan. Save to `.codex-loop/implementation.md`.

## Phase 5: Review (Codex)

Send the diff + original plan to Codex via `task`:

- **Standard**: bugs, logic errors, performance issues, security vulnerabilities, plan deviations.
- **`--performance-focus`** (`high` effort): algorithm complexity, N+1 queries, unbounded loops, memory allocation, I/O bottlenecks, caching opportunities.

Classify findings by severity. Save to `.codex-loop/phase5_review.md`.

## Phase 6: Iterate — convergence check

Apply fixes for Critical/Major findings, then send the fix diff back to Codex via `codex-companion.mjs task --resume-last` (session continuity, same companion path as every other phase in this loop — never the raw `codex exec` CLI). **Concrete exit condition** (codex-kit's own addition — the vague "quality standards met" from the original design was flagged as a defect and replaced): stop iterating when either (a) two consecutive rounds report only Minor/Info findings, or (b) all Critical/Major findings from the prior round are confirmed fixed in this round's review. Log every round in `.codex-loop/iterations.md`. Discuss with the user (not silently auto-resolve) if a Critical/Major finding persists past 3 rounds.

Severity-gated response: Critical → fix immediately. Architectural → discuss with the user. Minor/Info → document, don't block.
