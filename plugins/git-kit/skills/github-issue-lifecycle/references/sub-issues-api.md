# Native Sub-Issues API

Verified live against this repo during this skill's own Design phase (2026-08-28) — both the read and
write sides, plus one additional write-side correction (the `-F` vs `-f` typing gotcha below) found via
`cross-model-review` and confirmed against `gh api --help` rather than a fresh live write probe.

## Availability

Confirmed available on this repo during this skill's Design phase via a one-time, design-time GraphQL
query (a `subIssuesSummary` lookup) — this was a verification step taken while designing this skill,
not a capability this skill exercises at runtime; this skill's own `allowed-tools` grants only the REST
operations below, not `gh api graphql`. The GraphQL check returned real data (not null/absent) on a real
issue in this repo, confirming the feature is enabled.

## Reading Sub-Issues (REST)

`gh api repos/<owner>/<repo>/issues/<number>/sub_issues` — GET, plural `sub_issues`. Returns `[]` for
an issue with no sub-issues (200, not 404) — an empty array is a valid, successful result, not an
error.

## Adding a Sub-Issue (REST) — Verified Gotchas

`gh api repos/<owner>/<repo>/issues/<number>/sub_issues -F sub_issue_id=<id>` — POST, **plural**
`sub_issues` in the path.

Three things a naive implementation gets wrong. The first two were confirmed by a live probe against
this repo during Design; the third (`-F` vs `-f`) is a `gh api` typing rule confirmed against `gh api
--help`, not separately live-probed with a real write:

1. **The path is plural (`sub_issues`), not singular (`sub_issue`).** A singular-path POST returns a
   plain 404 Not Found — indistinguishable from "this repo doesn't support sub-issues" unless you
   already know to try the plural form. The plural path correctly returns a 422 validation error when
   `sub_issue_id` is missing, confirming the endpoint is real and live.
2. **`sub_issue_id` is the target issue's internal numeric `id`, not its visible `number`.** These are
   different values — e.g. a real issue in this repo had `number: 163` but `id: 5277175402`. Get the
   internal id first: `gh api repos/<owner>/<repo>/issues/<target-number> --jq '.id'`.
3. **Use `-F`/`--field`, not `-f`/`--raw-field`, for `sub_issue_id`.** `-f` always sends a string value;
   `-F` applies `gh api`'s own type conversion, sending a bare integer as a JSON number. Since
   `sub_issue_id` must be a number, `-f sub_issue_id=<id>` risks GitHub's schema validation rejecting
   the request — found via `cross-model-review` (2026-08-28), not part of the original Design-phase
   live probe, which tested the two gotchas above but never this specific typing distinction.

## No Native `gh issue` Subcommand

`gh issue --help` has no sub-issue-specific subcommand — every sub-issues operation in this skill goes
through `gh api`'s REST surface directly (the read/write operations above), not a higher-level `gh
issue` wrapper.
