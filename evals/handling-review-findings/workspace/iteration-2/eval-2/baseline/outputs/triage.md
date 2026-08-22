# Triage: PR #142 — Codex finding on `auth/session.py:88`

## Finding under review

> **Minor** — `auth/session.py:88` (a file this PR never touches) has a stale docstring that still describes a removed parameter.

**Context:**
- PR #142 changes only `billing/invoice.py`.
- Round: 1 (first review round).
- `review_findings_severity_gate`: `false` (default).
- `review_findings_generate_issues`: `false` (default).

## Decision: File as a GitHub issue (Issue path) — Out-of-scope-component exception

This finding is routed to the **Issue path**, not the Fix path, even though:
- We are in round 1, well within any round budget.
- `review_findings_generate_issues` is `false` (the default budget-exhaustion behavior is irrelevant here anyway, since the round budget isn't exhausted).
- The severity gate is `false`, so a Minor finding would normally still be eligible for an in-session fix.

None of that matters here because the finding fails a more fundamental scope test before the round/severity logic is even consulted: **the finding is not about a file this PR changed.**

### Which named exception applies, and why

Of the three named exceptions that can pull a real, valid finding out of the normal "fix it in this round" default:

1. **Direct instruction** — does not apply. No one (user or reviewer) has said "don't fix this, file it instead." This exception is not in play here.
2. **Out-of-scope component** — **applies.** PR #142's diff touches only `billing/invoice.py`. The flagged file, `auth/session.py`, is not part of this PR's change set at all. Fixing a stale docstring in a file this PR never modified would:
   - Expand the PR's diff into unrelated territory, which reviewers and CI expect *not* to happen mid-review.
   - Attribute an unrelated code change to a commit/PR whose stated purpose is billing/invoice work, hurting blame/audit trail clarity.
   - Not have been caught by this PR's own tests/CI path, so an in-session "fix" here isn't actually exercised by anything this review round is validating.
3. **Too large for this session** — does not apply. The fix itself (correcting a docstring) is trivially small. Size/complexity is not why this is deferred — scope is.

Because exception 2 is met, this routes to the **Issue path regardless of round number and regardless of `review_findings_generate_issues`.** The `generate_issues` flag governs what happens to *in-scope* findings once the round budget is exhausted — it does not gate whether an *out-of-scope* finding gets filed. An out-of-scope finding is never eligible for an in-session fix in the first place, no matter how early the round or how minor the severity, so it always goes to the Issue path independent of that setting.

I am explicitly **not** fixing this in-session just because it happens to be easy (a one-line docstring edit). Ease of fix is not one of the three exceptions and is not a reason to expand this PR's scope.

## Drafted GitHub issue

**Title:** Stale docstring in `auth/session.py:88` references a removed parameter

**Body:**

```markdown
## Summary
`auth/session.py:88` has a docstring that still describes a parameter that has since been removed
from the function's signature. The docstring should be updated to match the current signature.

## Traceability
- **Source PR:** #142 (https://github.com/<org>/<repo>/pull/142)
- **Head SHA at time of finding:** <PR_142_HEAD_SHA>
- **Review thread / comment:** <LINK_TO_CODEX_REVIEW_COMMENT_ON_PR_142>
- **Reviewer:** Codex
- **Severity:** Minor

## Why this isn't fixed in PR #142
PR #142 only changes `billing/invoice.py`. `auth/session.py` is out of scope for that PR's diff,
so this finding is filed separately rather than fixed inline, to avoid scope creep in an unrelated
change set.

## Suggested fix
Update the docstring at `auth/session.py:88` to remove the reference to the deleted parameter (and
verify no other parameters/return-value documentation drifted at the same time).

Found in PR #142
```

**Non-closing PR reference (exact text used inside the issue body):**

```
Found in PR #142
```

This is deliberately a plain, non-closing reference — never `Fixes #142` or `Closes #142` — because filing this issue does not resolve or complete PR #142; it only records a separate, unrelated cleanup task that PR #142's review happened to surface.

## Drafted reply to Codex's review thread

```
Thanks for flagging this — you're right that the docstring at `auth/session.py:88` is stale.
However, this PR only touches `billing/invoice.py`, and `auth/session.py` is outside its scope,
so I don't want to fold an unrelated file change into this diff. I've filed this separately as
issue #<NEW_ISSUE_NUMBER> so it can be tracked and fixed on its own. Leaving this thread open/
unresolved since it isn't being addressed in this PR.
```

(The literal issue number is a placeholder — `#<NEW_ISSUE_NUMBER>` — since this is a simulated
exercise with no real issue tracker call made.)

## Thread resolution status

**The thread is NOT resolved.** It is replied to (pointing at the newly filed issue) but left open,
because the underlying finding has not actually been addressed by this PR — it's been deferred to a
separate issue for out-of-scope reasons, not fixed, declined, or otherwise closed out. Resolving the
thread would misrepresent the finding as handled when in fact no code change addressing it has
happened in this PR at all.
