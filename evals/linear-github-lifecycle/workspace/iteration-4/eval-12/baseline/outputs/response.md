I stay in this skill (merge-to-completion); linear-github-lifecycle dispatched it for exactly this phase, so I don't hand the request back or restart the lifecycle.

Next: invoke `repository-gates` to confirm git-kit is the required merge provider (step 1). Then read ENG-205's identity and criteria, and confirm merge method, branch behavior and the disposition workflow via AskUserQuestion. "All the way to merge" doesn't replace that gate.

On yes: `git-kit:merge-pr` for PR 45 (it owns readiness and cleanup); read back state and SHA; record `pr-merged` via `linear-github-linking`.

Then separately compare each criterion, confirm any consequential disposition, route approved follow-ups through `open-item-management`, and close via `linear-work-management` only if step 13 holds. Finally, return the result to linear-github-lifecycle.
