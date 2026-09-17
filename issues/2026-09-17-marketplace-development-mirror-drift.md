## Summary
`marketplace-development` skill's canonical copy and its `.claude/` mirror have diverged

## Environment
- **Product/Service**: plugin-devkit (this marketplace's own plugin)
- **Region/Version**: N/A

## Reproduction Steps
1. Diff `plugins/plugin-devkit/skills/marketplace-development/` against its `.claude/skills/marketplace-development/` mirror.
2. Observe the two copies are not byte-identical.

## Expected Behavior
Per this repo's R19 in-development-mirror convention, `plugins/plugin-devkit/` is canonical and
`.claude/` is a generated/staged mirror that should stay byte-identical to it.

## Actual Behavior
The two copies have diverged for `marketplace-development` specifically — the canonical and mirror
content differ.

## Impact
**Low** — no immediate functional break reported, but a stale mirror risks a session reading/editing
the wrong copy, or a rulebook/audit pass flagging drift that a mirror-sync pass should have caught.

## Additional Context
Discovered during a 2026-09-16/17 `plugin-lifecycle-downstream` QA session on plugin-devkit's
`marketplace-documentation` feature; confirmed via `git status` as untouched by that session's own
commits (pre-existing, unrelated). Suggested fix: run this plugin's mirror-sync tooling (or a manual
diff-and-reconcile pass) to bring the `.claude/` copy back in sync with the canonical
`plugins/plugin-devkit/` copy, then verify via `diff`.
