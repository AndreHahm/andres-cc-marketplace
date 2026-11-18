I would write `Context mode: ship`.

All of the skill's conditions for `ship` are met here. The rule says to use `ship` "only when the next step is `merge-pr` or a publish and nothing else is left before it", and for a PR merge, "the PR is not a draft, no review findings are left to triage, no fix commits are pending, and when last checked the required checks were green and secretlint had passed". The next step is only merge-pr, so the "when unsure, choose `review`" fallback doesn't come into play.
