## Summary
`scripts/marketplace_ci`'s `check-plugin-mirrors` parity check only verifies `skills/` mirror content — it doesn't catch a plugin-level `references/*.md` file that has drifted between its canonical `plugins/<name>/...` copy and its `.claude/` mirror counterpart.

## Environment
- **Product/Service**: `scripts/marketplace_ci` (this repo's own plugin-mirror sync/parity tooling)
- **Region/Version**: this repo, found during PR #179 (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Edit a plugin-level `references/*.md` file directly under `plugins/<name>/references/` (not inside a specific skill's own `skills/<skill>/references/` directory — a top-level, plugin-wide reference file).
2. Run `uv run python -m scripts.marketplace_ci sync-plugin-mirrors` and `uv run python -m scripts.marketplace_ci check-all`.
3. Observe that the check reports OK even when the `.claude/`-mirrored copy of that plugin-level reference file no longer matches its canonical source.

## Expected Behavior
`check-plugin-mirrors` should detect and flag content drift in plugin-level `references/*.md` files the same way it already does for `skills/` mirror content, so a stale plugin-level reference file doesn't silently diverge from its canonical source.

## Actual Behavior
The parity check's coverage is scoped to `skills/` mirrors only. A plugin-level `references/*.md` file (distinct from a skill's own `skills/<skill>/references/` directory, which — if it's covered at all — would fall under the existing `skills/` mirror check) can drift indefinitely with no tooling signal.

## Impact
[Severity: Medium] This is a real, disclosed gap in the marketplace's own consistency tooling — the same category of blind spot as issue #123 (`marketplace-ci: plugin-level scripts/ directories aren't mirrored or parity-checked`), just for a different plugin-level directory (`references/` instead of `scripts/`). It doesn't cause a live runtime failure on its own, but it means a plugin-level reference file's canonical and mirrored copies can silently disagree, with nothing in `check-all`/CI catching it — the exact failure mode `check-plugin-mirrors` exists to prevent for every other covered component type.

## Additional Context
Disclosed as a known, out-of-scope limitation in PR #179's own "Open Items" section rather than fixed there, since it's a shared-tooling change (`scripts/marketplace_ci`) affecting the sync/parity behavior for every registered plugin with a plugin-level `references/` directory, not scoped to that PR's own `analysis-kit` work.

**Likely related**: issue #123 already tracks the sibling gap for plugin-level `scripts/` directories being excluded from `COMPONENT_DIRS`. Both may share the same root cause (`scripts/marketplace_ci/sync.py`'s `COMPONENT_DIRS` tuple not covering every plugin-level directory that has a `.claude/` mirror expectation) and might be worth resolving together — see #123's own "To close, in a future session" list, which already asks the broader question of what should count as a mirrored component type.
