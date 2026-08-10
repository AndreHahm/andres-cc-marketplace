---
name: codex-peer-review
description: >-
  Validate Claude's own analysis, design, or recommendation against Codex
  before presenting it to the user. Use manually/on-request only — e.g. "get
  a second opinion from codex before we commit to this", "codex peer review
  this design". Not a proactive/automatic trigger (codex-kit deliberately
  narrowed this from the original design's 'fires before every
  recommendation' behavior — too many silent Codex calls by default). For
  verifying an existing written plan/document file, use codex-verify instead.
argument-hint: "[--base <ref>] [question or design summary]"
allowed-tools: ["Bash(node:*)", "AskUserQuestion", "Agent", "WebSearch"]
---

# Peer validation of Claude's own output

Catches blind spots in single-perspective analysis by running Codex in parallel on the *same question* and comparing outputs — **before** Claude presents a design, recommendation, or review finding to the user.

**Always dispatch via a subagent** (the `Agent` tool, general-purpose) to keep this comparison out of the main conversation's context — matches the rationale that made this pattern worth adopting from its source.

## Command selection (the #1 mistake to avoid)

- Reviewing **actual code changes** (a diff): use `${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs review --base <ref>`.
- Validating a **design, plan, refactoring proposal, or answer to a question** (no diff to point at): use `${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs task` with the position written out as the prompt.
Using the wrong one is the most common failure mode — check which case applies before invoking.

## Round 1

State Claude's position with its supporting evidence. Send it to Codex (`--json`, capture the `threadId` from the response for Round 2 continuity).

## Round 2

Respond to Codex's Round 1 evidence using `${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs task --resume-last`. Attempt synthesis.

## Classify the outcome

- **Agreement** — both land on the same conclusion.
- **Resolved disagreement** — synthesis after 2 rounds converges.
- **Unresolved after 2 rounds** — escalate. Security, architecture conflicts, breaking changes, or order-of-magnitude performance disagreements skip straight to escalation without waiting for 2 rounds.

## Escalation

For unresolved disagreements, use WebSearch (or a configured research MCP tool, if available) for authoritative outside guidance. Never invent a tiebreak — present both positions and the escalation source to the user.

## Output

Present the final report to the user in one of three shapes: **Agreement** (both aligned, brief), **Resolved Disagreement** (both positions + the synthesis + why), or **External Research Arbitration** (both positions + escalation findings, unresolved). This session-level outcome vocabulary is intentionally separate from the per-finding Agreed/Disagreed/Nuanced/False-Positive/Uncited taxonomy other codex-kit components use — this skill validates a *position*, not individual findings.

Never ask before Round 1 or Round 2 — only the escalation and final-output steps involve the user directly, keeping the loop itself autonomous once invoked.

---

## Testing & Validation

**Verify this skill activates on:**
- "get a second opinion from codex before we commit to this design"
- "codex peer review this design" (explicit, manual request only)

**Verify it does NOT activate on:**
- Proactively, without an explicit request — this skill deliberately has no automatic trigger
- Verifying an existing written plan/document file → `codex-verify`

**Concrete scenarios to check:**
1. A code-diff question routed to `task` instead of `review --base` (the #1 mistake this skill names) → wrong command selected, review the Command selection section.
2. Round 2 converges → outcome classified "Resolved disagreement", not silently reported as "Agreement".
3. A security or architecture-conflict disagreement → escalates immediately, skipping the normal 2-round wait.
4. An unresolved disagreement after escalation → both positions and the escalation source are presented; no invented tiebreak.

**Current test coverage:**
- `evals/codex-peer-review/evals.json` — 1 defined scenario (subagent dispatch, 2-round protocol, escalation path). Definition only — not yet run and graded.
- No persisted smoke test exists for this skill (its output depends on Claude's own position and Codex's live response, not a fixed template).

**Quality gates:**
- [ ] Never asks the user before Round 1 or Round 2
- [ ] Always dispatches via a subagent, never inline in the main conversation
- [ ] A security/architecture/breaking-change disagreement always skips straight to escalation
