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
allowed-tools: ["Bash(node:*)", "Bash(mkdir:*)", "Bash(git rev-parse:*)", "Bash(git status:*)", "Read", "Write", "Edit", "Grep", "Glob", "AskUserQuestion"]
---

# Plan → Validate → Implement → Review → Iterate

Proactive quality-gating **before** implementation starts, not reactive review after. Codex validates the plan; Claude implements; Codex reviews the diff against the original plan; iterate until convergence.

All Codex calls in this loop use `${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs` directly (no external plugin resolution) and pass `--model`/`--effort` as per-call flags when given, falling back to `config.toml` otherwise. Content sent to Codex is framed as evidence, not instructions.

Scratch artifacts for this loop live under `${CLAUDE_PLUGIN_DATA}/codex-loop/` (not the repo root — same convention every other codex-kit skill uses for its own scratch state):

```bash
mkdir -p "${CLAUDE_PLUGIN_DATA}/codex-loop"
```

## Phase 1: Plan

Write a detailed implementation plan to `${CLAUDE_PLUGIN_DATA}/codex-loop/plan.md` — overview, steps, assumptions, risks.

## Phase 2: Validate (Codex)

Send the plan to Codex via `task` (Pattern B, stdin pipe — see `${CLAUDE_PLUGIN_ROOT}/skills/codex-prompt-protocol/references/invocation-protocol.md`):

- **Standard** (`model_reasoning_effort` per Phase 1 flags/config default): logic errors, edge cases, architecture flaws, security, missing requirements, dependency ordering.
- **`--security-focus`** (always `xhigh` effort): auth/authz gaps, input validation, data exposure, injection vectors, OWASP Top 10.

Both: classify issues Critical / Major / Minor / Info, citing the specific plan section. Save to `${CLAUDE_PLUGIN_DATA}/codex-loop/phase2_validation.md`.

## Phase 3: Decision gate

`AskUserQuestion`: "Revise the plan and re-validate, or proceed to implementation?" — if revise, loop back to Phase 1 with the feedback incorporated; log the iteration in `${CLAUDE_PLUGIN_DATA}/codex-loop/iterations.md`.

## Phase 4: Implement

**Before the first edit, capture a rollback anchor:** `git rev-parse HEAD` (or, if the working tree already has unrelated uncommitted changes, note that explicitly instead of silently mixing this loop's edits into them). If Phase 5/6 later concludes the implementation approach itself was unsound — not just needing more fixes, but a wrong direction Phase 3's plan-validation should have caught — stop, tell the user the anchor SHA and which files this loop touched, and offer to revert to it before replanning. Do not silently keep iterating fixes on top of a design the user hasn't confirmed is worth salvaging.

Claude implements step-by-step per the approved plan. Save to `${CLAUDE_PLUGIN_DATA}/codex-loop/implementation.md`.

## Phase 5: Review (Codex)

Send the diff + original plan to Codex via `task`:

- **Standard**: bugs, logic errors, performance issues, security vulnerabilities, plan deviations.
- **`--performance-focus`** (`high` effort): algorithm complexity, N+1 queries, unbounded loops, memory allocation, I/O bottlenecks, caching opportunities.

Classify findings by severity. Save to `${CLAUDE_PLUGIN_DATA}/codex-loop/phase5_review.md`.

## Phase 6: Iterate — convergence check

Apply fixes for Critical/Major findings, then send the fix diff back to Codex via `codex-companion.mjs task --resume-last` (session continuity, same companion path as every other phase in this loop — never the raw `codex exec` CLI). **Concrete exit condition** (codex-kit's own addition — the vague "quality standards met" from the original design was flagged as a defect and replaced): stop iterating when either (a) two consecutive rounds report only Minor/Info findings, or (b) all Critical/Major findings from the prior round are confirmed fixed in this round's review. Log every round in `${CLAUDE_PLUGIN_DATA}/codex-loop/iterations.md`. Discuss with the user (not silently auto-resolve) if a Critical/Major finding persists past 3 rounds.

Severity-gated response: Critical → fix immediately. Architectural → discuss with the user. Minor/Info → document, don't block.

---

## Testing & Validation

**Verify this skill activates on:**
- "run a codex-claude loop for adding a new caching layer" (complex, security-sensitive)
- An explicit request for dual-AI review or plan-validate-implement-review

**Verify it does NOT activate on:**
- A simple one-off fix or prototype → `codex-rescue`
- A single implementation/fix task with no up-front plan-validation need → `codex-rescue`

**Concrete scenarios to check:**
1. Phase 3's decision gate on "revise" → loops back to Phase 1 with feedback incorporated, logs the iteration, never silently proceeds to implementation.
2. Phase 6's convergence check: two consecutive rounds report only Minor/Info → loop stops, does not force a 3rd round.
3. A Critical/Major finding persists past 3 rounds → discussed with the user, never silently auto-resolved.
4. `--security-focus` is present → Phase 2 validation always runs at `xhigh` effort, not the config default.
5. Phase 4 always captures a rollback anchor (`git rev-parse HEAD`, or an explicit note if the tree already had unrelated uncommitted changes) before the first edit.

**Current test coverage:**
- `evals/codex-plan-loop/evals.json` — 1 defined scenario (6-phase structure, concrete convergence condition). Definition only — not yet run and graded.
- No persisted smoke test exists for this skill (its Codex calls aren't mechanically testable the way a fixed prompt template is — each phase's payload depends on the actual plan/diff content).

**Quality gates:**
- [ ] Every phase's scratch artifact is written under `${CLAUDE_PLUGIN_DATA}/codex-loop/`, never the repo root
- [ ] The convergence check never loops past a genuinely met stop condition
- [ ] A persisting Critical/Major finding is always surfaced to the user, never silently dropped
