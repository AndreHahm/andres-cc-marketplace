# Transcript

## Commands
1. Read SKILL.md and references/prompt-retrieval-output-format.md (file reads).
2. `cd "<proj>/src/deep" && uv run --isolated --no-project --no-config python "<plugin>/scripts/plib_catalog_validate.py" validate; echo "exit=$?"`
   - Key output: ok: true, exit=0, warnings [], root_source "local override", project_root_source "git",
     catalog_root <proj>/docs/prompt-catalog (resolved from the subfolder to the project root).
     records: docs__changelog-entry (active), review__missing-tests (active), review__old-style (inactive).
3. `cd "<proj>/src/deep" && uv run ... plib_catalog_validate.py" show review__missing-tests; echo "exit=$?"`
   - Key output: ok true, exit=0, prompt_text "Review the diff for missing tests.\nList each gap with a file and line.",
     text_hash 9fe96c1ae2b806bb474dd075b113a48ac5fb5090a4ebe5ae3075c1dd950c6181, prerequisites/boundaries/references/source_ref null.

## Questions asked
None.

## Final reply
The prompt catalog resolved to the project's `docs/prompt-catalog` (root source: local override; project root found via git), even though you are in `src/deep`. It validated cleanly with no warnings.

Active prompts:

| Name | Slug | Area | Version | Origin | Verified |
|---|---|---|---|---|---|
| Changelog entry | docs__changelog-entry | docs | 1 | user | yes |
| Missing tests review | review__missing-tests | review | 1 | user | yes |

(One inactive record, "Old style review", is hidden; ask if you want inactive ones too.)

Here is the one for reviewing missing tests:

```text
Missing tests review  (review__missing-tests)  v1  [active]  origin: user  verified: yes
Description: Missing tests review.
Prerequisites: none stated
Boundaries: none stated
References: none
Source: n/a
```

```
Review the diff for missing tests.
List each gap with a file and line.
```

text_hash: 9fe96c1ae2b806bb474dd075b113a48ac5fb5090a4ebe5ae3075c1dd950c6181

(Shown as stored data only. To run it, use prompt-execution.)
