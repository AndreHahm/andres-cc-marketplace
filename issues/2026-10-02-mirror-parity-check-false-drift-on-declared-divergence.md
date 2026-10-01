# mirror-parity-check.sh reports false DRIFT for a declared divergence and exits 1 with no argument

## Summary
`plugin-rulebook`'s `mirror-parity-check.sh` reports `DRIFT: skills/marketplace-development` even though that divergence is declared in `.claude/marketplace-sync.json`, because the script never reads the declared list. Its CI validator entry also passes no argument, so the script prints its usage message and exits 1.

## Environment
- **Product/Service**: `plugin-devkit`, `plugins/plugin-devkit/skills/plugin-rulebook/scripts/mirror-parity-check.sh`, validator entry `plugin-devkit.mirror-parity-check` in `.github/marketplace-validators.json`
- **Region/Version**: repository state on 2026-10-02 (branch `refactor/plugin-rulebook`)

## Reproduction Steps
1. Run `bash plugins/plugin-devkit/skills/plugin-rulebook/scripts/mirror-parity-check.sh plugin-devkit` from the repo root. It prints `DRIFT: skills/marketplace-development` and exits 1.
2. Open `.claude/marketplace-sync.json`: `divergence_exceptions` already declares that `.claude/` copy as intentionally divergent. The repo's own `check-plugin-mirrors` honors it and reports only an informational warning.
3. Run the script with no argument, as the validator entry does (it has no `args` field). It prints its usage line and exits 1.

## Expected Behavior
- A divergence declared in `divergence_exceptions` is not reported as DRIFT (or is reported as informational), and the script exits 0 when nothing else differs.
- The validator entry supplies the plugin-name argument the script requires, or the script defaults sensibly.

## Actual Behavior
- Exit 1 with `DRIFT: skills/marketplace-development` for a declared divergence.
- Exit 1 on the usage message when run without an argument.

## Impact
**Low** - The repo's own mirror check passes. I did not verify how the validator harness treats this script's exit code, so whether CI is affected is unconfirmed.

## Additional Context
- Found while extending this script to compare rules, `hooks/scripts` and `scripts` in the `plugin-rulebook` refactor; it was listed there as a known pre-existing gap and not fixed.
- A fix needs a small reader for `divergence_exceptions` plus a test; the script currently has none.
- Related: #202 (a mirror-sync registration list can be incomplete for a tracked copy).
