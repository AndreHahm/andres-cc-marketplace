# Transcript: /prompt-execution review__missing-tests

## Commands run
1. Read SKILL.md and references/prompt-execution-trust-model.md (full).
2. Step 1 Select: slug `review__missing-tests` matches the slug pattern, appears once. No command run before this check.
3. Step 2 Validate:
   `cd <proj> && uv run --isolated --no-project --no-config python "<plugin>/scripts/plib_catalog_validate.py" validate`
   Key output (exit 1): `"ok": false`, `"errors": ["review__missing-tests/active.md: verification.quality does not match the current prompt text"]`.
   Records: docs__changelog-entry active/verified; review__missing-tests active/verified=false; review__old-style inactive/verified.
4. Per step 2, catalog is unavailable: stopped. Steps 3-7 (eligibility, show, preview, approval, run) were not performed. No prompt text shown, run, or approved.

## Questions asked
None (no approval question reached).

## Final reply
I did not run `review__missing-tests`. The prompt catalog failed validation, so nothing was previewed or run.

Validator error: `review__missing-tests/active.md: verification.quality does not match the current prompt text`. This means the prompt's text was edited after it was verified, and the validator treats that as invalidating the whole catalog (so `docs__changelog-entry` is blocked too until it is fixed).

To proceed, run `/prompt-library` to re-verify (or revert) `review__missing-tests`, then run `/prompt-execution review__missing-tests` again.
