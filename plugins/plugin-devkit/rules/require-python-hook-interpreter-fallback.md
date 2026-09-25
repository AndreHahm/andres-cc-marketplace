# Require the uv/python3/python Fallback for Python-Backed Hooks

## When this applies

Registering a new hook in any `hooks.json` (plugin-level or a skill's own frontmatter `hooks:` block)
whose `command` invokes a Python script directly or indirectly — before the hook is finalized.

## Rule

A hook's `command` must never call `python3`/`python` bare, or with only a partial fallback (e.g.
`python3 || python` with no `uv` tier). It must use the full `uv` → `python3` → `python` cascade, with a
graceful degradation branch (never an uncaught crash) if none of the three is found — see
`hook-development`'s Pattern 11 (`references/patterns-and-templates.md`) for the two valid shapes (an
inline `hooks.json` `command` cascade, or a `.sh` wrapper + sibling `.py` for a more complex hook) and
when to pick each. `hooks.json` invokes `command` by bare path with no interpreter of its own, so a hook
that skips this either breaks outright on a system with only `python` (no `python3`), or hard-crashes
when none of the three is on `PATH` at all.

## Incorrect

```json
"command": "command -v python3 >/dev/null 2>&1 && exec python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py || exec python \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py"
```
No `uv` tier, and no branch for "neither `python3` nor `python` exists" — it just fails.

## Correct

```json
"command": "if command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then exec uv run --no-project \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; elif command -v python3 >/dev/null 2>&1; then exec python3 \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; elif command -v python >/dev/null 2>&1; then exec python \"${CLAUDE_PLUGIN_ROOT}\"/scripts/my-hook.py; else exit 0; fi"
```
All three tiers present, plus a final branch that degrades gracefully instead of crashing. The `uv`
tier's `&& uv --version >/dev/null 2>&1` is a functional probe, not just an existence check — `command -v
uv` alone only confirms a `uv` binary is on `PATH`, not that invoking it actually works; since `exec`
irrevocably replaces the shell process, a present-but-broken `uv` would otherwise dead-end instead of
falling through to `python3`/`python`.

## Why

`plugin-devkit`'s own hooks (`rulebook-check.sh` and siblings) already implement this pattern correctly,
proven necessary while fixing a real executable-bit bug (commit `e30bdbfa`). Before this rule, it was
only documented as "(optional)" in `hook-development`, and at least two hooks shipped without it:
`context-kit`'s `detect_mode.py` `UserPromptSubmit` hook (partial fallback, no `uv` tier) and
`plugin-devkit`'s own `marketplace-development/hooks/post_edit_validate.sh`/`post_edit_sync_check.sh`
(no fallback at all — a bare inline `python3 -c "..."`). See issues #358/#359.

## Enforcement

Policy gate, no backing hook — same disclosed-limitation model most process rules in this repo use.
Neither `plugin-devkit/hooks/rulebook-check.py` nor `hooks-schema-check.sh` currently checks a hook's
`command` string against this convention; whether a new hook actually uses the full cascade depends on
author/reviewer attention at "before finalizing" time, not a mechanical check.
