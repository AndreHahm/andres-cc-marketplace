I leave linear-github-lifecycle and invoke `Skill(pr-to-linear)` directly for PR 45 / ENG-205, scoped to review/fix + ready only.

Why: the request is one stage ("nothing else"). The loaded skill's When NOT to Use says to invoke the focused skill directly for a single stage, and its phase table assigns Review/fix + Ready to pr-to-linear. "Pick up again" resumes that stage, not the full lifecycle, so I skip this skill's resume cursor and sequence-level confirmation.

pr-to-linear runs its own checks and confirmation gates before readiness; blockers, or a mismatch between PR 45 and ENG-205, get reported instead of forced through. Then I stop: no merge-to-completion, Linear disposition, or Notion learning.
