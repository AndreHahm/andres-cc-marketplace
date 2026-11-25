I run this skill (work-to-development) for ENG-205 myself. I do not route back to linear-github-lifecycle: it dispatched me for this phase, so the "When NOT to Use" merge exclusion doesn't apply, and this skill never dispatches it.

Next, in order:
1. Invoke `linear-work-management` to read ENG-205 and check readiness; stop if criteria are missing or contradictory.
2. Invoke `repository-gates` for policy and provider.
3. Invoke `linear-github-linking` to search for existing artifacts.
4. Present readiness and branch name; confirm via AskUserQuestion.
5. Invoke `git-kit:starting-work`; read back actual identity.
6. Record `work-started` via `linear-github-linking`, then set Started via `linear-work-management`.
7. Read back, report to the running `linear-github-lifecycle`, which owns later phases (no commit, PR or merge here).
