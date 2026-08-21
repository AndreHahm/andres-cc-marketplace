# Triage Decision: PR #150, Round 1 — Incomplete Fix to Discount Bug

## Finding Summary

**PR:** #150  
**Round:** 1  
**Severity:** Major  
**Location:** `pricing.py:34` in `calculate_discount()`  
**Original Issue:** Function applies discount percentage as a whole number instead of dividing by 100, causing overcharges on every discounted order.  
**Fix Status:** Attempted but failed verification.

## Verification Outcome

A fix was applied and pushed: the code now divides by 100. However, re-reading the fix against the finding revealed the fix is **incomplete and still wrong**:

- **Problem:** The fix divides by 100 in the wrong place
- **Current behavior:** Multiplies the raw (un-divided) percentage against the price first, then divides the result by 100
- **Correct behavior:** Should divide the percentage by 100 first, then multiply against the price
- **Verification result:** **FAILED** — the bug persists; the discount calculation is still incorrect

## Decision: Do Not Reply, Do Not Resolve

Per the skill's Workflow step 4 (Fix path, rounds 1-2):

> "Verification is a hard precondition on replying and resolving — a reply-and-resolve never happens on the strength of a pushed commit alone."
>
> "**If verification fails**, don't reply or resolve — the finding stays open in the same round."

**Action:**
- **Do NOT reply to the review thread** — no GitHub comment should be posted claiming the fix is complete
- **Do NOT resolve the thread** — leave it in unresolved state
- **Keep the finding open in Round 1** — verification failure means the fix was not accepted; the round remains active for this issue

## Reasoning

The skill defines verification failure as the grounds for withholding a reply-and-resolve action. Posting a reply and resolving the thread when verification shows the fix is incomplete would:

1. Misrepresent the PR's actual state to reviewers and future readers
2. Hide an unresolved defect behind a false "resolved" marker
3. Violate the hard precondition that verification must pass before claiming a fix is accepted

The thread being left unresolved correctly signals: "this finding is still open, the attempted fix did not work, further action is needed."

## Next Steps (Not Part of This Triage)

Once a proper fix is applied and verification confirms it works:
- Reply to the thread with the fixing commit's SHA and verification summary
- Resolve the thread only then
- Close Round 1 with this corrected fix

If a second fix attempt also fails verification, Round 1 remains open. Only once verification passes does this finding exit Round 1. If Round 2 begins (a new external review cycle against a new head SHA) and the same issue is found again, that becomes a separate finding in Round 2, subject to the dedup rule in `references/round-and-dedup-rules.md`.
