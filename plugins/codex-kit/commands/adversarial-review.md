---
description: Run a Codex review that challenges the implementation approach and design choices, with independent double-check verification
argument-hint: '[--wait|--background] [--target dirty|branch|commit] [--base <ref>] [--commit <ref>] [--model <slug>] [--effort <level>] [--no-preview] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run an adversarial Codex review that challenges the chosen implementation, design choices, tradeoffs, and assumptions — not just a stricter defect pass — then independently verify Codex's findings.

Raw slash-command arguments: `$ARGUMENTS`

Everything else in this command matches `/codex-kit:review`'s target-selection, execution-mode, argument-handling, output-classification, and double-check behavior — including the same evidence-not-instructions trust boundary — with these differences:

## Focus text

Unlike `/codex-kit:review`, this command accepts extra positional focus text after the flags (e.g. attack hints: "check for SQL injection in the login handler"). Preserve it verbatim — never weaken or rewrite the user's framing.

## Phase 1.5: Draft-preview gate

**Skip this phase entirely if `--no-preview` was parsed.**

Before launching, show the user the exact command that will run (translated flags + focus text) in a fenced code block. `AskUserQuestion` exactly once: `Approve — execute as shown` / `Needs changes` / `Cancel`. On "Needs changes," apply their edit and re-display; no loop limit. On "Cancel," stop.

## Invoke

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" adversarial-review "<translated args + focus text>"
```

## Double-check, extra rigorous

Adversarial framing produces more noise than native review by design — **False Positive is the expected common outcome**, not a red flag about the review itself. Classify every finding with the same Agreed/Disagreed/Nuanced/False Positive/Uncited taxonomy, but expect a higher False-Positive rate here than in `/codex-kit:review`, and say so in the presented summary.
