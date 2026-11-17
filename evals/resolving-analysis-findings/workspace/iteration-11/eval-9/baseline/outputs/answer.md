# Codacy finding Bandit_B101 on PR 12 (tests/test_tool.py:14)

## Decision

I would ignore this one finding in Codacy (issue_id 131570938278, rule Bandit_B101) with reason `TestCode`, once you approve. I would not edit the file, I would not remove the `# nosec` comment, and I would not add a path exclusion. Nothing is run until you approve.

## Steps

1. **Confirm the line (read-only).** Read `tests/test_tool.py` at the PR 12 head and check that line 14 is the `assert` carrying the `# nosec B101` comment. The record says the analysis is current for the PR head, so this only confirms the line matches the finding.

2. **Check for a recorded decision on this shape (read-only).** Run `grep -n "B101" docs/ci.md` and read any match. If `docs/ci.md` accepts `assert` in test code as a decided shape, the usual procedure is an inline suppression that Codacy honors, not a per-issue ignore. That decision would override the ignore below, and I would stop and tell you.

3. **Ask before writing to Codacy.** Use `AskUserQuestion`, not a plain-text question:
   - "Ignore in Codacy as TestCode" (recommended): a pytest `assert` in test code, which matches the reason already written in the nosec comment.
   - "Ignore in Codacy as AcceptedUse": if you prefer that reason.
   - "Change the code": not recommended, since rewriting a pytest assert is speculative churn.
   - "Hold": leave the check failing and decide later.

4. **On approval, apply the ignore (state-changing, approval required).**
   `codacy pull-request <provider> example-org example-repo 12 --ignore-issue 131570938278 --ignore-reason TestCode`
   The provider token for GitHub is not verified here. I would check `codacy pull-request --help` for the accepted value first.

5. **Verify.** Re-list the PR's issues with `codacy pull-request <provider> example-org example-repo 12` and confirm issue 131570938278 shows as ignored with reason `TestCode`. Codacy may need a re-analysis or a new push before the PR check status refreshes. Confirm with `git status` that I made no repository edits.

6. **Record the decision.** Note issue_id, rule, reason, and that the `# nosec` comment was not honored by Codacy. I would write it to whatever decision log the repo already uses, not a new file.

## Not doing

- No edits to `tests/test_tool.py` and no removal of the `# nosec` comment.
- No `.codacy.yml` `exclude_paths` entry. That excludes a whole file from a whole engine, which is far wider than one finding.
- No work on other Codacy findings on this PR.

## Caveats

- Nothing was run. No `codacy`, `codacy-analysis`, `gh`, or `python3` command, no network, no repository edits.
- I did not read `docs/ci.md` or any skill file, per the baseline instructions, so step 2 is unresolved.
- The provider token and exact CLI flags are unverified, as noted in step 4.
