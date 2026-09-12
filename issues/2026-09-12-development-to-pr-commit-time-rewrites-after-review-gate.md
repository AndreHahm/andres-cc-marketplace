## Summary
`development-to-pr`'s new existing-PR `cross-model-review` gate (step 2.5) can review a diff that
`git-kit:commit`'s own step 7.5/8 then modifies before the actual push, so the pushed content can
differ from what was reviewed.

## Environment
- **Product/Service**: `workmanagement-kit` (`development-to-pr`), which invokes `git-kit`'s
  `cross-model-review` and `commit`
- **Region/Version**: this repo, PR #314 (`chore/workmanagement-kit-downstream-qa`), commit
  `93303937b9cf76f21dabc8f5332f370ca5371b14`

## Reproduction Steps
1. On `development-to-pr`'s existing-PR path, step 2.5(b) runs `Skill(git-kit:cross-model-review)`
   with `BASE=HEAD` against the pending uncommitted diff, and it clears (no findings, or all
   findings declined).
2. Step 3 invokes `Skill(git-kit:commit)`. If the staged change includes Python files or a
   canonical marketplace source (a mirrored `plugins/<name>/...` file), `commit`'s own step 7.5
   (`ruff check --fix`) and step 8 (marketplace-CI mirror sync/regeneration) can modify and re-stage
   content as part of that same invocation.
3. `commit`'s own step 16 then pushes the resulting commit immediately afterward, within the same
   invocation.

## Expected Behavior
The diff that reaches the remote should be the same diff `cross-model-review` actually reviewed at
step 2.5(b) — that is the entire point of running the gate before `commit` is invoked.

## Actual Behavior
Because step 7.5/8's rewrites happen *inside* the same `commit` invocation, after the gate already
cleared but before the push, the pushed diff can silently differ from the reviewed one. Nothing in
`development-to-pr`'s own procedure detects this or re-reviews the difference.

## Impact
**Major** — this undermines the review gate's own stated guarantee ("reviews exactly what step 3's
commit is about to capture and push") specifically for the class of changes most likely to trigger
`commit`'s own auto-fix/mirror-sync steps (Python scripts, canonical marketplace sources) — exactly
the kind of change a security- or correctness-relevant finding is likely to touch.

## Additional Context
Found live by a real Codex delta review dispatch (GitHub's CI-triggered automated review, not a
manually-run pass) against PR #314, `chatgpt-codex-connector[bot]`, P1 severity, inline comment on
`plugins/workmanagement-kit/skills/development-to-pr/SKILL.md:127`
(https://github.com/AndreHahm/andres-cc-marketplace/pull/314#discussion_r3995316138).

**Suggested next step** (not prescribing the fix): this needs either (a) a `git-kit:commit` change
exposing a way to skip step 7.5/8's auto-modification for a nested, already-reviewed invocation
(mirroring the existing push/Auto-PR skip instructions `create-pr` and `development-to-pr` already
pass it), or (b) `development-to-pr` itself diffing the actual pushed commit against what step
2.5(b) reviewed and re-running the gate on any delta before considering the push complete. Option
(a) is a `git-kit`-level change, out of scope for `workmanagement-kit`'s own PR, matching the same
"no git-kit skill owns X" pattern already tracked at
[#318](https://github.com/AndreHahm/andres-cc-marketplace/issues/318).
