# Triage: PR #150, Round 1 — Bypassable Input Sanitization

## Inputs

- PR #150, review round 1 of a max of 3 (`review_findings_max_rounds: 3`) — plenty of budget left, so round-limit pressure is not a factor in this decision.
- Two independent reviewers — Codex and CodeRabbit — each raised a **Major** finding against `validate.py`.
- No GitHub issue currently exists for this PR.

## Step 1: Are these the same finding, or two findings?

Comparing the two comments:

- **Codex**: "the entire input-sanitization layer is bypassable because three different call sites each reimplement their own partial sanitization instead of routing through `sanitize_input()`; fixing this properly requires tracing every call site across the codebase and consolidating them, not a local edit."
- **CodeRabbit**: "inconsistent sanitization across `validate.py` callers — a real architectural gap needing a data-flow audit across the codebase, not a text-only patch."

Both reviewers are describing the *same root cause* (multiple call sites bypassing the shared `sanitize_input()` helper by reimplementing partial sanitization) and reach the *same conclusion* (this is not a local/textual fix — it requires a codebase-wide trace/audit and consolidation). Different wording, same defect, same severity, same scope assessment. This is a **duplicate finding from two independent sources**, not two separate defects. Treating it as two separate issues would double-count the same problem and create two overlapping/duplicate tracking tickets that would need to be reconciled later anyway.

**Decision: one underlying finding, sourced from two reviewers.** Two independent reviewers agreeing on the same root cause is a *confidence signal* (it corroborates that the defect is real, not a single reviewer's false positive) — it is not a reason to file twice.

## Step 2: Which exception applies?

Normal handling for a valid Major finding in round 1 (well within the round budget) would be: fix it now, in this PR, and reply to the thread once fixed.

That default doesn't fit here, because **both reviewers explicitly scope the fix as larger than this PR/session can reasonably absorb**:
- Codex: "requires tracing every call site across the codebase and consolidating them, not a local edit."
- CodeRabbit: "needing a data-flow audit across the codebase, not a text-only patch."

This is a legitimate, real, high-severity defect — but it is not fixable as a contained, local diff within the current PR/session. That combination (real + Major + explicitly too large in scope for an in-session fix) is exactly the shape of a **"too large for this session/PR" exception**, as distinct from:
- **False positive / won't-fix** (not applicable — both reviewers independently corroborate a real architectural gap; there's no basis to dispute it), or
- **Fix now** (not applicable — fixing it "properly" per both reviewers means an unbounded codebase-wide audit and refactor, not a change that belongs bundled into whatever PR #150 is actually about).

Being only in round 1 of 3 doesn't change this: the constraint here isn't "we've run out of review rounds," it's "this fix's scope doesn't belong in this PR at all," regardless of how many rounds remain. Expanding PR #150 to also do a full sanitization-architecture consolidation would blow its scope and mix an unrelated refactor into whatever the PR was originally for.

**Decision: apply the too-large-for-session exception.** Defer the actual fix to tracked follow-up work rather than attempting it inside PR #150.

## Step 3: How many GitHub issues get filed?

**One.** Since Step 1 established this is a single underlying defect independently corroborated by two reviewers, exactly one GitHub issue should be filed for it — not one per reviewer. A single issue that:
- Describes the root cause (call sites in `validate.py` bypass `sanitize_input()` by reimplementing partial sanitization).
- States the required remediation scope (trace all call sites, consolidate onto the shared sanitizer, likely needs a data-flow audit).
- Cites **both** reviewers as sources, since both independently corroborated the same defect — this is useful evidence for whoever picks up the issue, and avoids losing the fact that two tools agreed.
- Links back to PR #150 and both review threads for traceability.

Filing two issues for the same root cause would fragment tracking, risk divergent/duplicate fixes, and hide the corroboration signal that made this finding high-confidence in the first place.

## Step 4: What happens to each reviewer's own thread?

Each reviewer's thread is handled individually (they are separate threads on separate comments, even though they describe the same defect), but both resolve the same way:

1. **Reply on the Codex thread**: acknowledge the finding as valid and Major, state that it's out of scope for a local fix in this PR, and link the newly filed tracking issue. Note that it's the same underlying defect CodeRabbit also flagged, and that the issue captures both.
2. **Reply on the CodeRabbit thread**: same acknowledgment, same issue link, noting it's the same defect Codex flagged and that a single tracking issue was filed to avoid duplicating the two.
3. **Resolve/close both threads** in the review tool once the reply is posted — not because the underlying defect is fixed, but because each thread's expected action (triage decision + follow-up path) is complete. Resolution here means "acknowledged and tracked," not "fixed." Nothing is silently dismissed: each reviewer gets an explicit reply naming the decision and the issue number.

## Summary

| Item | Decision |
|---|---|
| Same defect or two? | Same underlying defect, corroborated by two reviewers |
| Exception applied | Too-large-for-session — real Major finding, but fix scope (codebase-wide call-site trace + consolidation) exceeds what belongs in PR #150 |
| Issues filed | 1 (not 2) — cites both reviewers as sources |
| Codex thread | Replied (ack + issue link + note re: duplicate), then resolved |
| CodeRabbit thread | Replied (ack + issue link + note re: duplicate), then resolved |
| Fixed in this PR? | No — deferred to the filed issue as follow-up work |
