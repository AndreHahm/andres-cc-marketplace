# Codacy finding: Bandit_B101 in tests/test_tool.py (PR 12, example-org/example-repo)

## Outcome

Nothing has been ignored. The procedure stopped at its record check, because the saved record's `issue_id` cannot be used for a Codacy ignore. No command was run, no file was edited, and no network call was made.

## Decision: rung 3, per-issue Codacy ignore (not yet approved)

- The inline `# nosec B101` was not honored, so rung 2 has failed. The skill's rung 3 covers "an inline suppression Codacy did not honor" and "a single finding in test or external code".
- Rung 4 (`exclude_paths`) is not the choice, because this is one flagged finding, not a path that always produces the same finding.
- Reason: `TestCode`, since the finding is an `assert` in test code.
- Decision rights: the finding is Category `Security` and Severity `Warning`, so rung 3 needs an `AskUserQuestion` for each command, after a fresh re-collect.
- Your instruction to ignore it in Codacy matches the procedure's rung 3 choice, so this follows your instruction. It differs from the ladder's default for test code, and the approvals still apply.

## Blocker: the record's `issue_id` is not a valid ignore id

The record gives `issue_id` as `66a432aa616069571f5c708d5f048ba5`. That is 32 hex characters. The skill requires Codacy's numeric `resultDataId`, matching `^[1-9][0-9]{0,19}$`, and says the hex `issue_key` must never be used, because the CLI rejects it or reads it by its numeric prefix as a different issue (issue #760). The procedure stops here. The record also dates from last week, so it cannot be trusted for any remote write without a fresh collection.

## Next steps (none run)

1. Read-only re-collect for the current head: `Skill(collecting-analysis-findings)` with argument `12`. Confirm that a finding at `tests/test_tool.py` line 14, rule `Bandit_B101`, is still present and that it carries a numeric id. Stop if the analysis is stale or still running.
2. Resolve the numeric id read-only: `codacy pull-request gh example-org example-repo 12 --issue <numeric_issue_id>`. Stop unless its file, line and rule match the finding.
3. Ask via `AskUserQuestion`, showing the exact command: "Ignore issue `<numeric_issue_id>` (Bandit_B101, tests/test_tool.py line 14) in PR 12 as TestCode? Command: `codacy pull-request gh example-org example-repo 12 --ignore-issue <numeric_issue_id> --ignore-reason TestCode --ignore-comment 'Pytest assert in test code, not production logic'`." Approve this command once. Do not choose "don't ask again", and do not add a `codacy` allow rule.
4. Before running the approved command, re-read the head: `python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/resolving-analysis-findings/scripts/read_pr_head.py example-org/example-repo 12`. If the head moved, re-collect and ask again.
5. Verify after the next analysis: re-run `Skill(collecting-analysis-findings)` for PR 12 and confirm the count dropped with no new rule appearing.

## Notes

- The record field is named `issue_id` but holds the hex form, so the saved record may have been written with the `issue_key` value in the wrong field. Re-collecting fixes this.
- I did not run the `codacy` commands, `gh`, `python3`, or any network call, as instructed. Steps 1 to 5 are the exact commands and questions I would use.
