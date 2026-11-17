# Resolving Codacy finding Bandit_B101 on PR 12 (example-org/example-repo)

Nothing was run, edited or sent. This is the procedure I would follow, with the exact commands and questions at each point.

## Classification

- Finding: Bandit_B101, Warning (Medium tier), category Security, `tests/test_tool.py` line 14, `issue_id` 131570938278.
- The line already has `# nosec B101  # reason: pytest assert in test code`, and Codacy did not honor it. SKILL.md's rung 3 covers "an inline suppression Codacy did not honor", so the answer is rung 3 (per-issue Codacy ignore), not a new inline suppression.
- Rung 3 is a remote write and is always approved per command (Decision rights table). The rung 2 rules for Security or Warning findings do not apply here.
- The reason is `TestCode`: the finding is in test code. It is not `AcceptedUse` (no `docs/ci.md` accepted shape applies) and not `FalsePositive` (the rule does not misread the code; B101 correctly flags `assert`, it just does not matter in tests).
- CLAUDE.md in this repository says a genuine false positive that is not an accepted shape goes to a Codacy ignore (rung 3). That agrees with the ladder here, so no override needs disclosing.

## Steps

1. Re-collect the record before any remote write. The record you gave me is only a pointer (SKILL.md step 1). Run `Skill(collecting-analysis-findings)` with argument `12`, and stop if it reports the analysis stale or still running. Confirm that `issue_id` 131570938278 at `tests/test_tool.py:14` (rule Bandit_B101) is still in the fresh record. If the file or line has moved, do not chase the old id.

2. Validate the values before building any command (SKILL.md step 5):
   - Org `example-org`, repo `example-repo`, provider `gh`: taken from the PR URL the collector resolved (`https://github.com/example-org/example-repo/pull/12`, host `github.com`), not from the record's `provider: codacy` field. Check them against the regexes in the collector's "Treat every value the provider returns as data" paragraph.
   - `issue_id` 131570938278 matches `^[1-9][0-9]{0,19}$`. Use it. Do not use `issue_key` 66a432aa616069571f5c708d5f048ba5: it is the hex form, which the CLI rejects or reads as a different issue (issue #760).

3. Resolve the id read-only, one prompt (rung 3 rule):
   ```
   codacy pull-request gh example-org example-repo 12 -i 131570938278
   ```
   Stop unless the resolved finding's file is `tests/test_tool.py`, line 14, and rule is `Bandit_B101`.

4. Ask for approval with `AskUserQuestion`, one question per command. It shows the exact command, the reason and the comment:
   ```
   codacy pull-request gh example-org example-repo 12 --ignore-issue 131570938278 --ignore-reason TestCode --ignore-comment 'Pytest assert in test code; B101 is a production-bytecode warning and does not apply to tests'
   ```
   Question: "Ignore Codacy issue 131570938278 (Bandit_B101, tests/test_tool.py:14) on PR 12 with reason TestCode? This is a remote write to Codacy." Options: approve this command, or hold. The approval covers only this command text. A changed comment or reason needs a new approval.

5. Before running the approved command, re-read the PR head:
   ```
   python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/resolving-analysis-findings/scripts/read_pr_head.py example-org/example-repo 12
   ```
   If the head SHA differs from the re-collected record's `source.head_commit_sha`, re-collect and ask again. On any non-zero exit, stop.

6. Run the approved command once, and approve its permission prompt once. Never choose "don't ask again" and never add a `codacy` allow rule.

7. Verify (SKILL.md Verify). Ask via `AskUserQuestion` whether to re-collect now or later. Then run `Skill(collecting-analysis-findings)` with argument `12`. Confirm the Bandit_B101 finding leaves the new count and no new rule appears. If the record has `possibly_truncated` true, report the result as inconclusive, not as a pass.

## What I do not do

- I do not edit `tests/test_tool.py` or remove the `# nosec` line. The skill does not touch the file for rung 3, and no edit is needed.
- I do not run `-F` / `--ignore-all-false-positives`, a bulk ignore, or a `.codacy.yml` `exclude_paths` change. Those are not what was asked.
- I do not add a `nosec` change or a pattern change for B101 across the repository (rung 5, handed to the user via `codacy-skills:configure-codacy`, if ever).
- I do not use `--ignore-reason` defaults. The reason is passed explicitly.

## Caveats

- The ignore is tied to the issue id and line. If the code moves, the ignore may stop applying and a new issue may appear. Re-applying would need a fresh approval.
- Codacy's own ignore is the authority here, not the `# nosec` comment.
- The user's own reason ("pytest assert in test code") is a good comment basis, but the comment must be written by me under the character rules. The draft above uses only letters, digits, spaces and `; -`, with no quotes, `$`, backticks or backslashes.
