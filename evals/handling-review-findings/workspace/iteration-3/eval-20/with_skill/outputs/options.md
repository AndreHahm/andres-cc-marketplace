# Workflow Step 8 — Question 1 Options for PR #210

## Situation recap

- `review_findings_min_rounds` = 2, `review_findings_max_rounds` = 3.
- Triggered-cycle count so far = 1 (round 1's automatic CI trigger only — no proactive trigger
  batch has been posted by this skill yet).
- 1 < 2, so the current triggered-cycle count is **below `min_rounds`**.
- All three seed reviewers (Codex, CodeRabbit, Devin) are enabled and their trigger strings pass
  Workflow step 8's three-step validation (tracked-ness gate, anchored content regex, handle-token
  match) — all three survive and are eligible to appear as options.

## What Question 1 would offer

Question 1 ("reviewer(s)") would be a **multi-select** with exactly **3 options**, one per
validated reviewer entry:

1. **Codex** — description names the reviewer plainly (not yet the exact trigger string; that
   depends on Question 2's default-vs-full answer).
2. **CodeRabbit** — same treatment.
3. **Devin** — same treatment.

**No "No further round for now" option is included.** That 4th option is only added when the
current triggered-cycle count already meets `review_findings_min_rounds`. Here the count is 1 and
the floor is 2, so the floor is not yet met, and per the skill's own wording another cycle is
"required — proceed without asking whether, only which." Offering a stop option here would let the
user defeat a floor the settings explicitly established, so it's omitted entirely rather than
included and discouraged.

## Why this shape

- **3 options, not 4**: one per reviewer that survived the name/trigger-string validation, with
  nothing appended, since there is no legitimate "stop" choice while the floor is unmet.
- **Multi-select**: the user can still choose any combination of the three reviewers for this
  mandatory next cycle — the mandatory part is only that *some* cycle happens, not which or how
  many reviewers are chosen.
- **Within the cap regardless**: `AskUserQuestion` caps options at 4 per question; 3 is comfortably
  under that, so no reviewer needs to be dropped or combined to fit.
- **Reviewer identity only, not yet the trigger text**: each option's description names the
  reviewer (Codex/CodeRabbit/Devin) rather than the literal `@codex`/`@coderabbitai`/`/devin`
  string, because the exact string to post is only resolved after Question 2 (default vs. full
  review profile) is answered.
- **Separately, Question 2** (not part of this question) would still ask, single-select, "Default
  review" vs. "Full review," applied uniformly to whichever reviewer(s) are picked in Question 1 —
  that keeps the per-reviewer mode choice out of Question 1 so the option count never has to double
  per reviewer.

I would not actually invoke `AskUserQuestion` in this simulated exercise — the above is a
description of exactly what that call's Question 1 would contain and why, per Workflow step 8's
documented rule for a triggered-cycle count below `min_rounds`.
