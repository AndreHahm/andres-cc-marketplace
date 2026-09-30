# R33 assessment: `legacy-kit` (absent `prefix` key)

**Verdict: this is a finding. It is not silently inert, and it is not an R33 file-naming finding.** It is a schema/record-integrity gap.

## Basis (SKILL.md R33 and references/component-file-prefix.md)
- SKILL.md R33: "Every plugin's inventory record must carry a `prefix` key; `null` (with no `domain_prefix`) means none is registered ... and R33 raises no finding for it." Only an explicit `null` is the inert opt-out.
- Gating section of the reference: "The `prefix` key itself is required in both inventory schemas and enforced by the two inventory scripts' validators, so an absent key is never treated as inert there." It also says `prefix_check.py` "does not yet tell an absent key from `null`".

## Application
- Record: `legacy-kit`, status `active`, fields id/name/source/status, **no `prefix` key**.
- This is a missing required key, not `prefix: null`. The null opt-out does not apply, so the record is not treated as "inert, no finding".
- Kind of finding: REQUIRED-level record/schema violation (missing required `prefix` key). It is reported by the inventory validators, and I'm reporting it here as a record-integrity finding. It is not an R33 per-file naming violation.
- `scripts/legacy-tool.sh`: no prefix is registered, so R33 cannot say the file is mis-prefixed. No per-file finding is raised for it yet. The plugin is `active`, so it is in status scope, but the registered-prefix gate leaves the file check vacuous.
- Caveat: the mechanical `prefix_check.py` cannot distinguish absent from `null`. It would treat this plugin as inert, so the policy check here must not rely on the CI script to catch it.

## Fix
1. Add a `prefix` key to the `legacy-kit` record in `marketplace-inventory.json` (via the `marketplace-inventory` skill's plan/approve/apply flow).
2. If no prefix is registered yet, set an explicit `"prefix": null`. That clears the schema finding, and R33 then raises nothing.
3. Once a curated prefix (and/or `domain_prefix`) is registered, `scripts/legacy-tool.sh` becomes in scope. Rename it to `<prefix>-legacy-tool.sh` (or `<domain>-...`), and update references and the `.claude/` mirror.
