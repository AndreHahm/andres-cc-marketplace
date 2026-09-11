## Are the gate results at `a1b2c3d` still valid at `e4f5a6b`?

**No — you need to rerun both required checks before merging.**

GitHub's required-status-check mechanism (and the Checks API / Commit Status API underneath it) binds every check result to a specific commit SHA, not to a branch, a PR number, or "the tree contents as of the last check I ran." Branch protection evaluates mergeability by asking "does the *current* HEAD SHA of this PR have a successful run of every required check?" — it does not walk backward through ancestor commits to see if *some* earlier SHA passed.

When you pushed the new commit, the PR's HEAD moved from `a1b2c3d` → `e4f5a6b`. That is a brand-new SHA with no check runs attached to it yet. As far as the merge gate is concerned:

- `Python quality (ruff, ty, pytest)` — pending/missing on `e4f5a6b` until CI runs again on that commit.
- `Publish Codex policy result` — same: the recorded pass was for `a1b2c3d`'s diff/tree, and the policy result needs to be re-published against the new HEAD.

This is true even though nothing about the change looks risky, and even though `a1b2c3d` is a direct ancestor of `e4f5a6b` (a clean fast-forward, no rebase, no force-push). GitHub does not "carry forward" a passing status just because the new commit is additive — the merge button will show the checks as not-yet-satisfied for `e4f5a6b` regardless of how trivial the new commit is. In practice this is usually automatic and low-friction: pushing a commit to an open PR branch typically retriggers your CI workflows on the new SHA on its own, so "rerun" often just means "wait for the already-triggered run to finish" rather than something you have to manually kick off — but you should not merge on the strength of the `a1b2c3d` evidence alone, and you should confirm both checks actually show green against `e4f5a6b` specifically before merging.

The one thing that *is* preserved: since this was a plain add-a-commit push, `a1b2c3d` is still reachable in the branch's history, so the old check run remains inspectable for audit purposes, and the diff reviewers need to look at is cleanly scoped to just the one new commit (`a1b2c3d..e4f5a6b`).

## How would this differ if you had force-pushed instead?

The core requirement — checks must be re-evaluated against the new HEAD SHA — doesn't change; that part is identical. What changes is everything *around* it:

| | Plain new commit (fast-forward) | Force-push (amend/rebase/squash) |
|---|---|---|
| Is `a1b2c3d` still an ancestor of HEAD? | Yes | Not necessarily — it may be dropped from history entirely |
| Is the old check run still traceable to a commit on the branch? | Yes, `a1b2c3d` is still part of the PR's commit list | Often no — if `a1b2c3d` was rewritten/amended away, it becomes a dangling/orphaned commit no longer reachable from any ref, and its check run is effectively orphaned too |
| Diff a reviewer needs to re-examine | Exactly the new commit (`a1b2c3d..e4f5a6b`) | Potentially the *entire* branch, since a rebase/amend can silently alter content in commits that aren't the "newest" one — GitHub can still show a before/after force-push compare, but it's less automatic and easy to miss |
| Review approvals | May or may not be dismissed, per repo settings ("dismiss stale approvals on push") — same trigger fires for either kind of push | Same dismissal trigger, but combined with the harder-to-audit diff, teams typically treat a force-push as requiring a fresh human look, not just a fresh CI run |
| SHA-bound attestations (e.g., a security/policy sign-off recorded specifically "as of SHA X") | Still meaningfully "SHA X passed, and X is still in the history" | The recorded SHA may no longer exist on the branch at all — re-attesting isn't just "convenient," it's necessary, because the thing that was attested to may literally be gone |

So: **for merge-gate purposes, both cases are the same** — new HEAD, no valid check runs yet, must rerun. The practical difference is in **auditability and trust**. A plain new commit is a strictly additive, easy-to-diff change on top of an evidence trail that's still intact. A force-push can rewrite or discard the very commit the evidence was recorded against, which is why it's generally treated as the higher-scrutiny case: don't just rerun the checks, also re-verify what actually changed between what was reviewed/attested and what's being merged now, since a simple `a1b2c3d..e4f5a6b` diff may no longer be a valid way to see that.
