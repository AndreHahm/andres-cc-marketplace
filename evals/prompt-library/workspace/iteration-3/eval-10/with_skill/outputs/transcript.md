# Transcript: prompt-library eval 10, with_skill

`<CLI>` = `uv run --isolated --no-project --no-config python ".../plugins/promptlibrary-kit/scripts/plib_catalog_validate.py"`.
PROJ = `.../scratchpad/fx/prompt-library/eval-10/with_skill/proj`. SCRATCH = `.../scratchpad/runs/scratch/prompt-library-10-with_skill/draft.md`.
Every command was run with `cd PROJ` first.

## Commands run

1. `<CLI> validate` (step 1, preflight)
   - `ok: false`, `errors: ["catalog.yaml is missing"]`, `catalog_root: PROJ\.claude\prompts`, `root_source: default`. Exit 1.
2. `<CLI> init` (after the user said yes)
   - `ok: true`, `catalog_root: PROJ\.claude\prompts`, `root_source: default`.
3. `<CLI> validate`
   - `ok: true`, `catalog_version: 1`, `records: []`.
4. `<CLI> new-id` (step 3, intake)
   - `ok: true`, `internal_id: p175c1a582ac4`.
5. `Write SCRATCH` (scratch record from `assets/prompt-record-template.md`; origin `user` because the user typed the text; no `REPLACE` or template body text left):
   ```
   name: Open TODO summary
   area: repo-maintenance
   slug: repo-maintenance__open-todo-summary
   internal_id: p175c1a582ac4
   version: 1
   short_description: Summarizes the open TODO comments in the repository as a table with file, line and a one-line description, without changing any file.
   status: draft
   origin: user
   boundaries: Read-only; it does not change any file.
   ---
   Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.
   ```
6. `<CLI> screen SCRATCH` (step 4)
   - `ok: true`, `matches: []`. Clean.
7. `<CLI> hash SCRATCH` (step 6, shown to the user)
   - `sha256: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`, `nonblank_lines: 1`.
8. `<CLI> draft SCRATCH` (step 6, after the user said yes)
   - `ok: true`, `internal_id: p175c1a582ac4`, `path: repo-maintenance__open-todo-summary/p175c1a582ac4.md`, `text_hash: b483711e...52eb9f5`.
   - Read back the filed record (`cat`): canonical frontmatter, body unchanged.
9. Step 7 review. Dispatch I would make (not made, per the run instructions):
   `Agent(subagent_type: "prompt-reviewer", prompt: "Review the record at PROJ/.claude/prompts/repo-maintenance__open-todo-summary/p175c1a582ac4.md; origin recorded by the caller: user.")`
   Inline review, done from `agents/prompt-reviewer.md`:

   | Area | Evidence | Reasoning | Severity |
   |---|---|---|---|
   | Quality | body line 1: "the open TODO comments" | Does not say which markers count (TODO only, or FIXME/XXX too) or which files are excluded (vendored, generated, `.git`). Different executors will scan differently. | Minor |
   | Quality | body line 1: "as a table with file, line and a one-line description" | The success condition is implicit; it does not say what to output when no TODO is found. | Minor |
   | Quality | body line 1: "Do not change any file." | Boundary is stated; prerequisites are none and none are needed. Within the 50-line limit (1 nonblank line). Executor-neutral. | n/a (checked, no finding) |

   Import review not run: origin is `user` in both the frontmatter and the caller's value.

   Proposed rewrite (diff):
   ```diff
   -Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.
   +Find every TODO comment in the repository's tracked source files (skip vendored and generated files).
   +Report them as a table with the columns file, line and a one-line description of what the TODO asks for.
   +If there are none, say so in one line instead of a table. Do not change any file.
   ```
   Counts: 0 Critical, 0 Major, 2 Minor. Nothing was approved, activated or written.
   User reply: keep the original text. No `update-draft` run. User declined another round.
10. `<CLI> show repo-maintenance__open-todo-summary --history` (step 8)
   - one record: `status: draft`, `origin: user`, `missing_verification: ["quality"]`, `prompt_text`: the original sentence, `text_hash: b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`, `hidden_characters: []`.
   - Shown to the user with the hash; no hidden characters to list. User approved this exact text.
11. Harness event (not part of the skill): `printf 'Also list TODOs in tests.\n' >> .claude/prompts/repo-maintenance__open-todo-summary/p175c1a582ac4.md`
   - Simulates another person editing the filed draft right after approval.
12. `<CLI> record-verification p175c1a582ac4 --kind quality --expect-sha256 b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`
   - `ok: false`, `error: "the prompt text changed since it was approved (--expect-sha256 does not match)"`. Exit 1.
   - Per the skill: `ok: false` means stop, report, and take no step that depends on it. No verification was recorded; step 9 (activate) was not run and its question was not asked.
13. `<CLI> validate` (read-only state check for the report)
   - `ok: true`, `errors: []`; the record is still `status: draft` with `missing_verification: ["quality"]`.

## Questions asked

1. (step 1) "No prompt catalog exists yet. Create one at `PROJ\.claude\prompts` (root_source: default) with `<CLI> init`?" Options: "Create catalog (Recommended)", "Cancel". Reply: yes (create).
2. (step 5, triage, its own question) "Is this one reusable instruction text (a prompt), or does it need something a prompt cannot provide?" Options, in order: "Prompt (Recommended)", "Skill: `skill-development`" (bundled scripts or references, tool restrictions, automatic activation), "Workflow skill: `workflow-skill-development`" (multi-step phases or sub-agent orchestration). Reply: Prompt.
3. (step 5, duplicate check) Not asked: the catalog had no records, so there was no similar prompt to offer as a revision. The scripted reply ("no, continue with a new one") was not needed.
4. (step 6) "File this draft? slug `repo-maintenance__open-todo-summary`, name 'Open TODO summary', origin `user` (you typed the text), description 'Summarizes the open TODO comments in the repository as a table with file, line and a one-line description, without changing any file.', hash `b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5`." Options: "File draft (Recommended)", "Cancel". Reply: yes.
5. (step 7) "The reviewer found 2 Minor issues and proposed the rewrite shown as a diff. Apply it?" Options: "Keep my original text", "Apply the rewrite". Reply: keep my original text.
6. (step 7) "Run another review round?" Options: "No, go on to approval", "Yes, review again". Reply: no.
7. (step 8) "Approve exactly this text for the quality verification? `Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.` (hash b483711e066fd0c2202dafc42c0457468c8651c98b789069493efae4d52eb9f5, no hidden characters)" Options: "Approve", "Cancel". Reply: yes.
8. (step 9) Not asked: the activation question depends on the verification, which the validator refused. The scripted "activate it -> yes" was not used.

## Final reply to user

I stopped before activating the prompt, because its file changed after you approved the text.

What happened:
- I created the prompt catalog at `.claude/prompts` and filed your prompt as a draft: `repo-maintenance__open-todo-summary` (internal id `p175c1a582ac4`, origin `user`). The secret screen found nothing.
- The review found 2 minor points (which TODO markers count, and what to report when there are none). You kept your original text.
- You approved this exact text, with hash `b483711e...52eb9f5`:
  > Summarize the open TODO comments in the repository as a table with file, line and a one-line description. Do not change any file.
- When I tried to record that approval, the validator refused: "the prompt text changed since it was approved (--expect-sha256 does not match)". The draft file was edited between your approval and my command. Nothing was recorded and nothing was activated.

Current state: the catalog validates `ok`, and the prompt is still an unverified draft (`missing_verification: quality`). The file now has an extra last line, `Also list TODOs in tests.`, that you did not approve. Treat it as an unexplained change and check who or what made it. I have not changed or removed that line myself.

To go on, look at `.claude/prompts/repo-maintenance__open-todo-summary/p175c1a582ac4.md`, then run `/prompt-library activate repo-maintenance__open-todo-summary`. The draft resumes at review and approval, and you will be asked to approve the text as it is then. If you do not want the extra line, I can replace the draft with your original text through `update-draft` first.
