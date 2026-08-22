# PR #170 — Next-Round Decision (Round 1 → Round 2)

## Situation

- Round 1 was triggered automatically by CI when the PR went ready-for-review.
- Round 1 produced exactly one finding, and it is now fully triaged (fixed, verified, replied, resolved).
- `review_findings_min_rounds = 1` → already satisfied by round 1. Nothing *requires* another round.
- `review_findings_max_rounds = 3` → two more rounds are still allowed, but not mandated.
- All three seed reviewers (Codex, CodeRabbit, Devin) are enabled with their default trigger strings.
- This is the first next-round decision point in this conversation — no prior answer to fall back on, so it must be asked rather than assumed.

Because the config only bounds the decision (min satisfied, max not reached) without forcing an outcome either way, this is a genuine judgment call that belongs to the user, not something to resolve silently. Proceeding to trigger round 2 on my own would be assuming the user wants more review cycles than the minimum; stopping on my own would be assuming they're satisfied — both are real decisions, not mechanical consequences of the settings.

## What I would ask

I would use a single `AskUserQuestion` call (not raw free-text) with one question, since the choice is a single fork in the road and fits well within the 4-option-per-question cap.

**Question header:** "Trigger round 2 of review?"

**Question text:**
"Round 1 is fully resolved (1 finding fixed and verified). The minimum required rounds (1) is already satisfied, and up to 2 more rounds are allowed (max 3). Do you want to request another review round now, and if so, from whom?"

**Options (exact option labels shown to the user):**

1. **"Yes — all 3 reviewers (Codex, CodeRabbit, Devin)"**
   Description shown under the option: Re-requests review from every enabled reviewer by posting one trigger comment per reviewer on PR #170.

2. **"Yes — pick specific reviewers"**
   Description: Continue to round 2, but first choose which of the 3 enabled reviewers to re-request (opens a follow-up question rather than assuming "all").

3. **"No — stop here, round 1 was enough"**
   Description: The minimum-rounds requirement is already met; close out the review-findings workflow for this PR without requesting further rounds.

4. **"Not yet — decide later"**
   Description: Leave the PR as-is for now; don't post any trigger comments or close the loop. Ask again next time this decision needs to be made.

I'm keeping "pick specific reviewers" as its own option rather than trying to cram a reviewer-multiselect into this same question, because `AskUserQuestion` options are single-select per question, and per this repo's own convention, a list of related-but-distinct decisions should be asked sequentially, not batched into one overloaded prompt. If the user picks option 2, the very next step is a second, separate `AskUserQuestion` listing Codex / CodeRabbit / Devin as up-to-4 individually toggleable options (or three yes/no questions, if the harness's multiselect support is uncertain) — asked only after this first question resolves, not in parallel with it.

## Literal trigger-comment text (assumption, stated explicitly)

I do not have access to this skill's actual settings file, so the reviewer trigger strings below are my own general, publicly-documented-convention assumption, not a verified value from `review_findings_reviewers`. If the real settings file defines different literal strings, those should be used instead — this is exactly the kind of tool/API-behavior assumption that should be verified against the real source before being relied on, and I'm flagging it rather than presenting it as confirmed:

- **Codex:** `@codex review`
- **CodeRabbit:** `@coderabbitai review`
- **Devin:** `@devin review`

If option 1 ("all 3 reviewers") is chosen, I would post three separate PR comments — one per reviewer, each containing only that reviewer's own trigger string — rather than one combined comment mentioning all three. Reviewer bots typically key off their own exact mention pattern; bundling three mentions into a single comment risks one or more bots not recognizing the trigger, and it also keeps each reviewer's subsequent findings comment easy to attribute to a specific trigger event in the PR timeline.

## What I would do after the user answers

- **Option 1 (all 3):** Immediately before posting, re-check the PR's actual current state (head SHA, whether it's still open and not already merged/closed, and that no other actor has posted a conflicting re-review request since round 1 closed) rather than trusting the round-1-complete status alone — that status could be stale by the time the trigger comments actually go out. Then post the three trigger comments, record that round 2 has been requested, and move into a wait/poll step for each reviewer's response. Once findings come back (or a reviewer reports no findings), resume the same triage loop used for round 1 — fix/verify/reply/resolve each finding — and only then re-ask this same next-round question, this time checking round count (2) against `review_findings_max_rounds` (3).

- **Option 2 (pick specific reviewers):** Ask the follow-up reviewer-selection question described above, then proceed exactly as option 1 but only for the reviewers selected — posting only their trigger comment(s).

- **Option 3 (stop here):** Do not post any trigger comments. Close out the review-findings workflow for this PR at round 1, noting explicitly that this was a user decision to stop early (min_rounds satisfied, max_rounds not reached, user declined further rounds) so a later reader of the PR history understands why no round 2 exists — not silently ending the loop with no record of why. Hand off to whatever the next stage is (e.g., merge-readiness check), rather than assuming the workflow is fully done end-to-end.

- **Option 4 (not yet):** Take no side-effecting action (no comments posted, no state closed out). Leave the decision open and re-ask the identical question the next time a next-round decision needs to be made for this PR, rather than silently defaulting to either "stop" or "continue" after a delay.

In all four branches, I would avoid inferring an answer from round 1's outcome alone (e.g., "only one small finding, so no one will want another round") — the fixed/verified finding count says nothing about whether the user wants the extra safety margin of another review pass before merge, so the decision stays with the user rather than being defaulted.
