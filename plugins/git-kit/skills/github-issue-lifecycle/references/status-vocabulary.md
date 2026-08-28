# Status Vocabulary

Reuses `handling-review-findings`'s FIXED / declined / filed status pattern for freestanding issues —
an independent reuse of the same vocabulary and round model, not a runtime dependency (that skill's own
SKILL.md explicitly scopes it to PR-review findings, excluding freestanding issues).

## Mapping

| This skill's status | `handling-review-findings` equivalent | Meaning |
|---|---|---|
| Resolved | FIXED | Something was actually fixed |
| Declined | declined | Closed with nothing fixed (won't-fix / duplicate / risk-accepted / stale / process-gap-not-defect) |

The distinction matters because this repo's real issues otherwise blur it in prose ("deferred," "risk
accepted," "not fixed... tracked as open" even while still marked OPEN) with no structural marker.
Splitting Resolved from Declined makes that distinction a first-class action (Workflow 3, Step 2)
instead of prose buried in a comment.

## Round-Based Follow-Up

Reused directly from `handling-review-findings`'s own round model: a follow-up need after an issue
closes starts a new round rather than silently reopening or leaving an orphaned comment. Workflow 3,
Step 4 applies this.
