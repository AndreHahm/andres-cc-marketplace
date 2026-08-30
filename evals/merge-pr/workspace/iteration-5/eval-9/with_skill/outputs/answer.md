# What I do before running `gh pr merge <n> --squash`

Context: at step 7, `pr_merge_type` (resolved at step 6) is `SQUASH`, and it was the configured
setting from the start — not a strategy arrived at via step 7(a)'s rebase pre-check or step 7(d)'s
rejection fallback. The PR has 12 commits.

## 1. Step 7(a) does not apply here

Step 7(a), the rebase-compatibility pre-check (counting existing merge commits via
`gh api repos/{owner}/{repo}/pulls/<number>/commits --paginate --jq '...' | wc -l`), only runs
**"when the `pr_merge_type` resolved in step 6 is `REBASE`."** Since it's `SQUASH`, this branch never
enters (a) at all — I skip it, not as an oversight but because it's explicitly out of scope for a
non-`REBASE` resolved type.

## 2. Apply step 7(c)'s squash-tradeoff disclosure — mandatory, before the merge command runs

Step 7(b) says explicitly: *"If the resolved strategy is `--squash`, apply (c)'s disclosure before
running this command — this includes [when] `pr_merge_type` was already `SQUASH` from the start,
since that path never enters (a) and would otherwise reach `--squash` here first."*

Step 7(c) itself is unambiguous that this fires **regardless of how squash was reached**: *"whenever
`--squash` is about to run — whether `pr_merge_type` was already `SQUASH`, it was chosen preemptively
in (a), or reactively in (d) below."* The fact that `SQUASH` was the pre-existing configured default
does not exempt it, and the skill is explicit that "Recommended"/pre-configured status must never
carry the decision silently.

So before doing anything else, I:
- State the exact commit count that will collapse into one on the base branch. The skill's canonical
  way to get this is `gh pr view $ARGUMENTS --json commits --jq '.commits | length'`; here that
  count is already given as a fact for this exercise: **12 commits**.
- State the tradeoff in plain terms: squashing collapses all 12 commits into a single commit on the
  base branch, and individual fix-round/review-commit granularity is permanently lost there (the
  original 12-commit history still exists on the source branch/PR until deleted, but the base branch
  will only ever show one squashed commit).
- I do **not** silently let "this was already configured" substitute for actually naming the
  tradeoff — the skill treats a pre-configured squash exactly the same as an ad hoc choice for
  disclosure purposes.

This disclosure is surfaced to the user as explicit text (not just logged internally) before the
merge command is issued.

## 3. Write the merge marker immediately before merging

Per step 7(b): `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-merge merge-pr` — this
satisfies git-kit's PR-operations guard hook, which requires a marker no more than 60 seconds old.
I write it right before the merge call, not earlier (e.g. not back at step 5's confirmation), so it
doesn't go stale while the disclosure/confirmation text above is being composed.

## 4. Then, and only then, run the merge command

`gh pr merge $ARGUMENTS --squash`, adding `--delete-branch` if `merge_auto_delete_branch` (read at
step 6) is `true`.

## 5. After the command returns

Per step 7(e), regardless of the command's exit code, I check
`gh pr view $ARGUMENTS --json state,mergeCommit` next (a non-zero exit doesn't necessarily mean the
merge failed — e.g. a local `--delete-branch` follow-through error can fail the command after the
remote merge already succeeded) and branch on `state`/`isCrossRepository`/`merge_auto_delete_branch`
exactly as steps 7(e)'s enumerated cases describe (OPEN → real failure and stop; MERGED + fork →
skip branch-deletion fallback and report; MERGED + same-repo + auto-delete true → verify with
`git ls-remote --heads origin <headRefName>` and finish the deletion via
`gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>` if it didn't actually take; MERGED +
same-repo + auto-delete false → ask separately whether to delete). I then report the merge
commit/method used, whether the strategy differed from the configured `pr_merge_type` (here it
didn't — squash was configured from the start), and the branch-deletion outcome.

## Summary of the immediate next actions, in order

1. Skip step 7(a) (only applies to `REBASE`).
2. Disclose the squash tradeoff per 7(c): 12 commits will collapse into 1; fix-round/review-commit
   granularity is lost on the base branch. This fires unconditionally, even though `SQUASH` was
   already the configured default.
3. Write the `gh-pr-merge` marker immediately before merging.
4. Run `gh pr merge <n> --squash` (plus `--delete-branch` if configured).
5. Re-check `state`/`mergeCommit` afterward regardless of exit code, and handle branch deletion per
   7(e)'s enumerated cases before reporting the final result.
