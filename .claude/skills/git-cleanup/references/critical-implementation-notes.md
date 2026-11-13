# Critical Implementation Notes

### Squash-Merged Branches Require Force Delete

**IMPORTANT:** `git branch -d` will ALWAYS fail for squash-merged branches because git cannot detect that the work was incorporated. This is expected behavior, not an error.

When you identify a branch as squash-merged:
- Plan to use `git branch -D` (force delete) from the start
- Do NOT try `git branch -d` first and then ask again for `-D` - this wastes user confirmations
- In the confirmation step, show `git branch -D` for squash-merged branches

### Thorough PR History Investigation

Don't rely on simple keyword matching. For `[gone]` branches:

```bash
# 1. Get the branch's commits that aren't in default branch
git log --oneline "$default_branch".."$branch"

# 2. Search default branch for PRs that incorporated this work
# Search by: branch name, commit message keywords, PR numbers
git log --oneline "$default_branch" | grep -iE "(branch-name|keyword|#[0-9]+)"

# 3. For related branch groups, trace which PRs merged which work
git log --oneline "$default_branch" | grep -iE "(#[0-9]+)" | head -20
```

### Rebase-Backup Tag Reachability (Safety Rule 10)

Why each part of Safety Rule 10's check exists. Rebasing rewrites commit SHAs in the merged case (a merged
branch's current tip being an ancestor of the default branch says nothing about whether the tag's own
pre-rebase commit is), so raw-SHA ancestry alone is not enough; the fallback is a per-path,
per-blob-and-mode history search: every path each of the tag's own commits changed must have that exact
post-image blob AND mode somewhere in the default branch's own history at that same path. A plain deletion
is the exception: it requires the path to be absent from the default branch's current tree, not merely
deleted at some point after the merge-base.

- **Exact content:** Git blobs are purely content-addressed, so this is already exact byte-for-byte
  equality with no whitespace-insensitivity to guard against.
- **Per path, not per commit:** unlike an earlier version that required one single commit on the default
  branch to reproduce a tag commit's entire diff byte-for-byte, it recognizes content the default branch's
  own history reorganized into a different commit grouping than the tag recorded.
- **Mode as well as blob, literal paths:** unlike an earlier version of this redesign itself, it also
  catches a mode-only change (`chmod +x`, or a file/symlink swap with identical blob bytes) that never
  landed, and matches every path literally rather than as a pathspec glob.
- **Bounded to the merge-base:** the history search covers commits at or after the tag's own merge-base
  with the default branch. An unbounded full-history search is a real false positive, not just
  theoretical: a path added then deleted from the default branch entirely BEFORE the branches diverged,
  then coincidentally re-added with byte-identical content on the tag's own branch, would otherwise match
  that stale pre-divergence state and be reported reachable even though the default branch never actually
  restored it after diverging.
- **Merges diffed against each parent:** a merge commit inside the tag's own history is diffed against
  EACH parent separately (`git diff-tree -m`), not treated as a special trivial-or-unverifiable case. An
  earlier version used `--cc` (which only shows a path differing from every parent) to decide whether a
  merge was "trivial" and safe to skip, but that's blind to a merge that force-resolves to exactly one
  parent's state for a path - invisible to `--cc` by definition, even when it represents real,
  unrecoverable content loss relative to the OTHER parent (live-verified: a scratch-repo merge that drops a
  file matching one parent exactly reported "reachable" under the old check even though the default branch
  still had that file).

See `delete-rebase-backup-tags.sh`'s own `is_tag_content_reachable`/`is_path_blob_reachable` for the full
mechanism, including its fail-closed handling of merge commits and `git diff-tree` failures.
