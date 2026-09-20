## Summary
Audit every plugin's hooks for a Python interpreter invocation missing the graceful uv/python3/python fallback, then retrofit the ones found.

## Environment
- **Product/Service**: all plugins in this marketplace (`plugins/*/hooks/hooks.json`, `skills/*/SKILL.md` frontmatter `hooks:` blocks)
- **Region/Version**: n/a

## Current Behavior
A shallow grep this session found at least one existing hook that invokes Python without the full
fallback: `plugins/context-kit/hooks/hooks.json`'s `SessionStart` hook for
`skills/context-mode/scripts/detect_mode.py` uses only `python3 || python` — no `uv` tier, and no
graceful "no runtime found" degradation — unlike plugin-devkit's own `hooks/*.sh`.

Scope is **not** fully known yet: only a shallow grep of `plugins/*/hooks/hooks.json` was done this
session, not a full audit of skill-frontmatter `hooks:` blocks inside `SKILL.md` files across all
plugins.

## Desired Behavior
1. Grep every `plugins/*/hooks/hooks.json` and every `skills/*/SKILL.md` frontmatter `hooks:` block
   repo-wide for a hook command invoking `python`/`python3` directly without the full
   uv→python3→python cascade and without graceful no-runtime degradation.
2. Retrofit each finding to the shared convention once the companion issue's convention is finalized
   and documented in `hook-development`.

## Impact
**Low** — these hooks work today as long as `python3` (or `python`) is present on `PATH`; the gap is
resilience/consistency, not a currently-observed failure.

## Additional Context
- Blocked on #358 ("Standardize the uv/python3/python hook-interpreter fallback in hook-development
  and add a rule") landing first — the target convention should be finalized before retrofitting
  other plugins to match it.
- Known starting point: `plugins/context-kit/hooks/hooks.json`'s `SessionStart` hook
  (`python3 || python`, no `uv` tier, no graceful degradation).
