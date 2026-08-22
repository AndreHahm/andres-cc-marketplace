# Triage: PR #150 — Pre-push `security-reviewer` finding during round 2

## Question: does this open round 3, or does it stay within round 2?

**It stays within round 2.** This does not open, advance to, or consume any part of round 3.

### Reasoning

Per `references/round-and-dedup-rules.md`'s round definition, a round is the window between two
fix-driven pushes: round *N* opens at the push that applied round *N-1*'s accepted fixes, and stays
open until the *next fix-driven push* happens. Round 2 here opened when round 1's fix was pushed, and
is still open — round 2's own fix (addressing the round-1 finding) has been *written* but explicitly
**not yet pushed**.

A `security-reviewer` (or other self-invoked) verification pass run *before* pushing a round's fix —
specifically to confirm the fix itself doesn't introduce a new Critical/Major problem — is explicitly
called out as **not a new round**. It's part of finishing the round already in progress. That's exactly
the situation described: the pass ran on the not-yet-pushed round-2 diff, before that diff went out.

This holds regardless of the severity of what the pass finds. The rule doesn't carve out an exception
for "unless the pre-push pass finds something Critical" — the worked example in
`references/round-and-dedup-rules.md` shows this exact shape (a `security-reviewer` verification pass
on round 1's own fix turning up 1 Critical + 3 Major findings, all fixed within round 1, "not a new
one"). Finding a Critical issue during the pre-push check doesn't change *when* the round boundary
falls; the boundary is defined purely by fix-driven pushes, not by what severity of finding triggered
work within the round.

This is also consistent with `.claude/rules/require-security-review-before-new-gate.md`: that rule
mandates resolving Critical/Major findings from a security review before a new gate ships, and the
round-budget machinery doesn't suspend that mandate — it just doesn't treat resolving those findings as
its own separate round.

### None of the three named exceptions apply, and this isn't budget exhaustion either

- **Exception 1 (direct instruction):** nobody asked to file this instead of fixing it.
- **Exception 2 (out-of-scope component):** the vulnerability is in the file-loading helper that
  round 2's own fix touched — squarely in-scope, not an unrelated file/component.
- **Exception 3 (too large for this session):** nothing in the scenario suggests this needs
  cross-codebase tracing or an architectural change; it's a path-traversal fix in a helper this
  session is already editing. Default is to attempt the fix, not reach for this exception.
- **Budget exhaustion / `review_findings_generate_issues`:** irrelevant here — the round budget
  (whatever `max_rounds` is) isn't exhausted; this is round 2 of a run still well within budget, and
  the finding isn't arriving after the proactive triggering window closed. This setting only matters
  for a finding that shows up *after* the round budget is already exhausted, which is not the case here.

So none of the routing exceptions or the post-budget path are in play — this new Critical finding is
just more work to finish before round 2's push goes out.

## What to do about the new Critical finding

1. **Fix it now, within round 2, before pushing.** Address the path-traversal vulnerability in the
   file-loading helper as part of the same round-2 change set — do not defer it, do not file it as an
   issue, and do not treat it as consuming a slot in a hypothetical round 3.
2. **Verify the new fix** the same way any Fix-path change is verified — re-read the corrected code
   against the specific defect described (unsanitized/unvalidated path input reaching the file-loading
   helper) or run the applicable test mechanism if this changes tested behavior.
3. **Combine both fixes into round 2's push.** The pushed commit(s) address both the original
   round-1 finding (round 2's original purpose) and this newly discovered Critical path-traversal
   issue — both are round-2 work, landing on round 2's single fix-driven push.
4. **Only after that push lands and verification confirms both fixes are correct**, proceed with the
   normal Fix-path close-out: reply to the relevant thread(s) citing the fixing commit SHA and a
   one-line summary of what verification confirmed, then resolve. (The round-1 finding's own thread
   gets this treatment for round 2's fix as already planned; if the `security-reviewer` pass itself
   produced an external, PR-visible finding/thread — as opposed to being purely a self-invoked internal
   check — that thread gets the identical reply-with-SHA-then-resolve treatment once verified.)
5. **Do not advance any round counter.** After this push, the round-2 window closes and round 3's
   window opens (if a subsequent external reviewer's findings arrive against the new head) — but that
   is the ordinary round-2-to-round-3 transition on the next fix-driven push, not something caused by,
   or accelerated by, this pre-push security finding.

## Summary

| Question | Answer |
|---|---|
| Does this open round 3? | No |
| Which round does the fix land in? | Round 2 |
| Which exception applies? | None — this isn't an exception case, and it isn't the budget-exhaustion path either |
| Fix, file, or decline? | Fix — within round 2, before the round-2 push goes out |
| Effect on round counter | None — round counter only advances on fix-driven pushes, and this is folded into round 2's own (not-yet-made) push |
