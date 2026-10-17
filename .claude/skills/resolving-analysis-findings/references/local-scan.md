# Local Pre-PR Scan

Flags verified 2026-10-17 against `codacy-analysis analyze --help` in this repository; the output shape is
not verified (see below).

## When

Before `create-pr`, when the PR adds or changes scripts, workflow files or configuration. Cheaper than a
push, wait and Cloud re-check cycle, but it is a preview: the Cloud analysis stays the authority.

## Command

```text
codacy-analysis analyze --pr --output-format json --output <scratchpad file>
```

The output file goes in the session scratchpad directory, never the repository. The command raises a permission
prompt: read it, because `--output` can overwrite any file and `--install-dependencies` installs tools. Alternatives for a narrower
scope: `--staged` (only the git staging area), `--diff [base]` (changes against a base branch), `--files
<paths...>`. `--inspect` reports which tools are available without analysing; `--fail-if-missing` stops if a
configured tool is unavailable; `--tool <id>` restricts to one tool.

## Config must exist first

The scan reads `.codacy/codacy.config.json`. This repository has none: `codacy-analysis analyze . --inspect`
reports "No .codacy/codacy.config.json found. Run `codacy-analysis init`" and finds 0 tools. So:

1. Run `--inspect` first. If the config is missing, stop and tell the user.
2. Ask where the config should live: tracked in git so everyone scans the same way, or local and ignored so
   it follows each person's tooling. The file's name and JSON format are fixed by the tool; only the storage
   is the user's choice.
3. After that answer, hand the user the exact `codacy-analysis init` command to run; this skill does not run
   it. It creates files in the repository.

## Reading the result

The JSON the local scan writes is read as printed. The collecting skill's
`collect_codacy.py` has no parser for it: its shape has not been verified here
because the scan could not run without a config. Do not treat a local count as the PR's Codacy count.

## When local and Cloud disagree

Cloud wins. The local run may use different tool versions, miss tools that are not installed, or skip
Codacy's own configuration. Record the difference in the report (rule, file, local count, Cloud count) and
decide from Cloud's numbers.
