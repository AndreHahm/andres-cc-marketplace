# Codacy Adapter

Verified 2026-10-17 against the Codacy Cloud CLI (`codacy`, whose help prints `codacy-cloud-cli`) and this
repository's real output. Re-check the shapes below before trusting them after a CLI update.

## Read commands (the only forms this skill runs)

Pipe each command's output into `scripts/collect_codacy.py --input -`; the raw response (it holds committer names
and emails) is never written to a file.

| Source | Command | `--kind` |
|---|---|---|
| A PR's new issues | `codacy pull-request <provider> <org> <repo> <number> --output json` | `pr` |
| Default-branch issue list | `codacy issues <provider> <org> <repo> -c Security -n 1000 -o json` (`-b <branch>` for another branch) | `repo` |
| Issues already ignored | `codacy issues <provider> <org> <repo> -i -n 1000 -o json` | `ignored` |
| Filtered total, for the truncation check below only | `codacy issues <provider> <org> <repo> -c Security -O` (same filters as the list) | none: read the printed total, do not pipe it |

`-n` is capped at 1000 (the CLI's help: default 100, max 1000), so a list with more matching issues comes back
truncated while the record's `counts.total` looks complete. If `counts.total` is 1000, treat the record as
possibly truncated and compare it with the filtered total from the overview row above
(`-O`, same filters) before reporting counts, and say in the report that the record is possibly truncated. Checked 2026-10-17 against `codacy issues --help`; the
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
| 0 | Record written | The record on stdout, or with `--output` a one-line summary on stdout and the record in the file |
| 2 | The input is unreadable, is outside a scratchpad directory you own, is not a regular file, is larger than 32 MiB, is not valid JSON, is nested too deeply, has an `issueId` that is not a plain identifier (`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`), or is not a shape above; or the command line is invalid (a bad `--kind`, `--group-by` or `--format`); or `--output` is refused (not inside a directory named `scratchpad`, on POSIX one that you do not own or that others can write to, inside a folder containing `.git`, a symlink that leaves the scratchpad, a directory, or in a directory that does not exist) | Message on stderr, nothing on stdout, no output file created or changed |

With `--output` the script writes a private temporary file and replaces the target only after the whole record is
built, so a failed run does not create or modify the output file; an older file at the same path survives.
The Cloud CLI command is piped into the adapter, and `codacy` commands are not pre-approved, so the command raises
its own permission prompt showing the whole pipeline. If the CLI fails, the adapter gets empty or invalid input and
exits 2. On any non-zero exit discard an output file made another way; a partial record is never a result.
