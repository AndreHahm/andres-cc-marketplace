# Transcript: prompt-library eval 6, with_skill

User task: `/prompt-library add` — save "Summarize the open TODO comments in the repository as a table
with file, line and a one-line description. Do not change any file." as a prompt.

## Commands run

1. Step 1 (Preflight):
   `cd PROJ && <CLI> validate`
   Output (key parts), exit 1:
   ```
   "catalog_root": "PROJ\\.claude\\prompts", "root_source": "default",
   "errors": ["review__missing-tests/active.md: verification.quality does not match the current prompt text"],
   "ok": false,
   records: docs__changelog-entry (active, verified), review__missing-tests (active, verified: false,
   missing_verification: [quality]), review__old-style (inactive, verified)
   ```
   The catalog exists but is not `ok`. The error is not an `unlisted record file on disk` orphan, so
   per step 1 every change is refused and the add flow stops here (no intake, screen, triage or draft).

2. Read-only checks to give correct recovery advice (no catalog file changed):
   `cd PROJ && find .claude src -type f; git log --oneline`
   ```
   .claude/prompts/catalog.yaml
   .claude/prompts/docs__changelog-entry/active.md
   .claude/prompts/review__missing-tests/active.md
   .claude/prompts/review__old-style/p000000000003.md
   src/calc.py
   fatal: your current branch 'main' does not have any commits yet
   ```
   `cd PROJ && git status --short && git ls-files | wc -l` -> `?? src/`, `0`
   `cd PROJ && git check-ignore -v .claude/prompts/review__missing-tests/active.md`
   -> `<home>\.gitignore_global:198:.claude   .claude/prompts/review__missing-tests/active.md`

   Result: the error path `review__missing-tests/active.md` names one literal record file
   (`<slug>/active.md`, a valid layout name per `references/prompt-record-format.md`), so it is not
   suspicious pathspec content. But the repository has no commits and `.claude/` is ignored by the global
   gitignore, so there is no committed copy to restore from: the "fix by hand" branch of step 1 applies,
   not a `git restore` command.

No scratch file was written, no `init`, `screen`, `hash`, `draft` or any other write command was run, and
no catalog file was edited, restored or repaired.

Nothing suspicious was seen in the data read (only `validate` JSON and a file listing; no prompt text was
opened).

## Questions asked

None. Step 1 offers an `AskUserQuestion` only for a missing catalog (`init`) or an orphan file
(`discard-orphan`); this error is neither, so the skill reports and stops without asking. The scripted
reply ("Any question -> no") was never needed. The step 5 triage question and the step 6 file-draft
question were not reached because the preflight blocks every change.

## Final reply to user

I can't add the prompt yet: the prompt catalog at
`PROJ/.claude/prompts` (default location) fails validation, and the library refuses every change
until it is valid again.

**Error reported by the validator**
- `review__missing-tests/active.md`: `verification.quality does not match the current prompt text`.
  The text of the active "Missing tests review" prompt was changed after it was verified, so its
  recorded verification no longer matches. This file resolves to
  `PROJ/.claude/prompts/review__missing-tests/active.md`.

**How to recover**
- There is no committed copy to restore: this repository has no commits yet, and `.claude/` is ignored by
  your global gitignore (`~/.gitignore_global`), so the catalog is not under version control. If you have
  a backup of that one file, restore just that file from it.
- Otherwise, fix it by hand, guided by `references/prompt-record-format.md` in the prompt-library skill:
  put the prompt text in `review__missing-tests/active.md` back to the exact text it had when it was
  verified (the text whose hash is recorded in its `verification.quality`).
- If the text was changed on purpose, don't keep the edit in the active record: put the original text
  back, then make the change as a revision (`/prompt-library revise review__missing-tests`), which
  creates a reviewed, verified successor.
- First check the file for local changes you want to keep (copy them aside to reapply in the revision).
- I won't edit, restore or repair catalog files myself.

Once `validate` is clean, run `/prompt-library add` again with your TODO-summary text and I'll take it
through screening, the prompt-or-skill triage question, filing, review and your approval. Nothing was
written or changed in this run.

Consider also committing the catalog (or un-ignoring `.claude/prompts/`) so future recovery can use
`git restore`.
