## Summary
`git-cleanup`'s default-branch resolution hardcodes a fallback to `main` when `origin/HEAD` is unset, which can silently resolve to the wrong branch in a repo whose real default is something else (e.g. `master`)

## Environment
- **Product/Service**: `git-kit` plugin, `git-cleanup` skill (`phase1-analysis.sh`, `delete-rebase-backup-tags.sh`)

## Reproduction Steps
1. In a repo with no `origin` remote (or one whose `origin/HEAD` symbolic ref was never set), whose real integration branch is `master` (not `main`)
2. Have an unrelated local branch that happens to be literally named `main`
3. Run `git-cleanup`'s Phase 1 analysis or `delete-rebase-backup-tags.sh --list`
4. Both scripts resolve `default_branch` to `main` via `${default_branch:-main}`, not the repo's actual default (`master`)

## Expected Behavior
Branch/tag categorization (merged status, reachability) should be evaluated against the repository's real default/integration branch.

## Actual Behavior
Every categorization decision that depends on `$default_branch` (`SAFE_TO_DELETE`, `SQUASH_MERGED` detection, and the newer `STALE_REBASE_BACKUP_TAG` reachability check) is evaluated against the coincidental local `main` branch instead. If that branch happens to already contain a tag's commit as an ancestor, a genuinely non-redundant rebase-backup tag could be misclassified as safe to delete.

## Impact
**Medium** — Live-verified (see Additional Context) that the straightforward version of this scenario does *not* actually misfire in practice, since an unrelated coincidental `main` branch is unlikely to already contain the tag's commit. The gap is real and architecturally worth closing, but the realistic exploit path requires an additional, unlikely coincidence beyond just "no `origin/HEAD` is configured" — not an easily-triggered data-loss bug. Scored Medium (workaround exists: keep `origin/HEAD` configured) rather than Critical/High.

## Additional Context
This is a pre-existing gap in `phase1-analysis.sh`'s default-branch resolution (`default_branch="${default_branch:-main}"`), shared by the skill's entire branch-categorization logic — not something introduced by the `delete-rebase-backup-tags.sh` rebase-backup-tag feature added in PR #262, which only reuses the same already-existing `$default_branch` value.

A proper fix means resolving the real default branch more robustly when `origin/HEAD` is unset (e.g. probing `main`/`master`/`develop` with an explicit, documented policy, or refusing to categorize until the default branch is confirmed) across both `phase1-analysis.sh` and `delete-rebase-backup-tags.sh` — broader in scope than PR #262's own feature, so it was deliberately deferred rather than folded into that PR.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/262
- **Head SHA at time of finding**: `9b34d40feac0933ddbef306bb47bdc567b6c25eb`
- **Review thread/comment URL**: N/A — found via a local `cross-model-review` pass (round 5, pre-merge), not posted as a GitHub PR review comment
- **Reviewer**: Codex (fresh-eyes + independent Phase 2 re-derivation), corroborated by Claude (Phase 2 challenger pass, which also live-verified the realistic exploit path and corrected the severity from Codex's original "critical")
- **Stated severity**: Codex: critical (Phase 1) / major (independently re-derived, Phase 2); Claude Phase 2: major, with live-verification narrowing the realistic exploit path — see Impact above
