# Triage Decision — PR #142

## Finding

> **Critical** — SQL injection possible in `build_query()` at `db.py:210` — user input is concatenated
> directly into the query string.

Raised by: a human teammate, via a brand-new review comment against the current head SHA. This comment
was **not** something `handling-review-findings` triggered itself — it arrived independently, after this
skill had already triggered and fully triaged all 3 rounds it's allowed to trigger under
`review_findings_max_rounds: 3`.

## Round classification

The round budget (`review_findings_max_rounds: 3`) is already exhausted — this skill has triggered and
triaged rounds 1, 2, and 3. This finding is not "round 4" in any proactive sense: this skill does not
open or trigger further rounds beyond `max_rounds` (Workflow step 8 is skipped entirely once the budget
is reached). This finding instead falls into the one remaining situation the round-budget machinery
still has to account for: **a finding that shows up after the round budget is already exhausted** —
here, a human comment posted independently of anything this skill triggered.

## Which path — and why this is NOT one of the three named exceptions

It would be a mistake to reach for exception 1 (direct instruction), exception 2 (out-of-scope
component), or exception 3 (too large for this session) here — none of them apply:

- **Not exception 1** — nobody has said "file this instead of fixing it"; the disposition here is driven
  entirely by budget exhaustion + the `generate_issues` setting, not an explicit instruction.
- **Not exception 2** — `db.py` is presumably within this PR's own changed scope (nothing in the prompt
  suggests otherwise); this isn't a bug in a file the PR never touches.
- **Not exception 3** — nothing here indicates the fix itself needs capabilities beyond a same-session
  fix (data-flow analysis, a multi-file architectural change); a parameterized-query fix to
  `build_query()` is plausibly a normal, session-sized fix. Severity and "too large for a session" are
  independent axes — a Critical finding is not automatically exception 3.

This is the **separate, fourth "budget exhaustion" path** described in
`references/settings-and-round-budget.md`'s "`review_findings_generate_issues` and budget exhaustion"
section: the one situation where `review_findings_generate_issues` actually matters. Since
`review_findings_generate_issues` is `true` in this project's settings, the finding is **filed as an
issue instead of forcing a fourth round or fixing it in-session right now** — the same disposition that
would apply for a Minor/nit finding under this same setting, because this path is driven purely by
budget exhaustion + the setting, not by severity.

## The Hard Cap exception still applies — filing is not the end of the story

Because this finding is **Critical**, `references/round-and-dedup-rules.md`'s Hard Cap exception governs
what happens next, on top of the routing decision above:

- A Critical/Major finding may still legitimately end up *filed* as an issue (this is exactly one of the
  documented ways that can happen — budget exhaustion with `generate_issues: true`) — filing it here is
  not itself wrong or a violation of the Hard Cap rule.
- **But filing the issue is never itself an acceptance decision.** The PR does not get to proceed toward
  merge on the strength of "we filed it" alone. Merging with this Critical finding still open and
  unfixed requires a **separate, explicit `AskUserQuestion` risk-acceptance** from the user, before
  `merge-pr` is ever invoked. That confirmation has not happened yet as part of this triage pass — it is
  a distinct, later step (see `outputs/disclosure.md`).

## Dedup check (before filing)

Before drafting a new issue, check for an existing issue already filed against this PR/head-SHA for the
same finding — `gh issue list -R "<owner>/<repo>" --search "PR #142" --state all --limit 100` (unqualified
`gh issue list` is never used, since its default 30-issue cap and open-only default could hide a real
match). In this simulated exercise no such search is actually run (no real GitHub state exists), but the
triage explicitly assumes: no existing issue already covers this exact SQL-injection defect in
`build_query()` — so this is a fresh filing, not a duplicate.

## Drafted GitHub issue body

Filed as a local draft under `issues/` (e.g. `issues/2026-08-22-sql-injection-build-query.md`), following
`github-issue-creator`'s template, with the traceability payload `references/github-api-mechanics.md`
requires appended as its own `## Review Finding Source` section:

```markdown
# SQL injection possible in build_query() (db.py:210)

## Summary
`build_query()` in `db.py:210` concatenates user input directly into the query string, allowing SQL
injection.

## Details
A human reviewer flagged that user-supplied input is concatenated directly into the SQL query string
inside `build_query()` rather than being passed as a parameterized/bound value. This is exploitable by
any caller able to influence the concatenated input.

## Suggested Fix
Replace the string concatenation with parameterized query construction (bound parameters / prepared
statement placeholders) so user input is never interpolated directly into SQL text.

## Additional Context
This finding arrived after PR #142's review-round budget (`review_findings_max_rounds: 3`) was already
exhausted. Because `review_findings_generate_issues` is `true` for this project, it is filed as an issue
rather than triggering a fourth review round or being fixed within this session's remaining scope.

## Review Finding Source
- **PR:** <PR URL for PR #142> (placeholder — no real PR exists in this simulated exercise)
- **Head SHA:** <head SHA the finding was raised against> (placeholder)
- **Thread/comment:** <review thread/comment URL or ID for the human teammate's comment> (placeholder)
- **Reviewer:** Human teammate (not a bot/automated reviewer)
- **Severity:** Critical
```

Filed with a **plain, non-closing reference** — "Found in PR #142" — never "Fixes #142" / "Closes #142",
so a later merge cannot auto-close this still-open, still-unaddressed issue.

## Reply to the finding's own thread

```
Filed as issue #<new-issue-number> (Found in PR #142) rather than fixed in this session — this finding
arrived after this PR's review-round budget (max_rounds: 3) was already exhausted, and this project's
review_findings_generate_issues setting is true, which routes a post-budget finding to an issue instead
of forcing another round. Because this is a Critical (SQL injection) finding, it is also being flagged
separately to the team as a merge-blocking risk requiring explicit sign-off before this PR merges —
filing this issue does not by itself mean the risk has been accepted. This thread is being left
unresolved until the issue is addressed.
```

## Resolve the thread?

**No.** This finding is not fixed, and filing an issue for it is not equivalent to it being handled the
way a fix is. Per `references/round-and-dedup-rules.md`'s "Already-fixed threads get resolved with
commit-SHA evidence; deferred ones don't get resolved at all" — a deferred/filed finding gets a reply
pointing at the tracking issue, but its thread is explicitly left **unresolved**. Resolving it would
misrepresent the state to anyone reading the PR later, especially given the finding is Critical.
