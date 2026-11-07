# Sonar CLI Commands

Checked 2026-11-07 against `sonar` CLI 1.11.0 and SonarQube Cloud.

## Read forms

| Question | Command |
|---|---|
| A gate status | `sonar quality-gate status -p <key> --format json 2>/dev/null` (`--branch <b>` for another branch) |
| A PR's gate, head and analysis date | `sonar api get "/api/project_pull_requests/list?project=<key>" 2>/dev/null \| jq '.pullRequests[] \| select(.key == "<n>") \| {key, analysisDate, sha: .commit.sha, gate: .status.qualityGateStatus}'` |
| Open issues on a PR | `sonar list issues -p <key> --pull-request <n> --format json 2>/dev/null \| jq "$FIELDS"` |
| Open issues on a branch | `sonar list issues -p <key> --branch <b> --format json 2>/dev/null \| jq "$FIELDS"` |
| One file's issues | add `--file <path>` |
| One issue's status and comment text | `sonar api get "/api/issues/search?issues=<key>&additionalFields=comments" 2>/dev/null \| jq '.issues[] \| {key, issueStatus, comments: [.comments[]?.markdown]}'` |
| What an endpoint accepts | `sonar api get "/api/webservices/list?include_internals=false" 2>/dev/null` |

`$FIELDS` is `.issues[] | {key, rule, severity, type, impacts, component, line, message, issueStatus}`. Each form keeps
only what it needs, because the raw responses carry identity fields. `sonar quality-gate status` carries none.

`--page-size` is at most 500. The API refuses to go past 10,000 results with a `400`.

## Severity names

Responses say `BLOCKER`, `CRITICAL`, `MAJOR`, `MINOR`, `INFO`. In this project's MQR mode `--severities` takes `INFO`,
`LOW`, `MEDIUM`, `HIGH`, `BLOCKER`. In Standard Experience mode it takes the response names.

## Write forms: never run here

`sonar api post|put|patch|delete`, `sonar remediate`, `sonar analyze`, `sonar import`, `sonar integrate`, `sonar link`,
`sonar auth`, `sonar config set|unset`, `sonar system reset`, `sonar allowlist`, `sonar update`, `sonar architecture`
writes.

Transitions belong to `resolving-analysis-findings`. Anything else is given to the user as an exact command.
