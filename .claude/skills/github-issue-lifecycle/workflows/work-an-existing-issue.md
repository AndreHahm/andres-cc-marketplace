# Workflow 2: Work an Existing Issue

## Step 1: Review Status

`gh issue view <number>` — read the current state, labels, and comment history before doing anything
else.

## Step 2: Re-Verify Staleness

Distinct from Workflow 1's filing-time verification: re-check whether the issue's original claims still
hold *now*, against the current repo state — not just re-reading the old issue text. This repo's own
culture leans on this pattern (`analyzing-sessions`, and real issues that were "reproduced again" across
multiple sessions before being trusted).

## Step 3: Find and Validate Related Issues

Search first: `gh api search/issues -f q="repo:<owner>/<repo> is:issue <keywords>"`. Then validate —
this is the mandatory second step, not optional. GitHub's full-text search returns real false positives
(a PR number appearing inside an example shell command, a generic word matching an unrelated issue) —
read each candidate's actual content before recording it as genuinely related. Never report a search hit
as "related" without this validation step.

## Step 4: Relate via Native Sub-Issues API

Read the current relationship first: `gh api repos/<owner>/<repo>/issues/<number>/sub_issues` (REST,
plural `sub_issues`) or a GraphQL `subIssuesSummary` query.

To add one: get the target's internal numeric `id` first —
`gh api repos/<owner>/<repo>/issues/<target-number> --jq '.id'` (this is **not** the same as the
target's visible `number`; using `number` here fails). Then
`gh api repos/<owner>/<repo>/issues/<number>/sub_issues -f sub_issue_id=<that-internal-id>` — note the
path is **plural** `sub_issues`; the singular `sub_issue` 404s.

See `references/sub-issues-api.md` for the verified live-probe evidence behind both gotchas above, if
more detail is needed.

## Step 5: Group for Resolution

Cluster related issues that share a root cause or would naturally be fixed together, once Step 3 has
validated the relationships.

## Step 6: Prioritize

A severity/impact-driven ordering judgment across the current working set.

## Step 7: Impact Analysis (Re-Run)

Re-run the same impact-analysis judgment from Workflow 1's Step 5. This is explicitly re-runnable, not
one-shot — a new angle or a third independent pass can raise the assessed severity on reconfirmation
(this repo has a real precedent: an issue was escalated to Critical only after a 3rd independent pass
reconfirmed it).

## Step 8: Create Comments

`gh issue comment <number> --body "<text>"`. When citing supporting evidence (run records, `scope.json`,
retrospective docs), link the specific file path in the comment — this repo's real issues commonly cite
evidence this way, so treat it as a documented comment convention here rather than a separate task.
