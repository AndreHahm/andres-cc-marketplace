# Orphaned Worktree: Don't Trust Git Reads Alone After Removal

## When this applies

Any point in a session where a worktree the session's cwd was pointed at gets removed mid-conversation —
via `git-cleanup`, `finishing-work`'s hand-off, or a manual `git worktree remove` — while the session's own
working directory is still set to that now-removed path.

## Rule

After a worktree is removed mid-session while the session's cwd is still pinned to it, do not trust
`git status`/`git log`/`git branch -vv`/`git rev-parse --show-toplevel` output alone as evidence the
session can now operate on `main`. Git's own upward directory search, finding no local `.git` in the
now-empty worktree path, walks up through the parent directories and finds the primary checkout's `.git`
there — every git read then reports the **primary checkout's** real state, which looks exactly like "this
session is now effectively on `main`," but is a read-path accident, not a permission grant.

Before trusting that the session can write to the primary checkout, cross-check with a plain filesystem
listing of the current directory (`ls -la` / `Get-ChildItem`, not git-mediated) — a genuinely orphaned
worktree path shows as empty or containing only a stray `.claude/` folder, which is the tell that the git
output above was a fallthrough illusion. If the listing confirms this, the fix is a genuinely new session
rooted at the primary checkout path, not continuing in the orphaned one — `Write`/`Edit` calls will
continue to be correctly rejected by the worktree-isolation guard (which matches on the literal bound
path, not on where git's fallthrough search happens to land) regardless of how normal the git reads look.

See also [[require-worktree-rooted-absolute-paths]] for the broader, related case: a hand-typed absolute
path to `Read`/`Edit`/`Grep` landing on the wrong checkout at any point in a worktree-bound session, not
just this rule's narrower post-removal git-fallthrough scenario.

## Why

Reproduced twice within a single session (`bb9785ce`, 2026-08-13): after `git-cleanup` removed a worktree
whose branch had just merged, the session's own git reads kept succeeding and reporting the primary
checkout's real, current state, building false confidence that the session was now "on `main`." Both an
eval re-run and a live end-to-end dry run hit the same first-real-write rejection after several git reads
had already succeeded — the block was real and correct, but only surfaced at the point of actual `Write`,
well after the read-path illusion had already taken hold. Documented once as a workaround
(`feedback_orphaned_worktree_after_git_cleanup.md`); recording it here as a rule since a second
independent reproduction in the same session is evidence the workaround alone isn't being applied
reliably without an explicit, citable checkpoint.
