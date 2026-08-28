# Task: Mark issue #50 as a sub-issue of issue #40

## Mechanism

`github-issue-lifecycle` uses **GitHub's native sub-issues API** for this — not this repo's older
"Related: #N" prose-comment convention, and not any built-in `gh issue` subcommand (there isn't one:
`gh issue --help` has no sub-issue-specific command). This falls under Workflow 2 ("Work an Existing
Issue"), Step 4: Relate via Native Sub-Issues API, documented in
`workflows/work-an-existing-issue.md` and backed by the verified endpoint details in
`references/sub-issues-api.md`.

Concretely, for #50 as a sub-issue of #40, the skill would:

1. **Read the current relationship first**
   `gh api repos/<owner>/<repo>/issues/40/sub_issues` (REST GET, plural `sub_issues`) — or a GraphQL
   `subIssuesSummary` query — to see what #40 already has before adding anything.

2. **Resolve #50's internal numeric `id`** (see gotcha below)
   `gh api repos/<owner>/<repo>/issues/50 --jq '.id'`

3. **POST to add the relationship**
   `gh api repos/<owner>/<repo>/issues/40/sub_issues -f sub_issue_id=<50's internal id>`
   — issued against the **parent** issue's endpoint (#40), plural `sub_issues` path.

## The specific gotcha

**`sub_issue_id` must be the target issue's internal numeric `id`, not its visible issue `number`.**
These are different values — the skill's own verified example: a real issue in this repo had
`number: 163` but `id: 5277175402`. So marking #50 as a sub-issue of #40 requires first fetching
#50's real internal `id` via a GET (`gh api repos/<owner>/<repo>/issues/50 --jq '.id'`) and passing
*that* value as `sub_issue_id` — passing `50` directly would fail. This is called out as "a real
gotcha" directly in the skill's own SKILL.md (Native Sub-Issues API section) and verified live
against this repo during the skill's Design phase (2026-08-28), per `references/sub-issues-api.md`.

A second, related gotcha documented alongside it (same reference file): **the API path is plural
(`sub_issues`), not singular (`sub_issue`)**. A singular-path POST returns a plain 404 — indistinguishable
from "this repo doesn't support sub-issues" — unless you already know to use the plural form. The
plural path correctly 422s when `sub_issue_id` is missing, which is how the skill's authors confirmed
the endpoint was real and live rather than just guessing.

## Sources consulted

- `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md` — routes relate-work to Workflow 2 and names
  the native sub-issues API and the id-vs-number gotcha up front.
- `plugins/git-kit/skills/github-issue-lifecycle/workflows/work-an-existing-issue.md` — Step 4 gives the
  exact `gh api` sequence (read, resolve internal id, POST).
- `plugins/git-kit/skills/github-issue-lifecycle/references/sub-issues-api.md` — verified endpoint
  shapes and both gotchas (plural-path 404 trap; id-vs-number), with live-probe evidence from this repo.
