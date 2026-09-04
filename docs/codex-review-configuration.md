# Codex Review Configuration

How to customize what the external `chatgpt-codex-connector[bot]` GitHub App reviewer looks for, and
where this repo's own configuration for it lives.

Source: <https://learn.chatgpt.com/docs/third-party/github#customize-what-codex-reviews>

## How Codex finds review rules

Codex searches for `AGENTS.md` files throughout the repository:

- Root-level `AGENTS.md` — repository-wide guidance.
- Nested `AGENTS.md` files — scoped to a subdirectory (e.g. `services/<name>/AGENTS.md`).

Both the root file and any more-specific `AGENTS.md` covering a changed file apply together.

## Required format

A `## Code Review Rules` heading, with `###`-level category headings and bullet lists underneath:

```markdown
## Code Review Rules

### Category Name

- Rule description here
- Another rule here
```

## Rule-writing guidance (per the source doc)

- Target consequential behavior — a compatibility constraint, a data boundary, an unsafe side effect
  — and explain why it matters.
- Give Codex enough context to distinguish a real issue from expected behavior.
- Prefer durable guidance (outcomes, not function names that can change); place it near the code it
  governs.
- Avoid mechanical checks — leave formatting/linting to CI.
- Test by opening a representative PR and requesting `@codex review`, then refine rules based on
  actual findings.

## Where this applies in this repo

This repo's own `## Code Review Rules` section lives in the root [`AGENTS.md`](../AGENTS.md). It
governs only the external `chatgpt-codex-connector[bot]` reviewer — a separate reviewer from this
repo's own CI-dispatched Codex pipeline (`scripts/marketplace_ci/review.py` via
`codex-review-bridge`), which reads `.codex/agents/<name>.toml` directly (see
[`codex-subagents-schema.md`](codex-subagents-schema.md)) and is unaffected by anything in
`AGENTS.md`. [`REVIEW.md`](../REVIEW.md) remains the fuller reference the other reviewers (Devin,
CodeRabbit, Claude, human) read; `AGENTS.md`'s section is a condensed subset written specifically for
Codex's own rule-discovery convention above.
