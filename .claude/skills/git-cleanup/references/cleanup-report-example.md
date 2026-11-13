# Cleanup Report Example (Phase 6)

The shape of the report Phase 6 prints once Phase 5 has run: what was deleted, by category, and what remains.

```markdown
## Cleanup Complete

### Deleted
- fix/typo
- feat/login
- feat/api
- feat/api-v2
- feat/api-refactor
- feat/api-final
- Worktree: ../proj-auth
- Remote branch (stale, Phase 3.5): feat/old-worktree-feature
- Rebase-backup tag (stale, Phase 3.6): feat/gone-branch-rebase-backup-20260701-093000

### Remaining (4 branches)
| Branch | Status |
|--------|--------|
| main | current |
| wip/new-feature | active work |
| experiment/old | needs review |
```
