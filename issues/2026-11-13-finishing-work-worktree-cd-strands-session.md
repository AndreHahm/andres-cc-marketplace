## Summary
git-kit `finishing-work` step 5 says to flag a leftover worktree "especially if it has uncommitted changes" but gives no command for checking it, so an agent can `cd` into the worktree, which rebinds the session to it and blocks `/git-cleanup`.

## Environment
- **Product/Service**: git-kit `finishing-work` skill (`plugins/git-kit/skills/finishing-work/SKILL.md` and its `.claude/skills/finishing-work/SKILL.md` mirror, step 5, lines ~94-98)
- **Region/Version**: `main` at `33ff1155`
- **Browser/OS**: Linux, Claude Code CLI

## Reproduction Steps
1. Merge a PR whose branch has its own worktree under `.claude/worktrees/<name>`.
2. From a session started in the primary checkout, run `/finishing-work <PR>`.
3. At step 5, check the leftover worktree for uncommitted changes with `cd .claude/worktrees/<name> && git status --porcelain` (the step does not name a command).
4. Run `/git-cleanup`.

## Expected Behavior
Step 5 checks the other worktree without changing the session's working directory, and `/git-cleanup` runs in the same session.

## Actual Behavior
- After the `cd`, the harness rebinds the session's primary working directory to the worktree and tells the agent not to `cd` back to the repository root.
- `/git-cleanup` refuses in a worktree-bound session (its own When NOT to Use), so the agent tells the user to start a fresh session.
- The `ExitWorktree` tool is a no-op here: it only reverses a worktree entered with `EnterWorktree`.
- Observed 2026-11-13 while finishing PR #716: a later Bash call that ran `cd` to the primary checkout rebound the session back, so the session was recoverable, but only by doing what the harness had told the agent not to do.

## Error Details
~~~
ExitWorktree: No-op: there is no active EnterWorktree session to exit.
~~~

## Impact
**Medium** - the post-merge cleanup flow stalls in the same session and the user is sent to a fresh session; workaround exists (fresh session, or a `cd` back to the primary checkout).

## Additional Context
Proposed fix:
- Step 5 names `git -C <worktree-path> status --porcelain` (and `--ignored` if relevant) as the check, and states never to `cd` into the worktree, since that rebinds the session.
- Apply the same edit to both copies (`plugins/git-kit/` and the `.claude/` mirror).
- `git-cleanup` Phase 4 already uses `git -C <worktree-path>`; consider the same explicit "don't `cd`" note there.

Related but separate: #707 (dirty-worktree Stop hook false positive on rebase/squash-merged branches) fired repeatedly in the same session, because the worktree's commits were on `main` only under new SHAs.
