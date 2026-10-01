# mirror sync: retire or reconcile `.claude/hooks/_external-scripts/` and `EXTERNAL_HOOK_SCRIPT_MIRRORS` now that `scripts/` can be mirrored

## Summary
Once plugin-root `scripts/` is mirrored per plugin (#446), `.claude/hooks/_external-scripts/` and its hand-maintained `EXTERNAL_HOOK_SCRIPT_MIRRORS` list overlap with the new `.claude/scripts/` mirror: context-kit's hook scripts now exist twice, codex-kit still needs the old mechanism, and three places still describe `scripts/` as unmirrored.

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `scripts/marketplace_ci/sync.py`, `sync_plan.py`, `registry.py`
- **Region/Version**: branch `feat/mirror-plugin-root-shared-folders` (the #446 implementation); `main` as of 2026-10-01

## Reproduction Steps
1. On the #446 branch, `.claude/marketplace-sync.json` lists `scripts_mirrors`: plugin-devkit, git-kit, analysis-kit, session-kit, workmanagement-kit, context-kit. codex-kit and antigravity-kit are not listed.
2. Run `python -m scripts.marketplace_ci sync-plugin-mirrors`.
3. Compare `.claude/scripts/` with `.claude/hooks/_external-scripts/context-kit/scripts/`.

## Expected Behavior
One mechanism owns each plugin script. The hook rewrite target, the hand-maintained list, and the docs agree with how `scripts/` is actually mirrored.

## Actual Behavior
- **Double mirroring (context-kit):** `context-monitor.py`, `ctx-pre-compact.py` and `ctx-post-compact-restore.py` exist in both `.claude/scripts/` and `.claude/hooks/_external-scripts/context-kit/scripts/`. Harmless, but two copies of the same files.
- **codex-kit cannot simply migrate (inference from the comments in `sync.py`, not a test run):** its hook closure needs plugin-root siblings (`.claude-plugin/plugin.json`, `prompts/stop-review-gate.md`, `schemas/review-output.schema.json`) at plugin-relative positions. `_external-scripts/<plugin>/` preserves that layout; a flat `.claude/scripts/` does not. Separately, two codex-kit skill scripts import `../../../scripts/lib/codex-exec.mjs`, which resolves in the mirror only if codex-kit's `scripts/` were mirrored (it is not opted in).
- **Duplicate directory tuple:** `sync.py` defines `_MIRRORED_COMPONENT_DIR_PREFIXES` (around line 179) as a hard-coded copy of the component directory names, independent of `COMPONENT_DIRS` in `sync_plan.py`. It decides how `${CLAUDE_PLUGIN_ROOT}/<dir>/...` is rewritten in hook commands. #446 deliberately left it unchanged so codex-kit hooks keep using `_external-scripts`. If it were ever extended to `scripts`, codex-kit hooks would rewrite to `.claude/scripts/` and break.
- **Hand-maintained list:** `EXTERNAL_HOOK_SCRIPT_MIRRORS` has 29 entries (26 codex-kit, 3 context-kit). A new hook referencing a script outside the list raises `SyncError`; a stale entry fails loudly. Nothing re-verifies the codex-kit closure automatically (the comment block above the list says so).
- **Stale text:** `.claude/hooks/README.md` ("deliberately not a general `plugins/*/scripts/` mirror"), the comment block above `EXTERNAL_HOOK_SCRIPT_MIRRORS` in `sync.py`, and the `prefix_check.py` docstring ("never mirrored into `.claude/`") are now partly wrong.

## Visual Evidence
None.

## Impact
**Low** - Cosmetic duplication today, plus a maintenance trap: the hand-maintained list and the directory tuple can drift apart silently. Nothing is broken; hooks run as before.

## Additional Context
Decisions to settle:
1. Retire the list for context-kit and rewrite its hooks to `.claude/scripts/`, or keep both. Unverified: its scripts are described in a `sync.py` comment as self-contained and stdlib-only.
2. codex-kit: keep `_external-scripts`, mirror its `scripts/` plus siblings, or something else. Opting codex-kit into `scripts_mirrors` also copies its 26 smoke-test files, since the opt-in is per plugin.
3. Derive `_MIRRORED_COMPONENT_DIR_PREFIXES` from `COMPONENT_DIRS`, or keep it separate on purpose.
4. Update the three stale docs listed above.
5. Whether the list can be generated or verified instead of curated by hand.

Related: #446 (its Proposed Scope point 3 is this question; the implementing change settles the mirror side only), #316, #123, #248, #192.
