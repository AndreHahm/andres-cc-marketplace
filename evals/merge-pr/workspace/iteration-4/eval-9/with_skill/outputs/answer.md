# Step 7 — what happens before `gh pr merge <n> --squash`

Context: step 6 resolved `pr_merge_type = SQUASH` as the configured setting from the start (not a
choice forced by the rebase pre-check in 7(a), and not a reactive fallback from 7(d)). The PR has 12
commits.

## 1. Step 7(a) rebase-compatibility pre-check — does not apply, skip it entirely

7(a) only runs "when the `pr_merge_type` resolved in step 6 is `REBASE`." Here it's `SQUASH`, so:

- No merge-commit count check against `gh api repos/{owner}/{repo}/pulls/<number>/commits`.
- No `AskUserQuestion` about switching strategy — there's nothing to switch away from; squash was
  already the configured strategy, not something arrived at because rebase was rejected.
- Proceed straight to 7(b)/7(c) with `SQUASH` as the strategy, per 7(b)'s own text: "or `pr_merge_type`
  directly when (a) didn't apply — i.e. it isn't `REBASE`, or found no merge commits."

## 2. Step 7(c) — the squash tradeoff must still be disclosed, unconditionally

Before the `--squash` merge command actually runs, state the tradeoff explicitly. The SKILL is
explicit that this disclosure fires **regardless of how squash was arrived at**:

> "whenever `--squash` is about to run — whether `pr_merge_type` was already `SQUASH`, it was chosen
> preemptively in (a), or reactively in (d) below — state how many commits will collapse into one...
> and that individual fix-round/review-commit granularity is lost on the base branch... never let
> 'Recommended' carry the decision silently, and state it even when the user already picked squash
> themselves in (a) or (d)."

So even though nothing forced this choice and no re-ask is needed, I still tell the user, before
merging:

- The commit count that will collapse into one: 12 commits (confirmed via
  `gh pr view $ARGUMENTS --json commits --jq '.commits | length'` — here given as a fact, 12).
- The concrete cost: all 12 commits' individual fix-round/review-commit granularity is lost on the
  base branch after the squash — only a single squashed commit will land on `main`.

This is a disclosure, not a new gate — it doesn't require a fresh `AskUserQuestion` re-confirmation
of the merge itself (step 5's confirmation already covered "merge now, yes/no"), but it must be
stated plainly before the merge command executes, per both step 7(c) itself and the repo's
`disclose-before-overriding-decisions` convention of never letting a consequential fact ride silently
on a pre-existing setting.

## 3. Step 7(b) — write the marker, then execute the merge

Immediately before merging (not earlier — the marker is only valid for 60 seconds):

1. Run `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-merge merge-pr` — this satisfies
   git-kit's PR-operations guard hook, which hard-blocks a raw `gh pr merge` call with no matching
   marker.
2. Then run `gh pr merge <n> --squash`, adding `--delete-branch` if `merge_auto_delete_branch`
   (resolved in step 6) is `true`.

## Summary — the concrete pre-merge sequence

1. Confirm `pr_merge_type` is `SQUASH` (already resolved in step 6) → skip 7(a)'s rebase pre-check
   and its `AskUserQuestion` entirely; nothing to reconcile.
2. Disclose the squash tradeoff per 7(c): "This will squash all 12 commits into a single commit on
   the base branch — individual fix-round/review-commit granularity will be lost." State this even
   though squash was already the configured default — never let the pre-existing setting carry the
   decision silently.
3. Write the merge marker: `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-merge merge-pr`.
4. Run `gh pr merge <n> --squash` (plus `--delete-branch` if configured).
5. (Downstream, not part of this question) Regardless of exit code, step 7(e) still checks
   `gh pr view $ARGUMENTS --json state,mergeCommit` and, if applicable, the `git ls-remote` /
   `gh api -X DELETE` branch-deletion fallback before reporting the result.
