## Summary
`github-issue-lifecycle`'s `workflows/resolve-an-issue.md` sends the reader to
`references/status-vocabulary.md` mid-instruction for a "Why `filed` is missing" explanation, instead of
being self-contained — a chain-violation per the mandatory workflow-self-containment check.

## Environment
- **Product/Service**: `plugins/git-kit/skills/github-issue-lifecycle/workflows/resolve-an-issue.md`
  (mirrored under `.claude/`)
- **Region/Version**: this repo, found by a `skill-reviewer` pass, 2026-09-26

## Reproduction Steps
1. Read `workflows/resolve-an-issue.md`'s "Why `filed` is missing" note.
2. It ends with "...so `filed` has no analog here. See `references/status-vocabulary.md` for the full
   mapping."
3. A reader following this workflow step by step is sent to a second file mid-instruction rather than
   having the load-bearing fact stated inline.

## Expected Behavior
A workflow step should be self-contained for anything actually needed to execute it — a reference file
is for optional deeper background, not a fact the step itself depends on.

## Actual Behavior
The mapping table `status-vocabulary.md` holds is only 2 rows, small enough to inline directly, but the
workflow instead sends the reader on a second file load for it.

## Impact
**Minor** — this is a workflow-clarity/self-containment gap, not a functional defect; the workflow
still executes correctly for anyone willing to follow the reference link.

## Additional Context
Found alongside a similar, already-fixed issue in `handling-review-findings`'s own
`workflows/work-an-existing-issue.md` (fixed in PR #407, same session) — the fix there inlined a
load-bearing caveat instead of citing a reference for it. The same treatment likely applies here:
inline the 2-row mapping directly in `resolve-an-issue.md`, keeping `status-vocabulary.md` as optional
deeper background only.

**Not fixed in PR #407** — `resolve-an-issue.md` is not a file that PR's diff touches; filed separately
per `merge-pr`'s step 1.5 session open-issues check.
