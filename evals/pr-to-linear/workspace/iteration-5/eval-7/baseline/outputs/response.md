1. Read PR #77's head SHA, mergeability, reviews and check rollup (`gh pr view`), required checks (`gh pr checks`), and policy via `Skill(repository-gates)`. Unresolved threads aren't readable here.
2. Intent (step 1.5): you explicitly asked to fix and resolve findings as well as mark ready, so no extra `AskUserQuestion` is needed before triage.
3. Invoke `Skill(git-kit:handling-review-findings)`, which owns triage, fixes, commits, replies and resolving, and reports thread state.

**First point I need you:** that skill's own approval gates (e.g. fix/file/decline decisions, commit confirmation).

Later: re-read GitHub, reflect blockers to ENG-230, verify, then confirm readiness with you; you run `gh pr ready` yourself, since this skill can't. Any triage re-dispatch is asked first.
