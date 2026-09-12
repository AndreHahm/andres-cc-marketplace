## Summary
`git-cleanup`'s rebase-backup tag reachability check reports a tag as "not reachable" even when its content is fully and verifiably present in the default branch, if the tag's own branch merged the default branch back in mid-development and continued editing the same file

## Environment
- **Product/Service**: `plugins/git-kit/skills/git-cleanup/scripts/delete-rebase-backup-tags.sh` — functions `is_tag_content_reachable`, `is_path_blob_reachable`, `check_diff_records`
- **Region/Version**: this repo (`andres-cc-marketplace`)

## Reproduction Steps
1. Create a feature branch, commit a change to a shared file (e.g. add a section to `.codacy.yml`).
2. Separately, on the default branch, add a *different* section to the same file, in an earlier commit than the feature branch's merge below.
3. Merge the default branch back into the feature branch (bringing in that earlier default-branch section) and continue development.
4. Land the feature branch's own original change on the default branch too (e.g. via its own PR/commit), so the default branch now has both sections — but added in the opposite order from how the feature branch acquired them.
5. Run `delete-rebase-backup-tags.sh --list` (or the `git-cleanup` skill's Phase 3.6) against a rebase-backup tag on the feature branch.

## Expected Behavior
The tag should be reported reachable/safe-to-delete, since its final content for the shared path is byte-identical to the default branch's current content.

## Actual Behavior
The tag is reported "not reachable" and left for manual review.

Root cause: `is_tag_content_reachable()` walks each of the tag's own unique commits (`mb..tag`) individually and requires each commit's own resulting per-path blob to independently match some blob in the default branch's history at that same path (via `is_path_blob_reachable`/`check_diff_records`). When a branch merges the default branch back into itself mid-development and keeps editing the same file, an earlier commit's blob reflects only that commit's own edit — without the content the later merge brought in — and the default branch's own history may never have passed through that same intermediate, partial state, even though the branch's FINAL state for that path is identical to the default branch's current state.

Live-verified in this repo, 2026-09-11/12, during a real `/git-cleanup` run: tag `feat-analysis-kit-new-dimensions-rebase-backup-20260910-194109` was reported "not reachable". Investigation:
- Blocking commit: `c4690df1` "fix(ci): exclude plugin test suites from Codacy security scanning" (touches `.codacy.yml`).
- Its merge-base with main is `8e45ea17` ("ci(codacy): exclude the .claude/ mirror tree from scanning").
- The tag's branch later merged main back in (commit `341bcc7f`, "chore: merge main and resolve .codacy.yml conflict"), whose second parent is `8e45ea17`.
- Manually diffed the tag's FINAL `.codacy.yml` (at tip commit `453bf31a`) against main's CURRENT `.codacy.yml`: byte-identical (confirmed with `diff`, no output).
- But `c4690df1`'s own post-image blob for `.codacy.yml` (`d3f42344...`) never appears anywhere in main's own `.codacy.yml` history, because main added the same two pieces of content (mirror-tree exclusion, then plugin-test-suite exclusion) in the opposite order from the tag branch (which added the plugin-test-suite exclusion first, then merged in the mirror-tree content). Neither branch's intermediate state matches the other's at any single commit — only the final states converge.

This is distinct from the merge-vs-`--cc` gap already fixed in PR #315 — that fix was about diffing a merge commit against each parent instead of `--cc`; this gap is about per-commit blob matching not accounting for cross-branch edit reordering.

## Error Details
~~~
--- feat-analysis-kit-new-dimensions-rebase-backup-20260910-194109 (branch: feat-analysis-kit-new-dimensions) ---
branch status: no longer exists locally
reachable from main: NO -- this tag may be the only remaining copy of its commits
~~~

## Visual Evidence
N/A

## Impact
**Medium** — this is a false negative only (the script never deletes something it shouldn't; its fail-closed design is preserved). But safe-to-delete rebase-backup tags can get stuck in "needs manual review" indefinitely whenever their originating branch merged the default branch back in mid-development, which is a common workflow pattern (long-running branches routinely sync with the default branch). Left unfixed, these tags accumulate and require manual, per-tag investigation (as done here) to confirm they're actually safe to remove.

## Additional Context
Found 2026-09-12 while running `/git-cleanup` after merging PR #315 (`git-cleanup`'s own merge-commit reachability fix). Five rebase-backup tags were left for manual review; manual investigation confirmed at least one (`feat-analysis-kit-new-dimensions-...`) is a genuine false negative caused by this gap, distinct from the other four tags in that batch, which appear to be either genuinely unreachable work or too heavily reorganized to verify by any per-path content check.

Suggested fix (not prescriptive): in addition to the existing per-commit check, also check whether the tag's own FINAL blob at a path (the tip commit's state) matches the default branch's CURRENT blob at that path. This is a cheap, sufficient additional check that would catch this exact case without weakening the existing per-commit checks — those would still run for paths where the final-state shortcut doesn't apply (e.g. a path deleted after the tag's tip but changed somewhere in the unique-commit range).
