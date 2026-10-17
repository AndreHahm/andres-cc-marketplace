# Codacy finding: High-severity Semgrep_dangerous-subprocess-use on run-git.py line 120

## Outcome

No decision recorded yet. The finding cannot be confirmed from this sandbox, so the ladder stops at step 1 and no rung is taken. Nothing was run and no repository file was edited.

## Why the procedure stops here

1. **No fresh record.** The skill's step 1 requires re-running `collecting-analysis-findings` for the PR's current head and confirming the finding (`file`, `line`, `issue_id`) is still in that record before any decision. This sandbox forbids `codacy`, `codacy-analysis` and `gh` commands and network use, so the record cannot be collected. The "false positive" view is the user's hypothesis and has not been checked against a current record.
2. **The file is not in this checkout.** `plugins/example-kit/scripts/run-git.py` does not exist. `plugins/` in this worktree holds `analysis-kit`, `antigravity-kit`, `codex-kit`, `context-kit`, `example-plugin`, `github-actions-kit`, `git-kit`, `plugin-devkit`, `promptlibrary-kit`, `quality-kit`, `session-kit`, `workledger-kit` and `workmanagement-kit`, and no `run-git.py` exists anywhere in the tree. Either the finding belongs to a different branch or head, or the path is wrong. Per the skill, it must not be chased by line number.
3. **Classification cannot be made.** The skill says to read the flagged line and what feeds it, not the rule name alone. That reading is impossible here, so neither "false positive" nor "real" can be assigned.

## What the procedure would do once the finding is confirmed

- **Severity gate.** `High` is not in the `Minor` / `Info` / `Warning` group. A rung 2 inline suppression on it needs an `AskUserQuestion` approval first. A rung 3 Codacy ignore needs a per-command approval showing the exact command. Neither can run on the user's word alone.
- **Rung 1 if the call is not safe.** If the code builds a command from a variable, uses `shell=True`, or feeds user text into it, the finding is real and the fix is in code, with the count proven to drop afterwards.
- **Rung 2 if the call is a deliberate, literal, list-form call.** The shape would be `# nosemgrep: Semgrep_dangerous-subprocess-use` on the flagged line with a written reason. Caveat: `references/suppression-formats.md` lists the Semgrep syntax as repository precedent only and says it was not re-verified against Codacy. Whether Codacy honors it is confirmed only by a push and a Cloud re-check. If Codacy does not honor it, fall back to rung 3 and say so.
- **Rung 3 for a single flagged issue** (for example test code), with `--ignore-reason FalsePositive`, `NotExploitable` or `AcceptedUse` as the classification fits. The reason must name what the rule misread or why the call is unreachable, not "false positive".
- **The docs precedent does not transfer directly.** `docs/ci.md` ("Codacy: git through subprocess in plugin scripts") covers Bandit `B404`/`B603`/`B607`, not Semgrep's `dangerous-subprocess-use` rule. It can be cited as the reason for accepting a literal `git` call, but it does not by itself settle this rule.

## What the user should do next

1. Run `collecting-analysis-findings` for the PR in a session that allows the read-only Codacy forms, and confirm the finding's `file`, `line`, `issue_id` and `head_commit_sha` against the current head.
2. Confirm the real path. If it is not `plugins/example-kit/scripts/run-git.py`, the finding may be stale or from another branch.
3. Read the flagged line and the code that feeds the call, then choose the rung. Only after that, answer the `AskUserQuestion` for the rung 2 or rung 3 approval.

## Questions this agent could not put to the user

This subagent does not have `AskUserQuestion` available in its tool set, so the decision gate is stated here instead. Once the finding is confirmed, the question for the user is which of these to take:

- Rung 1: fix in code (if the call is unsafe).
- Rung 2: `# nosemgrep: Semgrep_dangerous-subprocess-use` with a stated reason (if the call is deliberate and literal). This needs approval because the severity is High.
- Rung 3: a per-issue Codacy ignore with a named reason (if the finding is in test code or a single flagged issue). This is a remote write and needs approval of the exact command.
- Hold: take no action until a fresh record exists.

## Sandbox compliance

No `codacy`, `codacy-analysis` or `gh` command was run. No network was used. No repository file was edited. The only file written is this one, under the outputs directory.
