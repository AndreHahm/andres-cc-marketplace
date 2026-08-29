## Summary
A root-finder's fallback used a hardcoded relative-parent-depth assumption (`start.parents[2]`) that correctly located the repo root for one mirrored copy of a skill but broke for the other — the two copies sit at different depths from the repo root, so a single fixed depth can't serve both.

## Environment
- **Product/Service**: `analysis-kit` plugin — `mining-review-learnings`'s `scripts/smoke_test.py` (`PLUGIN_ROOT` fallback)
- **Region/Version**: this repo, found during PR #179 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Run the smoke test from an environment where `.git` is absent (the fallback path), for both the `.claude/skills/mining-review-learnings/` mirror copy and the `plugins/analysis-kit/skills/mining-review-learnings/` canonical copy.
2. For the `.claude/` copy, `start.parents[2]` correctly resolves to the repo root.
3. For the `plugins/analysis-kit/` copy, the same fixed depth (`start.parents[2]`) resolves to `<repo>/plugins` instead — one directory too shallow, since the canonical copy sits one level deeper than the `.claude/` mirror.
4. `PLUGIN_ROOT` becomes an invalid path for the canonical copy specifically.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| A fixed relative-parent-depth (`.parents[2]`) locates the repo root the same way for every mirrored copy of a script | The two mirrored copies of the same script sit at different depths from the repo root, so one fixed depth is correct for only one of them |

## Expected Behavior
A root-finder's fallback should not assume a fixed relative-parent-depth applies uniformly to every mirrored copy location — it should walk up looking for a directory containing known markers (e.g. both `plugins/` and `.claude/`), which stays correct regardless of how deep any particular copy sits.

## Actual Behavior
The fallback was correct for one mirror copy and silently wrong for the other, in exactly the `.git`-absent environment the fallback exists to handle.

## Impact
[Severity: Medium] A structural smoke test with a broken fallback for one of its own two mirrored locations undermines confidence in the check across environments without `.git`. Fixed in `analysis-kit`'s PR #179 (commit `3a7a5b5`): `_find_repo_root`'s fallback now walks up looking for a directory containing both `plugins/` and `.claude/` (depth-independent) before falling back to the old fixed `parents[2]`, verified correct for both the plugin-copy and mirror-copy depths via a standalone synthetic-directory test.

## Additional Context
Mined from PR #179's own review history (`coderabbitai[bot]`; 25 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #179` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/179#discussion_r3885947287
