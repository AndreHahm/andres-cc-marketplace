# Triage: PR #142, Round 2 Finding at handler.py:120

## Findings under comparison

**Round 1 (already resolved, commit `abc123f`):**
> Major — authorization check missing in `handler.py:120` — the endpoint doesn't verify the
> caller owns the resource before deleting it.

**Round 2 (just posted):**
> Minor — no test coverage for the error path in `handler.py:120` when the resource doesn't
> exist.

## Is this a repeat of the round-1 finding, or genuinely new?

Same file, same line number, so the surface-level signal (location) looks like a duplicate.
But triage has to go on the substance of the finding, not the coordinates, and on substance
these are two different claims:

1. **What they're each about.** Round 1 is a *security/authorization* defect: the delete
   handler performs the deletion without checking that the caller owns the resource. Round 2
   is a *test-coverage* gap: there's no test exercising what happens when the resource being
   deleted doesn't exist at all (a not-found / 404-style path). "Missing an owner check" and
   "missing a test for the not-found branch" are not the same claim, and fixing one does not
   imply the other was addressed — a correct ownership check and a correct not-found path are
   independent pieces of behavior.

2. **Why they'd land on the same line.** The round-1 fix (commit `abc123f`) necessarily added
   new logic to `handler.py:120` to perform the ownership check — which, in essentially every
   realistic implementation, first requires *fetching the resource* before comparing its owner
   against the caller. That fetch step is exactly where a "resource doesn't exist" branch
   naturally gets introduced (e.g. `get_or_404`, a `None` check before the ownership
   comparison, etc.). In other words, the round-1 fix plausibly introduced the very code path
   round-2 is now flagging as untested. The shared line number is best explained as "the fix
   landed here and reshaped this line," not "the reviewer is re-raising the old issue."

3. **Severity and category also diverge.** Round 1 was Major (a real authorization bypass —
   correctness/security). Round 2 is Minor (a coverage gap — process/quality, not a live bug
   by itself). A reviewer re-flagging an already-resolved Major would ordinarily either repeat
   the Major severity or explicitly say the fix is incomplete/regressed. Nothing in the round-2
   text claims the authorization check is missing, wrong, or reverted — it only claims the
   not-found branch lacks a test. That's consistent with an independent, narrower observation
   made *after* reviewing the round-1 fix, not a re-assertion of the round-1 defect.

**Conclusion: this is a genuinely new finding, not a repeat.** It should not be closed as a
duplicate of the resolved round-1 thread. The same-line coincidence is circumstantial and, if
anything, corroborates that round-2 is reacting to code the round-1 fix introduced, rather than
recycling round-1's own complaint.

(Caveat/assumption stated explicitly: this reasoning assumes the round-1 fix actually is what's
currently sitting at `handler.py:120`, i.e. round-2 was raised against the post-fix code, not
against some pre-fix snapshot. That's the natural reading of "round 2, just posted" arriving
after a "round 1, already resolved" — but it's worth a one-line confirmation against the diff
being reviewed in round 2 before treating this as fully settled.)

## Decision: Fix

Recommend fixing now rather than filing for later or declining, for three reasons:

- **Cheap.** Adding one test case (call delete on a nonexistent resource ID, assert the
  expected error/status) is small, self-contained, and doesn't require design discussion —
  exactly the kind of Minor finding that's more expensive to track than to just fix.
- **High leverage given what it's testing.** This isn't test coverage for an arbitrary line —
  it's coverage for a branch that sits directly next to a just-fixed authorization
  vulnerability. Locking in the not-found behavior with a test reduces the chance that a future
  edit to this same authorization logic silently breaks the not-found path (or reintroduces an
  information-leak / error-handling regression) without anyone noticing.
- **Same file, same review pass.** The handler is already open and already the subject of
  active review attention in this PR; deferring a one-test fix to a separate follow-up adds
  process overhead (a new issue, a future PR, a future review cycle) disproportionate to the
  size of the gap.

**Action:** add a test exercising `handler.py`'s delete endpoint when the target resource does
not exist, asserting the correct error path (e.g. 404, not a 403/500/silent success), then
reply on the round-2 thread noting the test was added and citing the new commit, and resolve
the thread. Do not fold this into or reference the round-1 thread — it's a distinct finding
with its own resolution, even though it happens to sit on the same line.
