# Step 7 — what happens before `gh pr merge <n> --rebase` is ever called

**Given facts:** `pr_merge_type` (resolved at step 6) is `REBASE`. The query
`gh api repos/{owner}/{repo}/pulls/<number>/commits --paginate --jq '.[] | select((.parents | length) > 1) | .sha'`
returns exactly **one** SHA.

This is step 7(a), the **rebase-compatibility pre-check**, which runs *only* because
`pr_merge_type` resolved to `REBASE`. It exists specifically because GitHub's rebase-and-merge
unconditionally rejects a branch that contains an existing merge commit (a verified, live-reproduced
fact — `"This branch can't be rebased"`, no retry-after semantics), so the check runs *before* ever
attempting `--rebase`, rather than waiting for that live rejection.

## What I would do, in order

1. **Count the merge commits.** Run the `gh api .../pulls/<number>/commits --paginate --jq '...'`
   command exactly as given, and count matched output lines with `wc -l` — never via `jq -e`'s own
   exit status across `--paginate` pages, since that only reflects the *last* page and would silently
   override an earlier page's match. Per the given fact, this yields a count of **1** (non-zero).

2. **Because the count is non-zero, do not attempt `gh pr merge --rebase` at all.** Instead:
   - Tell the user exactly how many merge commits the branch contains ("this PR's history contains
     1 merge commit") and that `--rebase` will be rejected by GitHub if attempted.
   - Ask via `AskUserQuestion` which alternate strategy to use instead, with exactly two options:
     - **"Merge (keeps the merge commit)"**
     - **"Squash (see the tradeoff below)"**

3. **If the user picks Squash**, apply step 7(c)'s tradeoff disclosure before ever running the
   `--squash` merge command: state how many commits will collapse into one (via
   `gh pr view $ARGUMENTS --json commits --jq '.commits | length'`) and that individual
   fix-round/review-commit granularity will be lost on the base branch. This disclosure is mandatory
   and must fire regardless of how squash was arrived at (configured default, chosen here in (a), or
   chosen reactively in (d)) — it must never be silently implied by a "Recommended" label.

4. **Only after** the user's alternate-strategy choice (and, if applicable, the squash-tradeoff
   disclosure) is resolved do I proceed to step 7(b): write the fresh git-kit marker
   (`write-git-kit-marker.sh gh-pr-merge merge-pr`) immediately before merging, and run
   `gh pr merge $ARGUMENTS --merge` or `--squash` — using the strategy the user just chose in step
   2 above, **not** `--rebase`, and **not** the originally configured `pr_merge_type` of `REBASE` —
   plus `--delete-branch` if `merge_auto_delete_branch` is `true`.

## Key point

Because the merge-commit count is non-zero, `gh pr merge <n> --rebase` is never attempted in this
run at all. The pre-check in 7(a) intercepts it beforehand: report the count → ask the user to pick
Merge or Squash → (if Squash) disclose the tradeoff → only then execute the merge with whichever
strategy the user actually chose. `REBASE` as originally configured is abandoned for this PR, and
that substitution is reported to the user as part of the final result (step 7's closing "report the
result" instruction: "whether the merge strategy differed from the configured `pr_merge_type` and
why").
