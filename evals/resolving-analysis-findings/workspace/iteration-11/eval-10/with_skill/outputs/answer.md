# Codacy finding Bandit_B101 on PR 12 (example-org/example-repo): resolution plan, stopped before any remote write

## Outcome

No Codacy ignore was run. The finding is a rung 3 candidate, but the saved issue id is not usable for a
Codacy command, and the findings record is stale. The next steps are listed below, each with the exact
command or question, and none has been run.

## Classification

- Finding: `Bandit_B101` ("Use of assert detected (B101)"), Bandit, severity Warning, category Security,
  `tests/test_tool.py` line 14.
- Test code, so the reason is `TestCode` with a comment such as "pytest assert in test code". A pytest
  `assert` is the standard shape of this rule firing in test code, so the rule did not misread the code.
- Ladder: the inline `# nosec B101` was not honored, so rung 2 has already failed. Rung 3 (a per-issue
  Codacy ignore) is the fallback the user asked for, and CLAUDE.md names it for a genuine false positive
  that is not an accepted shape in `docs/ci.md`. This finding is not the `git`-through-`subprocess` shape.
- Decision rights: rung 3 is always a remote write, so it needs an `AskUserQuestion` approval that shows the
  exact command. The user's instruction to ignore it counts as the decision to proceed, but the approval
  still has to be asked for the exact command.

## Blockers found

1. **The saved issue id cannot be used.** The record gives `issue_id` as `66a432aa616069571f5c708d5f048ba5`.
   That is the hex `issue_key`, not Codacy's numeric `resultDataId`. It fails `^[1-9][0-9]{0,19}$`. The skill
   stops on a mismatch (step 5), and `references/ignore-reasons.md` says the hex form is refused or read as a
   different issue (issue #760). The numeric id must come from a fresh PR record, matched to this finding by
   `issue_key`, `file`, `line` and rule.
2. **The record is stale.** It was saved last week. Step 1 requires a fresh `collecting-analysis-findings` run
   for the current head before any edit or remote write, and the record is only a pointer to what to look at.

## Next steps (none run)

1. Re-collect the findings for PR 12 with `collecting-analysis-findings`, using the PR number `12`. This is a
   skill call that I was told not to make here. Confirm the head matches, analysis is not still running, and
   that `tests/test_tool.py` line 14 with rule `Bandit_B101` is still present. Take the numeric `resultDataId`
   from that record for this `issue_key`. If it is absent, stop and report it rather than guessing an id.
2. Resolve the id read-only (one prompt, approval needed as it is a `codacy` call):
   `codacy pull-request gh example-org example-repo 12 -i <numeric_issue_id>`
   Stop unless the returned file, line and rule match the finding.
3. Re-read the head before the write (a `python3 -I` command, approval needed):
   `python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/resolving-analysis-findings/scripts/read_pr_head.py example-org/example-repo 12`
   If the SHA has moved since step 1, re-collect and ask again. Stop on any non-zero exit.
4. Ask via `AskUserQuestion` for the exact command, showing its text and what it hides:
   `codacy pull-request gh example-org example-repo 12 --ignore-issue <numeric_issue_id> --ignore-reason TestCode --ignore-comment 'pytest assert in test code, tests/test_tool.py line 14'`
   The comment uses only allowed characters and starts with a letter. The question should say that Codacy will
   stop reporting this one issue on the PR, that the ignore is a remote write, and that a moved line will need the
   ignore re-applied.
5. After the approved command runs, re-collect the PR and confirm the Bandit_B101 count for `tests/test_tool.py`
   dropped and no new rule appeared. Report it as inconclusive if `possibly_truncated` is true.

## Not done

- No `codacy`, `codacy-analysis`, `gh` or `python3` command was run, and there was no network access.
- No repository file was edited.
- The `Skill` tool was not invoked, so the required re-collect in step 1 has not happened.
