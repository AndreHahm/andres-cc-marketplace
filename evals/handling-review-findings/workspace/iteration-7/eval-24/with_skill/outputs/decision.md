# PR #502 — Workflow Step 8b Decision

## Scenario recap

- `review_findings_min_rounds` = 1, `review_findings_max_rounds` = 3.
- Rounds 1 and 2 have completed; 8a's triggered-cycle count = 2 (1 for round 1's automatic CI
  trigger, plus 1 distinct self-authored `<batch-id>` for round 2's manual trigger).
- 2 already meets/exceeds `min_rounds` (1), and is still below `max_rounds` (3) — so per 8a, this
  is the "ask whether to run another cycle at all" zone, not the "must ask which" zone (that only
  applies below the floor) and not the "skip step 8 entirely" zone (that only applies at
  `max_rounds`).
- At step 8c, all three reviewer entries (Codex, CodeRabbit, Devin) survive validation — this is
  the normal ≥2-survivors case, not the "fewer than 2 reviewers survive" edge case in 8b.

## What Question 1 offers

Question 1 is a multi-select with one option per reviewer entry that survived 8c, **plus** an
explicit "No further round for now" option:

1. Codex
2. CodeRabbit
3. Devin
4. No further round for now

That's 4 options total — at `AskUserQuestion`'s own per-question cap (`maxItems: 4`), so no
narrowing is needed here.

The "No further round for now" option is included specifically **because** the triggered-cycle
count (2) already meets `min_rounds` (1) — per 8b's own rule, that option is only offered once the
floor is met; below the floor it would be omitted entirely (except the separate one-survivor
exception, which doesn't apply here since 3 reviewers survived). Each reviewer option names the
reviewer plainly, not yet the exact trigger text — the exact trigger string depends on Question 2
(review profile: "Default review" / "Full review", single-select, asked as its own question so
Question 1 doesn't have to also enumerate both modes per reviewer).

## What happens if the user selects "No further round for now"

Because the triggered-cycle count already meets `min_rounds`, this option was offered under the
normal (not one-survivor-below-floor) rule, so selecting it — alone or in combination with any
reviewer option — is **authoritative**:

- Question 2 (review profile) is still asked as part of the same single `AskUserQuestion` call (per
  8b's opening line, both questions are submitted together in one call) — but its answer is ignored
  once "No further round for now" wins, since there's no reviewer left to apply a profile to.
- Nothing is posted — no trigger comment, no marker write, no batch-id generated.
- Per 8a: "on 'no,' stop here — this run ends with step 7's report as the final word." The skill's
  run for this invocation ends at that point; step 7's fixed/filed/declined report is the final
  output of this triage pass.
- No further round is triggered. A future finding (if any reviewer posts one later without this
  skill having triggered it) would be triaged the next time this skill is invoked, but this run
  itself does not loop back to ask again or trigger anything automatically.

This is distinct from the below-`min_rounds`, exactly-one-surviving-reviewer exception (8b's
"Fewer than 2 reviewers survive 8c" bullet), where selecting "No further round for now" does *not*
end the run silently — instead it reports that the floor requires another cycle and asks the user
to confirm triggering the one remaining reviewer or fix the reviewer configuration. That exception
does not apply here: 3 reviewers survived (≥2), and the count already meets the floor, so the
plain authoritative-stop behavior above is what applies.
