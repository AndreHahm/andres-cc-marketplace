## Summary
A mechanism deciding whether to re-stage a derived/generated artifact iterated "current files" (files that exist on disk right now) to find contributing sources — so a staged deletion of a contributing source was invisible to it, since a deleted file has no "current file" to enumerate, leaving the regenerated artifact un-staged and silently retaining the deleted contributor's content.

## Environment
- **Product/Service**: this repo's own `scripts/marketplace_ci` — `sync.py`'s hooks-merge staging (`stage_hooks_merge_result`)
- **Region/Version**: this repo, found during PR #159 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Register two plugins that each contribute a `hooks.json` merged into one generated `.claude/hooks/hooks.json`.
2. Stage a deletion of one contributing plugin's `hooks.json` (`git rm plugins/<name>/hooks/hooks.json`).
3. Re-plan against the now-current registry (as the CLI actually does) and run `sync-plugin-mirrors --stage`.
4. The "current files" tuple this logic scans no longer contains the deleted source at all — so the staging decision, built only from files that currently exist, can't recognize the deletion happened.
5. The regenerated merged artifact is left un-staged, so the commit records the canonical deletion while the generated `.claude/hooks/hooks.json` still contains the deleted plugin's hook behavior.

## Expected Behavior
A mechanism deciding whether to re-stage a derived/generated artifact must check staged deletions explicitly against git's own staged-paths state (`GitState.staged_paths()`), not rely solely on enumerating files that currently exist — a deletion has no "current file" to enumerate, so it needs its own separate check.

## Actual Behavior
`check_staged_parity` deliberately excludes top-level plugin hook manifests from its own check, so nothing else caught this either — the commit skill's own staged-parity step still succeeded and committed the canonical deletion while retaining the removed hook in the generated configuration.

## Impact
[Severity: Medium] Silently retained hook behavior from a plugin that was just deleted from the registry — a correctness/consistency gap that wouldn't surface until the retained hook actually ran unexpectedly. Fixed in `git-kit`/`scripts/marketplace_ci`'s PR #159 (commit `b3d7107`): added a check against `GitState.staged_paths()` for a staged deletion whose old path matches the plugin-hooks-source shape (`plugins/<name>/hooks/hooks.json`) or the repo-level default path, as a separate signal alongside the main per-source loop. Reproduced the exact scenario (delete one of two contributors, re-plan against the now-current registry) before fixing, confirmed the merge now gets staged, covered by a new test.

## Additional Context
Mined from PR #159's own review history (`chatgpt-codex-connector[bot]`; 19 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #159` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/159#discussion_r3878835372
