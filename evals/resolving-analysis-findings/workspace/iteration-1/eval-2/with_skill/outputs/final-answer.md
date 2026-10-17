# Codacy High finding on run-git.py line 120 (Semgrep_dangerous-subprocess-use)

Nothing has been changed and nothing was sent to Codacy. No `codacy`, `codacy-analysis` or `gh` command was run, in line with the sandbox rules.

## Where this stands (SKILL.md steps 1-2)
- The skill says to treat a handed-over finding only as a pointer. Before any edit or remote write I have to re-run `collecting-analysis-findings` for the PR's current head. I need to confirm that `file`, `line` and `issue_id` are still in that fresh record. If the analysis is stale or still running, I decide nothing.
  - I can't do that in this sandbox. The decision below is provisional until it is done.
- The path `plugins/example-kit/scripts/run-git.py` does not exist in this worktree (there is no `plugins/example-kit/`). The finding's path must be checked against the fresh record before any edit. The skill requires a relative path inside the repo, not under `.claude/` or `.github/`.
- It is production code, so I'm assuming it is a `new` finding on this PR. The fresh record has to show that. A baseline (`existing`) finding would just be reported, not fixed.

## Real or false positive (the skill says to read the code)
I haven't read line 120 and what feeds it, because the file isn't here. That has to happen before choosing. The skill's classification is:
- If the command is a variable or a non-literal, this may be real, and the answer is rung 1 (fix in code).
- If it is a fixed literal `git` command in list form with no shell, this is the repo's standing accepted-use case. The reason is `AcceptedUse`, linked to `docs/ci.md`, section "Codacy: git through subprocess in plugin scripts".
- Do not swap in an absolute path to clear it. That makes the command a variable, which is exactly what `dangerous-subprocess-use` flags. Verify catches this case.

## Ladder and decision rights
- The default for an accepted `git` subprocess call is rung 2, an inline `# nosemgrep: Semgrep_dangerous-subprocess-use` with a stated reason. The exact rule id has to be copied from the fresh record. This syntax is repo precedent but has not been verified against Codacy.
- The severity is High, which is not one of Minor, Info or Warning. So rung 2 needs an `AskUserQuestion` approval first. I won't add the suppression myself.
- A rung 3 per-issue Codacy ignore is a remote write. It needs a separate per-command approval showing the exact text. I'd only use it if Codacy doesn't honor the inline suppression after a push.
- Rung 4 (`exclude_paths`) is wrong here. It would drop every engine for a production file.

## Question I would send
AskUserQuestion:
- Question: "Semgrep_dangerous-subprocess-use (High) at run-git.py:120 looks like an accepted literal git call. Add an inline `# nosemgrep: Semgrep_dangerous-subprocess-use` with this reason: 'Fixed literal git command, list arguments, no shell; accepted use is recorded in docs/ci.md'?"
- Options:
  1. "Add inline suppression (rung 2)". This is a local edit only, to the canonical plugins/ file, and it is not honored until a push and a Cloud re-check.
  2. "Fix in code instead (rung 1)". Use this if line 120 turns out to take a non-literal or user-influenced command.
  3. "Leave it for now". Report it only.
- I'd attach the code of line 120 and the fresh-record confirmation once I have them.

## After approval
1. Edit the canonical `plugins/...` file only (the `.claude/` mirror is synced, not hand-edited). Put the comment on the line where the finding is reported.
2. Record the reason in place.
3. After the push, re-run `collecting-analysis-findings`. Confirm the head matches, the count dropped and no new rule appeared. If Codacy didn't honor the suppression, fall back to rung 3 with its own approval, and say so.
