# Sonar CLI Commands

Checked 2026-11-07 against `sonar` CLI 1.11.0 and SonarQube Cloud.

## Read forms

Run each form exactly as written; the pipes are real shell pipes. The piped forms start with `set -o pipefail;`,
because `2>/dev/null` hides the CLI's error and `jq` exits 0 on empty input: without it a failed lookup looks like an
empty answer. A non-zero exit means the lookup failed: report that, never "nothing found".

A gate status (`--branch <b>` for another branch):

```bash
sonar quality-gate status -p <key> --format json 2>/dev/null
```

A PR's gate, head and analysis date:

```bash
set -o pipefail; sonar api get "/api/project_pull_requests/list?project=<key>" 2>/dev/null | jq '.pullRequests[] | select(.key == "<n>") | {key, analysisDate, sha: .commit.sha, gate: .status.qualityGateStatus}'
```

Open issues on a PR, or on a branch with `--branch <b>` in place of `--pull-request <n>`; add `--file <path>` for one
file's issues:

```bash
set -o pipefail; sonar list issues -p <key> --pull-request <n> --format json 2>/dev/null | jq '.issues[] | {key, rule, severity, type, impacts, component, line, message, issueStatus}'
```

One issue's status and comment text:

```bash
set -o pipefail; sonar api get "/api/issues/search?issues=<key>&additionalFields=comments" 2>/dev/null | jq '.issues[] | {key, issueStatus, comments: [.comments[]?.markdown]}'
```

What an endpoint accepts:

```bash
sonar api get "/api/webservices/list?include_internals=false" 2>/dev/null
```

Each form keeps only what it needs, because the raw responses carry identity fields. `sonar quality-gate status` carries none.
`sonar list issues` is pre-approved, so a bare run without the `jq` part raises no prompt and prints `author` and
`assignee` into the session: never run it without the projection.

`--page-size` is at most 500. The API refuses to go past 10,000 results with a `400`.

## Severity names

Responses say `BLOCKER`, `CRITICAL`, `MAJOR`, `MINOR`, `INFO`. In this project's MQR mode `--severities` takes `INFO`,
`LOW`, `MEDIUM`, `HIGH`, `BLOCKER`. In Standard Experience mode it takes the response names.

## Write forms: never run here

`sonar api post|put|patch|delete`, `sonar remediate`, `sonar analyze`, `sonar import`, `sonar integrate`, `sonar link`,
`sonar auth`, `sonar config set|unset`, `sonar system reset`, `sonar allowlist`, `sonar update`, `sonar architecture`
writes.

Transitions belong to `resolving-analysis-findings`. Anything else is given to the user as an exact command.
