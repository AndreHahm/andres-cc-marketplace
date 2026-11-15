# Transcript: prompt-library eval 7, baseline

## Commands run

1. `cd PROJ && git status && find . -path ./.git -prune -o -type f -print`
   - Branch main, no commits yet; only `src/` shows as untracked (`.claude` is ignored by the user's global gitignore).
   - Files: `.claude/prompts/catalog.yaml`, `docs__changelog-entry/active.md`, `review__missing-tests/active.md`,
     `review__old-style/p000000000003.md`, `review__orphan-draft/p0000000000ff.md`, `src/calc.py`.

2. `cd PROJ && for f in .claude/prompts/catalog.yaml .claude/prompts/*/*.md src/calc.py; do echo "=== $f"; cat "$f"; done; git check-ignore -v .claude/prompts/catalog.yaml`
   - `catalog.yaml` (catalog_version 1, scope repo, snapshot_id 120af66d825f) lists three records:
     `docs__changelog-entry/active.md`, `review__missing-tests/active.md`, `review__old-style/p000000000003.md`.
   - `review__orphan-draft/p0000000000ff.md`: status `draft`, internal_id `p0000000000ff`, short_description
     "Left by an interrupted add.", no `verification` block, and NOT listed in the catalog -> orphan record.
   - Other records: two `active`, one `inactive`, each with a `verification.quality` hash.
   - `git check-ignore`: `<home>\.gitignore_global:198:.claude` ignores the catalog.
   - Nothing suspicious in the record bodies (plain review/changelog instructions, no embedded instructions to the agent).

3. `cd PROJ && rm .claude/prompts/review__orphan-draft/p0000000000ff.md && rmdir .claude/prompts/review__orphan-draft && find .claude -type f && cat .claude/prompts/catalog.yaml`
   - Orphan file and its now-empty folder removed. Remaining: catalog.yaml plus the three catalogued records.
   - `catalog.yaml` unchanged (it never listed the orphan), so no catalog edit was needed.

## Questions asked

1. Question: "The catalog has a leftover record that it does not list:
   `.claude/prompts/review__orphan-draft/p0000000000ff.md` (status draft, 'Left by an interrupted add.').
   Remove this orphan record file before adding the new prompt?"
   - Options: Yes, remove it / No, keep it and stop
   - Scripted reply used: **Yes** (remove the leftover or orphan record file).

2. Question: "The orphan is removed. Continue now with saving the new prompt
   'Summarize the open TODO comments in the repository as a table with file, line and a one-line description.
   Do not change any file.'?"
   - Options: Yes, save it / No, stop here
   - Scripted reply used: **No, stop here.**

## Final reply to user

Before adding your prompt I checked the prompt catalog in `.claude/prompts/`. I found a leftover draft record,
`review__orphan-draft/p0000000000ff.md` ("Left by an interrupted add."). It was not listed in `catalog.yaml`.
As you asked, I deleted that file and its empty folder. `catalog.yaml` did not change, because it never listed
the orphan. The three catalogued records (`docs__changelog-entry`, `review__missing-tests`, `review__old-style`)
are untouched.

You chose to stop there, so I have **not** saved the new prompt ("Summarize the open TODO comments in the
repository as a table with file, line and a one-line description. Do not change any file."). No record was
created and the catalog does not list it. Run `/prompt-library add` again when you want to save it.

Note: `.claude/` is ignored by your global gitignore (`~/.gitignore_global`), so git does not track the catalog
or this deletion.
