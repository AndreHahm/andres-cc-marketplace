## Summary
`scripts/marketplace_ci/sync.py`'s `COMPONENT_DIRS = ("skills", "agents", "commands", "hooks", "rules")` deliberately excludes plugin-level `scripts/` directories -- meaning `plugins/<name>/scripts/*` is never auto-synced into `.claude/` and never covered by `marketplace_ci check-all`'s parity check. All 4 registered plugins (`plugin-devkit`, `git-kit`, `analysis-kit`, `codex-kit`) have a plugin-level `scripts/` directory, so this is a repo-wide blind spot, not a git-kit-specific one.

## Environment
- **Product/Service**: `scripts/marketplace_ci/sync.py` (this repo's own plugin-mirror sync/parity tooling)
- **Region/Version**: this repo, branch `fix/git-kit-downstream-qa`, PR #121

## Reproduction Steps
1. Modify or add a file under `plugins/git-kit/scripts/` (e.g. this PR's own `lint-staged-python.sh`/`unstage-flagged-files.sh`, or an update to `scan-staged-files.sh`).
2. Run `uv run python -m scripts.marketplace_ci sync-plugin-mirrors` and `uv run python -m scripts.marketplace_ci check-all --staged`.
3. Observe: neither command touches, creates, or flags anything under `.claude/scripts/` -- `sync-plugin-mirrors` reports `0 action(s)` even when `plugins/git-kit/scripts/` content has genuinely diverged from `.claude/scripts/`'s existing copy.
4. Confirmed live in this PR: `.claude/scripts/scan-staged-files.sh` had silently drifted to a stale pre-this-session version (missing `--null` mode and path-segment matching added in commit `a5ec301`), and `.claude/scripts/unstage-flagged-files.sh`/`lint-staged-python.sh` (both new files this session) didn't exist under `.claude/scripts/` at all -- found only by Codex's automated PR review (round 2), not by this repo's own tooling.

## Expected Behavior
Either (a) `plugins/<name>/scripts/` is a registered, auto-synced, parity-checked mirror component like `skills`/`agents`/`commands`/`hooks`/`rules` already are, or (b) if plugin-level scripts are deliberately meant to live only under the canonical `plugins/<name>/` tree (no `.claude/` mirror expected), then `.claude/scripts/` should not exist as an apparent partial mirror at all -- its current state (a mix of real mirror content and unrelated utility scripts, some stale) is ambiguous about which regime it's actually under.

## Actual Behavior
`.claude/scripts/` exists, contains what look like mirror copies of at least 2 of git-kit's plugin-level scripts (`scan-staged-files.sh`, `write-git-kit-marker.sh`) alongside unrelated content, and none of it is kept in sync or checked for parity by the tooling that handles every other component type. A canonical-source edit can silently diverge from its `.claude/` counterpart indefinitely with no tooling signal.

## Impact
**Medium** -- whether this causes a *live* runtime failure depends on whether `${CLAUDE_PLUGIN_ROOT}` (as referenced in skill instructions like `.claude/skills/commit/SKILL.md`'s `${CLAUDE_PLUGIN_ROOT}/scripts/...`) ever resolves against the `.claude/` tree for a primary-checkout-mirrored skill dispatch -- not independently confirmed in this session (see Additional Context). Independent of that question, this is a confirmed, real staleness/consistency gap: this repo's own parity discipline (`check-all --staged`, enforced on every `commit` skill invocation) has a blind spot for an entire component type that exists in every registered plugin.

## Additional Context
Found by Codex's automated PR review (round 2, `@codex full review`) on PR #121, as two related P1 findings: (1) the 2 new scripts this PR added were committed non-executable (100644) despite being invoked directly -- fixed directly in this PR (`6ae2115`); (2) `.claude/scripts/`'s stale/missing copies of those same scripts -- also fixed directly in this PR by manually syncing the 3 affected files, since that fix was small, safe, and clearly in-scope for the files this PR itself touches.

**This issue covers the broader, structural question the manual fix didn't address**: should `scripts/marketplace_ci/sync.py`'s `COMPONENT_DIRS` include `scripts` (or some scoped subset of it) so this class of drift is caught automatically going forward, for all 4 plugins, not just re-discovered ad hoc per plugin when a reviewer happens to notice? This wasn't fixed here because:
- It's a shared-tooling change (`scripts/marketplace_ci/sync.py`) affecting all 4 registered plugins' sync/parity behavior at once, not a git-kit-scoped fix.
- It needs its own audit first: does every plugin's `.claude/` tree already have a partial/stale `scripts/` mirror like git-kit's, or is git-kit's `.claude/scripts/` actually an unrelated, pre-existing directory that happens to share some filenames? (`.claude/scripts/` also contains `cancel-skill-improver.sh`, `cleanup-scratchpad.sh`, `lib.sh`, `setup-skill-improver.sh` -- not obviously git-kit-owned, suggesting `.claude/scripts/` may be a shared/general-purpose directory, not a per-plugin mirror target, which would need resolving before deciding how `COMPONENT_DIRS` should change.)
- Whether `${CLAUDE_PLUGIN_ROOT}` genuinely resolves against `.claude/` for a primary-checkout-mirrored skill (which would make this a live bug, not just a staleness one) is itself unconfirmed and worth investigating as part of scoping the real fix.

**To close, in a future session**: (1) confirm what `.claude/scripts/` actually is and which files in it are genuinely per-plugin mirror targets vs. unrelated content; (2) confirm whether `${CLAUDE_PLUGIN_ROOT}` resolution makes this a live runtime bug or "only" a tooling/consistency gap; (3) decide and implement the right fix to `COMPONENT_DIRS` (or an explicit documented exception, matching R19's existing exception model) so this doesn't require a reviewer to notice it again for `plugin-devkit`, `analysis-kit`, or `codex-kit`.
