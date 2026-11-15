# Transcript: prompt-retrieval eval 3, with_skill

Read SKILL.md and `references/prompt-retrieval-output-format.md` first.

## Commands run

1. `cd PROJ && <CLI> validate` (CLI = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`)

   Exit code 1. Key output:
   ```
   "project_root_source": "git",
   "warnings": [],
   "catalog_root": "PROJ\\.claude\\prompts",
   "root_source": "default",
   "errors": ["review__missing-tests/active.md: verification.quality does not match the current prompt text"],
   "ok": false,
   records: docs__changelog-entry (active, verified true), review__missing-tests (active, verified false,
   missing_verification [quality]), review__old-style (inactive)
   ```

Per Step 1, `ok: false` means the catalog is unavailable: stop. No list was rendered from the `records`
array, no `show` was run, and no record file was read directly. The non-zero exit is the expected invalid
result, not a tool failure.

The "run" half of the request belongs to `prompt-execution`, which is user-invoked only; this skill never
carries out a prompt's text. It was not started, and in any case the catalog failing validation (on that
exact prompt) would block it.

Suspicious content: none read (no prompt text was shown). Note: the failing record is the one the user
wants to run; its text no longer matches its quality verification hash, which may mean it was edited
after review.

## Questions asked

None. No question was needed; no scripted reply used.

## Final reply to user

The prompt catalog at `PROJ\.claude\prompts` (default) is unavailable: review__missing-tests/active.md: verification.quality does not match the current prompt text.

Nothing was listed. A catalog that fails validation cannot be listed from, because records in it may no longer match their verification. No warnings were reported.

The failing record is the missing-tests review prompt itself: its current text differs from the text that was verified, so it may have been changed since it was reviewed. Run `/prompt-library` to see how to recover the catalog (for example, re-reviewing and re-verifying that prompt). Please don't fix the record files by hand.

About running it: I can only look prompts up, not run them. Once the catalog validates again, you can run the prompt yourself with `/prompt-execution review__missing-tests`, which shows you the full text and asks for your approval first.
