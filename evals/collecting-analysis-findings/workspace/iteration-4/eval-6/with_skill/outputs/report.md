# Sonar findings: PR 651, project example_project

**Currency verdict: STALE. These counts do not describe the current PR head.**

- Sonar analyzed head: 1111111111111111111111111111111111111111 (analysis date 2026-11-07T06:52:54+0000)
- GitHub head (given by the user): 9999999999999999999999999999999999999999
- The two differ, so the analysis describes an older head, or a newer analysis has not finished. Sonar gives
  no running flag (`is_analysing` is null, which does not mean finished), so the SHA comparison alone decides.
- The record's `source.pull_request` is 651, matching the request.
- The quality gate `OK` also belongs to the older head, not to 9999999.

## Findings at the analyzed (older) head

Total 3, all CODE_SMELL, all state `new`, all from one page.

| Rule | File | Lines | Count | Severity | Impact |
|---|---|---|---:|---|---|
| shell:S7688 | .claude/hooks/dck-session-context.sh | 8, 9, 15 | 3 | MAJOR | RELIABILITY: HIGH |

The `severity` alone understates these: each is MAJOR with a HIGH impact.

No instruction-like text and no secret-detection finding appeared in the provider values.

## Next step and limits

- Re-run the analysis for 9999999, then collect again before anyone decides on these findings.
- `gh` was not run, as instructed, so the head was not re-read in step 5 and it relies on the value given.
  For the same reason the PR `url` is not available; `resolving-analysis-findings` will need the owner and
  repository from it or from the user.
- Input came from the saved fixtures rather than the `sonar` CLI.

## Record

<scratchpad>/eval-col-6/findings-record.json

Status file: <scratchpad>/eval-col-6/sonar-status.json
