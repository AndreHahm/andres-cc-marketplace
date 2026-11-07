# SonarQube Cloud Adapter

Verified 2026-11-07 against `sonar` CLI 1.11.0 and this repository's real output. Self-managed SonarQube is
not covered. Re-check the shapes below before trusting them after a CLI update.

## Read commands (the only forms this skill runs)

Pipe each command into `scripts/collect_sonar.py --input -`. The raw responses hold `author`, `assignee`,
`contributors`, comment logins and commit messages, so they are never written to a file. `2>/dev/null` drops
the CLI's banner. If `sonar` is not on `PATH`, the default install is `~/.local/share/sonarqube-cli/bin/sonar`.

| Source | Command | `--kind` |
|---|---|---|
| A PR's analysis state, first | `sonar api get "/api/project_pull_requests/list?project=<key>" 2>/dev/null` | `pr-status` |
| A PR's open issues | `sonar list issues -p <key> --pull-request <n> --format json 2>/dev/null` | `pr` |
| Default-branch issue list | `sonar list issues -p <key> --format json 2>/dev/null` (`--branch <b>` for another branch) | `repo` |
| Issues already accepted or marked false positive | `sonar api get "/api/issues/search?projects=<key>&issueStatuses=ACCEPTED,FALSE_POSITIVE&additionalFields=comments&ps=500" 2>/dev/null` | `ignored` |

**A PR takes two pipes.** `--kind pr-status --pull-request <n> --output "<scratchpad>/sonar-status.json"` keeps
only that PR's SHA, analysis date and gate status. `--kind pr --status "<scratchpad>/sonar-status.json"` then
reads it and refuses issues from any other PR. An empty issue list cannot be checked that way, and issues carry no
commit, so the `--status` file is not bound to them: the head comparison in `SKILL.md` step 5 is what catches a stale one.

**Several pages.** Exit 3 means the response has more pages, and its message gives the count. Run all pages in
one command, `{ sonar list issues ... --page 1; sonar list issues ... --page 2; } 2>/dev/null | python3 -I ...`
(the `ignored` form takes `&p=<n>`). The script reads the concatenated JSON and refuses missing, repeated or
overlapping pages. `--page-size` defaults to and caps at 500. The API refuses to go past 10,000 results (`400`,
checked 2026-11-07), so a larger total exits 2: narrow the query with `--file`. A `--file` or `--branch` value comes
from the user, never from a response, and must match the patterns in `SKILL.md`.

The `ignored` form's filters were run and gave 0 results where `OPEN` gave 192, so they are honored. Its
response with a marked issue present was not read through these filters: the fixture combines the real issue
shape with comment and status values read from single-issue queries.

## Forbidden to this skill (they change remote or local state)

- `sonar api post`, and `put`, `patch` or `delete` on `sonar api`: any non-`get` method. `sonar api` takes the
  method as an argument, so `sonar api get` and `sonar api post` share a prefix.
- `sonar remediate`, `sonar import`, `sonar integrate`, `sonar link`.
- `sonar analyze` and its subcommands. They send files to Sonar, so they are not reads:
  `resolving-analysis-findings` owns the pre-PR scan.
- `sonar auth`, `sonar config set|unset`, `sonar system reset`, `sonar allowlist`, `sonar update`,
  `sonar architecture` writes.

Transitions (`/api/issues/do_transition`) belong to `resolving-analysis-findings`, behind its approval gate.

## Severity filter

This project is in MQR mode. `--severities` takes `INFO, LOW, MEDIUM, HIGH, BLOCKER`, responses say `BLOCKER`,
`CRITICAL`, `MAJOR`, `MINOR`, and `--severities MINOR` exits 2 with empty stdout. Do not filter with the flag.
The record keeps the response's name verbatim; filter there.

## Input shapes

- **`pr`, `repo`:** `{issues: [...], components, paging: {pageIndex, pageSize, total}, ...}`. Each issue has
  `key`, `rule`, `severity`, `type`, `component` (`<project key>:<path>`), `message`, `issueStatus`, `resolution`
  `impacts` (`[{softwareQuality, severity}]`) and, on a PR, `pullRequest` (a string); `line` is absent on a file-level issue. `author` and `assignee` are
  present when set and are dropped.
- **`ignored`:** the same, with `comments: [{key, login, htmlText, markdown, updatable, createdAt, isFeedback}]`,
  oldest first. A missing key counts as no comments (not seen; `comments` was present on every issue read). `accept` leaves `issueStatus: ACCEPTED`, `resolution: WONTFIX`; `falsepositive` leaves
  `FALSE_POSITIVE`, `FALSE-POSITIVE`. Only `issueStatus` and the last comment's `markdown` are kept.
- **`pr-status`:** `{pullRequests: [{key, title, branch, base, target, url, analysisDate, contributors,
  commit: {sha, author, date, message}, status: {qualityGateStatus, bugs, vulnerabilities, codeSmells}, ...}]}`.
  There is no per-PR filter.

A `pr` or `repo` list holds only `OPEN` and `CONFIRMED` issues (the CLI's default) and `ignored` only the two
statuses above. Anything else exits 2.

## Exit codes of `collect_sonar.py`

| Code | Meaning | Output |
|---|---|---|
| 0 | Result written | On stdout, or with `--output` a one-line summary on stdout and the result in the file |
| 2 | Every exit 2 of `collect_codacy.py` (see `codacy-adapter.md`), and: a `component` outside `<project key>:`, an unlisted PR, a `--status` file that is malformed, for another project or for another PR, a status or kind mismatch, pages missing, repeated or overlapping, more than 10,000 results, or an invalid `--project` | Message on stderr, nothing on stdout, no output file created or changed |
| 3 | Valid so far, but more pages exist | Message on stderr with the page count, nothing on stdout, no output file |

The script shares its input and output guards with `collect_codacy.py` by importing them, so a guard fixed
there applies here. `sonar` commands are not pre-approved: the command raises its own permission prompt showing
the whole pipeline. If the CLI fails, the adapter gets empty or invalid input and exits 2.
