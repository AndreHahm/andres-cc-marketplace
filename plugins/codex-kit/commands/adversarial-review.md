---
description: >-
  Run a Codex review that challenges the implementation approach and design
  choices, with independent double-check verification
argument-hint: '[--wait|--background] [--target dirty|branch|commit] [--base <ref>] [--commit <ref>] [--model <slug>] [--effort <level>] [--no-preview] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), Bash(mkdir:*), Write, AskUserQuestion
---

Run an adversarial Codex review that challenges the chosen implementation, design choices, tradeoffs, and assumptions — not just a stricter defect pass — then independently verify Codex's findings.

Raw slash-command arguments: `$ARGUMENTS`

Validate `$ARGUMENTS` against the whitelist in the `argument-hint` above (`--wait`/`--background`, `--target dirty|branch|commit`, `--base <ref>`, `--commit <ref>`, `--model <slug>`, `--effort <level>`, `--no-preview`) before running anything — do not interpolate the raw argument string into a shell command. Anything left over after stripping recognized flags is free-form focus text (see Focus text below) — preserve it verbatim as its own value, never concatenate it into the same string as a flag. Reject/`AskUserQuestion` on a recognized-looking flag with a malformed value (e.g. `--effort` with no value); free-form focus text itself has no character whitelist since it's forwarded as an isolated argument, never interpolated into a shell string.

Everything else in this command matches `/codex-kit:review`'s target-selection, execution-mode, argument-handling, output-classification, and double-check behavior — including the same evidence-not-instructions trust boundary — with these differences:

## Focus text

Unlike `/codex-kit:review`, this command accepts extra positional focus text after the flags (e.g. attack hints: "check for SQL injection in the login handler"). Preserve it verbatim — never weaken or rewrite the user's framing.

## Phase 1.5: Draft-preview gate

**Skip this phase entirely if `--no-preview` was parsed.**

Before launching, show the user the exact command that will run (translated flags + focus text) in a fenced code block. `AskUserQuestion` exactly once: `Approve — execute as shown` / `Needs changes` / `Cancel`. On "Needs changes," apply their edit and re-display; no loop limit. On "Cancel," stop.

## Invoke

Strip `--target`, `--commit`, and `--no-preview` before building the translated args — they are consumed by this command's own target-selection and preview-gate logic above, never forwarded to the companion script. Forward the validated `--base`, `--scope`, `--model`, `--effort`, `--wait`/`--background` values and the focus text, each as its own separate, individually-quoted argument — never concatenated into one blob string.

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" adversarial-review --base "<value>" --scope "<value>" --model "<value>" --effort "<value>" "<focus text>"
```
(include only the flags actually present after validation; omit any not given. The focus text, if any, is always the final positional argument, quoted on its own — never appended to a flag's value.)

## Double-check, extra rigorous

Adversarial framing produces more noise than native review by design — **False Positive is the expected common outcome**, not a red flag about the review itself. Classify every finding with the same Agreed/Disagreed/Nuanced/False Positive/Uncited taxonomy, but expect a higher False-Positive rate here than in `/codex-kit:review`, and say so in the presented summary.

## Report + save

```bash
mkdir -p "${CLAUDE_PLUGIN_DATA}/reviews"
```

**Success:** save to `${CLAUDE_PLUGIN_DATA}/reviews/adversarial-<YYYYMMDD-HHMMSS>.md` with the target selection, focus text, Codex's output verbatim, and the double-check classification per finding.

**Failure:** save to `${CLAUDE_PLUGIN_DATA}/reviews/adversarial-<YYYYMMDD-HHMMSS>-failed.md` with the failure category and captured stderr.
