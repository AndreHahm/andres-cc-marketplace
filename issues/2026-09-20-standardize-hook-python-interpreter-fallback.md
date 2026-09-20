## Summary
Make the uv/python3/python interpreter-fallback pattern the documented default (not "optional") in `hook-development`, document the two-file `.sh`+`.py` convention it relies on, and back it with a rule.

## Environment
- **Product/Service**: plugin-devkit (`hook-development` skill), this marketplace's `.claude/rules/`
- **Region/Version**: n/a

## Current Behavior
`plugins/plugin-devkit/hooks/*.sh` (`rulebook-check.sh`, `security-precommit-check.sh`,
`r25-overhead-disclosure-check.sh`, `r26-expensive-action-check.sh`) each implement a three-way
`uv run` → `python3` → `python` interpreter fallback, wrapping a sibling `.py` file that holds the
real logic, with a graceful JSON "no Python runtime found" error as the final fallback instead of a
bare crash. This pattern was confirmed correct and necessary in a session fixing plugin-devkit's own
hook executable-bit bugs (commit `e30bdbfa`, branch `fix/plugin-devkit-script-executability`): the
`.sh` needs the executable bit because `hooks.json` invokes it by bare path, while the `.py` doesn't,
since it's always passed as an argument to the resolved interpreter.

`plugins/plugin-devkit/skills/hook-development/SKILL.md` (around line 329) and
`skills/hook-development/references/patterns-and-templates.md` ("Pattern 11: Cross-Platform Python
Hook", around lines 835–841) already document a similar fallback, but:
- it's marked "(optional)"
- the documented snippet has no graceful "no interpreter found" degradation path — it unconditionally
  falls through to `exec python "$0" "$@"` with no handling if even that binary is missing

This is inconsistent with what plugin-devkit's own hooks actually do, and leaves authors of new hooks
without a clear, required convention to follow.

## Desired Behavior
1. In `hook-development`'s `SKILL.md`/`patterns-and-templates.md`, make the uv→python3→python
   fallback (with graceful degradation — e.g. emitting a `hookSpecificOutput`-shaped JSON error) the
   recommended default for any hook whose logic is Python, not "(optional)".
2. Document the two-file convention explicitly (a `.sh` wrapper handling interpreter selection + a
   sibling `.py` holding the actual logic) as the pattern to use when the hook is registered via a
   bare `hooks.json` command path, using plugin-devkit's own `hooks/` directory as the worked example.
3. Add a new `.claude/rules/*.md` rule (or extend an existing hook-authoring rule) requiring/
   recommending this fallback pattern for any new hook that invokes Python, enforced at "before
   finalizing" time per this repo's existing rule conventions.

## Impact
**Low** — no hook is currently broken by this gap (the documented pattern still works when followed),
but new hooks authored without this convention risk the same class of silent-failure bug
`fix/plugin-devkit-script-executability` just fixed for plugin-devkit's own hooks.

## Additional Context
See also the companion follow-up issue for auditing/retrofitting *existing* hooks in other plugins
against this same convention, once it's finalized here.
