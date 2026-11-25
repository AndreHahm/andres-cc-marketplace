I stay in this skill: the request covers only its PR review and ready step, not a run to merge.

1. Read PR #77's head SHA, mergeability, draft state, reviews and checks, plus policy via `repository-gates`.
2. You explicitly asked to fix and resolve, so I skip step 1.5's permission question and invoke `Skill(git-kit:handling-review-findings)`. It owns triage, fixes, commits, replies and resolution, and alone reports thread state. If that dispatch fails, I stop and report it.

First point I need you: that skill's own triage decision or commit confirmation. If it raises none, I re-read GitHub, summarize to ENG-230, re-verify and revalidate Linear, then need you at step 7's readiness confirmation. Nothing is marked ready before then; you would run `gh pr ready` yourself.
