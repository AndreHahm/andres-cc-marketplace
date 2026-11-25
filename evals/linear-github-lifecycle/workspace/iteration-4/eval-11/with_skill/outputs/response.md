I continue in pr-to-linear. linear-github-lifecycle dispatched it, so the "When NOT to Use" routing back there doesn't apply; I don't re-invoke it.

Next:
1. Read PR 45's head SHA, draft state, reviews and checks with `gh pr view`/`gh pr checks`, and policy via `repository-gates`.
2. This phase includes fixing and readiness, so invoke `git-kit:handling-review-findings`, the sole source for thread resolution.
3. Re-read GitHub; reflect concise blockers via `linear-work-management`.
4. If all findings are fixed, filed or declined: re-verify the current SHA and preconditions, revalidate Linear, confirm via AskUserQuestion, and ask the user to run `gh pr ready` (never myself).
5. Read back; record SHA-bound `pr-ready` via `linear-github-linking`.

Then the phase result returns to linear-github-lifecycle. I don't merge.
