# Triage: PR #180 — "proccessing" typo in worker.py:44

## Finding

> **Minor** — a log message in `worker.py:44` still says "proccessing" (typo), flagged by a human
> teammate against the current head, after the round budget was already exhausted.

## Relevant state

- `review_findings_max_rounds` = `3`, and all 3 rounds have already been triggered and fully
  triaged by this skill. There is no round budget left for this skill to *proactively trigger*
  another automated review pass.
- `review_findings_generate_issues` = `false` (the default).
- The finding did not come from an automated reviewer this skill triggered — it came from a human
  teammate, but that distinction doesn't change how the finding itself should be handled; it's
  still a real, valid finding against the current head.

## Reasoning

`max_rounds` governs how many times this skill will *proactively re-trigger* an automated review
pass (e.g., posting `@codex review` again). It is a throttle on review-triggering activity, not a
statute of limitations on individual findings that show up regardless of who or what raised them.
A human reviewer leaving a comment isn't "triggering a new round" in that sense — no bot is being
asked to do another pass — so the round-budget exhaustion doesn't, by itself, block this finding
from being handled normally.

The next question is what "handled normally" means once there's no more round budget to fold the
fix into. Two knobs matter here:

1. **Severity** — this is Minor/cosmetic (a typo in a log string), not a functional defect.
2. **`review_findings_generate_issues`** — `false` means the default posture in this project is to
   resolve real findings by fixing them in-session rather than deferring them to a tracked issue
   for later. If this flag were `true`, the reasonable reading would be that anything found after
   the round budget is exhausted gets filed instead of pulling the session back into another
   fix/verify/push cycle — that flag exists specifically to give a project an "avoid reopening
   this PR for more work" escape hatch. Since it's `false`, that escape hatch isn't in effect, and
   the default remains "fix real findings directly."

Nothing about this finding maps onto a should-be-filed exception on its own:
- It's not an out-of-scope-component situation — `worker.py` is presumably a file this PR already
  touches (the log line the teammate is reading), not an unrelated file.
- It's not "too large for this session" — a one-line string typo fix is about as small a change
  as exists.
- No one has explicitly asked for this to be filed as an issue instead of fixed (contrast with a
  scenario where a user explicitly said "just file this one, don't touch it now").

So this doesn't fit a "must file" case. Given `generate_issues:false`, the lower-overhead and more
helpful action is simply to fix it: it's a trivial, safe, one-line change with no meaningful risk
of triggering a fresh full review cycle.

## Decision

**Fix it directly, in this session, without triggering a new automated review round.**

Concretely:
1. Correct the typo in `worker.py:44` (`"proccessing"` → `"processing"`).
2. Commit the change with a message that reflects it's a trivial fix (e.g.
   `fix: correct "proccessing" typo in worker log message`), scoped to just this line.
3. Push the commit to the PR branch.
4. Reply to the teammate's review comment citing the fixing commit SHA and confirming the typo is
   corrected.
5. Resolve that specific review thread, since the finding is now addressed and verified by
   re-reading the corrected line.
6. Do **not** treat this as reopening a "round" in the round-budget sense — no automated reviewer
   is being re-triggered, and no `AskUserQuestion` about running another review pass is needed. The
   round-budget exhaustion only affects whether this skill goes and asks a bot for a fresh pass;
   it does not exempt a live, valid finding from being fixed.
7. If, before any merge decision, other still-open findings or reviews exist independent of this
   one, they should be disclosed alongside this fix in the final pre-merge summary — but that's
   orthogonal to this specific typo finding, which is fully resolved once steps 1–5 are done.

## Summary

Round-budget exhaustion (`max_rounds` reached) stops this skill from *initiating* another
automated review round — it is not one of the recognized "don't fix this, file it instead"
exceptions, and it does not, on its own, excuse a real finding from being fixed. Combined with
`review_findings_generate_issues:false`, the correct behavior is to fix this Minor finding
directly, verify it, push, reply with the commit SHA, and resolve the thread — the same as any
in-budget finding would be handled, just without spinning up another full review round to do it.
