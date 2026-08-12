# Testing & Validation

**Verify this skill activates on:**
- "clean up my old branches and worktrees"
- "I have a bunch of stale branches, help me clean up"

**Verify it does NOT activate on:**
- "delete this one specific branch" without a broader cleanup context
- automated/headless invocation — this skill requires two user confirmations and is not designed for
  non-interactive use

**Verify Phase 4's gitignored-content detection:**
- A worktree whose only content is gitignored (e.g. a local `.env`, nothing else uncommitted) — confirm
  Phase 4 warns with the "Ignored (not tracked by git, will also be deleted):" block, rather than reporting
  the worktree as clean because `git status --porcelain` alone found nothing
- A worktree with both tracked-dirty and gitignored content — confirm both warning blocks appear together,
  clearly separated
- A worktree with neither — confirm no warning fires and the worktree proceeds through normal
  categorization

**Quality gates:**
- [ ] Phase 4 always runs `--ignored` alongside the plain `--porcelain` check for every worktree, never
      only one or the other
- [ ] A long ignored-file list (e.g. `node_modules/`) is summarized (top-level entries + count), never
      dumped in full and burying the warning
- [ ] `git clean` is never invoked at any point in this skill — detection only, never deletion of untracked
      or ignored content
- [ ] Safety Rule 5's "dirty" always includes gitignored content, not just tracked/untracked-but-not-ignored
      changes
