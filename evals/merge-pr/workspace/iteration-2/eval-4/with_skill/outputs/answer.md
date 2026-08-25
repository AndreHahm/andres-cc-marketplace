# merge-pr Step 7 — Scenario Walkthrough (Simulated, no real gh/git calls)

## Scenario recap

- `merge_auto_delete_branch` = `true`
- `isCrossRepository` (from step 1) = `true` — PR #150 came from a contributor's fork
- Ran (conceptually): `gh pr merge 150 --rebase --delete-branch` → exited **non-zero**, stderr:
  `fatal: 'main' is already used by worktree '/repo'`
- Already checked: `gh pr view 150 --json state,mergeCommit` → `state` is `MERGED`

## What I do next, in order

1. **Don't treat the non-zero exit as a merge failure.** Step 7 is explicit that a local
   side effect — exactly this `fatal: '<default>' is already used by worktree ...` error
   when `gh` tries to check out the default branch locally after `--delete-branch` — can
   fail the CLI command even though the remote merge already succeeded. This is also the
   exact scenario step 5's confirmation note warns the user about in advance.

2. **Trust the state check I already ran, per the skill's own precedence rule.** Since
   `gh pr view 150 --json state,mergeCommit` shows `state: MERGED`, I treat the merge as a
   success and continue into the "branch-delete/report path" rather than reporting a
   failure. I'd also pull the `mergeCommit` value out of that same JSON to report the
   merge commit SHA in the final summary — no second call needed since I just made this
   one immediately before the side-effecting decision (the rebase/merge command itself is
   the side effect; the state check is the re-verification of its outcome, done right
   before I act on it, not reused from some earlier step).

3. **Check `isCrossRepository` before doing anything about branch deletion.** This is the
   decision point in step 7 that actually changes what happens next:
   - `merge_auto_delete_branch` is `true`, so ordinarily (same-repo case) I'd need to
     verify the remote branch is actually gone, since the local worktree-checkout error
     can silently skip the remote deletion too.
   - But `isCrossRepository` is `true` here. Per step 7: *"If `isCrossRepository` is
     `true` (the PR came from a fork), never run the `git ls-remote`/`gh api -X DELETE`
     fallback at all... report that the branch lives in the contributor's fork and isn't
     this skill's to delete, whether or not the local `--delete-branch` step failed."*

4. **Report the result** (no further tool calls): merge succeeded via rebase, merge commit
   from the `mergeCommit` field, and branch deletion was skipped because the head branch
   lives in the contributor's fork — not something this skill deletes, regardless of
   whether the local `--delete-branch` half of the command failed.

5. **Proceed to step 8** — ask via `AskUserQuestion`: "Run `finishing-work` now to sync
   local `main` and check for cleanup?" (Yes/No). This always runs after a successful
   merge, independent of the cross-repo branch-deletion question above. If the user says
   yes, I'd invoke `Skill(git-kit:finishing-work)` bound to PR #150 specifically, not a
   re-resolved "current branch" PR.

## Do I ever run `git ls-remote --heads origin <headRefName>` or `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>` in this scenario?

**No — neither command runs, in any form, at any point.**

Both of those commands are the *same-repo* fallback path (`isCrossRepository == false`),
used to confirm/finish a remote branch deletion when the local `--delete-branch` step hit
the worktree-checkout error. Step 7 is unambiguous that this fallback is gated on
`isCrossRepository` being `false`, and separately, explicitly instructs never running it
when `isCrossRepository` is `true`.

The reason isn't just "the skill says so" — it's a correctness issue with what those two
commands actually target:

- `git ls-remote --heads origin <headRefName>` and
  `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`

both resolve `origin` / `{owner}/{repo}` to **this repository**, not the contributor's
fork the PR's head branch actually lives in. A fork PR's `headRefName` (e.g. `main`, or
any other name) is a branch *in the fork*, not in this repo. If I ran either command here:

- `git ls-remote --heads origin <headRefName>` would be querying *this repo's* refs for a
  branch name that happens to be borrowed from the fork's naming — e.g. if the fork's
  branch were literally named `main`, this would check whether *this repository's own
  `main`* still exists, which is a nonsensical/misleading check that has nothing to do
  with whether the fork's branch is gone.
- `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>` would be even worse: it
  would attempt to **delete a ref in this repository** under that same borrowed name — in
  the worst case, deleting a real, unrelated branch (or `main` itself) that just happens to
  share the fork's branch name. This is exactly the misdirected-deletion risk the skill's
  `isCrossRepository` guard exists to prevent.

So in this scenario the correct — and only — action regarding the branch is to report that
it lives in the contributor's fork and is not this skill's to delete, and skip both
commands entirely, independent of whether the local `--delete-branch` step succeeded or
hit the worktree-checkout error.
