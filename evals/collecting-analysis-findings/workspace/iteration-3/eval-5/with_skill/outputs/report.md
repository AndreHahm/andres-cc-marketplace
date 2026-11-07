# Sonar findings: example_project PR 651

**Source:** SonarQube Cloud, project `example_project`, PR 651. Read from saved fixture output (`pr-list.json`,
`pr.json`); no `sonar`, `gh` or network command was run.

**Currency verdict: CURRENT.** The record's `head_commit_sha` (`1111111111111111111111111111111111111111`) equals the
head SHA supplied for this PR. Sonar gives no running flag (`is_analysing` is null), so the SHA comparison decides.
The live head was not re-read with `gh pr view` because `gh` was not to be run; the supplied SHA is the comparison
basis. The PR URL is not in the inputs, so none is given.

**Quality gate at the analyzed head:** OK.

## Counts (3 findings, all new, all open)

| Rule | File | Count | Severity | Type |
|---|---|---|---|---|
| shell:S7688 | `.claude/hooks/dck-session-context.sh` | 3 (lines 8, 9, 15) | MAJOR | CODE_SMELL |

By category: CODE_SMELL 3. No ignored findings in this list.

The finding message is provider text, quoted only for the rule: "Use '[[' instead of '[' for conditional tests."
Issue ids are `AaFIXTURE00000000001` to `...003`.

## Files

- Record: `<scratchpad>/eval-col-5/findings-record.json` (schema 1.1.0)
- Status file: `<scratchpad>/eval-col-5/sonar-status.json`
- Copy of the record: `evals/collecting-analysis-findings/workspace/iteration-3/eval-5/with_skill/outputs/record.json`
