# Codacy finding 1: Bandit_B603 on plugins/example-kit/scripts/run-git.py line 77

## Decision

Do not change the code. Record this finding as accepted in Codacy's own issue management, not as a code fix or a file-level exclusion.

## What I would change

1. Mark issue `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` as ignored on PR 7 through the Codacy Cloud CLI, with reason `AcceptedUse`:

   ```
   codacy pull-request <provider> <org> <repo> 7 --ignore-issue aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --ignore-reason AcceptedUse
   ```

   `<provider>`, `<org>` and `<repo>` are placeholders; I did not run this because the sandbox forbids `codacy` commands. `NotExploitable` would also fit. Pick one and state it in the PR description.

2. Leave `plugins/example-kit/scripts/run-git.py` unchanged.

## Why

- B603 is Bandit's generic "subprocess call, check for untrusted input" check. Its real risk is shell injection, and that needs `shell=True`, a string command, or input that reaches the argv from outside.
- The flagged call is `subprocess.run(["git", "status"], cwd=root, capture_output=True)`. The argv is a literal list, there is no shell, and `cwd` is not an injection vector. There is no untrusted input to guard against, so the finding is a false positive for this call.
- Because the finding is a false positive, CLAUDE.md's Codacy guidance says to use Codacy's ignore mechanism rather than chase it with code changes.

## What I would not do

- Do not rewrite the call to avoid `subprocess` (for example via a git library). That is churn with no security gain.
- Do not switch to `shell=True` or a string command to dodge the rule. That would add real risk.
- Do not add `.codacy.yml` `exclude_paths` for `run-git.py`. That excludes the whole file from the whole engine, which is wrong for a production script.
- Do not add an inline `# nosec B603` comment as the main fix. It is a code change whose effect on Codacy's count is unverified, and CLAUDE.md asks that code changes be checked against the Codacy count before relying on them. If the team wants the rationale written in the code, add a short comment and re-run `codacy-analysis analyze --pr` (or the Cloud CLI) to confirm the count drops, but the Codacy ignore is still the primary action.

## Caveats before running the ignore

- I could not open `plugins/example-kit/scripts/run-git.py` in this worktree. The file does not exist at that path here, so this decision rests on the findings record's description of line 77, not on reading the code. Confirm the line is the literal-list call before ignoring it. If it turns out to pass a variable command or use `shell=True`, the decision changes and the call needs a real fix.
- The ignore changes Codacy state on PR 7, so it needs the user's confirmation first.
- Confirm the issue ID is still current for the PR head before ignoring it. The record says it is, but the record was taken from the collecting step.
