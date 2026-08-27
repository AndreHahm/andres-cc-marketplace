# Step 7 — REBASE pre-check found 1 merge commit

**Context:** `pr_merge_type` (step 6) = `REBASE`. The rebase-compatibility pre-check
(step 7a) command:

```
gh api repos/{owner}/{repo}/pulls/<number>/commits --paginate --jq '.[] | select((.parents | length) > 1) | .sha'
```

returned exactly one SHA — i.e. the merge-commit count (via `wc -l` over that output) is
**1, not 0**.

## What I do before ever calling `gh pr merge <n> --rebase`

Per SKILL.md step 7(a), a non-zero merge-commit count means I must **not** attempt
`gh pr merge --rebase` at all — GitHub's rebase-and-merge unconditionally rejects a branch
containing an existing merge commit (a verified, live-reproduced fact per
`.claude/rules/verify-tool-behavior-before-instructing.md`, not a hypothetical to test by
trying it and seeing what happens). So:

1. **Tell the user the finding before taking any merge action**: this PR's history
   contains 1 merge commit, and `gh pr merge --rebase` would be rejected by GitHub
   (`"This branch can't be rebased"`) if attempted as configured.

2. **Ask via `AskUserQuestion`** which alternate strategy to use instead, offering exactly
   the two options step 7(a) specifies:
   - "Merge (keeps the merge commit)"
   - "Squash (see the tradeoff below)"

3. **If the user picks Squash**, apply step 7(c)'s tradeoff disclosure *before* running the
   squash merge — never let "Recommended" or the earlier pre-check silently carry the
   decision:
   - Look up the real commit count via `gh pr view $ARGUMENTS --json commits --jq '.commits | length'`.
   - State explicitly how many commits will collapse into one, and that individual
     fix-round/review-commit granularity will be lost on the base branch.
   - Only after stating that tradeoff, proceed to run `gh pr merge <n> --squash`.

4. **If the user picks Merge**, proceed to step 7(b) using `--merge` instead of `--rebase`
   (still preceded by writing the git-kit marker via
   `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-merge merge-pr`
   immediately before the merge command, per step 7(b)).

5. **`gh pr merge <n> --rebase` is never invoked in this scenario** — the pre-check already
   determined it will be rejected, so step 7(d)'s "rejection fallback" path (which handles a
   *live* rejection after the pre-check missed something) doesn't even come into play here;
   the branch to a different strategy happens proactively in 7(a), not reactively in 7(d).

## Why (traceability to the skill)

- Step 7(a): "If the count is non-zero, tell the user how many merge commits the branch
  contains and that `--rebase` will be rejected, then ask via `AskUserQuestion` which
  strategy to use instead ... before ever attempting `gh pr merge --rebase`. Apply (c)'s
  tradeoff disclosure if squash is chosen here."
- Step 7(c): the squash tradeoff disclosure "always fires before the `--squash` merge
  command runs," regardless of whether squash was reached via (a) or (d).
- `.claude/rules/verify-tool-behavior-before-instructing.md`'s own table (PR #142 row)
  documents the underlying fact this pre-check exists to act on: a branch containing a
  merge commit is unconditionally rejected by GitHub's rebase-and-merge, confirmed live via
  `"This branch can't be rebased"`.
