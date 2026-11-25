I stop pr-to-linear here, run none of its steps, and hand over to linear-github-lifecycle by invoking `Skill(linear-github-lifecycle)` with ENG-205, PR 45, "in review", and "resume until merged".

Why: pr-to-linear's "When NOT to Use" sends "resuming an interrupted lifecycle run that spans more than this stage" to linear-github-lifecycle. This request spans review, ready and merge, and that skill did not dispatch this one. The routing is for the caller: pr-to-linear has no grant for it, so I invoke it as the session, not as a step of pr-to-linear.

I don't call merge-to-completion or handling-review-findings directly; the lifecycle skill should establish the current phase and dispatch stages. "In review" is unverified, and the merge request doesn't waive its confirmation gates.
