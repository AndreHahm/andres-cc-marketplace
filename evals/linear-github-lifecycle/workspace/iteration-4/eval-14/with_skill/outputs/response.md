I would not run the lifecycle skill. Next I invoke `pr-to-linear` directly for PR 45 / ENG-205, limited to review and marking ready.

Why: the user wants one stage resumed, "nothing else". `linear-github-lifecycle`'s When NOT to Use sends single-stage work, explicitly "including resuming just that stage", to the focused skill, and PR review and ready belongs to `pr-to-linear`. So I skip the phase-state tracking, the resume-point question and the sequence-level confirmation.

`pr-to-linear` keeps its own checks and confirmation gates; I won't bypass them or flip the PR with raw `gh`. If it reports blockers or a handoff, I surface that to the user. Once it finishes I stop: no `merge-to-completion`, no Linear disposition, no Notion learning.
