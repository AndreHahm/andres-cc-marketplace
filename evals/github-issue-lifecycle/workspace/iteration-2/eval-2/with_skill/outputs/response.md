# Marking Issue #50 as a Sub-Issue of Issue #40

## Mechanism

`github-issue-lifecycle` uses GitHub's **native sub-issues REST API**, accessed via `gh api` — not
this repo's older "Related: #N" prose-comment convention. This is Workflow 2 ("Work an Existing
Issue"), Step 4: "Relate via Native Sub-Issues API," documented in
`plugins/git-kit/skills/github-issue-lifecycle/references/sub-issues-api.md`.

There is no native `gh issue` subcommand for this — `gh issue --help` has no sub-issue-specific
command, so every sub-issue operation goes through `gh api`'s REST surface directly.

### Concrete steps for #50 → sub-issue of #40

1. **Read the current relationship first** (don't add blindly):
   `gh api repos/<owner>/<repo>/issues/40/sub_issues` — GET, plural `sub_issues`. Returns `[]` (200,
   not 404) if #40 has no sub-issues yet — that's a valid result, not an error.

2. **Get #50's internal numeric `id`** (not its visible number):
   `gh api repos/<owner>/<repo>/issues/50 --jq '.id'`

3. **POST #50 onto #40 as a sub-issue**, using that internal id:
   `gh api repos/<owner>/<repo>/issues/40/sub_issues -f sub_issue_id=<internal-id-from-step-2>`
   — POST, path is `.../issues/40/sub_issues` (the parent's number goes in the path; the child issue
   is identified by `sub_issue_id` in the payload).

## The specific gotcha

**`sub_issue_id` must be the target issue's internal numeric `id`, not its visible issue `number`.**
These are different values (e.g. one real issue in this repo verified during the skill's design
phase had `number: 163` but `id: 5277175402`). Passing `50` (the visible number) as `sub_issue_id`
fails — you must first `GET repos/<owner>/<repo>/issues/50` and read `.id` out of the response, then
use *that* value in the POST.

There's a second, related gotcha worth flagging alongside it: **the endpoint path is plural
(`sub_issues`), not singular.** A singular-path POST (`.../sub_issue`) returns a plain 404 — which is
indistinguishable from "this repo doesn't support sub-issues at all" unless you already know to try
the plural form. The correct plural path instead returns a 422 validation error when `sub_issue_id`
is missing, which is what confirms the endpoint is real and live. Both gotchas were verified live
against this repo during the skill's own design phase (2026-08-28), not assumed from the API's name.

## Source files consulted

- `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md` — routes relate-work to Workflow 2 and
  flags the native sub-issues API + id-vs-number gotcha at a high level.
- `plugins/git-kit/skills/github-issue-lifecycle/workflows/work-an-existing-issue.md` — Step 4 gives
  the exact GET/POST sequence.
- `plugins/git-kit/skills/github-issue-lifecycle/references/sub-issues-api.md` — full verified detail
  on both gotchas (plural path, id-vs-number), plus the empty-array-is-not-an-error note for reads.
