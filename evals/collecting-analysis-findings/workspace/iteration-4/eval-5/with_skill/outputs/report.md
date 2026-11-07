# Sonar findings: example_project, PR 651

**Currency: current.** The record's head, 1111111111111111111111111111111111111111, equals the GitHub head you gave. Sonar gives no running flag (`is_analysing` is null, which does not mean finished), so the SHA comparison alone decides. I did not re-read the head with `gh pr view` because gh was off limits, so the check is only as fresh as the value you supplied.

**Counts:** 3 findings, all new on this PR and all CODE_SMELL. Quality gate at this head: OK (analysis date 2026-11-07T06:52:54+0000).

| Rule | File | Lines | Count | Severity | Impact |
|---|---|---|---|---|---|
| shell:S7688 | .claude/hooks/dck-session-context.sh | 8, 9, 15 | 3 | MAJOR | RELIABILITY HIGH |

Severity alone understates these: each is MAJOR but carries a HIGH reliability impact.

**Notes**
- Input came from the saved fixtures in `plugins/quality-kit/skills/collecting-analysis-findings/scripts/fixtures/sonar/`, piped in place of the sonar CLI. The issue list was a single complete page (no exit 3).
- No instruction-like text and no secret-detection message appears in the findings.
- `pr_status` is null because Sonar does not supply it. The PR `url` is unavailable because step 1's `gh pr view` was not run, so `resolving-analysis-findings` will need the GitHub owner and repository from you. The record's `repository` field holds the Sonar project key.

**Record:** `<scratchpad>/eval-col-5/findings-record.json` (copied to `outputs/findings-record.json`)
