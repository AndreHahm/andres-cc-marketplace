## Summary
`example-plugin`'s mirror files appear to have never been synced into `.claude/`, and `marketplace-development`'s mirrored `SKILL.md` has drifted from its canonical source

## Environment
- **Product/Service**: `scripts/marketplace_ci` (`plan_plugin_sync` / `apply_sync_plan`)
- **Region/Version**: n/a

## Reproduction Steps
1. Run `plan_plugin_sync`/`apply_sync_plan` unscoped, against the full marketplace registry (not
   scoped to a single plugin).
2. Inspect the resulting plan/diff for `example-plugin` and for `plugin-devkit`'s
   `marketplace-development` skill.

## Expected Behavior
Every plugin's canonical `skills/agents/commands/hooks/rules` content is mirrored into `.claude/` and
stays in sync with its canonical source.

## Actual Behavior
- `example-plugin`'s mirror files appear to have never been synced into `.claude/` at all — missing:
  - `.claude/agents/example-agent.md`
  - `.claude/commands/hello.md`
  - `.claude/skills/example-skill/`
  - `.claude/hooks/.gitkeep`
  - `.claude/rules/.gitkeep`
- `.claude/skills/marketplace-development/SKILL.md` shows drift from its canonical plugin source.

## Error Details
~~~
(no error/exception — a silent sync gap, only visible by diffing an unscoped plan/apply run
against .claude/'s current contents)
~~~

## Visual Evidence
N/A

## Impact
**Low/Medium** — doesn't block anything currently, but means `.claude/`'s dogfooding mirror is
silently out of sync with at least one plugin's real source, which could mislead anyone reading
`.claude/` as ground truth for that plugin's content.

## Additional Context
Discovered incidentally while live-testing a fix for issue #413 (mirror executable-bit handling) in
worktree `413-mirror-executable-bit-windows`, 2026-09-28. The discovering session reverted all
changes immediately (`git clean`/`git restore`) and did not investigate root cause — explicitly out
of scope for #413.

Suggested next step: re-run `plan_plugin_sync` against the full registry, inspect the diff for
`example-plugin` and `marketplace-development`, and determine whether this is a one-time sync gap
(e.g. these two were never synced since `plan_plugin_sync`/`apply_sync_plan` were introduced) or a
recurring bug in the sync tooling itself.
