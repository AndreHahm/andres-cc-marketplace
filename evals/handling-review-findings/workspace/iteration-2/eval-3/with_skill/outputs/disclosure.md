# Disclosure Report — PR #142

*(per Workflow step 7 — reported plainly before any merge discussion, per
`.claude/rules/disclose-before-overriding-decisions.md`)*

## Round-budget status

`review_findings_max_rounds` (3) has already been reached and fully triaged — this skill will **not**
trigger any further review round for this PR (Workflow step 8 is skipped entirely at this point; a
further finding that shows up anyway is handled per `review_findings_generate_issues`, exactly as
happened below).

## What was handled this session

| Finding | Severity | Source | Disposition |
|---|---|---|---|
| SQL injection possible in `build_query()` (`db.py:210`) — user input concatenated directly into the query string | **Critical** | Human teammate, posted after the round budget was already exhausted | **Filed as an issue** (`issues/2026-08-22-sql-injection-build-query.md`, to become issue `#<new-issue-number>` on filing) — not fixed in-session, not a fourth round |

No other findings were part of this session's scope.

## Why this was filed rather than fixed or re-rounded

This did **not** go through any of the three named exceptions (direct instruction, out-of-scope
component, too-large-for-this-session). It went through the separate, fourth path that exists
specifically for this situation: a finding arriving **after** `review_findings_max_rounds` is already
exhausted, with `review_findings_generate_issues` set to `true` for this project. Under that
combination, the finding is filed as an issue instead of the skill forcing a fourth round or fixing it
outside its normal round-triggering flow.

## This finding is Critical — merge-blocking, not merge-cleared

**This is the most important part of this report.** Because the finding is Critical (SQL injection):

- **Filing the issue is not a risk-acceptance decision.** An issue being filed and a review thread
  getting a reply pointing at it does not mean the underlying vulnerability has been evaluated and
  accepted as safe to leave unfixed for now — those are two independent things, and only the first has
  happened so far.
- **This finding is explicitly named here as a merge-blocking risk.** The PR should not be treated as
  safe to merge while a known, unfixed SQL-injection vulnerability sits in `build_query()`, regardless of
  how clean every other review round came back.
- **Merging requires a separate, explicit human risk-acceptance decision before `merge-pr` is invoked at
  all.** That confirmation (a distinct `AskUserQuestion` explicitly asking whether this specific known,
  unfixed Critical risk is accepted) has **not** happened as part of this triage pass and must happen
  before any merge step is discussed or run.
- This report itself is purely informational disclosure, not that confirmation — reading this report is
  not equivalent to accepting the risk.

## Relationship to `merge-pr`

This disclosure never implies the PR is mergeable, and it is not a substitute for `merge-pr`'s own
independent readiness gate (required status checks, no outstanding `CHANGES_REQUESTED` review, any
"require conversation resolution" branch-protection setting). Even if `merge-pr`'s own checks all pass
independently, this Critical, unfixed, filed-not-fixed SQL-injection finding must be named explicitly
and separately risk-accepted by the user before merge is discussed further — `merge-pr` being green on
its own criteria does not substitute for that acceptance step.

## Bottom line

- 1 finding handled this session: Critical SQL-injection risk in `build_query()`, filed as issue
  `#<new-issue-number>`, thread replied-to and left **unresolved**.
- No further review rounds will be triggered by this skill (`max_rounds` reached).
- **Do not proceed to `merge-pr` without first getting an explicit, separate risk-acceptance decision
  for this specific Critical finding.**
