# SonarQube Cloud Adapter

Verified 2026-11-07 against `sonar` CLI 1.11.0 and this repository's real output. Self-managed SonarQube is
not covered. Re-check the shapes below before trusting them after a CLI update.

## Read commands (the only forms this skill runs)

Every read is `python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/qlty-sonar-read.py <form> ...`,
piped into `scripts/collect_sonar.py --input -`. The wrapper runs `sonar` with a fixed argument list from a fresh, empty
temporary directory outside every checkout (exit 2 if it is inside one), so a repository's own configuration file
cannot pick the server, validates every value, and prints only
the fields the adapter reads: the raw responses hold `author`, `assignee`, `contributors`, comment logins and commit
messages, which it drops. `sonar` must be on `PATH` (`sonar.exe` on Windows) in a folder outside the repository; the
default install is `~/.local/share/sonarqube-cli/bin`.

| Source | `qlty-sonar-read.py` form | `--kind` |
|---|---|---|
| A PR's analysis state, first | `pr-list --project <key> --pull-request <n>` | `pr-status` |
| A PR's open issues | `issues --project <key> --pull-request <n>` | `pr` |
| Default-branch issue list | `issues --project <key>` (`--branch <b>` for another branch, and the same `--branch <b>` to `collect_sonar.py` so the record names it; `--file <f>` narrows) | `repo` |
| Issues already accepted or marked false positive | `ignored --project <key>` (the comment text only, no login) | `ignored` |

What each form runs: `pr-list` is `sonar api get /api/project_pull_requests/list`; `issues` is `sonar list issues`
with `--format json --page-size 500 --page <n>`; `ignored` is `sonar api get /api/issues/search` with
`issueStatuses=ACCEPTED,FALSE_POSITIVE`, `additionalFields=comments`, `ps=500` and `p=<n>`. A fourth form,
`issue-state --issue <id>`, reads one issue's `issueStatus` and comment count (never the text; exit 2 unless Sonar
returns exactly that issue with a status) for
`resolving-analysis-findings` and `using-sonarqube-cloud`, and `gate-status --project <key>` with exactly one of
`--branch` or `--pull-request` runs `sonar quality-gate status` for `using-sonarqube-cloud`.

The `ignored` form keeps only the last comment's text, the one the record stores as `ignore_comment`. That text
can still name a person or hold contact details: keep the record in the scratchpad, and quote an `ignore_comment`
in a report or a shared file only when asked.

**Which `sonar` runs, and with what environment.** The wrapper uses codex-kit's `gitExecutable` pattern (`cdx-lintignore-base.mjs`):
it searches `PATH` itself and skips an empty, relative or quoted-empty entry and any folder inside a checkout that
encloses the caller's working directory (every enclosing one, so a worktree nested in its main checkout or a submodule
in its superproject excludes the outer tree too), compared by spelling and by file identity, because an activated
`.venv` or `node_modules/.bin` there can carry a `sonar` a branch committed. A `sonar` link that resolves into such a
folder is refused, and `sonar` itself gets the same filtered `PATH`. It accepts only `sonar.exe` on Windows, so a
`.cmd` shim never runs through `cmd.exe`. Like codex-kit's `gitEnv`, it drops the variables the CLI reads to choose
its server or fetch code (`SONARQUBE_URL`, `SONAR_HOST_URL`, `SONARQUBE_CLI_SERVER`, the `SONARQUBE_CLI_*_URL`
overrides and `SONARQUBE_CLI_UPDATE_SCRIPT_BASE_URL`, read from the CLI's own bundle 2026-11-09 and 2026-11-10) and keeps the authentication ones. A security review checked this lookup on 2026-11-09.

**Known residuals.** A `sonar` in a `PATH` folder outside every enclosing checkout is trusted, as the former direct
grant trusted it, and the skip only knows the checkouts around the working directory: run from outside a checkout, an
in-repository `PATH` folder is accepted. Other variables the CLI reads still pass through: the proxy variables
(`SONAR_HTTPS_PROXY_URL`, `SONAR_HTTP_PROXY_URL`, `HTTPS_PROXY`, `HTTP_PROXY`), the CA and TLS variables
(`SONAR_CA_CERT`, `NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `NODE_TLS_REJECT_UNAUTHORIZED`), `SONARQUBE_CLI_KEYCHAIN_FILE`
and `SONAR_USER_HOME`, whose `sonarqube-cli/state.json` holds the active server URL (a 2026-11-10 security review read
this from the bundle; stored proxy and CA settings are likely but unverified). A proxy combined with a trusted CA
could intercept the token; proxies are kept so a corporate proxy still works. Because `SONARQUBE_CLI_SERVER` is
dropped, environment-variable authentication through the wrapper works only for SonarQube Cloud's default region:
SonarQube Server and US-region users authenticate with `sonar auth login` instead. Git's repository-location
variables (`GIT_DIR`, `GIT_WORK_TREE` and siblings) are dropped too, so the CLI's own configuration search stays in the
wrapper's empty working directory. Another user who owns a parent of `TMPDIR` could rename it between the wrapper's
checkout check and the run; under the default sticky `/tmp` that is not possible. On a filesystem without file ids (`st_ino` 0, for example
FAT or some network shares) only the spelling comparison applies, so a junction or 8.3 alias there is not caught. It was not
run on Windows: there, `python3` may be
absent (the grants call `python3 -I`, like every quality-kit script grant), and that the Windows CLI is a `sonar.exe`
is unverified (a `.cmd` install is refused, not run).

**A PR takes three pipes.** `--kind pr-status --pull-request <n> --output "<scratchpad>/sonar-status.json"` keeps
only that PR's SHA, analysis date and gate status. `--kind pr --status "<scratchpad>/sonar-status.json"` then
reads it and refuses issues from any other PR. An empty issue list cannot be checked that way, and issues carry no
commit, so the `--status` file is not bound to them: the head comparison in `SKILL.md` step 5 is what catches a stale one. The third pipe re-reads the PR list after
the issues with `--confirm "<scratchpad>/findings-record.json" --output "<scratchpad>/findings-record.json"`: it
compares the SHA, analysis date and gate with the record's and sets `source.snapshot_consistent`.

**Several pages.** `qlty-sonar-read.py` fetches every page itself (500 per page) and prints one JSON document per page;
`collect_sonar.py` reads them and refuses missing, repeated or overlapping pages. The API refuses to go past 10,000
results (`400`, checked 2026-11-07), so the wrapper stops at 20 pages with exit 3, printing nothing: narrow the read
with `--file`. `collect_sonar.py`'s own exit 3 (more pages exist) applies only to input that did not come from the
wrapper. A `--file` or `--branch` value comes
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
| 1 | Stdout could not be written, because the reader left early or the write failed: treat the output as incomplete. With `--output`, the file is written and only the summary line was lost |
| 2 | The input is unreadable, outside a scratchpad directory you own, not a regular file, larger than 32 MiB, not valid JSON or nested too deeply; the command line is invalid; `--output` is refused (outside a directory named `scratchpad`, on POSIX one you do not own or that others can write to, inside a folder containing `.git`, a symlink leaving the scratchpad, a directory, or a missing directory); or: a `component` outside `<project key>:`, an unlisted PR, a `--status` file that is malformed, for another project or for another PR, a status or kind mismatch, pages missing, repeated or overlapping, more than 10,000 results, or an invalid `--project` | Message on stderr, nothing on stdout, no output file created or changed |
| 3 | Valid so far, but more pages exist | Message on stderr with the page count, nothing on stdout, no output file |

The script shares its input and output guards with `collect_codacy.py` by importing them, so a guard fixed
there applies here. The only Sonar grant is `qlty-sonar-read.py`. If the CLI fails, the wrapper exits 1 (2 for a
response that is not JSON; `gate-status` instead prints the verdict and exits 0 when the CLI reports a failing
gate with exit 51, or exit 1 with an uncomputed gate) and prints nothing; with `set -o pipefail` the pipe fails, and without it the adapter
gets empty input and exits 2.
