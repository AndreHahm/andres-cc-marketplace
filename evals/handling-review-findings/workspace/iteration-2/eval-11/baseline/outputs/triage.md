# Triage: PR #150, Round 2 — Pre-Push Security-Reviewer Finding

## Question

Round 2's fix (addressing a round-1 finding) has been written but **not yet pushed**. Before pushing,
a self-invoked `security-reviewer` pass on that not-yet-pushed diff finds a brand-new **Critical**
issue: the round-2 fix itself introduces a path-traversal vulnerability in a file-loading helper it
touched.

Does finding and fixing this new Critical issue open round 3, or does it stay within round 2?

## Reasoning

A "round" in this kind of PR-review workflow is defined by the push/review cycle, not by how many
times something gets checked. The natural boundary between one round and the next is: a fix gets
pushed, updating the PR's head SHA, and a reviewer then reviews that new head. Nothing has crossed
that boundary yet here:

- The round-2 fix has been **written but not pushed**. The head SHA has not changed.
- The `security-reviewer` pass was **self-invoked** by the person/agent doing the fix, as a
  verification step on their own not-yet-pushed diff — it is not an external reviewer (Codex,
  CodeRabbit, a human, etc.) reviewing a PR state that's actually live on GitHub. There is no new
  review event against a new head SHA; there is only an internal check on a draft the author hasn't
  shipped yet.
- Nothing has been posted to the PR, and no new external review comment or thread exists. A round
  is triggered by an external review pass against a pushed head, not by an internal QA step the
  author runs on their own pending diff.

Because no push and no external review-against-a-new-head has happened, there is no event that could
open "round 3." This is still round 2 in progress — the security-reviewer check is simply part of
*finishing* round 2's own fix correctly before it goes out the door, the same way you'd re-read a diff
or run tests locally before pushing. Finding a bug in your own not-yet-pushed work during your own
pre-push verification does not consume review-round budget; it's just quality control on the round-2
work product itself.

This also is not any kind of exception case (e.g., "out of scope for this PR," "needs a separate
issue," "too large for this session," or a budget-exhaustion scenario) — there's no round-budget
question here at all, because no round has been triggered or consumed by this event. Those
mechanisms only matter once a finding has actually been posted against a live, pushed head by an
external reviewer and needs to be routed somewhere. This finding never reaches that stage as a
"posted" item — it's caught and fixed before it's ever exposed to a reviewer.

## What I'd do about the new Critical finding

1. **Do not push yet.** Pushing a diff that is now known to contain a Critical path-traversal
   vulnerability would be actively harmful — it would ship a new, more severe defect than the one
   round 2 was trying to fix.
2. **Fix the path-traversal issue in the same, still-unpushed diff**, before any push happens. This
   keeps round 2 a single, coherent unit of work: it now fixes both the original round-1 finding and
   the newly discovered Critical defect, in one push.
3. **Re-verify** the corrected file-loading helper — ideally with another quick self-check (e.g.,
   confirm the path is properly sanitized/canonicalized and constrained to the intended directory,
   and that the original round-1 finding is still resolved) before pushing.
4. **Push once**, with both fixes included. This becomes the single commit/push that round 2's
   external reviewer(s) will evaluate. Since the vulnerability never reached a reviewer or a live PR
   state, there is nothing to reply to or resolve on GitHub for it — it was never posted as a finding
   in the first place, so it doesn't need its own thread, issue, or disclosure entry as a "handled
   review finding." (It's still worth mentioning in any human-facing summary of what changed in this
   push, purely for transparency, but that's a changelog/commit-message concern, not a review-thread
   triage concern.)
5. **Round 3 is not opened by this.** Round 3 would only begin if/when this pushed, corrected diff is
   reviewed again by an external reviewer and that reviewer raises something new. Until a push and an
   external review against the new head actually happen, the round counter stays at 2.

## Bottom line

This stays within round 2. A pre-push self-verification catching a new Critical issue in
not-yet-shipped work is quality control on the round's own output, not a new review round — round
boundaries are defined by push + external review against a new head SHA, and neither has occurred
here. Fix the vulnerability now, re-verify, and push once with both fixes combined; round 3 only
becomes relevant after that push is reviewed.
