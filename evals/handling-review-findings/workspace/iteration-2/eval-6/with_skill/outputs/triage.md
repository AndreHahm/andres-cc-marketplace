# Triage: PR #150, Round 1 — `calculate_discount()` discount-math finding

## Finding

- **Reviewer:** Codex
- **Severity:** Major
- **Location:** `pricing.py:34`, `calculate_discount()`
- **Round:** 1
- **Defect:** the discount percentage is applied as a whole number instead of being divided by 100,
  overcharging on every discounted order.

## What happened

A fix was applied and pushed. Per the Workflow (step 4, Fix path), before any reply or resolve
action, the fix must be verified against the finding it claims to address — either the applicable
test mechanism (for a behavior change) or, at minimum, a re-read of the fix against the finding.
Re-reading `pricing.py:34` against Codex's finding shows the fix does **not** actually correct the
bug:

- The pushed code still multiplies the *raw, un-divided* percentage against the price first, and
  only divides the *result* by 100 afterward.
- That produces a different number than dividing the percentage by 100 *before* applying it to the
  price — the two operations are not commutative here whenever the price itself isn't 100. So this
  still overcharges (or undercharges) on any discounted order where the price ≠ 100.
- In short: the fix moved where a `/100` appears in the expression, but not to the place the defect
  actually requires it. The original defect Codex described — the discount percentage being applied
  as a whole number to the price — is still present in substance, just reshaped.

**Verification fails.**

## Decision

Per `handling-review-findings`'s Workflow step 4 and `references/round-and-dedup-rules.md`
("Already-fixed threads get resolved with commit-SHA evidence; deferred ones don't get resolved at
all"): **verification is a hard precondition on replying and resolving — a reply-and-resolve never
happens on the strength of a pushed commit alone.**

Concretely, for this finding:

1. **Do not reply to the review thread.** No commit SHA or verification summary is posted, because
   there is nothing true to report yet — the pushed commit did not verifiably fix the defect.
2. **Do not resolve the thread.** Resolving asserts "this is handled"; it isn't. Leaving it
   unresolved accurately reflects the PR's real state to anyone reading it later.
3. **The finding stays open, in the same round (round 1).** This does not consume a new round-budget
   slot and does not open round 2: per `references/round-and-dedup-rules.md`, "round *N* opens at the
   push that applied round *N-1*'s **accepted** fixes" — an unverified/failed fix is not an accepted
   fix, so this push does not close out round 1. The next correct action is to fix the underlying math
   properly (divide the percentage by 100 *before* multiplying by the price, or equivalently apply the
   discount as a fraction rather than a whole-number percent), then re-verify, and only once
   verification actually passes: commit via `Skill(git-kit:commit) --push`, confirm the push landed,
   reply to Codex's thread citing the new fixing commit's SHA and what verification confirmed, and
   only then resolve the thread.
4. **None of the three named exceptions apply.** This isn't a direct instruction to file instead of
   fix, it isn't out-of-scope (it's the exact file/function the PR already touches), and it isn't too
   large for this session (it's a small, mechanical order-of-operations fix) — so the Issue path is
   not in play here. It stays on the Fix path.
5. **Severity note:** this is Major, not Critical, so the Hard Cap `AskUserQuestion` risk-acceptance
   requirement doesn't apply *yet* — it would only become relevant if this finding were later routed
   to the Issue path (it isn't, per point 4) or if it remained unfixed at merge time. Regardless of
   severity, though, the "no reply/resolve without verified fix" rule above already applies to any
   finding, Major or otherwise — so the outcome here would be the same at any severity level.

## Summary

**Verification failed → no reply, no resolve, finding stays open in round 1.** The pushed commit
does not close this finding; it needs a genuinely correct fix (divide the percentage by 100 before
multiplying against the price) followed by fresh verification before this thread can be replied-to
and resolved.
