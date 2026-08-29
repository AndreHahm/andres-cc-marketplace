## Summary
A Git-operation completion/validity check must (a) scope any content scan to what actually changed rather than the whole tracked tree, and (b) model the operation's full state lifecycle explicitly rather than treating a state marker's mere presence as "not yet done" — two related validator bugs found together in the same conflict-resolution logic.

## Environment
- **Product/Service**: `git-kit` plugin (`resolving-merge-conflicts/scripts/validate-conflicts.sh`)
- **Region/Version**: this repo, found during PR #143 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
**Bug 1 (whole-tree scan):**
1. Resolve all conflicts and confirm zero unmerged paths remain.
2. The validator then scans *every tracked file* in the repository for lines beginning with `<<<<<<<`, `=======`, or `>>>>>>>`.
3. Any tracked file containing content that merely resembles a conflict marker (Markdown headings, separator output, this very skill's own documentation with example marker text) makes the scan report a false failure.

**Bug 2 (state-lifecycle modeling):**
4. After every conflicted path is resolved and staged (but before the merge commit is made), `MERGE_HEAD` still legitimately exists — this is Git's own normal in-progress-but-resolved state.
5. A separate check treats `MERGE_HEAD`'s mere presence as failure, so the validator can never report success for a merge-originated conflict, even once fully resolved.

## Expected Behavior
The completion check should scope its content scan to only staged/changed files (never the whole tracked tree), and should model the operation's actual state lifecycle ("in progress," "resolved but uncommitted," "complete") rather than treating a state marker's mere presence as equivalent to "unresolved."

## Actual Behavior
Both bugs made validation fail on legitimate states: unrelated tracked content with marker-like lines caused permanent false failures (this repo has 20+ such files), and a normal resolved-but-uncommitted merge state was always reported as failing.

## Impact
[Severity: High] The validator was unusable for its core purpose in both directions. Fixed in `git-kit`'s PR #143: the whole-tree-scan bug was fixed in a follow-up commit (`0fe8945`) by scoping the fallback scan to staged files only, live-tested for both a false-positive-avoidance case and genuine leftover-marker detection; the `MERGE_HEAD`-lifecycle bug was fixed in the main commit (`0bb9d72`) by renaming the check to `check_operation_state`, making it informational-only (never fails the overall result) and adding `CHERRY_PICK_HEAD` detection alongside it with the correct finalize guidance for each state.

## Additional Context
Mined from PR #143's own review history (`devin-ai-integration[bot]`, `coderabbitai[bot]`; 24 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #143` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/143#discussion_r3861466870, https://github.com/AndreHahm/andres-cc-marketplace/pull/143#discussion_r3861794687
