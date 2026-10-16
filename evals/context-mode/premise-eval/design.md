# context-mode premise eval: design

Question: does an injected mode profile change the assistant's behavior beyond what CLAUDE.md and the
always-loaded `.claude/rules/` already produce? Basis: `.draft/_open/context-kit/refactor-context-mode/report.md`
(finding 3: no behavior could be credited to the modes) and its decision log, item 7.

## Method

- 8 scenarios (`scenarios.json`), 2 per mode, one prompt each.
- 2 arms per scenario: `baseline` (no profile) and `with_profile` (full text of `references/<mode>.md`
  prepended as injected context). One run per arm, so n = 1 per cell (see Limits).
- Plan-only: runners get the wrapper in `scenarios.json` and call no tools. They state what they would do.
- Runners never see assertions or the other arm. Both arms use the same agent type and model.
- Grading: one blind grader per scenario receives the two replies as "A" and "B" (arm order randomised),
  the assertions without their `profile_only` tags, and returns pass/fail plus a quote per assertion.
  The arm mapping is revealed only after grading.

## Pass criteria (fixed before any run)

- A scenario shows a profile effect when `with_profile` passes at least 2 more `profile_only: true`
  assertions than `baseline`. If scenario 2's only gain is 2c and 2d, both count.
- A mode keeps its profile content when at least one of its two scenarios shows a profile effect.
- A mode with no profile effect in either scenario is cut to its repo-specific routing hints only, or
  merged into another mode. A mode with an effect in one scenario keeps only the lines that the
  passing assertions trace to.
- Assertions with `profile_only: false` are controls: a with_profile gain on them is reported, but does
  not count toward the effect (the always-loaded rules already ask for them).
- Overall premise holds when at least 3 of the 4 modes keep their profile. If fewer, the refactor is
  reduced to a single short posture block, and that decision goes back to the owner.

## Limits

- n = 1 per cell. A gain of exactly 1 assertion is treated as noise; only gains of 2 or more count.
  A borderline scenario (gain of 1 to 2) is re-run once per arm before the decision.
- Plan-only runs show intended actions, not executed ones.
- Subagents may load a different set of project instructions than the interactive session. The
  `CLAUDE.md visible` line in each reply is recorded; a `no` in either arm of a scenario voids that
  scenario's baseline and it is re-run.
- The wrong-profile control (profile of mode X on mode Y's prompt) is not part of this pass.

## Round 3 addendum (fixed before any round 3 run; owner chose "more evidence first" on 2026-10-16)

Reason: round 1 and 2 left review as the swing mode (means +1.5 and +1.0), and the matched-profile gain could be a
generic effect of any added instruction text rather than something the matched mode adds.

Runs (plan-only, same wrapper, same agent type and model; runners save their own reply to a file):
- A third baseline run and a third matched-profile run for scenarios 3 and 4 (review): 4 runners.
- One wrong-profile run per scenario 2 to 8, with a different mode's profile prepended: 7 runners. Mapping:
  scenarios 2, 3, 4 get the ship profile; 5, 6 get the admin profile; 7, 8 get the review profile.

Grading: blind graders, labels X/Y/Z shuffled per file, no arm shown. The graders get the same instruction as
round 2 (a multi-part assertion needs all parts to pass).

Decision rules:
- Review keeps its profile when the mean delta over its three runs is 2.0 or more in scenario 3 or in scenario 4.
- Mode-specific check, per mode (review = scenarios 3+4, ship = 5+6, admin = 7+8): the matched profile is
  mode-specific when the sum of its two-run mean profile-only scores over the mode's two scenarios exceeds the sum
  of the wrong-profile scores for the same assertions by 2 or more. Otherwise the mode's gain is attributed to
  generic instruction text and the mode's content is folded into the single posture block.
- A mode keeps its own profile when it meets both its keep rule above and the mode-specific check.
  Dev stays cut. The owner decides the outcome; this file only fixes how the evidence is read.
