1. Read PR #77 with `gh pr view` (head SHA, mergeability, reviews, checks) and `gh pr checks`; read policy via `repository-gates`.
2. Readiness intent always requires triage first, so run `Skill(git-kit:handling-review-findings)`: only it reports thread state; "looks done" isn't evidence. Its own triage questions may reach the user first.
3. Re-read checks/reviews; summarize meaningful blockers to ENG-230 via `linear-work-management`. If anything is unresolved, report it, don't proceed.
4. Re-verify draft state, head SHA, checks, reviews, description/link; revalidate ENG-230's acceptance context and blockers.
5. First user stop of my own: `AskUserQuestion` presenting the readiness action and gaps. If approved, I'd ask the user to run `gh pr ready`; I never run it.

Nothing executed; plan only.
