# Route Git Operations Through git-kit's Lifecycle Skills

## When this applies

Any git or GitHub operation in this repo that corresponds to one of git-kit's six lifecycle skills:
starting a new branch or worktree, committing, opening a PR, reviewing/commenting on a PR, merging a PR,
or syncing back to `main` after a merge.

## Rule

Use the matching lifecycle skill instead of the equivalent raw command, in this order:

```
starting-work → commit → create-pr / collaborating-on-a-pr → merge-pr → finishing-work
```

- **Starting new work** → `Skill(git-kit:starting-work)` — syncs `main`, validates the branch name, asks
  worktree vs. plain branch.
- **Committing** → `Skill(git-kit:commit)` — staging review, sensitive-file scan, message confirmation.
- **Opening a PR** → `Skill(git-kit:create-pr)`, or `Skill(git-kit:collaborating-on-a-pr)` when an issue
  should be linked.
- **Reviewing a PR** (approve/comment/request changes) → `Skill(git-kit:collaborating-on-a-pr)` — adds
  CODEOWNERS context `gh-operations`' raw reference commands don't.
- **Merging** → `Skill(git-kit:merge-pr)` — readiness and merge-rights checks before merging.
- **Cleaning up after a merge** → `Skill(git-kit:finishing-work)`, which hands off to `/git-cleanup` for
  the actual branch/worktree deletion.

`git-kit`'s hard-block `PreToolUse` hook enforces the raw-command bypass for `commit`, `create-pr`,
`merge-pr`, `starting-work`'s branch creation, and `collaborating-on-a-pr`'s reviewer actions — this rule
is the discoverable, human-readable statement of that same chain, not a duplicate enforcement mechanism.

## Why

Each of these six skills exists because the equivalent raw command is missing something the skill adds
(sync-before-branch, sensitive-file scanning, CODEOWNERS context, merge-rights verification, cleanup
hand-off) — using the raw command silently skips that safeguard. Without a single place stating the full
chain, each individual skill's own cross-references only cover its immediate neighbors, and the seams
between non-adjacent skills (e.g. why a review action shouldn't go through `gh-operations`) tend to stay
undocumented until a specific gap is noticed and patched one skill at a time.
