# Transcript: /prompt-library add (eval-3, with_skill)

CLI = uv run --isolated --no-project --no-config python <plugin>/scripts/plib_catalog_validate.py
(run from the proj dir, with the plugin root substituted)

## Commands and key output
1. `<CLI> validate` -> ok:false, errors ["catalog.yaml is missing"], catalog_root = proj/.claude/prompts, root_source default. exit 1.
2. QUESTION (AskUserQuestion): "No catalog exists. Create it at proj/.claude/prompts (root_source: default)?" Options: Create / Cancel. REPLY: yes.
3. `<CLI> init` -> ok:true. `<CLI> validate` -> ok:true, records []. `<CLI> new-id` -> internal_id p4f0ccc561f12.
4. Mode: add (first word of arguments). Intake: user-typed text, so origin user. Draft built from the template into scratchpad draft-todo.md (via Write tool): slug maintenance__summarize-open-todos, area maintenance, boundaries "Read-only; do not use it to resolve or remove TODOs."
5. `<CLI> screen <draft>` -> ok:true, matches []. `<CLI> hash <draft>` -> sha256 52fefc6abfc8fc23c282655fcf24ea8c24d82c2a157689cded396a7aba2522a4, 1 nonblank line.
6. QUESTION (triage): "Is this one reusable instruction text (prompt), or does it need scripts/tools/automatic activation (skill)?" REPLY: no, keep it a prompt. Catalog empty, so no duplicate to offer as a revision.
7. QUESTION: "File this draft? slug maintenance__summarize-open-todos, name Summarize open TODOs, origin user, hash 52fefc6a..." REPLY: approve.
8. `<CLI> draft <draft>` -> ok:true, path maintenance__summarize-open-todos/p4f0ccc561f12.md, text_hash 52fefc6a...
9. Review: prompt-reviewer was NOT dispatched; I reviewed inline. No Critical findings. Advisory: does not say whether vendored/generated dirs are excluded, nor what to output if there are no TODOs. No rewrite proposed, so no update-draft.
10. `<CLI> show maintenance__summarize-open-todos --history` -> status draft, verified false, text_hash 52fefc6a..., text matches.
11. QUESTION: "Approve exactly this text (hash 52fefc6a...)?" REPLY: approve.
12. `<CLI> record-verification p4f0ccc561f12 --kind quality --expect-sha256 52fefc6a...` -> ok:true, recorded quality. (No import verification: origin is user.)
13. QUESTION: "Activate maintenance__summarize-open-todos (draft -> active, hash 52fefc6a)?" REPLY: approve.
14. `<CLI> activate p4f0ccc561f12 --expect-sha256 52fefc6a...` -> ok:true, status active.
15. `<CLI> validate` -> ok:true, errors []. Files: .claude/prompts/catalog.yaml, .claude/prompts/maintenance__summarize-open-todos/active.md.

Note: references/ and assets/ live under skills/prompt-library/, not the plugin root (first ls at the plugin root failed; corrected).

## Final reply to the user
Saved and activated the prompt `maintenance__summarize-open-todos` (version 1, origin user) in a new catalog at `.claude/prompts/`.

Text: "Summarize the open TODO comments in the repository as a table with the columns file, line and a one-line description. Do not change any file."
Hash 52fefc6a, quality verified, secret screen clean, catalog validates ok.

Review notes (advisory, nothing changed): the prompt does not say whether vendored or generated directories are excluded, nor what to output when no TODOs exist. Say so if you want a revision that adds that.
