# Review Thread Triage: PR #150, Round 1

## Finding Summary
- **Component**: `pricing.py:34` — `calculate_discount()` function
- **Severity**: Major
- **Original Issue**: Discount percentage applied as whole number instead of divided by 100
- **Impact**: Overcharges on every discounted order

## Fix Verification Result
**FAILED** — The fix does not resolve the issue.

### What Was Attempted
The fix divides by 100, but in the wrong order of operations:
- Current (broken) logic: `result = (price * percentage) / 100`
- This still produces incorrect amounts when `percentage ≠ 100`

### Why the Fix Is Still Wrong
Order-of-operations error:
- For `price=50, percentage=10`: current fix yields `(50 * 10) / 100 = 500 / 100 = 5` ✓ (correct by accident)
- For `price=75, percentage=10`: current fix yields `(75 * 10) / 100 = 750 / 100 = 7.5` ✗ (should be 7.5 applied to 75, not the raw product divided)

**Correct logic** should be: `discount_amount = price * (percentage / 100)`

The current implementation multiplies the raw percentage against the price first, then divides the *result*, which treats the percentage as a fixed multiplier rather than a proportion of 100. This produces mathematically different values than the intended behavior across the full range of prices and discounts.

## Decision

**Thread Status**: KEEP OPEN (Not Resolved)

### Action Required
1. **Post a comment** on the review thread:
   - Acknowledge the fix attempt
   - Clearly state that verification revealed the issue remains unresolved
   - Explain the order-of-operations bug concisely
   - Specify the correct calculation: `discount_amount = price * (percentage / 100)`
   - Request the author rework the fix

2. **Do not close or resolve the thread** — keep it as an active, unaddressed Major finding

3. **Expect a follow-up commit** — the author must re-attempt the fix and push a new commit for re-verification

### Why This Decision

Per the project's `recheck-state-before-side-effecting-action.md` rule: a side-effecting action (resolving a review thread, considering a Major bug "fixed") requires re-checking the state immediately before that action. The re-check revealed the fix is incomplete — the state has not actually changed from "Major bug present" to "Major bug resolved."

Closing the thread or marking it resolved after an incomplete fix would be:
- **Inaccurate** — it misrepresents the actual state of the codebase
- **Unsafe** — it signals the defect is handled when it is not
- **Wasteful** — it creates a false closure that wastes round-trips when the real fix is finally needed

Keeping the thread open with clear feedback is the correct path to actual resolution.
