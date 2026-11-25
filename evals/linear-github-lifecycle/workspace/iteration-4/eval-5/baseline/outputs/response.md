I stop before this skill's Procedure and invoke `Skill(linear-github-lifecycle)` for ENG-205, with the scope "accepted issue, start to merge".

Why: `work-to-development` covers only readiness and the branch request. Its "When NOT to Use" sends committing, PR publication and merging to `development-to-pr` and `merge-to-completion`. The doc names no end-to-end owner. From its name alone, I infer that `linear-github-lifecycle` is the coordinator; I have not read it.

I expect it to run `work-to-development`, `development-to-pr`, `pr-to-linear`, then `merge-to-completion`, keeping each stage's approval gates. "All the way to merge" does not pre-approve the branch request or other gated steps.

If that skill cannot be invoked or does not fit, I report that and ask via AskUserQuestion. I create no branch and change no Linear state now.
