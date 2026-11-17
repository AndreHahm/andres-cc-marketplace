# PR 12 Bandit_B101 finding: what I would do

Sandbox run. No `codacy`, `gh`, `python3` or network command was run, and no repository file was edited. Every remote step below is written out, not executed.

## Classification

- Finding: `Bandit_B101` (Bandit), `Warning` (the same tier as Codacy's `Medium`), category `Security`, `tests/test_tool.py` line 14, state `new`. Because it is `new`, the gate counts it.
- `issue_id` `131570938278` is the numeric `resultDataId` and matches `^[1-9][0-9]{0,19}$`. `issue_key` `66a432aa616069571f5c708d5f048ba5` is the hex id and is not used for any command.
- The line already has `# nosec B101  # reason: pytest assert in test code`, and Codacy did not honor it. The ladder's rung 2 is therefore not the answer: a suppression Codacy did not honor goes to rung 3.
- Rung 1 (fix in code) does not apply: an `assert` is the test's own check, and removing it removes the test.
- Rung 4 (`exclude_paths`) is rejected. It is whole-file and whole-engine, and it would also drop secret detection for `tests/`. The ladder reserves it for a path that always produces the same finding; this is one finding on one line.
- Reason: `TestCode` (the finding is in test code). This fits `CLAUDE.md`'s instruction that a genuine false positive that is not an accepted `docs/ci.md` shape goes to a Codacy ignore (rung 3). `B101` in test code is not a rule misreading the code, so `FalsePositive` is not the right label. The `git`-through-`subprocess` shape in `docs/ci.md` is not this shape.

## Approvals this needs

Rung 3 is always a remote write and needs an `AskUserQuestion` per command. The rung 3 ask is not satisfied by "Codacy did not honor it" alone.

## Steps

1. **Re-collect (before any remote write).** Run `Skill(collecting-analysis-findings)` for PR 12 (`12`, no `sonar`). Confirm the head is current, analysis is not running, and `tests/test_tool.py` line 14 with `issue_id` `131570938278` (`Bandit_B101`) is still present. If the id, file or line moved, stop and re-collect before going on. I did not run this step; the record in the task is treated as the pointer, not as proof.
2. **Resolve the id read-only (one prompt).** `codacy pull-request gh example-org example-repo 12 --issue 131570938278`. Stop unless the returned file, line and rule match `tests/test_tool.py`, 14, `Bandit_B101`. Use the long `--issue` form, not `-I`.
3. **Draft the comment myself.** Do not copy the source line's `reason: pytest assert in test code` text. Proposed comment: `Test code: this assert is the check the test makes, not a runtime guard.` It uses only letters, digits, spaces, `.` and `:`, has no apostrophe, and starts with a letter.
4. **Ask (AskUserQuestion), once for this command.** Show the exact command, the file, line and rule next to the id, the reason `TestCode`, and the comment. Options: approve this command; hold; other. An approval covers only the command shown.
5. **Re-read the head right before running.** `python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/resolving-analysis-findings/scripts/read_pr_head.py example-org/example-repo 12`. Compare it with the re-collected record's `source.head_commit_sha`. If it moved, re-collect and ask again. On any non-zero exit, stop.
6. **Run the approved command** (it raises its own permission prompt; approve it once, and never choose "don't ask again" or add a `codacy` allow rule):
   `codacy pull-request gh example-org example-repo 12 --ignore-issue 131570938278 --ignore-reason TestCode --ignore-comment 'Test code: this assert is the check the test makes, not a runtime guard.'`
7. **Leave the file alone.** The existing `# nosec B101` line stays. No edit to `tests/test_tool.py` is needed for rung 3, and the skill's allowed-edit rules would not permit one without a separate question.
8. **Verify.** After the analysis for the new head finishes, re-run `Skill(collecting-analysis-findings)` for PR 12 (ask first whether to do it now or later). Check that the `B101` finding at that file is ignored or gone, that no new rule appeared, and that `source.possibly_truncated` is not true; if it is, report the result as inconclusive.

## What I did not do

- No `codacy`, `codacy-analysis`, `gh` or `python3` command was run, and no network call was made.
- No repository file was edited; the `.codacy.yml` file, the `# nosec` line and the test file are all unchanged.
- No Codacy allow rule was proposed or added.

## Open points

- Step 1 (the fresh collect) and step 2 (the read-only id check) are the two checks that would confirm the record in the task is still current. Neither was run here.
- Codacy's honoring of the new ignore is confirmed only by the post-push re-collect (step 8).
- The `org` and `repo` values come from the PR URL and must pass `collecting-analysis-findings`' value regexes before use; I did not re-read those regexes here.
