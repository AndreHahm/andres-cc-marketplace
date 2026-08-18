# Why the throwaway index is seeded with a copy, not a fresh reseed

Extracted from SKILL.md's Inputs section per plugin-rulebook's R13 (SKILL.md grew past the 500-line
Critical threshold). SKILL.md keeps the ordering-critical warning (capture `$REAL_INDEX` before
exporting `GIT_INDEX_FILE`) and the `umask 077` requirement; this file holds the fuller "why a copy,
not a from-scratch reseed" rationale.

A fresh `GIT_INDEX_FILE` starts genuinely empty. Two distinct kinds of already-tracked file lose
their real status against an empty (or freshly-reseeded) index, both misreporting as **deleted**
rather than modified against `$MERGE_BASE`:

- **A gitignored-but-tracked file.** An empty index doesn't know the file is tracked, so `git add -N`
  refuses to add it (git won't add a new path matching an ignore rule), dropping it from the index
  entirely.
- **A sparse-checkout entry.** A from-scratch reseed like `git read-tree HEAD` populates the index
  from the tree, but doesn't preserve `skip-worktree` flags — the bits that tell git a tracked file
  is intentionally absent from the sparse working copy. Without them, the reseeded index expects the
  file on disk, and diffs it as deleted the moment it isn't there. Reproduced: `git update-index
  --skip-worktree` on a file, then `rm` it from the sparse working tree — the real `git diff HEAD`
  correctly shows nothing for that file, but a `git read-tree HEAD`-based reseed reports it `D`.

A byte-for-byte copy of the real index (`git rev-parse --git-path index` for the path) preserves
both — it isn't reconstructing state from a tree, it's carrying the real index's own tracked/ignored
status and `skip-worktree` flags over unchanged. Confirmed empirically for both scenarios: the copy
matches the real `git diff` output exactly, where a from-scratch reseed diverges on each.

`umask 077` matters because a plain file created by `cp`/`git` inherits the process umask, unlike
`$RUN`'s `mktemp -d` (which git-kit's own conventions already treat as 0700 by default) — without it,
the copied index can land world-readable (0644 in a default-umask reproduction), exposing repo
filenames and object IDs on a shared machine for as long as the file persists (see the closing note
on why it isn't deleted either).
