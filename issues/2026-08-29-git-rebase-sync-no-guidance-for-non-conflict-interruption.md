## Summary
`git-rebase-sync`'s workflow, Hard Rules, and activation text only account for a clean pick or a real content conflict — it has no documented guidance for a rebase interrupted by a non-conflict failure (e.g. a transient index-write I/O error), and in particular never warns that `.git/COMMIT_EDITMSG` can hold a stale message from an unrelated prior commit at exactly the point the skill's own recovery path would tell you to run `git commit`.

## Environment
- **Product/Service**: `git-kit` plugin, `git-rebase-sync` skill
- **Region/Version**: N/A
- **Browser/OS**: Windows

## Reproduction Steps
Not a single deterministic repro — observed live while resuming a genuinely-interrupted rebase. The general shape:
1. Start a rebase (`git rebase origin/<base>`) on a branch with several commits ahead.
2. Have it fail partway through a `pick` step with a non-conflict error — in this case `error: rebase: Unable to write new index file` (a transient Windows-side I/O failure, not a merge conflict: zero `<<<<<<<`/`=======`/`>>>>>>>` markers in any affected file, confirmed via grep).
3. Run `git rebase --continue` — it reports `you have staged changes in your working tree`, suggesting `git commit --amend` or `git commit` to complete the current step.
4. Check `.git/COMMIT_EDITMSG` at this point — item 2 below requires an unrelated prior (non-rebase) commit to have already populated it; if so, it holds *that* commit's message, not the one belonging to the commit currently being replayed.

## Expected Behavior
`git-rebase-sync`'s documented workflow should cover this failure mode explicitly:
- Guidance for taking over a rebase already in progress (not just one the skill itself started).
- An explicit warning that `.git/COMMIT_EDITMSG` can be stale at a manual-commit recovery step, and the safe fix: `git commit -C <original-commit-sha>` (reuses that commit's own author/date/message, ignoring whatever text is sitting in `COMMIT_EDITMSG`) — never a plain `git commit`/`git commit --no-edit` in this situation.
- A backup-ref procedure that also covers the already-in-progress case, anchored at `.git/rebase-merge/orig-head` (or the equivalent path under a linked worktree's own `rebase-merge/orig-head`) rather than "current HEAD," which is a moving target mid-rebase.
- A spelled-out restore command sequence in the Recovery section, not just "use `{backup_ref}` to restore."

## Actual Behavior
- **Step 2 (Preflight safety checks)** only says: "If `git status` indicates an in-progress merge/rebase/cherry-pick, stop and ask what to do (abort vs continue)" — no further guidance once "continue" is chosen for a non-conflict interruption.
- **Section 6 (Conflict handling loop)** is written entirely around real `<<<<<<<`/`=======`/`>>>>>>>` merge conflicts (open the file, resolve, `git add`, `git rebase --continue`) — it has no branch for "the interruption wasn't a content conflict at all."
- **Step 3 (backup ref)** only says "before starting the rebase" — no coverage for taking over one already in progress, and no mention of `orig-head`.
- **The Recovery section** just says "use `{backup_ref}` to restore the pre-rebase state" with no actual command sequence.
- Nothing in the skill mentions `.git/COMMIT_EDITMSG` staleness at all.

## Error Details
```
error: rebase: Unable to write new index file
hint: Could not execute the todo command
hint:
hint:     pick <sha> # <original commit message>
hint:
hint: It has been rescheduled; To edit the command before continuing, please
hint: edit the todo list first:
hint:
hint:     git rebase --edit-todo
hint:     git rebase --continue
```
followed later, after retrying, by:
```
error: you have staged changes in your working tree
If these changes are meant to be squashed into the previous commit, run:

  git commit --amend '-S'

If they are meant to go into a new commit, run:

  git commit '-S'

In both cases, once you're done, continue with:

  git rebase --continue
```
At this second point, `.git/COMMIT_EDITMSG` held an unrelated, stale commit message — not the message of the commit actually being replayed.

## Impact
[Severity: High] A plain `git commit` or `git commit --no-edit` at the exact recovery step this skill's own procedure would lead an operator to would silently write the *wrong* commit message into permanent, force-pushed history — with no error or warning from git itself to catch it. This is a real, repeatable near-miss (caught only because a human was asked to confirm before the risky step, not because the skill's documented procedure flagged it) rather than a cosmetic gap. The other items (no guidance for taking over an already-in-progress rebase, backup-ref anchoring, missing restore commands, activation coverage) are Minor/advisory documentation-completeness gaps by comparison, bundled here since they surfaced in the same real incident.

## Additional Context
None of this involved actual data loss or a real content conflict — the rebase in question completed correctly and was verified clean afterward (tests, lint, and marketplace-parity checks all passing; the PR's merge state showed clean after a force-with-lease push). The gap is purely that the skill's own documented procedure doesn't yet cover this failure category, so it currently depends on an operator independently noticing the same risk rather than being guided to check for it.

Suggested fix directions (not prescriptive — the skill's own maintainer should decide the exact wording/placement):
1. Add a branch to Section 6 (or a new section) distinguishing "real content conflict" from "non-conflict interruption" (e.g. an index-write failure, an out-of-disk-space error, or anything else that pauses a `pick` without leaving `<<<<<<<` markers).
2. Explicitly document the `COMMIT_EDITMSG` staleness risk and the `git commit -C <sha>` fix at that decision point.
3. Extend Step 3's backup-ref guidance to cover "already in progress" (anchor at `orig-head`), not just "before starting."
4. Spell out the actual restore command sequence in Recovery.
5. Consider adding "resume/recover a failed rebase" as a named activation trigger alongside the existing clean-scenario examples.

## Review Finding Source
- **PR URL:** N/A — not tied to a specific PR review thread; self-caught live during real use of the skill while syncing PR #179 (AndreHahm/andres-cc-marketplace) onto `main`.
- **Head SHA (at time raised):** 8c3d5fe56d91b5066595a5bf0d297e3f122ed8f3
- **Review thread/comment:** N/A — no PR/comment thread to cite; found through direct live usage, not an automated reviewer.
- **Reporter:** Self-caught during this session's own use of `git-rebase-sync`, not a reviewer bot or human reviewer.
- **Stated severity:** High (see Impact)

Found in this repo via live use of `git-rebase-sync` (not tied to a specific PR/issue number to close).
