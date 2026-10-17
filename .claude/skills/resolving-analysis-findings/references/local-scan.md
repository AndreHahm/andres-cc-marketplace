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

The output file goes in the session scratchpad directory, never the repository; stop if the path is anywhere
else. Never pass `--install-dependencies`. The command raises a permission prompt: read it, because `--output`
can overwrite any file and `--install-dependencies` installs tools. A `codacy-analysis` allow rule in the
user's own settings (for example one added for the external `codacy-skills` plugin) removes that prompt, so
check the command's text yourself before running it. Run the scan only on your own branch: some linters load
code from the repository's config files, so scanning someone else's checked-out PR branch would run their
code. Alternatives for a narrower
scope: `--staged` (only the git staging area), `--diff [base]` (changes against a base branch), `--files
<paths...>`. `--inspect` reports which tools are available without analysing; `--fail-if-missing` stops if a
configured tool is unavailable; `--tool <id>` restricts to one tool.

## Config must exist first

The scan reads `.codacy/codacy.config.json`. Without it, `codacy-analysis analyze . --inspect` reports "No
.codacy/codacy.config.json found. Run `codacy-analysis init`" and finds 0 tools. The storage was decided
2026-10-17: the file is local and ignored (`.codacy/` is in `.gitignore`), so it follows each person's own
tooling and no shared copy can drift. So:

1. Run `--inspect` first. If the config is missing, stop and tell the user.
2. Hand the user the exact command to run themselves; this skill does not run it, because it creates files in
   the repository:

```text
codacy-analysis init --default
```

   `--default` fills the config with Codacy's API-sourced default patterns (public API, no token). `--remote
   <provider> <org> <repo>` would copy this repository's own Cloud configuration instead, but needs a
   repository token. `--default` was checked against `codacy-analysis init --help` only; running it, and the
   shape of what the local scan then reports, are not verified here.

## Reading the result

The JSON the local scan writes is read as printed. The collecting skill's
`collect_codacy.py` has no parser for it: its shape has not been verified here
because the scan could not run without a config. Do not treat a local count as the PR's Codacy count.

## When local and Cloud disagree

Cloud wins. The local run may use different tool versions, miss tools that are not installed, or skip
Codacy's own configuration. Record the difference in the report (rule, file, local count, Cloud count) and
decide from Cloud's numbers.
