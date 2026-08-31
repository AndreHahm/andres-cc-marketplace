## Git Cleanup Analysis

### Related Branch Groups

**Group: feat/api-* (4 branches)**
| Branch | Status | Evidence |
|--------|--------|----------|
| feat/api | Superseded | Work merged in PR #29 |
| feat/api-v2 | Superseded | Work merged in PR #45 |
| feat/api-refactor | Superseded | Work merged in PR #67 |
| feat/api-final | Superseded | Older iteration, diverged |

Recommendation: Delete all 4 (work is in main)

---

### Individual Branches

**Safe to Delete (merged with -d)**
| Branch | Merged Into |
|--------|-------------|
| fix/typo | main |

**Safe to Delete (squash-merged, requires -D)**
| Branch | Merged As |
|--------|-----------|
| feat/login | PR #42 |

**Needs Review ([gone] remotes, no PR found)**
| Branch | Last Commit |
|--------|-------------|
| experiment/old | abc1234 "WIP something" |

**Stale remote-only branch (merged PR, remote never deleted)**
| Branch | Merged As | Evidence |
|--------|-----------|----------|
| feat/old-worktree-feature | PR #41 | `gh pr view` confirms `state: MERGED`; no local branch remains |

**Keep (active work)**
| Branch | Status |
|--------|--------|
| wip/new-feature | 5 unpushed commits |

**Stale rebase-backup tag (originating branch gone or merged, content verified reachable)**
| Tag | Branch | Branch Status |
|-----|--------|----------------|
| feat/old-feature-rebase-backup-20260701-093000 | feat/old-feature | no longer exists locally; reachable from main: yes |

**Needs Review (rebase-backup tag, branch gone, content NOT verified reachable)**
| Tag | Branch | Why it's not auto-deletable |
|-----|--------|------------------------------|
| feat/orphan-risk-rebase-backup-20260101-150000 | feat/orphan-risk | Branch no longer exists locally, and `git merge-base --is-ancestor` shows the tag's commit is NOT reachable from main — this tag may be the only remaining copy of that work |

### Worktrees
| Path | Branch | Status |
|------|--------|--------|
| ../proj-auth | feat/auth | STALE (merged) |
| ../proj-billing | feat/billing | DIRTY (uncommitted + ignored content) |

```
WARNING: ../proj-billing has uncommitted changes:
  M  src/billing.js

Ignored (not tracked by git, will also be deleted):
  .env

These changes will be LOST if you remove this worktree.
```

---

**Summary:**
- 4 related branches (feat/api-*) - recommend delete all
- 1 merged branch - safe to delete
- 1 squash-merged branch - safe to delete
- 1 needs review
- 1 to keep
- 1 stale rebase-backup tag - safe to delete

Which would you like to clean up?
