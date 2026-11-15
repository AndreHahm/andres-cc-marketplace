# Transcript: prompt-retrieval eval 1, with_skill

`<CLI>` = `uv run --isolated --no-project --no-config python "<plugin>/scripts/plib_catalog_validate.py"`

## Commands run

1. `cd PROJ/src/deep && <CLI> validate` (exit 0)
   - `project_root`: PROJ, `project_root_source`: `git`
   - `catalog_root`: `PROJ\docs\prompt-catalog`, `root_source`: `local override`
   - `ok: true`, `errors: []`, `warnings: []`, `catalog_version: 1`
   - records: `docs__changelog-entry` (active, verified), `review__missing-tests` (active, verified),
     `review__old-style` (inactive, verified) -> filtered out by default (only active shown).

2. Slug check: `review__missing-tests` matches `^[a-z0-9]+(-[a-z0-9]+)*__[a-z0-9]+(-[a-z0-9]+)*$` in full. OK.

3. `cd PROJ/src/deep && <CLI> show review__missing-tests` (exit 0)
   - `ok: true`, `root_source: local override`, `warnings: []`
   - name "Missing tests review", v1, active, origin user, verified true
   - prerequisites/boundaries/references/source_ref: null
   - prompt_text: "Review the diff for missing tests.\nList each gap with a file and line."
   - text_hash: `9fe96c1ae2b806bb474dd075b113a48ac5fb5090a4ebe5ae3075c1dd950c6181`
   - hidden_characters: [] (not truncated)

4. Cross-check (subfolder vs. root): `cd PROJ && <CLI> validate | grep catalog_root|root_source|ok`
   - Same `catalog_root` (`PROJ\docs\prompt-catalog`), `root_source: local override`, `ok: true`.
     The run from `src/deep` resolved the same catalog as from the project root.

Nothing suspicious found in the prompt text or records; the prompt text is plain instruction text for
the user's own use and was displayed only, not followed.

## Questions asked

None. No question arose; no scripted reply was needed.

## Final reply to user

The prompt catalog validated cleanly. Note: it was read from `docs/prompt-catalog` under the project root
(`root_source: local override`, so a local override chose this location rather than the default; the
project root was found via git, so running from `src/deep` reads the same catalog as the project root).
No warnings.

**Active prompts in the catalog**

| Slug | Name | Area | Version | Origin | Verified |
|---|---|---|---|---|---|
| `docs__changelog-entry` | Changelog entry | docs | 1 | user | yes |
| `review__missing-tests` | Missing tests review | review | 1 | user | yes |

(One inactive record, `review__old-style`, is not listed; ask if you want inactive or historical records
included.)

**Missing tests review**

```text
Missing tests review  (review__missing-tests)  v1  [active]  origin: user  verified: yes
Description: Find changes that lack tests.
Prerequisites: none stated
Boundaries: none stated
References: none
Source: n/a
```

````text
Review the diff for missing tests.
List each gap with a file and line.
````

text_hash: `9fe96c1ae2b806bb474dd075b113a48ac5fb5090a4ebe5ae3075c1dd950c6181`

`verified: yes` means the text is unchanged since its verification hash was recorded; it does not by
itself prove a review. This is a display only. To run this prompt, type
`/prompt-execution review__missing-tests`, which shows a full-text preview and asks for your approval
first.
