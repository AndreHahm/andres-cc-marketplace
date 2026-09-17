## Summary
`plugin-devkit`'s `plugin.json` and `marketplace.json` descriptions are not byte-identical

## Environment
- **Product/Service**: plugin-devkit (this marketplace's own plugin)
- **Region/Version**: N/A

## Reproduction Steps
1. Read `plugins/plugin-devkit/.claude-plugin/plugin.json`'s `description` field.
2. Read the root `.claude-plugin/marketplace.json`'s plugin-devkit entry `description` field.
3. Compare the two.

## Expected Behavior
Either the two descriptions should be identical, or the divergence should be documented as intentional.

## Actual Behavior
`plugin.json`'s description reads "...comprehensive plugin structure guidance" while
`marketplace.json`'s plugin-devkit entry reads "Claude Code Plugin Development" — the two are not
byte-identical, and nothing currently enforces or checks that they should match.

## Impact
**Low** — cosmetic/informational only. A maintainer or tool reading one file's description sees a
different capability summary than reading the other; no functional behavior is affected.

## Additional Context
Discovered during a 2026-09-16/17 `plugin-lifecycle-downstream` QA session on plugin-devkit's
`marketplace-documentation` feature; confirmed via `git status`/`git log` as pre-existing and unrelated
to that session's own changes (predates it). Suggested fix: reconcile the two descriptions to be
identical, likely just editing one or both fields to match — no behavior change required, just a
content sync.
