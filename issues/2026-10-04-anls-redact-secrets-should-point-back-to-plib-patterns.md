## Summary
`anls_redact_secrets.py` should point back to promptlibrary-kit's diverged secret patterns, so a change to one pattern list does not drift from the other unnoticed (plugin-rulebook R20, duplicate fact sweep).

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`)
- **Region/Version**: branch `feature/promptlibrary-kit-wave0` (promptlibrary-kit Wave 0)

## Reproduction Steps
1. Open `plugins/promptlibrary-kit/scripts/plib_catalog_validate.py` and read the comment above `SECRET_PATTERNS` (near line 120). It says the shapes were seeded from `plugins/analysis-kit/scripts/anls_redact_secrets.py` and that the list diverges on purpose (extra shapes; it detects and blocks, never rewrites).
2. Open `plugins/analysis-kit/scripts/anls_redact_secrets.py` and look for any pointer to the promptlibrary-kit list near `_PATTERNS`.

## Expected Behavior
A short comment near `_PATTERNS` in `anls_redact_secrets.py` names the promptlibrary-kit list as a sibling that diverges on purpose. No behavior change. analysis-kit's tests and smoke test still pass, and mirror copies stay in sync.

## Actual Behavior
The pointer exists in one direction only (promptlibrary-kit to analysis-kit). A maintainer editing `_PATTERNS` has no hint that a related list exists elsewhere.

## Impact
**Low** - Comment-only documentation consistency; no functional break.

## Additional Context
Found during the promptlibrary-kit Wave 0 work. Suggested label: `t: documentation`.
