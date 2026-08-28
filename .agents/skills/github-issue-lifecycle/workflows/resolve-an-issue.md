# Workflow 3: Resolve an Issue

## Step 1: Open-Question Gate

Before marking an issue Resolved, confirm no logged open question from prior comments remains
unaddressed. This gate must pass before Step 2 — an issue with an unresolved open question is not
ready to close as Resolved.

## Step 2: Resolve or Decline

Two distinct outcomes, both closing the issue but meaning different things:

- **Resolved** (status: FIXED — something was actually fixed). `gh issue comment <number> --body
  "Resolved: <summary>"` then `gh issue close <number>`.
- **Declined** (status: declined — closed with nothing fixed: won't-fix, duplicate, risk-accepted,
  stale, or process-gap-not-defect). `gh issue comment <number> --body "Declined: <reason>"` then
  `gh issue close <number>`.

Never close an issue silently — the status comment always precedes the close. See
`references/status-vocabulary.md` for why this maps onto `handling-review-findings`'s FIXED/declined
pattern, if more detail is needed.

## Step 3: Document Decisions

A comment summarizing the reasoning behind the resolution/decline, distinct from the one-line status
comment in Step 2 when the decision needs more explanation than that one line carries.

## Step 4: Follow-Ups

Reuses `handling-review-findings`'s round-based model directly: a follow-up need after closing starts a
new round, tracked the same way that skill tracks PR-review rounds, rather than inventing a separate
follow-up mechanism here.

## Step 5: Reopen (If Needed)

`gh issue reopen <number>` followed by a comment explaining why (new evidence contradicts the earlier
close), then re-run Workflow 2's Step 1 (Review Status) on it — a reopened issue re-enters Workflow 2,
it does not skip back into being "new."
