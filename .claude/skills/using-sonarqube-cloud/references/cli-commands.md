# Sonar CLI Commands

Checked 2026-11-07 against `sonar` CLI 1.11.0 and SonarQube Cloud.

## Read forms

Run each form exactly as written; the pipes are real shell pipes. The piped forms start with `set -o pipefail;`,
because `2>/dev/null` hides the CLI's error and `jq` exits 0 on empty input: without it a failed lookup looks like an
empty answer. A non-zero exit means the lookup failed (a missing project exits 1, checked 2026-11-08): report that,
never "nothing found". The exception is the gate form: if it printed JSON whose `qualityGate.status` is `ERROR`,
report a failed gate, not a failed lookup. Whether a failed gate exits non-zero was not checked (no failing gate was
available on 2026-11-08), so read the status either way.

A gate status. Always name the target: run from inside a checkout, a bare form reports the gate of that checkout's
branch or PR, not the default branch (checked 2026-11-08: inside a PR branch's worktree it returned that PR's gate):

```bash
sonar quality-gate status -p <key> --branch <b> --format json 2>/dev/null
```

Use `--pull-request <n>` in place of `--branch <b>` for a PR, and confirm the `branch` or `pullRequest` field in the
answer names what was asked for.

A PR's gate, the commit Sonar last analyzed and when. `sha` is that analyzed revision, which can be older than the
PR's current head: report it as the analyzed commit, and use `collecting-analysis-findings` when the gate must be
checked against the current head:

```bash
set -o pipefail; sonar api get "/api/project_pull_requests/list?project=<key>" 2>/dev/null | jq '.pullRequests[] | select(.key == "<n>") | {key, analysisDate, sha: .commit.sha, gate: .status.qualityGateStatus}'
```

Open issues on a PR, or on a branch with `--branch <b>` in place of `--pull-request <n>`; add `--file <path>` for one
file's issues:

```bash
set -o pipefail; sonar list issues -p <key> --pull-request <n> --format json 2>/dev/null | jq '{paging, issues: [.issues[] | {key, rule, severity, type, impacts, component, line, message, issueStatus}]}'
```

If `paging.total` is larger than the issues shown, the list is one page: say how many were shown out of the total,
and fetch the next with `--page <p>` (500 per page) only if the question needs the rest.

One issue's status and how many comments it has. Comment text is left out because it can name or mention a
person; if the question needs it, ask the user to read it in the Sonar UI and pass on what is relevant:

```bash
set -o pipefail; sonar api get "/api/issues/search?issues=<key>&additionalFields=comments" 2>/dev/null | jq '.issues[] | {key, issueStatus, comments: (.comments // [] | length)}'
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
