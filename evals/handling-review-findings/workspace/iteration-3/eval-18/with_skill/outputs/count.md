# Triggered-cycle count for PR #200 (Workflow step 8)

## Answer

**Triggered-cycle count = 1.**

This equals `review_findings_min_rounds` (1) and is below `review_findings_max_rounds` (3).

## Reasoning

Per Workflow step 8 (SKILL.md) and `references/round-and-dedup-rules.md`'s "Triggered-cycle count vs.
round" section, the triggered-cycle count is **not** the fix-driven-push "round" counter used elsewhere
in the Workflow. It is derived, from freshly re-fetched PR state, as:

> 1 (round 1's automatic CI trigger) + the number of distinct trigger *batches* this skill has posted
> to this PR — never a raw count of matching comments.

Applying that formula to the described state:

1. **Base of 1, for round 1's automatic CI trigger.** Round 1 was triggered automatically by CI (on
   PR-ready or draft→ready) and has already been fully triaged. That automatic trigger always counts as
   1, unconditionally — it's the fixed starting term in the formula, not something derived from comment
   history.

2. **Plus the number of distinct `handling-review-findings`-owned trigger batches found in the current
   comment list.** A batch is identified *only* by the presence of this skill's own marker,
   `<!-- handling-review-findings-trigger:<batch-id> -->`, appended to the comment body — never by
   matching a reviewer's trigger string alone (`@codex review`, `@coderabbitai review`, `/devin review`).
   The count is the number of *distinct* `<batch-id>` values captured from that marker across the
   re-fetched comments, not a count of comments and not a count of trigger-string matches.

   The scenario states plainly that `handling-review-findings` "has not yet posted any trigger comment of
   its own on this PR." So there are zero comments carrying the `handling-review-findings-trigger` marker,
   and therefore zero distinct batch-ids attributable to this skill. This term contributes **0**.

3. **The `codex-review-recovery` comment is explicitly excluded and contributes nothing.** A separate,
   plain top-level `@codex review` comment was posted by `codex-review-recovery` as a stuck-check
   recovery action (Codex's review had finished on its dashboard but never wrote back to GitHub) — a
   fundamentally different action from this skill's own proactive round trigger, per the SKILL.md's own
   "When NOT to Use" section and the round-and-dedup-rules "Ownership ambiguity" discussion. That comment
   has "no trailing marker of any kind," so it fails the marker check on its face — it is never counted,
   "no matter how closely its body matches a configured trigger string." This is exactly the scenario the
   marker mechanism (added after a round-2 GitHub review on PR #101) was designed to guard against: a
   byte-identical `@codex review` string that is not this skill's own trigger must not inflate the count
   and must not be mistaken for a round this skill triggered.

Total: **1 (automatic round-1 trigger) + 0 (no marked batches from this skill) = 1.**

## Consequences for the rest of step 8

- **1 meets `review_findings_min_rounds` (1)**, so the floor is already satisfied — another cycle is not
  mandatory. Question 1 (reviewer selection) would therefore include the "No further round for now"
  option as its 4th choice, since the current count already meets `min_rounds`.
- **1 is below `review_findings_max_rounds` (3)**, so proactively triggering another round is still
  within budget if the user wants one — step 8 is not skipped outright the way it would be at
  `max_rounds`.
- Net effect: this run proceeds to the normal reviewer/mode `AskUserQuestion` (Question 1 with the stop
  option included, Question 2 on review profile), rather than being forced into "must pick a reviewer, no
  stop option" (which would apply below the floor) or skipping step 8 entirely (which would apply at the
  ceiling).

## Note on what was and wasn't done

This is a simulated exercise. No `gh`/API calls were made; no comments were posted; nothing was fetched.
The count above is computed purely from the state described in the prompt, exactly as Workflow step 8
instructs it to be derived from re-fetched comment-list state in a real run.
