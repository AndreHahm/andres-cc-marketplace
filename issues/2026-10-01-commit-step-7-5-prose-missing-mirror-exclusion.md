# commit skill: step 7.5 prose does not mention that generated mirrors are skipped

## Summary
`git-lint-staged-python.sh` now skips staged Python under `.claude/`, `.agents/` and `.codex/` in a marketplace-CI repo, but the `commit` skill's step 7.5 text and its "Important Notes" line still describe every staged `.py` file as formatted and type-checked.

## Environment
- **Product/Service**: git-kit `commit` skill (`plugins/git-kit/skills/commit/SKILL.md`)
- **Region/Version**: branch `feat/mirror-plugin-root-shared-folders`, commit `6e5b0b5d`

## Reproduction Steps
1. Read `plugins/git-kit/skills/commit/SKILL.md` step 7.5 (around line 132) and the "Important Notes" bullet (around line 342).
2. Read the script's header comment in `plugins/git-kit/scripts/git-lint-staged-python.sh`.

## Expected Behavior
The skill text states the exclusion: when `.claude/marketplace-sync.json` exists, generated mirrors and exports are not auto-formatted or type-checked.

## Actual Behavior
- Line 132 says the script "derives the staged `.py` list itself".
- Line 342 says "In this repository, a staged `.py` file is auto-formatted and auto-fixed with `ruff format`/`ruff check --fix` ... and type-checked with `ty check`".
- Neither mentions the exclusion. This is incomplete rather than contradictory, so a reader could expect mirrored files to be reformatted.

## Visual Evidence
None.

## Impact
**Low** - Documentation completeness only. The behavior itself is correct and covered by tests.

## Additional Context
- **Why the exclusion exists:** the old behavior reformatted mirrored copies in place, breaking byte-parity with their sources. `check-all --staged` did not catch it when the source file was not also staged.
- **Why the prose was left alone in the fixing commit:** editing a SKILL.md is a skill-behavior prose change. Per `.claude/rules/require-tests-for-behavior-changes.md` it needs a test (a `skill-tester` eval or the Testing & Validation section), a plugin-rulebook pass, and regeneration of the `.claude/skills/commit/SKILL.md` mirror.
- The script's own behavior is already covered by `tests/marketplace_ci/test_lint_staged_python_script.py` (3 tests).
- Also re-read `plugins/git-kit/skills/commit/references/staging-fix-verification-log.md`'s step 7.5 narrative to confirm it still reads correctly.
- Related: #446, commit `6e5b0b5d`.
