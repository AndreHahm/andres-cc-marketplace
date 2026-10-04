# Transcript eval-8 (with_skill): /prompt-library add

CLI = `uv run --isolated --no-project --no-config python <plugin>/scripts/plib_catalog_validate.py` (run from the project dir).

## Commands and key output
1. `cat references/prompt-intake-sources.md references/prompt-record-format.md references/prompt-optimization-and-review.md assets/prompt-record-template.md` (read skill references)
2. `<CLI> validate` -> ok:true; records: docs__changelog-entry (active), review__missing-tests p000000000001 v1 (active, text "Review the diff for missing tests.\nList each gap with a file and line."), review__old-style (inactive).
3. `<CLI> show review__missing-tests --history` -> predecessor text and hash 9fe96c1a...; `<CLI> new-id` -> pd4660b7dce1d
4. Write scratch-v2.md (scratchpad): slug review__missing-tests, version 2, previous_id p000000000001, origin user, status draft, body = the user's text.
5. `<CLI> screen <scratch>` -> ok:true, no matches. `<CLI> hash <scratch>` -> 6e16942d... (1 nonblank line).
6. `<CLI> draft <scratch>` -> ok, path review__missing-tests/pd4660b7dce1d.md.
7. `<CLI> show review__missing-tests --history` -> draft v2, verified:false, hash 6e16942d...
8. `<CLI> record-verification pd4660b7dce1d --kind quality --expect-sha256 6e16942d...` -> ok (no import kind: origin user).
9. `<CLI> finalize pd4660b7dce1d --expect-sha256 6e16942d... --active` -> ok, status active.
10. `<CLI> validate` -> ok:true; v2 active, v1 historical.

## Questions and replies
- Triage: one reusable instruction text (prompt) or skill? Options: prompt / skill. Reply: no, keep it a prompt.
- Similar prompt review__missing-tests exists. Revise it, or add new? Reply: yes, revise it (switched to revise mode: version 2, previous_id p000000000001, same slug/area).
- File this draft? (slug review__missing-tests, name Missing tests review, origin user, hash 6e16942d) Reply: approve.
- Step 7 review done inline (no prompt-reviewer dispatch): clear, single goal, no secrets, no Critical findings; no rewrite proposed, text kept exactly as the user gave it.
- Approve exactly this text and hash 6e16942d? Reply: approve.
- Finalize review__missing-tests v2 as active, v1 becomes historical (6e16942d)? Reply: approve, make active.

## Notes
- SKILL.md says --inactive is "the only useful choice" when the predecessor was active; the user asked for active and the validator accepted --active.
- The user-supplied "add" was converted to a revision after the triage choice.

## Final reply
Saved as a revision of your existing prompt `review__missing-tests`. It is now version 2 and active, and version 1 is kept as historical. The text is exactly what you gave me: "Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it." (hash 6e16942d). It is a prompt, not a skill, since it needs no scripts. No secrets were found, and the catalog validates clean. I did the review step myself, with no reviewer agent, and it raised no concerns.
