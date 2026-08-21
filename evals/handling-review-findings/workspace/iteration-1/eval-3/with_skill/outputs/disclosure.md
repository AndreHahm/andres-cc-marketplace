# Review Finding Disclosure — PR #142 (before any merge discussion)

## Summary

Round 3 review produced **1 finding**, handled as follows:

| # | Finding | Severity | Round | Disposition |
|---|---|---|---|---|
| 1 | SQL injection in `build_query()` (`db.py:210`) — user input concatenated directly into the query string | Critical | 3 (new) | **Filed as an issue, not fixed.** Thread replied-to, left **unresolved**. |

**Fixed this session:** 0
**Filed as issues:** 1
**Declined:** 0

## Why this wasn't fixed now

This is the first appearance of this finding, but it surfaced in round 3. `handling-review-findings`
caps in-session fixing at two rounds per finding — a finding first raised in round 3 or later goes to
the Issue path regardless of how simple the fix looks, so the round cap doesn't turn into an
indefinitely-chased review loop. This routing is unaffected by whether the severity gate is on or off;
severity only changes the default for Minor/nit findings, and this finding is Critical.

## Outstanding risk — requires your explicit decision before merge

**This finding is Critical, and it is currently unresolved.** Filing it as a tracked issue is not the
same as accepting the risk — those are two separate, independently-required steps for any Critical or
Major finding under this skill's Hard Cap exception. The round cap governs how many fix cycles get
chased; it never authorizes merging with a known, unfixed Critical/Major defect on the strength of
"it's filed" alone.

**Before `merge-pr` is invoked, you need to explicitly confirm:**

> Do you accept merging PR #142 with a known, unfixed **Critical SQL injection** finding in
> `build_query()` (`db.py:210`), tracked as a separate issue rather than fixed in this PR?

Until that confirmation is given, this finding should be treated as merge-blocking. This disclosure is
informational only — it does not itself grant or imply merge readiness, and it doesn't substitute for
`merge-pr`'s own independent readiness gate (required status checks, no outstanding `CHANGES_REQUESTED`
review, any branch-protection "require conversation resolution" setting). If `merge-pr` is run next,
name this finding explicitly in that discussion — `merge-pr`'s generic "no outstanding
`CHANGES_REQUESTED`" check has no visibility into an intentionally-left-open review thread like this
one.

## Note on this session's constraints

This triage was run as a simulated exercise against a described review state, not a live PR — no
`gh`/API calls were made. The issue-filing and thread-reply actions described in `triage.md` are the
decisions this skill's workflow calls for, not actions actually executed against GitHub; a real run
would still need to re-fetch current PR state immediately before acting (per
`.claude/rules/recheck-state-before-side-effecting-action.md`), since state may have changed since this
finding was described.
