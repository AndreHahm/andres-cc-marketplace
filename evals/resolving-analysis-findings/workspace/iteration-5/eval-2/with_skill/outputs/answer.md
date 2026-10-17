# Codacy High finding: Semgrep_dangerous-subprocess-use at run-git.py:120

Nothing was changed or run. In this sandbox I did not run `codacy`, `codacy-analysis` or `gh`, I did not use the network, and I edited no repository file.

## Where this stands

- **Severity and rule.** High-severity `Semgrep_dangerous-subprocess-use` (Security) on a production script. `docs/ci.md` ("Codacy: `git` through `subprocess` in plugin scripts") records only Bandit B404/B603/B607 as the accepted `git`-through-`subprocess` shape. It does not cover this Semgrep rule at High. Under the skill's decision rights, this is not a decide-and-disclose case.
- **Not verified.** `plugins/example-kit/scripts/run-git.py` does not exist in this worktree (there is no `plugins/example-kit`). I could not read line 120 or what feeds it. I also could not re-collect the finding, because Codacy commands are off limits here. So "it is a false positive" is your hypothesis, not yet a finding of mine. The skill says to read the flagged line and its inputs, never to judge from the rule name.
- **Related warning in `docs/ci.md`.** Semgrep's `dangerous-subprocess-use` fires when the command is a variable. A common cause is replacing the bare `"git"` with an absolute path or a variable to satisfy Bandit B607. If that is what happened, the fix is to revert to the literal `"git"` (or use a helper such as `_git` in `git-verify-fix-diff.py`), not to suppress.

## Plan, following the skill's steps

1. **Fresh record.** Re-collect the PR's findings for the current head (a Codacy command, which needs a one-time permission prompt each). Confirm that the `file`, `line` and `issue_id` are still present, that the head matches and that the analysis is not running. Stop if it is stale. Take the org, repository and provider from the `gh pr view` URL.
2. **New or baseline.** Check that the finding is `new` rather than `existing`. A baseline finding in a file this PR does not touch is reported and left alone.
3. **Real or false positive** (read the code):
   - **Command or any argument built from untrusted text, or `shell=True`:** the finding is real. Use rung 1 (fix in code), then prove the count drops.
   - **Literal list-form command, no shell, no untrusted text:** this is a false positive or accepted use. Go to rung 2, an inline suppression with a stated reason. The exact line is "`# nosemgrep: dangerous-subprocess-use`" or a bare `# nosemgrep`, on the flagged line, with the reason after it. Semgrep's syntax is repository precedent only (`plugins/workledger-kit/scripts/wlgr_config.py` pairs `# nosec B603  # nosemgrep`). It is not verified against Codacy's Semgrep, so Codacy may not honor it.
4. **Ladder choice.** Take rung 2, not a Codacy ignore (rung 3) and not `exclude_paths` (rung 4). The inline comment travels with the code and keeps its reason. A Codacy ignore keys on an issue id that moves when code moves. `exclude_paths` would drop the whole file from the whole engine, including secret detection. Use rung 3 only if Codacy does not honor the comment, or if you tell me to use an ignore.
5. **Approval gate.** A High finding at rung 2 needs your explicit approval first, because it is a local edit by default. I will not add the suppression until you approve. A rung 3 ignore later would need its own approval of the exact command, which is a remote write.
6. **Verify after the push.** Wait for the analysis to finish, re-collect, and confirm that the targeted count dropped and that no new rule appeared. If Codacy did not honor the inline comment, fall back to rung 3 and say so.

## Decision needed

Which should I do?

1. **Inspect and classify first (recommended).** You paste lines ~110-125 of `run-git.py` and say how the command and arguments are built. I classify the finding as real or not. If it is a literal list-form call, I propose the exact `# nosemgrep` comment and the wording of the reason for approval.
2. **Approve a rung 2 suppression now.** You confirm the call is a literal list-form `git` command with no shell and no untrusted text. I write the `# nosemgrep` comment with that reason, once I can read the file.
3. **Use a Codacy ignore instead.** I hand you the per-issue ignore with a reason (`FalsePositive` if the rule misread the code, `NotExploitable` if there is no reachable harm), as an exact command for your approval. It is a remote write and may need re-applying when the id moves.

Whichever you pick, I will not use `-F` (bulk ignore). It can hide real findings across the whole PR, so I would hand you the command rather than run it. I will not change the quality gate or `.codacy.yml` without showing you the diff first.
