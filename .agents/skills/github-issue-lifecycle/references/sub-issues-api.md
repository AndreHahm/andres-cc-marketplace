# Native Sub-Issues API

Verified live against this repo during this skill's own Design phase (2026-08-28) — both the read and
write sides.

## Availability

Confirmed available on this repo via a live GraphQL query:

```text
{
  repository(owner: "<owner>", name: "<repo>") {
    issue(number: <n>) {
      subIssuesSummary { total completed percentCompleted }
    }
  }
}
```

Run via `gh api graphql -f query='...'`. Returns real data (not null/absent) on a real issue in this
repo, confirming the feature is enabled.

## Reading Sub-Issues (REST)

`gh api repos/<owner>/<repo>/issues/<number>/sub_issues` — GET, plural `sub_issues`. Returns `[]` for
an issue with no sub-issues (200, not 404) — an empty array is a valid, successful result, not an
error.

## Adding a Sub-Issue (REST) — Verified Gotchas

`gh api repos/<owner>/<repo>/issues/<number>/sub_issues -f sub_issue_id=<id>` — POST, **plural**
`sub_issues` in the path.

Two things a naive implementation gets wrong, both confirmed by a live probe against this repo:

1. **The path is plural (`sub_issues`), not singular (`sub_issue`).** A singular-path POST returns a
   plain 404 Not Found — indistinguishable from "this repo doesn't support sub-issues" unless you
   already know to try the plural form. The plural path correctly returns a 422 validation error when
   `sub_issue_id` is missing, confirming the endpoint is real and live.
2. **`sub_issue_id` is the target issue's internal numeric `id`, not its visible `number`.** These are
   different values — e.g. a real issue in this repo had `number: 163` but `id: 5277175402`. Get the
   internal id first: `gh api repos/<owner>/<repo>/issues/<target-number> --jq '.id'`.

## No Native `gh issue` Subcommand

`gh issue --help` has no sub-issue-specific subcommand — every sub-issues operation in this skill goes
through `gh api` directly (GraphQL for reads, REST for the read/write operations above), not a
higher-level `gh issue` wrapper.
