# Transcript eval-7 (with_skill): /prompt-library add

CLI = uv run --isolated --no-project --no-config python <plugin>/scripts/plib_catalog_validate.py
(proj = the eval project dir; every call run after cd into it)

## Commands and key output
1. `CLI validate` -> ok:false, errors: "unlisted record file on disk: review__orphan-draft/p0000000000ff.md"; 3 records (docs__changelog-entry, review__missing-tests active; review__old-style inactive).

QUESTION (AskUserQuestion, step 1): "The catalog has an orphan record file from an interrupted draft: review__orphan-draft/p0000000000ff.md (catalog root .../proj/.claude/prompts). Remove it with discard-orphan?" Options: Remove it / Leave it (add refused).
REPLY USED: yes, approve.

2. `CLI discard-orphan review__orphan-draft/p0000000000ff.md` -> ok:true, removed that file.
3. `CLI validate` -> ok:true, errors: [].
4. Mode: add (first word of $ARGUMENTS). Intake origin: user (typed text).
5. `CLI new-id` -> internal_id p82fc701d0e48
6. Write scratch draft (session scratchpad): slug maintenance__summarize-open-todos, area maintenance, origin user, boundaries "Read-only; never modify any file."
7. `CLI screen <scratch>` -> ok:true, matches: [].
8. `CLI hash <scratch>` -> sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5, 1 nonblank line.
9. Triage (stated to user): single reusable instruction text, so a prompt, not a skill; no existing record in the same area or with a similar name (docs, review areas only), so no revision offered.

QUESTION (AskUserQuestion, step 6): "File this draft? slug maintenance__summarize-open-todos; name Summarize open TODOs; origin user; description 'Lists the open TODO comments in the repository as a table without changing any file.'; hash b483711e..." Options: File draft / Don't file.
REPLY USED: decline (per USER REPLIES).

Steps 7-9 not run (nothing filed; no reviewer dispatch needed).
10. Final `CLI validate` run was done after the orphan removal (ok:true); nothing changed since, no catalog write after that.

## Final reply to user
The catalog had an orphan draft file (review__orphan-draft/p0000000000ff.md) from an interrupted draft. With your approval I removed it; the catalog now validates ok.

I prepared your prompt as a draft but did not file it, since you declined:
- slug: maintenance__summarize-open-todos
- name: Summarize open TODOs, origin: user
- text hash: b483711e... (secret screen clean)
It is a single reusable prompt (not a skill) and no similar prompt exists. Nothing was added to the catalog, and no prompt was activated. Re-run /prompt-library add to file it.
