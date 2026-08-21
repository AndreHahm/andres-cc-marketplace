## Summary
`plugin-lifecycle-downstream`'s Phase 2 (Prepare) only checks whether *some* test mechanism exists for a scoped skill (a `skill-tester` eval suite, or a `scripts/smoke_test.*`) before deciding whether to ask about creating missing assets. It doesn't check whether a skill matches the narrower, real sub-convention some of its own siblings already use — a persisted `scripts/smoke_test.py` *in addition to* eval coverage, for skills at a specific complexity tier. This let a real gap through undetected until a much later, manual audit pass caught it.

## Environment
- **Product/Service**: `plugin-lifecycle-downstream`'s Phase 2 (Prepare) procedure
- **Region/Version**: this repo, found live during a `plugin-lifecycle-downstream` run scoped to `feat/review-findings-handling` (git-kit plugin)

## Reproduction Steps
1. Build a new skill in `git-kit` with `skill-tester` eval coverage (`evals/<skill>/evals.json`) but no `scripts/smoke_test.py` of its own.
2. Run `plugin-lifecycle-downstream`'s Phase 2 against that skill.
3. Observe: Phase 2 concludes "no missing REQUIRED smoke tests/evals" and records itself `skipped`, since a test mechanism (the eval suite) already exists.
4. Separately check: 4 of `git-kit`'s 20 skills (`commit`, `merge-pr`, `codex-review-recovery`, `cross-model-review`) already carry their own `scripts/smoke_test.py` *alongside* `skill-tester` evals — a real, consistent pattern for complex, heavily-interactive skills in this plugin. The new skill matches that same complexity profile (multi-branch logic, settings-gate branching, external API mechanics) but Phase 2 never surfaced the missing smoke test as a candidate asset to ask about.

## Expected Behavior
Phase 2 should compare a scoped skill's own characteristics (complexity, presence of branching logic, existing sibling conventions within the same plugin) against whichever of its type-comparable siblings already carry a `scripts/smoke_test.py`, and surface a missing one as a candidate asset the user can approve or decline — not conclude "covered" purely because *a* test mechanism exists.

## Actual Behavior
Phase 2's own "missing assets" check is binary (mechanism present/absent), not tier-aware, so it silently passed a skill missing the smoke-test layer its closest siblings all have.

## Impact
**Medium** — no user-facing harm occurred this run (the gap was caught manually, mid-session, when the user asked directly why Phase 2 had been skipped, and folded into a later fix batch), but the failure mode is exactly the kind of "quiet gap that later analysis has to catch by hand" this pipeline exists to prevent. A less attentive run would ship a skill missing its expected structural-smoke-test coverage with Phase 2 having explicitly (and wrongly) reported "nothing missing."

## Additional Context
- Confirmed pattern: `commit`, `merge-pr`, `codex-review-recovery`, `cross-model-review` all have both `scripts/smoke_test.py` AND `evals/<skill>/evals.json`; the other 16 `git-kit` skills have neither the smoke test nor (in most cases) the eval suite.
- This is not a proposal to make `scripts/smoke_test.py` mandatory for every skill plugin-wide — it's specifically about Phase 2 failing to *surface the comparison* for the user to decide, the same way it already asks about genuinely missing coverage today.
- Suggested follow-ups (not implemented as part of this issue):
  - Add a step to Phase 2's scope inventory: for each scoped skill, glob its type-comparable siblings within the same plugin (or across the scope manifest) for `scripts/smoke_test.py` presence, and if a majority/notable fraction have one while the scoped skill doesn't, surface it as a candidate missing asset in the same `AskUserQuestion` Phase 2 already uses for genuinely-absent coverage.
  - Consider whether this comparison belongs in Phase 2 itself or as a `completeness-reviewer`/Phase 5 check instead, since it's arguably closer to a documentation-consistency concern than a "build missing test infrastructure" concern — either placement fixes the actual gap; this issue doesn't mandate one over the other.
