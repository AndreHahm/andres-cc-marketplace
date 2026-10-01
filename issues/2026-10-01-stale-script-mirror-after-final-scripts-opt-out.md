# mirror sync: a stale .claude/scripts mirror is kept when the last scripts_mirrors opt-out coincides with a source deletion

## Summary
When a plugin drops its last `scripts_mirrors` opt-in in the same change that deletes one of its scripts, the generated `.claude/scripts/` copy of the deleted script is neither pruned nor reported, and `check-all` stays green.

## Environment
- **Product/Service**: `scripts/marketplace_ci/sync_plan.py` (`plan_plugin_sync`), `.claude/marketplace-sync.json` (`scripts_mirrors`)
- **Region/Version**: branch `feat/mirror-plugin-root-shared-folders`, head `134d97c80bc87ebe17d6f15503ef7c17380323a7` (PR #455, implementing #446)

## Reproduction Steps
1. Use a throwaway repo with one registered plugin `kit` and a pre-existing mirrored file `.claude/scripts/kit-run.sh`.
2. Plan with a previous registry where `kit` is in `scripts_mirrors` and a current registry where it is not, in three variants: (A) `plugins/kit/scripts/kit-run.sh` still exists; (B) the source file is deleted in the same change; (C) `kit` stays opted in and the source file is deleted.
3. Inspect the actions planned for `.claude/scripts/kit-run.sh`.

## Expected Behavior
Every mirrored file whose source or owner is gone is pruned, or at least reported, regardless of how the owner left.

## Actual Behavior
Verified live against the real planner:

| Case | Planned action for the stale mirror |
|---|---|
| A: opt-out, source still present, previous registry passed | `delete` (works) |
| B: last opt-out and source deleted, previous registry passed | **none**; the file is silently kept |
| B: same, `bootstrap=True` | **none**; the bootstrap orphan scan covers `.claude/scripts` only while `scripts_mirrors` is non-empty, and after the last opt-out it is empty |
| C: still opted in, source deleted, `bootstrap=True` | `warn` (no canonical source) |
| C: still opted in, source deleted, plain check (`previous=None`, `bootstrap=False`, what `check-all` runs) | **none** |

Case C is existing behavior for every mirrored directory, not something this change introduced. Case B is specific to the new opt-out pruning.

## Visual Evidence
None.

## Impact
**Low** - A stale generated file is left behind. No outage or data loss is shown. A possible consequence is that an obsolete script (for example one removed because it was unsafe) stays tracked and callable under `.claude/scripts/` while `check-all` reports green. The workaround is deleting the stale file by hand.

## Additional Context
- **Root cause:** the opt-out pruning loop (over `removed.scripts_mirrors`) enumerates files by walking the plugin's current `scripts/` directory. A file that no longer exists on disk cannot be attributed to the removed owner, and the `.claude/scripts/` namespace is flat, so ownership cannot be inferred from the path.
- **Options, not decided:**
  1. Enumerate the previous revision's source tree (for example `git ls-tree` at the previous registry's revision) to attribute and prune the deleted file.
  2. Persist an ownership inventory (destination to owning plugin) that the sync maintains and the check can verify.
  3. Always scan `.claude/scripts/` in bootstrap mode, regardless of `scripts_mirrors`, and report ownerless files.
  4. Accept it and document it as a known limitation.
- **If fixed:** it needs a regression test in `tests/marketplace_ci/test_sync.py` for the final-owner deletion case. `sync_plan.py` is a Tier 1 (review-dispatch-critical) file, so that PR needs the bypass-attestation protocol as well.
- Related: #446, #123, #449, PR #455.

## Review Finding Source
- Found in PR #455: https://github.com/AndreHahm/andres-cc-marketplace/pull/455
- Head SHA the finding was raised against: `24c0458ae250c2d6def8ebaa6fffd6224cffbaad`
- Review thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/455#discussion_r4154372173
- Reviewer: CodeRabbit (the cross-model review's Codex pass had found the same limitation independently, before the PR was opened)
- Stated severity: Minor
