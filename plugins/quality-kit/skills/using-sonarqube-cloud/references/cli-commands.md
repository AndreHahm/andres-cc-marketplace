# Sonar CLI Commands

Checked 2026-11-07 against `sonar` CLI 1.11.0 and SonarQube Cloud.

## Read forms

Run each form exactly as written. `<read>` stands for
`python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/qlty-sonar-read.py`, the pre-approved wrapper
that runs a fixed `sonar` read and prints only the fields shown. A non-zero exit means the lookup failed (1: `sonar`
failed, for example a missing project, checked 2026-11-08; 2: a refused value, `sonar` off `PATH`, or a reply that is
not JSON; 3: more than 10,000 issues): report that, never "nothing found". The gate form exits 0 with the verdict
for a failing gate too: `sonar quality-gate status` itself exits 51 when the gate fails and 1 when no verdict was
computed, after printing it (the CLI's `verdict.ts`, read 2026-11-09; no failing gate was available to run live), and
the wrapper turns both into the printed verdict. Report `qualityGate.status` `ERROR` as a failed gate and `NONE` as
not computed, never as a failed lookup.

A gate status. The wrapper requires exactly one target and runs from a fresh, empty temporary directory, because a bare
`sonar quality-gate status` run inside a checkout reports that checkout's branch or PR, not the default branch
(checked 2026-11-08: inside a PR branch's worktree it returned that PR's gate):

```bash
<read> gate-status --project <key> --branch <b>
```

Use `--pull-request <n>` in place of `--branch <b>` for a PR, and confirm the `branch` or `pullRequest` field in the
answer names what was asked for.

A PR's gate, the commit Sonar last analyzed and when. `sha` is that analyzed revision, which can be older than the
PR's current head: report it as the analyzed commit, and use `collecting-analysis-findings` when the gate must be
checked against the current head:

```bash
<read> pr-list --project <key> --pull-request <n>
```

It prints `{"pullRequests": [{key, analysisDate, commit: {sha}, status: {qualityGateStatus}}]}`; an empty list means
Sonar has no analysis for that PR.

Open issues on a PR, or on a branch with `--branch <b>` in place of `--pull-request <n>`; add `--file <path>` for one
file's issues:

```bash
<read> issues --project <key> --pull-request <n>
```

It fetches every page (500 each) and prints one JSON line per page, `{paging, issues: [{key, rule, severity, type,
component, line, message, issueStatus, impacts}]}`; count across the lines.

One issue's status and how many comments it has. Comment text is left out because it can name or mention a
person; if the question needs it, ask the user to read it in the Sonar UI and pass on what is relevant:

```bash
<read> issue-state --issue <key>
```

What an endpoint accepts (not a wrapper form, so it prompts; its output names no person):

```bash
sonar api get "/api/webservices/list?include_internals=false" 2>/dev/null
```

Each wrapper form keeps only what it needs, because the raw responses carry identity fields. A direct `sonar list issues` or `sonar api get` is not pre-approved and prints those fields: use the
wrapper.

The API refuses to go past 10,000 results with a `400`, so the wrapper stops there with exit 3: narrow with `--file`.

## Gotchas

- **`sonar` may be off `PATH`.** The default install is `~/.local/share/sonarqube-cli/bin/sonar`; `qlty-sonar-read.py`
  finds it only on `PATH`, outside every checkout that encloses the working directory (`sonar.exe` on Windows), and
  exits 2 otherwise. A home directory that is itself a git checkout (a dotfiles repository) therefore always hides
  the default install, from inside a project too: install `sonar` in a `PATH` folder outside it.
- **The banner goes to stderr.** Add `2>/dev/null` when reading JSON.
- **Responses carry identity fields.** `author`, `assignee`, `contributors`, comment logins and commit messages. Use
  the `qlty-sonar-read.py` forms: a bare `sonar api get` or `sonar list issues` prints them all into the session.
- **`--severities` names differ from response names** in MQR mode, and `MINOR` exits 2 with empty stdout.
- **`.sonarcloud.properties` is read from the default branch only**, so a change takes effect after merge.
- **No coverage under Automatic Analysis.** A missing coverage figure is expected, not a fault.

## Severity names

Responses say `BLOCKER`, `CRITICAL`, `MAJOR`, `MINOR`, `INFO`. In this project's MQR mode `--severities` takes `INFO`,
`LOW`, `MEDIUM`, `HIGH`, `BLOCKER`. In Standard Experience mode it takes the response names.

## Write forms: never run here

`sonar api post|put|patch|delete`, `sonar remediate`, `sonar analyze`, `sonar import`, `sonar integrate`, `sonar link`,
`sonar auth`, `sonar config set|unset`, `sonar system reset`, `sonar allowlist`, `sonar update`, `sonar architecture`
writes.

Transitions belong to `resolving-analysis-findings`. Anything else is given to the user as an exact command.
