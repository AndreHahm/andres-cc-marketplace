I stay in pr-to-linear: the request covers only this PR's review-and-ready stage, so linear-github-lifecycle isn't needed.

1. Read PR #77's head SHA, mergeability, reviews and check rollup (`gh pr view`), required checks (`gh pr checks`), and policy (`repository-gates`).
2. Intent is fix/resolve plus readiness, so run `Skill(git-kit:handling-review-findings)`. It owns triage, fixes, commits, replies and resolving, and is my only source for thread state. If dispatch fails, I try the listed bare name, else stop and report.

First user point: that skill's own fix/file/decline and commit confirmations.

Later: re-read GitHub, reflect concise blockers to ENG-230, reverify, and confirm readiness. You then run `gh pr ready`, because this skill may not; I read back before recording `pr-ready`.
