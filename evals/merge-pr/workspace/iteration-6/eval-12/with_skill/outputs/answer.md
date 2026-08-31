# Scenario

At step 2 of `merge-pr`, all five required readiness checks have already passed:
not draft, status checks green, no outstanding change-request reviews, no merge
conflicts, not behind base.

The already-fetched PR data (from `gh pr view`, alongside `mergeable`) shows:

```
mergeStateStatus: BLOCKED
```

# Question

Does `mergeStateStatus: BLOCKED` block readiness or stop the flow? What do I do
with this value?

# Answer

**No — it does not block readiness and does not stop the flow.**

Per the skill's own instructions, `mergeStateStatus` is one of two **advisory
disclosures**, computed only once the five required checks above have already
passed. It is explicitly carved out from the readiness gate:

> "Never blocks readiness and never causes a stop on its own — if it should
> ever block, that's a signal to add a dedicated required check for the
> specific condition, not to gate on this summary value directly."

So even though the raw value is `BLOCKED` — which sounds alarming, and is
GitHub's own aggregate mergeability read — it does not override the fact that
this skill's five explicit checks (not-draft, status checks, no changes
requested, no conflicts, not behind base) are what actually gate proceeding.
Since all five passed, readiness is **not** re-litigated based on this value.

## What I actually do with it

1. **Do not stop the flow.** Proceed past step 2 to the merge-rights check
   (step 3) as normal, since readiness is satisfied.
2. **Carry the raw value forward, unmodified.** I don't interpret, soften, or
   explain away `BLOCKED` — I disclose exactly what GitHub returned.
3. **Surface it explicitly at step 5's confirmation.** When I use
   `AskUserQuestion` to confirm the merge, I must state both advisory
   disclosures plainly, including this one — a `BLOCKED` value doesn't get
   silently dropped just because it doesn't gate anything. (The instructions
   are explicit that even a boring `CLEAN` result must be surfaced, so a
   surprising `BLOCKED` result certainly must be too.)
4. **Also disclose the other advisory item**: the count of unresolved
   review-comment threads (even if zero).
5. **Frame it as informational, not a verdict.** The reasoning: this value is
   GitHub's own independent aggregate read of mergeability, which can disagree
   with this skill's own explicit checks (e.g. because of a branch-protection
   rule this skill doesn't independently model — such as required linear
   history, a required reviewer count beyond "no changes requested," or
   another repo-specific rule). Showing the user the raw `BLOCKED` value lets
   them catch a real problem that this skill's checks didn't independently
   catch, without the skill itself falsely gating on it (which would risk
   false negatives if `BLOCKED` reflects something already accounted for, or
   is transient/stale relative to the fresher check results).

## Example step-5 confirmation phrasing

> All required checks pass — this PR is ready to merge.
>
> Advisory (informational only, does not block):
> - GitHub's merge-state summary: **BLOCKED** (GitHub's own aggregate
>   mergeability read; disagrees with this skill's explicit checks — may
>   reflect a branch-protection rule not modeled here, e.g. required reviewer
>   count or required linear history. Worth a quick look before merging.)
> - Unresolved review-comment threads: 0
>
> Merge now?

## Key takeaway

`mergeStateStatus` is disclosure, not a gate. A `BLOCKED` value is surfaced
verbatim to the user at the confirmation step so they can make an informed
call, but it never causes the skill to stop, re-fail a already-passed check,
or refuse to proceed to the merge-rights check and confirmation.
