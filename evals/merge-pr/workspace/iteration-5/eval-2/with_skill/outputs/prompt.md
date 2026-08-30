# merge-pr — Step 5 Confirmation Prompt (simulated exercise, no real PR)

This describes exactly what I would present via `AskUserQuestion` at step 5 of the
`merge-pr` skill, given: step 3's merge-rights check returned `MERGE ALLOWED`, and
readiness is fully satisfied (step 2's three required checks all pass — not draft,
all required status checks passing, no outstanding `CHANGES_REQUESTED` reviews).

I am **not** calling `AskUserQuestion` for real — this is a description of its exact
content, since there is no real PR to operate on.

## What triggers this

Step 5 fires only when:
- `MERGE ALLOWED` (step 3), and
- readiness is fully satisfied — either directly from step 2, or via a successful
  bypass re-verification in step 4.

Per the skill's own text: "This step always runs, bypass or not — a bypassed Codex
check never substitutes for this explicit human confirmation."

## Exact `AskUserQuestion` content

**header:** `Merge PR #<N>`

**question:**
```
PR #<N> — "<PR title>" is ready to merge.

Readiness summary:
- Not a draft
- All required status checks passing
  [if bypass path: "except: Publish Codex policy result — bypassed
   (attested by @<actor>, reason: \"<reason>\")"]
- No outstanding change-request reviews
- Merge rights confirmed (repo owner / CODEOWNERS match / collaborator
  permission — whichever tier passed)

Advisory (informational only — does not block merging):
- Commits behind base: <N>
  [or, if isCrossRepository is true: "Out-of-sync check skipped — PR is
  from a fork"]
- Unresolved review threads: <N>

Note: branch deletion may report a local git error such as
  fatal: '<default>' is already used by worktree '...'
even though the merge itself succeeds. This is expected in a worktree-based
workflow and is handled automatically.

Merge this PR now?
```

**options:**
1. label: `Yes — merge now`
   description: Proceed to step 6/7 and execute the merge using the configured strategy.
2. label: `No — cancel`
   description: Stop here. No merge is performed.

## Notes on required content (per the skill's own text and its Testing & Validation section)

- The **two advisory disclosures** (commits-behind-base / fork-skip, and unresolved
  review-thread count) are **always stated explicitly, even when both are zero** —
  "never let a clean number pass silently" is stated twice in the skill (once for
  step 2's disclosures generally, once by analogy to step 7(c)'s squash-tradeoff
  disclosure).
- If the PR reached step 5 via the bypass path (step 4), the prompt **explicitly
  notes that Codex review was bypassed and why** (actor, reason) — this is called
  out by name in step 5's own instructions.
- The **worktree branch-delete git-error note** (`fatal: '<default>' is already
  used by worktree ...`) is always included, unconditionally.

## Does the step-5 prompt's content depend on `merge_auto_delete_branch`?

**No.** The skill is explicit about this, in two places:

1. Step 5's own instructions place the worktree-error note in the same sentence as
   the rest of the confirmation content, with no conditional language tied to any
   setting.
2. Step 6 — which reads `pr_merge_type` and `merge_auto_delete_branch` — is a
   *separate, later* step that runs only after step 5's confirmation succeeds. The
   skill's own Testing & Validation section states this directly: "the note about a
   possible `fatal: '<default>' is already used by worktree ...` error is present in
   step 5's confirmation prompt unconditionally — never gated on
   `merge_auto_delete_branch`, since that setting isn't read until step 6."

So structurally, step 5 *cannot* branch on `merge_auto_delete_branch` even if it
wanted to — the value doesn't exist yet at that point in the skill's execution
order. The prompt's content is fixed and identical regardless of whether
`merge_auto_delete_branch` will later resolve to `true` or `false`: the git-error
note is shown every time step 5 runs, not just when branch deletion will actually
be attempted.
