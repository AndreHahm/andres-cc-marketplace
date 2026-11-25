I stay in pr-to-linear for this dispatched phase; I don't re-invoke linear-github-lifecycle, which is already running.

1. Read PR 45's head SHA, mergeability, reviews and checks (`gh pr view`, `gh pr checks`); get policy via `repository-gates`.
2. The phase is fix plus readiness, not pure summary, so invoke `git-kit:handling-review-findings`, the only source of thread state.
3. Re-read GitHub; reflect concise blockers to ENG-205 via `linear-work-management`.
4. If clear: re-verify state/SHA, revalidate acceptance via `linear-work-management`, confirm via AskUserQuestion, ask the user to run `gh pr ready` (no skill owns it). Read back; record `pr-ready` for that SHA via `linear-github-linking`.
5. Return evidence, or any unresolved blockers, to linear-github-lifecycle, which owns the later merge phase. I never merge.
