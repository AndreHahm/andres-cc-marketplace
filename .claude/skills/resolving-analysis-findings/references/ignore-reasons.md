# Codacy Ignore Reasons

Used for rung 3 (a per-issue ignore). Every one of these is a remote write and needs the per-command approval
in `SKILL.md`'s Decision rights first.

Verified 2026-10-17 against `codacy pull-request --help`: the flags `--ignore-issue`, `--ignore-reason`
(default `AcceptedUse`), `--ignore-comment`, `--unignore-issue`, `-F`/`--ignore-all-false-positives` ("with
reason FalsePositive"), `--reanalyze` and `--reanalyze-and-wait` exist as described below. Not verified: running any of them, and
whether an ignore can target a repository-list finding.

## Command

```text
codacy pull-request <provider> <org> <repo> <number> \
  --ignore-issue <issueId> --ignore-reason <reason> --ignore-comment '<comment>'
```

`<issueId>` comes from the findings record (`issue_id`). A repository-level list carries none, so take the id
from the PR's own analysis. `--ignore-reason` defaults to `AcceptedUse` when omitted: always pass it
explicitly. `--unignore-issue <issueId>` reverses an ignore.

`-F`/`--ignore-all-false-positives` ignores every issue Codacy marks as a potential false positive in the PR
with reason `FalsePositive`. This skill never runs it: the findings record cannot say which issues the flag
would cover, so the exact command is handed to the user instead.

The comment is single-quoted and written by you from what the code does, using only letters, digits, spaces and
`. , : ; ( ) / _ -`. It starts with a letter or digit, so it can never be read as a flag, never contains `'`,
`$`, a backtick or a backslash, and is never copied from a provider message or a source line. `<issueId>` must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`; stop otherwise.

## Reasons

| Reason | Use when | Comment must say |
|---|---|---|
| `FalsePositive` | The rule misreads the code | What the rule assumed and what the code actually does |
| `NotExploitable` | The pattern is real but no harm is reachable | Why: for example "arguments are a commit id and a ref name, never user text" |
| `AcceptedUse` | The pattern is deliberate and accepted | What the use is and where the decision is recorded |
| `TestCode` | The finding is in test code | What it is (for example "pytest assert") |
| `ExternalCode` | Vendored or generated code that is not edited here | Where the code comes from |

## Example comments

- `AcceptedUse`: "Fixed literal command, list arguments, no shell; accepted use is recorded in docs/ci.md."
- `NotExploitable`: "List-argument call, no shell; the only variable argument follows a double dash."

A comment that restates the rule name ("subprocess call") is not a reason.

## Audit

`codacy issues <provider> <org> <repo> -i -n 1000 -o json` (run by the collecting skill, not directly from this
skill) lists ignored issues with reason, comment, who and when. `collecting-analysis-findings` reads it as `--kind ignored`. Its `-I`/`--ignore` flag (bulk ignore) is
not part of this workflow.
