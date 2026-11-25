I run this skill (development-to-pr) for this phase, starting at step 1, and commit nothing yet.

1. Resolve context: `linear-work-management` (ENG-205 outcome/title), `linear-github-linking` (evidence entries), `repository-gates` (policy profile).
2. Via `linear-github-linking`, search for an existing PR; confirm an Adoptable match, or resolve a Conflicting/Ambiguous one, with AskUserQuestion. The commit instructions depend on the result.
3. Existing PR: verify repo, push URLs and branch, run `git-kit:cross-model-review` (BASE=HEAD), then `git-kit:commit` with its push. New PR: `git-kit:commit` without push/Auto-PR, then confirm and `git-kit:create-pr`.

Record commit-linked, discover gates, read back PR and gate results, record pr-published. Then return results to the already-running `linear-github-lifecycle`, without re-invoking it; it owns review and merge.
