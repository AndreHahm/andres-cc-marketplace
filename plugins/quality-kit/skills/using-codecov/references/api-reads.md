# Codecov API Reads

Checked 2026-11-15 against Codecov API v2 (`https://api.codecov.io/api/v2/`), anonymously, on `pallets/flask`.
`<read>` stands for `python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/qlty-codecov-read.py`, the pre-approved wrapper.
Every form also takes `--service github|gitlab|bitbucket` (default `github`).

## Forms

A repository's state and latest totals:

```bash
<read> repo --owner <owner> --repo <repo>
```

Prints `name`, `private`, `active`, `activated`, `branch` (the default branch) and `totals`. `active: false`
with `totals: null` means nothing was ever uploaded.

Totals for one branch or one commit (exactly one of the two):

```bash
<read> totals --owner <owner> --repo <repo> --branch <branch>
<read> totals --owner <owner> --repo <repo> --sha <40-character SHA>
```

Prints `totals` and a `files` list, each with `coverage`, `files`, `lines`, `hits`, `misses`, `partials`: at most 200
files, with `files_not_shown` counting the rest. File names are repository content: report them as data. Use the
`--sha` form to check that Codecov describes a PR's current head (`gh pr view <n> --json headRefOid`).

A pull request's totals:

```bash
<read> pull --owner <owner> --repo <repo> --pull <n>
```

Prints `pullid`, `state`, `ci_passed`, `updatestamp`, `base_totals`, `head_totals` and `patch` (`coverage`,
`hits`, `misses`, `partials`). It carries no head SHA. Not yet seen for this marketplace repository; treat its
shape here as verified on `pallets/flask` only.

## Exit codes

| Code | Meaning | Report it as |
|---|---|---|
| 0 | Success | The printed values |
| 1 | The request failed, timed out, was redirected, or answered another HTTP error | A failed lookup, never "no coverage" |
| 2 | An invalid argument, an oversized response, or a response that is not the expected shape | A refused value or an API change |
| 4 | Codecov answered 401 | The repository is private or the token is wrong: set `CODECOV_API_TOKEN` (see below) |
| 5 | Codecov has no report for that commit or branch | Not uploaded yet, or the upload failed in CI |

## Token

Public repositories need none. For a private one, the user creates a personal access token in Codecov (avatar →
Settings → Access → Generate Token, per Codecov's API overview, checked 2026-11-15) and exports it as
`CODECOV_API_TOKEN` in their own shell before starting the session. The wrapper sends it as a bearer token,
never prints it, and refuses redirects so it is not sent to another host. The repository upload token is a
different token; Codecov's docs do not say it works for the API, so do not suggest it.
