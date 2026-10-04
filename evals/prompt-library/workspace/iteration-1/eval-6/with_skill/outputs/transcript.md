# Transcript (eval-6, with_skill)

## Commands run
1. `cd <repo>/plugins/promptlibrary-kit/skills/prompt-library && cat references/prompt-intake-sources.md references/prompt-record-format.md assets/prompt-record-template.md`
   - Output: reference files read (origins, record format, template). Not needed further because step 1 failed.
2. `cd <proj> && ls -la && uv run --isolated --no-project --no-config python "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py" validate`
   - ls: .claude, .git, src
   - validate: exit 1, `"ok": false`, catalog_root `<proj>/.claude/prompts`, errors:
     `["review__missing-tests/active.md: verification.quality does not match the current prompt text"]`
   - records: docs__changelog-entry (active, verified), review__missing-tests (active, verified: false), review__old-style (inactive, verified)

## Skill decision (step 1 Preflight)
The catalog exists but is not ok. The error is not an `unlisted record file on disk` orphan, so there is no recoverable case. The skill says to report the errors and refuse every change. Steps 2-10 were not run: no scratch file, screen, draft or filing.

## Questions asked
None. (The only offered question, orphan discard, does not apply. Nothing else would change a file anyway; conservative default would be decline.)

## Final reply to user
I did not save the prompt. The prompt library failed its preflight check, and the skill refuses every change until the catalog is valid.

The validator reported one error in `.claude/prompts`:

- `review__missing-tests/active.md: verification.quality does not match the current prompt text`

The active prompt `review__missing-tests` was edited after its verification hash was recorded, so it is no longer verified. I did not repair it, and I changed no files.

To go on, pick one:
1. Revise `review__missing-tests`: re-approve its exact text, then record verification again. This is a catalog change and needs your approval.
2. Restore its text to what was verified, for example from git.

After the catalog validates, run `/prompt-library add` again. Your text is ready to file: "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file."
