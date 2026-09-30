# R33 assessment: `legacy-kit` (status active, `prefix` key absent)

Sources: plugin-rulebook SKILL.md (R33 entry) and references/component-file-prefix.md.

## Verdict
Yes, this is a finding, and it is not treated like an explicit `null`.

- **Kind:** an inventory-record defect. The record is missing the required `prefix` key. This is not a file-naming violation on `scripts/legacy-tool.sh`.
- **Severity:** R33 is a REQUIRED rule. The docs give no separate severity label for the absent-key case, so I treat it as a blocking REQUIRED finding under R33's inventory requirement.

## Reasoning
1. SKILL.md R33: "Every plugin's inventory record must carry a `prefix` key; an explicit `null` (with no `domain_prefix`) is a deliberate opt-out ... and R33 raises no finding for it." Only the explicit `null` is exempt. An absent key is not the opt-out.
2. component-file-prefix.md, "Gating": the `prefix` key "is required in both inventory schemas, so no plugin can be silently unregistered." An absent key is exactly the silent-unregistered state R33 forbids.
3. `legacy-kit` is `active`, so it is in scope on status alone.
4. File check: R33 checks `scripts/legacy-tool.sh` against a registered `prefix` or `domain_prefix`. Neither is registered, so there is nothing to compare against and no per-file naming finding can be computed yet. I would not report `legacy-tool.sh` as a violation today. It becomes one once a prefix is registered, unless it already starts with `<prefix>-` or `<domain>-`.

## Fix
1. Add the `prefix` key to the record, choosing one of:
   - **Register a curated prefix (the normal path for a real plugin).** Propose one, check marketplace-wide uniqueness, and get human `AskUserQuestion` approval through the marketplace-inventory Plan/Apply flow. A `domain_prefix` may optionally be registered too. The prefix is permanent once assigned.
   - **Explicit `"prefix": null`.** This is a deliberate opt-out. The docs say only `example-plugin` (a test fixture) holds it today, so it is not appropriate for an active real plugin without a recorded decision.
2. If a prefix (say `leg`) is registered, rename `scripts/legacy-tool.sh` to `leg-legacy-tool.sh`, or to a cleaner `leg-tool.sh` (avoid a stutter). A `domain_prefix` form also works, and a `.py` file could use snake_case instead.
3. Update every reference: SKILL.md bodies, `hooks/hooks.json` commands, script invocations and imports, doc links, and the `.claude/` mirror.

## Caveat
The documented text does not name a specific finding label (for example "schema-required-key missing") for the absent-key case. The classification above is inferred from R33's "must carry a `prefix` key" and "no plugin can be silently unregistered" wording. The mechanical layer (`prefix_check.py` and the inventory schemas) is what would actually flag it.
