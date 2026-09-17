## Summary
antigravity-kit's mirrored docs links break once registered in mirror sync

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `scripts/marketplace_ci/sync.py`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. `antigravity-kit` is registered in `.claude/marketplace-sync.json`'s `plugin_mirrors` and `sync-plugin-mirrors` has been run (done as part of #335's fix).
2. Open the mirrored `.claude/commands/agy-migrate.md` (canonical source: `plugins/antigravity-kit/commands/agy-migrate.md`) and follow its link to `docs/agy-migration.md` (relative path `../docs/agy-migration.md`).
3. Same for the mirrored `.claude/skills/migrate-to-antigravity/SKILL.md` (canonical: `plugins/antigravity-kit/skills/migrate-to-antigravity/SKILL.md`), relative path `../../docs/agy-migration.md`.

## Expected Behavior
The link should resolve to the migration reference doc regardless of whether the file is read from its canonical `plugins/antigravity-kit/` location or its mirrored `.claude/` location.

## Actual Behavior
Both relative links resolve correctly from the canonical `plugins/antigravity-kit/` location (to `plugins/antigravity-kit/docs/agy-migration.md`, which exists) but resolve to a nonexistent `.claude/docs/agy-migration.md` from the mirrored location, because `docs/` is not one of the mirrored component directories (`scripts/marketplace_ci/sync.py`'s `COMPONENT_DIRS` is only `skills`, `agents`, `commands`, `hooks`, `rules`). Verified live: `ls .claude/docs/agy-migration.md` reports missing while `plugins/antigravity-kit/docs/agy-migration.md` exists.

## Impact
**Low-Medium** — a broken documentation cross-reference for anyone reaching these commands/skills via the shared mirrored namespace. The commands/skills themselves still work; only the "read more" link is broken from the mirrored copy.

## Additional Context
Found by Codex's Phase 2 challenger pass during a `cross-model-review` run while implementing #335's fix (registering `antigravity-kit` in mirror sync). Similar in shape to the already-resolved #335 (a mirror-sync structural gap surfaced by registering this plugin). Suggested remediation options, none prescriptive:
1. Rewrite the two canonical links to something that resolves correctly from both the canonical and mirrored locations.
2. Extend `scripts/marketplace_ci/sync.py` to also mirror a plugin's `docs/` directory.
3. Accept as a documented, permanent limitation (matching this plugin's own `KNOWN_ISSUES.md` convention for similar gaps).

This is a decision-tracking issue — the next step is choosing among these options, not implementing one now.
