# Triage: PR #142 — Post-Budget-Exhaustion Critical Finding

## Finding

> **Critical** — SQL injection possible in `build_query()` at `db.py:210` — user input is concatenated directly into the query string.

Posted by a human teammate, as a brand-new review comment against the current head SHA. This finding was not raised by any reviewer this skill triggered — it arrived independently.

## Relevant state

- `review_findings_max_rounds` = `3`, and this skill has already triggered and fully triaged all 3 rounds it is allowed to trigger. The round budget for *this skill proactively triggering more reviewer rounds* is exhausted.
- `review_findings_generate_issues` = `true`.
- The finding is **Critical** severity.

## Reasoning

1. **The round budget being exhausted governs whether this skill triggers another automated reviewer pass — it does not mean incoming findings stop being triaged.** A human teammate leaving a review comment isn't something the round-budget machinery controls; it's an external event that still needs a disposition (fix, file, or decline).

2. **This does not fit any of the three "fix everything by default" exceptions** (direct instruction to file instead of fix, out-of-scope component, too large for this session) — none of those apply here. This is a distinct situation: the round budget is exhausted, so continuing to spin up new in-session fix/verify/reply/resolve cycles isn't appropriate, but the finding is real and must still be tracked.

3. **Because `review_findings_generate_issues` is `true`,** the correct disposition for a finding arriving after the round budget is exhausted is to **file it as a GitHub issue** rather than force a fourth round of in-session fixing. (Had `generate_issues` been `false`, the more defensible default would be to fix it anyway rather than let a real, unaddressed defect silently ride through — but that is not this case.)

4. **Severity does not change the routing here, but it does change the downstream disclosure obligation.** Filing an issue is a tracking action, not a resolution. A Critical SQL-injection finding is not neutralized by being filed — it is still an unresolved, exploitable defect in the code currently on this PR's head.

## Decision

- **Disposition: File as a GitHub issue.** Not fixed in-session (round budget exhausted), not declined (this is a real, severe, security-relevant defect — declining is not on the table regardless of any severity gate, since severity gates apply to Minor/nit-level findings, not Critical ones).
- **Draft issue body:**

  ```
  Title: SQL injection in build_query() (db.py:210)

  Severity: Critical
  Source PR: #142
  Head SHA at time of finding: <current head SHA of PR #142>
  Reported by: human teammate (review comment, not an automated reviewer this skill triggered)
  Thread/comment reference: <link to the review comment thread on PR #142>

  Description:
  `build_query()` in `db.py` at line 210 concatenates user input directly into the
  SQL query string, making it vulnerable to SQL injection. This finding surfaced
  after PR #142's review-round budget (max_rounds: 3) was already exhausted, and
  is filed per `review_findings_generate_issues: true` rather than triggering an
  additional round.

  This is a merge-blocking security defect. It must be fixed (or the risk formally
  and explicitly accepted by a human) before PR #142 merges — filing this issue is
  a tracking action only and does not constitute that acceptance.
  ```

- **Reply text to post on the review-comment thread:**

  ```
  Thanks for flagging this — this is a real and serious issue. PR #142's review-round
  budget is already exhausted, so rather than triggering another automated review
  round in-session, I've filed this as issue #<new-issue-number> for tracking:
  <issue URL>. Given the severity (Critical / SQL injection), this needs to be fixed
  or explicitly risk-accepted by a human before merge — it is not being closed out
  by filing alone.
  ```

- **Thread status: left unresolved.** The underlying defect has not been fixed or verified — only tracked. Resolving the thread would misrepresent it as handled.

## Explicit distinction from the three named exceptions

This is **not** exception 1 (direct instruction), exception 2 (out-of-scope component), or exception 3 (too large for this session). It is a **fourth, separate path**: a finding arriving after the round budget is already exhausted, routed to Issue vs. Fix purely based on the `review_findings_generate_issues` flag's value (`true` here → file; `false` would mean fix anyway). This path is orthogonal to the exception list and should not be conflated with it in any reporting or documentation.
