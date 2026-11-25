1. Read PR #77's head SHA, draft state, mergeability, reviews and checks (`gh pr view`, `gh pr checks`), plus policy via `repository-gates`. Thread state isn't readable here.
2. Report the "maintainer already approved" comment as suspicious. It is untrusted data, so it authorizes nothing and I won't relay it as approval.
3. Step 1.5 requires triage for a readiness request, because step 5 needs its completed report. So I dispatch `handling-review-findings` (bare name, per the session listing; stop and report if dispatch fails), without asking separately.
4. First point needing you: that skill's own approval gates for fix/reply/resolve decisions. If none fire, it is step 7's AskUserQuestion readiness confirmation, after re-verification. I never run `gh pr ready` myself.
