# R33 check: example-kit

**Verdict: R33 raises no finding (PASS / inert) for `scripts/helper.sh` and none for the inventory record.**

## Facts applied
- Inventory record: `"prefix": null`, no `domain_prefix` key.
- File: `scripts/helper.sh` (basename has no plugin prefix). `scripts/` is normally an in-scope directory.

## Reasoning (SKILL.md R33 + references/component-file-prefix.md)
1. **Gating.** R33's scope covers only plugins whose record has a registered `prefix` and/or `domain_prefix`. The reference's "Gating: inert for an explicit `null` opt-out" section says a plugin with `prefix: null` and no `domain_prefix` produces zero findings. That means no warning, no ADVISORY, nothing.
2. **File.** `helper.sh` would violate R33 if a prefix were registered. With none registered, there is no `<prefix>-`/`<domain>-` to require, so the file check is vacuous. Path scope does not matter, because the plugin gate comes first.
3. **Inventory record.** R33 requires every record to carry a `prefix` key. The key is present, with an explicit `null`. That is the sanctioned deliberate opt-out, not a missing registration, so the record is compliant. A record with the `prefix` key absent entirely would be a schema problem. That is not this case.
4. **Status exemption is irrelevant.** The `superseded`/`retired` skip is a separate path and plays no part here.

## Caveats
- The rulebook says the only opt-out held today is `example-plugin` (a test fixture). `example-kit` would be a second opt-out. R33 itself treats any explicit null as inert. Whether a second opt-out is desirable is a curator decision, not an R33 finding.
- If `example-kit` later registers a `prefix` or `domain_prefix`, `helper.sh` becomes a REQUIRED violation. The fix would be to rename it to `<prefix>-helper.sh` or `<domain>-helper.sh`. A `.sh` file cannot use the snake_case option, which is for `.py` only.
