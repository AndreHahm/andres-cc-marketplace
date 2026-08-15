# Hooks-Sync Investigation

## Confirmed this session

- `plugins/codex-kit/hooks/hooks.json` defines exactly three events: `SessionStart`, `SessionEnd`,
  `Stop`. No `PreToolUse`, no per-command event of any kind.
- Codex CLI's own plugin cache (`~/.codex/plugins/cache/openai-codex/codex/<version>/hooks/
  hooks.json`) mirrors this file structurally — same three events, same shape. This confirms Codex
  CLI consumes a Claude-Code-compatible hooks format for its own plugin system, not that it
  supports more event types than what's actually declared.
- `scripts/marketplace_ci/sync.py`'s `plan_hooks_merge`/`apply_hooks_merge_plan` is the real,
  existing mechanism that performs a structural merge of a plugin's own `hooks/hooks.json` into
  `.claude/hooks/hooks.json`. This is genuine, already-shipped infrastructure — not proposed here,
  confirmed by reading the actual script.

## Open question — not resolved by this skill

Whether Codex's own hook runtime supports (or could be extended to support) a genuine
pre-execution interception event — something that could actually block one dangerous command
before it runs, the way `WINDOWS_GUARDRAILS.md`'s original "dangerous-command hook" envisioned.
Every `hooks.json` this investigation found only declares session-lifecycle events. That's evidence
the capability doesn't exist in the examples checked, not proof it can never exist — the Codex CLI's
own hook system may support more event types than any file in this repo currently declares and uses.

**Not resolved because:** confirming this needs live experimentation with Codex CLI's hook
configuration and observing whether an undeclared event type is ever honored — out of scope for this
Design/Build pass, and not something to assume an answer for. If this is investigated later and a
real interception event is found, `references/codex-instruction-template.md`'s instructed-only
approach could be upgraded to genuine enforcement for at least the dangerous-command case.
