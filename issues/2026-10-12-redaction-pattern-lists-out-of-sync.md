## Summary
The secret-redaction pattern list is hand-copied across four files and has drifted: fine-grained GitHub tokens (`github_pat_…`) are redacted in two of them and not the other two, and the bridge's dotenv-style rule misses an assignment that is not at the start of a line.

## Environment
- **Product/Service**: `codex-kit` (`plugins/codex-kit/scripts/lib/codex-exec.mjs`), `analysis-kit` (`plugins/analysis-kit/scripts/anls_redact_secrets.py`), `promptlibrary-kit` (`plugins/promptlibrary-kit/scripts/plib_catalog_validate.py`), marketplace CI (`scripts/marketplace_ci/review.py`)
- **Region/Version**: `main` plus the #544 fix (branch `fix/codex-exec-misclassified-exit`)
- **Browser/OS**: Linux

## Reproduction Steps
1. Run `redactSecrets` from `plugins/codex-kit/scripts/lib/codex-exec.mjs` on text containing a fine-grained GitHub token (`github_pat_` prefix): it is redacted after the #544 fix.
2. Run the same text through `plugins/analysis-kit/scripts/anls_redact_secrets.py` and the `SECRET_PATTERNS` check in `plugins/promptlibrary-kit/scripts/plib_catalog_validate.py`: neither recognizes it.
3. Run `redactSecrets("could not read env DATABASE_PASSWORD=<value> then more")`.

## Expected Behavior
The same secret shapes are recognized in every copy of the list, or each divergence is recorded as intentional. A `NAME_PASSWORD=<value>` assignment is redacted wherever it appears in the text.

## Actual Behavior
- The `github_pat_` shape is matched in `codex-exec.mjs` and `review.py`. The classic `gh[pousr]_` shape is the only GitHub shape in `anls_redact_secrets.py` (line 44) and `plib_catalog_validate.py` (line 142).
- `codex-exec.mjs`'s own comment says its list was ported from `anls_redact_secrets.py`, and that file's header says to check the sibling `plib` list when a pattern changes. The repo's duplicate-fact sweep (R20) expects sibling occurrences to be updated or the divergence recorded. Neither happened.
- The dotenv-style rule in `redactSecrets` (and its analysis-kit counterpart) is line-anchored (`^…=.+$` with the multiline flag), so step 3 above returns the text unchanged. `review.py` now has a value-only mid-line rule for its own error path, but the bridge's redactor still misses the case.

## Error Details
~~~
Verified by execution (Node and Python), 2026-10-12: a github_pat_-prefixed token is
unchanged by review.py before the #544 fix and redacted after; the mid-line
NAME_PASSWORD=<value> case is returned unchanged by redactSecrets.
~~~

## Visual Evidence
None.

## Impact
**Low** - Only text that reaches a persisted report or CI log matters. `review.py` now catches both shapes at the report boundary, so the remaining exposure is other consumers of `anls_redact_secrets.py` and `plib_catalog_validate.py`, and bridge detail text before it reaches `review.py`.

## Additional Context
Found by the cross-model review of the #544 fix (findings E1 and M1).

Needed:
- add `github_pat_` to `anls_redact_secrets.py` and `plib_catalog_validate.py`, with a test case each (`plugins/analysis-kit/tests/test_redact_secrets.py` exists);
- decide whether the dotenv rule should match mid-line assignments, with value-only replacement as in `review.py`;
- consider whether the four lists should share one source of truth instead of hand-copied duplicates, or record the intentional divergences.

Related: #544 (the fix where this was found), #545.
