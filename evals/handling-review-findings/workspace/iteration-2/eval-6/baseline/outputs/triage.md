# Triage Decision — PR #150, Round 1

## Finding

**Severity:** Major
**Location:** `pricing.py:34`, `calculate_discount()`
**Original issue:** the discount percentage was applied as a whole number instead of being
divided by 100, overcharging on every discounted order.

## What happened

A commit was pushed claiming to fix this: `pricing.py:34` now divides by 100 "before applying
the discount." Re-reading the actual diff against the original finding shows the division was
placed in the wrong spot — the code still multiplies the *raw, un-divided* percentage against
the price first, and only divides that intermediate result by 100 afterward. For any price that
isn't exactly 100, this produces a different number than the correct discount calculation, and
that number is still wrong. In other words: a commit exists, and it *touches* the right line,
but it does not actually resolve the reported behavior. The bug, as described in the finding, is
still present.

## Decision

**The finding is NOT resolved. It stays open, in the Fix path, in Round 1.**

Reasoning:

1. **Verification is a hard precondition, and it failed here.** The existence of a pushed
   commit is not evidence of a fix — the only thing that counts is whether the resulting code,
   read line-by-line against the finding's actual claim, now does the right thing. Here it does
   not: re-reading the diff turned up a second, distinct arithmetic error (wrong order of
   operations / wrong term being divided) that produces incorrect output for any non-100 price.
   Because verification failed, none of the "finding is done" actions are available yet — no
   reply claiming a fix, no resolving the thread.

2. **This does not count as a second review round.** A "round" is driven by an external
   reviewer (Codex) actually re-reviewing the PR and responding — not by an internal
   catch-it-before-you-post verification step. No reply was posted, so Codex has not seen or
   re-evaluated anything yet. This stays inside Round 1's fix effort: the first attempt just
   happened to be insufficient, and the correct response is to fix it properly before ever
   surfacing it to the reviewer, not to burn a round on a fix that was never actually verified.

3. **Severity and scope still point to Fix, not Filed or Declined.** This is a Major,
   in-scope, single-function correctness bug with a clear, small remediation — none of the
   normal reasons to divert it away from being fixed now apply:
   - Not a direct instruction to skip it.
   - Not an out-of-scope component.
   - Not "too large for this session" — it's a one-line arithmetic fix.
   - The round budget (default 1–3) hasn't been exhausted; this is still round 1.

   A Major finding does not get filed as a follow-up issue or declined just because the first
   attempt at fixing it was wrong — it gets fixed correctly.

## What happens to the review thread

- **Do not reply to the thread yet.** Replying now (e.g. "fixed in commit X") would be false —
  the fix is not actually correct, and posting an unverified "done" claim to a reviewer thread
  is exactly the failure mode to avoid.
- **Do not resolve the thread.** Resolution requires a verified fix. Nothing here has been
  verified as correct.
- **Next action:** apply a corrected fix to `calculate_discount()` — the discount amount must be
  computed as `price * (percentage / 100)` (divide the percentage by 100 before multiplying,
  or equivalently ensure the division and multiplication are algebraically applied to the
  percentage itself, not tacked onto the final result in a way that only happens to work when
  the price is 100). Commit that fix (via the project's normal commit flow, not a raw ad hoc
  commit), then **re-verify by re-reading the new diff against the original finding text**
  before doing anything else.
- **Only after that second verification passes:** post a single reply to the thread that (a)
  restates the original bug, (b) explains what was wrong with the first attempted fix and why,
  (c) describes the corrected fix and cites the new commit, and (d) marks the thread resolved —
  or leaves resolution to Codex's own re-review if that's how this repo's workflow is set up.
- **If a second verification also fails:** do not keep silently iterating without limit — at
  that point treat it as a legitimate use of the round/attempt budget and consider surfacing the
  repeated failure to the user rather than continuing to self-fix indefinitely.

## Summary

| Question | Answer |
|---|---|
| Round | 1 (unchanged — no external re-review has occurred) |
| Disposition | Fix path (not Filed, not Declined) |
| Is the finding resolved? | No |
| Reply posted to thread? | No — not until a verified fix exists |
| Thread resolved? | No |
| Next step | Apply a corrected fix, re-verify, then reply/resolve |
