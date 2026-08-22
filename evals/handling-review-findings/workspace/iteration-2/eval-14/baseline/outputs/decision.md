# Next-Round Decision — PR #170, after Round 1

## Situation

- Round 1 was auto-triggered by CI when PR #170 went ready-for-review.
- Round 1's single finding is fully triaged: fixed, verified, replied to, and resolved.
- `review_findings_min_rounds` = 1 → already satisfied.
- `review_findings_max_rounds` = 3 → up to two more rounds (2 and 3) are still allowed.
- All three seed reviewers (Codex, CodeRabbit, Devin) are enabled, each with its default
  tracked trigger string.
- This is the first next-round decision point in this conversation — no prior answer exists
  to reuse, so the user must be asked now. Per the eval's framing, whatever the user answers
  here is meant to govern the decision for all remaining possible rounds (2 and 3), not just
  the immediate next one — I would not re-ask this same question again after round 2 unless
  something material changes (e.g. a new finding reopens the round, or a reviewer config
  changes).

## Why ask at all

The minimum round requirement is already met, so nothing *forces* another round. But the
config still permits up to 3 rounds, and the user may want either:
- to stop now since the bar (`min_rounds`) is cleared and the one finding is resolved, or
- to keep going and re-request review from all three reviewers, on the theory that a fresh
  pass after fixes sometimes surfaces new findings (either against the fix itself or elsewhere
  in the diff), up to the configured ceiling of 3 rounds.

This is exactly the kind of judgment call that isn't safe to make silently — it changes
whether more automated reviewer activity (and possibly more rounds of fixes) happens against
a PR the user may consider done. So I would surface it via `AskUserQuestion` rather than just
picking a default.

## What I would ask (AskUserQuestion — not actually called, per the prompt's instruction)

**Question text:**

> Round 1 on PR #170 is fully resolved and the minimum required rounds (1) is already
> satisfied. Up to 2 more rounds are still allowed (max is 3). How should I proceed for the
> rest of this review cycle?

**Header:** `Next round?`

**Options presented (single-select):**

1. **Label:** `Trigger round 2`
   **Description:** Re-request a fresh review from all three enabled reviewers now, and keep
   auto-triggering another round the same way after each one resolves, until either a round
   comes back clean, or round 3 (the max) completes — whichever happens first. I will not ask
   again at each round boundary; this answer applies for the rest of the cycle.
   **Literal text that would be posted to PR #170 to trigger round 2** (one PR comment per
   reviewer's default tracked trigger string):
   - `@codex review`
   - `@coderabbitai review`
   - `@devin review`

2. **Label:** `Stop at round 1`
   **Description:** Minimum rounds is already satisfied and the only finding from round 1 is
   resolved — end the review-findings cycle here. No further reviewer-trigger comments are
   posted, and rounds 2–3 are not used even though the config allows them.
   **Literal text posted:** none — no PR comment is made.

3. **Label:** `Ask again next time`
   **Description:** Trigger round 2 now the same way as option 1, but instead of auto-continuing
   through round 3, ask this same question again once round 2's findings are fully triaged. Use
   this if you want a checkpoint before every additional round rather than a standing decision
   for the rest of the cycle.
   **Literal text posted for round 2 (same as option 1):**
   - `@codex review`
   - `@coderabbitai review`
   - `@devin review`

(I'm keeping this to 3 options, each with a short label and a one-line description, matching
`AskUserQuestion`'s normal shape; only options 1 and 3 involve posting anything to the PR.)

## What I would do after the user answers

- **If "Trigger round 2":** Post the three trigger comments above to PR #170 in one round,
  wait for all three reviewers to respond, triage whatever findings come back (fix/verify/
  reply/resolve each, same as round 1), and then — without asking again — repeat the same
  trigger-and-triage cycle for round 3 only if round 2 comes back with findings that required
  changes and the round count hasn't yet hit the max (3). If round 2 comes back with nothing
  to fix (a clean pass) or round 3's cap is reached, stop and report the final state.
- **If "Stop at round 1":** Take no further reviewer action on PR #170. Report that the
  review-findings cycle is complete (min rounds satisfied, round 1's finding resolved, no
  further rounds requested), and move on to whatever the user's next instruction is (e.g.
  merging, or handing off to `create-pr`/`merge-pr` follow-up steps).
- **If "Ask again next time":** Post the same three trigger comments for round 2, triage its
  findings, and then re-present this same three-option question (updated to reflect "round 2
  resolved, 1 round remaining") before deciding whether round 3 happens.

## Assumptions made explicit

- The exact default trigger strings for Codex, CodeRabbit, and Devin are drawn from general,
  publicly documented conventions for these tools (`@codex review`, `@coderabbitai review`,
  `@devin review`) since this is a simulated exercise with no real PR/config to inspect — the
  project's actual `review_findings_reviewers` config could specify different literal strings.
- "Trigger" is modeled as one PR comment per reviewer rather than a single combined comment,
  since each reviewer bot listens for its own mention/trigger string independently.
