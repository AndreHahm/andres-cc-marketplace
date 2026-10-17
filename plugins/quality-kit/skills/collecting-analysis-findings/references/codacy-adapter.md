# Codacy Adapter

Verified 2026-10-17 against the Codacy Cloud CLI (`codacy`, whose help prints `codacy-cloud-cli`) and this
repository's real output. Re-check the shapes below before trusting them after a CLI update.

## Read commands (the only forms this skill runs)

Redirect each output into a scratchpad file (`> <scratchpad>/<name>.json`), then pass that file to
`scripts/collect_codacy.py`.

| Source | Command | `--kind` |
|---|---|---|
| A PR's new issues | `codacy pull-request <provider> <org> <repo> <number> --output json` | `pr` |
| Default-branch issue list | `codacy issues <provider> <org> <repo> -c Security -n 1000 -o json` (`-b <branch>` for another branch) | `repo` |
| Issues already ignored | `codacy issues <provider> <org> <repo> -i -n 1000 -o json` | `ignored` |

`-n` is capped at 1000 (the CLI's help: default 100, max 1000), so a list with more matching issues comes back
truncated while the record's `counts.total` looks complete. If `counts.total` is 1000, treat the record as
possibly truncated and compare it with the filtered total from `codacy issues <provider> <org> <repo> -O`
(`--overview`, same filters) before reporting counts. Checked 2026-10-17 against `codacy issues --help`; the
truncation itself was not reproduced, because no list here exceeds the cap.

`<provider>` is `gh` for GitHub. `-s` filters by severity and `-c` by category. The Cloud CLI is the
authority: GitHub's check annotations show only a capped subset of what Codacy reports.

## Forbidden to this skill (they change remote state)

- On `codacy pull-request`: `--ignore-issue`, `--unignore-issue`, `-F`/`--ignore-all-false-positives`,
  `--reanalyze`, `--reanalyze-and-wait`.
- On `codacy issues`: `-I`/`--ignore` (ignores every issue matching the current filters), `-R`/
  `--ignore-reason`, `-m`/`--ignore-comment` and `-y`/`--skip-confirmation` (skips the confirmation prompt).
- Any command that enables, disables or configures a tool or pattern.

Those belong to `resolving-analysis-findings`, behind its approval gate.

Flag case matters: on `codacy issues`, lowercase `-i` (list the ignored issues) is the only sanctioned form;
uppercase `-I` is the bulk ignore. Both raise the same permission prompt: read its text before approving.

## Input shapes

- **`pr`:** `{pullRequest: {pullRequest: {repository, number, status, owner: {name}, headCommitSha, ...},
  isAnalysing, newIssues: <count>, ...}, newIssues: [{commitIssue: {issueId, filePath, lineNumber, message,
  patternInfo: {id, category, severityLevel, ...}, toolInfo: {name}, commitInfo: {sha, ...}}, deltaType}],
  potentialIssues: [], files: [...]}`. The top-level `newIssues` is the list; the number inside
  `pullRequest` is only a count.
- **`repo`:** `{issues: [{patternInfo: {id, severityLevel, category, subCategory}, message, filePath,
  lineNumber, lineText, resultDataId}]}`. No `issueId`, no `toolInfo`.
- **`ignored`:** `{ignoredIssues: [{issueId, reason, comment, ignoredByName, ignoredTimestamp, patternInfo,
  message, filePath, lineNumber, lineText}]}`. `reason` is one of `AcceptedUse`, `FalsePositive`,
  `NotExploitable`, `TestCode`, `ExternalCode`.

Not verified: the shape of a non-empty `potentialIssues` entry (it was empty when checked). The adapter maps
it like a `newIssues` entry with `state: potential` and fails closed if it does not fit.

## Exit codes of `collect_codacy.py`

| Code | Meaning | Output |
|---|---|---|
| 0 | Record written | The record on stdout |
| 2 | The input is unreadable, is not a regular file, is larger than 32 MiB, is not valid JSON, is nested too deeply, has an `issueId` that is not a plain identifier (`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`), or is not a shape above; or the command line is invalid (a bad `--kind`, `--group-by` or `--format`) | Message on stderr, nothing on stdout |

The shell redirect creates or truncates the output file before the script runs, so on any non-zero exit discard
the output file; a partial record is never a result.
