## Summary
A "stage the generated destination when its source is staged" mechanism generated content from working-tree bytes rather than the staged index, so a source with unstaged changes on top of what's staged produced a destination that didn't match the staged source — and the same gap recurred per-contributor when several sources merge into one generated artifact.

## Environment
- **Product/Service**: this repo's own `scripts/marketplace_ci` — `sync.py`'s `stage_generated_destinations`/hooks-merge staging
- **Region/Version**: this repo, found during PR #159 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. **Single-source case**: Stage a canonical source file, then make an *additional*, unstaged edit on top of it (partial staging).
2. Run `sync-plugin-mirrors --stage`, which regenerates the mirrored destination from the source's current *working-tree* bytes (including the unstaged edit) and stages it because the source itself is staged.
3. The staged destination now reflects content beyond what's actually staged for the source, so `check_staged_parity` rejects the commit.
4. **Multi-source case**: When two plugins' `hooks.json` files merge into one generated `.claude/hooks/hooks.json`, stage one contributor fully and leave a second contributor with unstaged edits.
5. `plan_hooks_merge` builds `merged_document` from the working-tree contents of *both* sources; the staging condition accepts the first staged contributor and stages the whole merge, silently including the second (dirty) contributor's unstaged content.

## Expected Behavior
A "regenerate and stage a derived artifact when its source(s) are staged" mechanism must confirm every contributing source has no unstaged changes on top of what's staged (not just "is staged at all") before staging the derived artifact — checked per-contributor when multiple sources merge into one output.

## Actual Behavior
Both cases allowed a generated/merged artifact to be staged from content beyond what was actually staged for its source(s), silently including working-tree changes never reviewed as part of the commit.

## Impact
[Severity: Medium (single-source) / High (multi-source, since it can silently include another plugin's unreviewed hook behavior)] Fixed in `git-kit`/`scripts/marketplace_ci`'s PR #159 (commits `8d1df09`, `b3d7107`): added `_is_fully_staged()`, used both for the single-source case (skip staging the destination when the source has unstaged changes on top of what's staged, covered by a new test) and the multi-source hooks-merge case (require every resolvable contributor to pass `_is_fully_staged` before staging the merge at all — reproduced the exact two-contributor scenario first, then confirmed the fix leaves the merged destination unstaged, covered by a new test).

## Additional Context
Mined from PR #159's own review history (`coderabbitai[bot]`, `chatgpt-codex-connector[bot]`; 19 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #159` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/159#discussion_r3878624145, https://github.com/AndreHahm/andres-cc-marketplace/pull/159#discussion_r3878835365
