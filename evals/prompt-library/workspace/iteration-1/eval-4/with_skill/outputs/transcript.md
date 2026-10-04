# Transcript: /prompt-library add (eval-4, with_skill)

CLI = uv run --isolated --no-project --no-config python "<plugin>/scripts/plib_catalog_validate.py"
PROJ = <fixtures>/prompt-library/eval-4/with_skill/proj (cd'd in every call)

## Commands and key output
1. `cd PROJ && ls -la && CLI validate` -> ok:false, errors ["catalog.yaml is missing"], catalog_root PROJ/.claude/prompts (root_source default), warning "local override catalog path rejected (resolves inside .claude/rules...); falling back".
   QUESTION: catalog missing at PROJ/.claude/prompts (default). Create it with init? [yes/no] -> REPLY: yes
2. `cd PROJ && CLI init; CLI validate; CLI new-id` -> init ok:true; validate ok:true, records []; new-id p34d8a9cae629.
3. Mode = add (from $ARGUMENTS). Intake: text typed by user -> origin user.
4. Write scratch draft (scratchpad dir, via Write tool) from the template: slug review__open-todo-summary, name "Open TODO summary", area review, origin user, internal_id p34d8a9cae629, version 1, status draft, boundaries "Read-only; ..."
5. `CLI screen <scratch>` -> ok:true, matches []. `CLI hash <scratch>` -> sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5, 1 nonblank line.
6. QUESTION (triage): one reusable instruction text (prompt) or a skill? -> REPLY: no, keep it a prompt. Catalog empty, so no duplicate to offer revising.
7. QUESTION: file this draft? (slug review__open-todo-summary, name Open TODO summary, origin user, description, hash b483711e...) -> REPLY: approve
8. `CLI draft <scratch>` -> ok:true, path review__open-todo-summary/p34d8a9cae629.md, text_hash b483711e...
9. Review (prompt-reviewer dispatch done INLINE by me, per env note d): 1 line (<=50), executor-neutral; Minor: success condition implicit, "open" undefined, empty-result behavior unstated. No Critical. No rewrite proposed.
10. `CLI show review__open-todo-summary --history` -> draft, verified false, text_hash b483711e...
    QUESTION: approve exactly this text (hash b483711e066f...)? -> REPLY: approve
11. `CLI record-verification p34d8a9cae629 --kind quality --expect-sha256 b483711e...` -> ok:true, recorded quality. (No import kind: origin is user.)
    QUESTION: activate review__open-todo-summary draft -> active, hash b483711e? -> REPLY: approve
12. `CLI activate p34d8a9cae629 --expect-sha256 b483711e...` -> ok:true, status active.
13. `CLI validate` -> ok:true, errors []; files: .claude/prompts/catalog.yaml, .claude/prompts/review__open-todo-summary/active.md

## Final reply to the user
Saved and activated the prompt `review__open-todo-summary` (version 1, origin: user) in the project catalog at `.claude/prompts/` (I created the catalog first, with your approval).

Text: "Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file." Hash b483711e. It passed the secret screen, was reviewed (minor notes only: the success condition and the no-TODOs case are implicit; I left your text unchanged), and you approved the exact text before it was verified and activated. The final catalog validation passes.

Note: the validator warned that a local override catalog path was rejected (it resolved inside `.claude/rules`), so the default location was used. Also, the prompt-reviewer review was done inline rather than by a dispatched agent.
