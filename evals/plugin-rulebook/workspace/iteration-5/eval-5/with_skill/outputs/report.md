# R33 check: example-kit

Sources: plugin-rulebook SKILL.md (R33 entry) and references/component-file-prefix.md (worktree copies).

## Result: no R33 finding for either target

| Target | R33 result |
|---|---|
| `scripts/helper.sh` (no prefix in basename) | PASS / no finding (rule inert) |
| `marketplace-inventory.json` record for example-kit | PASS / no finding |

## Why

1. **File naming is inert for this plugin.** `scripts/` is an in-scope directory, and `helper.sh` lacks any `<prefix>-`/`<domain>-` start. But R33's scope covers only plugins whose record has a registered `prefix` and/or `domain_prefix`. The "Gating: inert while no prefix is registered" section says a plugin with `prefix: null` and no `domain_prefix` produces zero findings. It is not a warning and not an ADVISORY. With no registered prefix there is nothing to match the basename against.
2. **The inventory record is valid.** R33 requires every record to carry a `prefix` key. The record has the key, with value `null`. `null` is explicitly allowed as a deliberate, recorded opt-out (or a not-yet-registered new plugin) and raises no finding.
3. **A missing `domain_prefix` key is fine.** `domain_prefix` is optional and independent of `prefix`. Only the `prefix` key is required. The absent-key case that would be a finding is a missing `prefix` key, which is not this scenario.
4. **Status and exclusion checks are not needed.** Gating already makes the rule vacuous. The Python snake_case option and exclusions (`__init__.py`, `hooks.json`, skill-scoped resources) do not apply.

## Caveat
If example-kit later registers a `prefix` or `domain_prefix`, `scripts/helper.sh` would become a FAIL (REQUIRED). The fix is to rename it to `<prefix>-helper.sh` or `<domain>-helper.sh` and update all references.
