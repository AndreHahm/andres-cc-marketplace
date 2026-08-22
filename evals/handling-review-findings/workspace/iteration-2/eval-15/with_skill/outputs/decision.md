# Decision: Round 3 Trigger for PR #170

## Facts as given

- Round 1 was triaged; at that point the user was asked (via `AskUserQuestion`, Workflow step 8) which
  reviewer(s)/mode to use for the rounds still to come, and chose **"Codex, full review" for all
  remaining rounds**.
- Round 2 was triggered by posting the validated trigger string `@codex full review`.
- Round 2's findings are now fully triaged (fixed/filed/declined, per steps 2-7).
- `review_findings_max_rounds` is `3` (and, per the skill's stated default, `review_findings_min_rounds`
  is `1`, unchanged here).
- Two rounds have completed so far (round 1, round 2); a potential round 3 would still be at or below
  `max_rounds` (3 ≤ 3), so it is not past the budget.

## Reasoning

1. **Round 3 is within budget.** `review_findings_max_rounds: 3` means this skill may proactively
   trigger rounds 1 through 3. Two rounds are already done, so triggering round 3 does not exceed the
   ceiling — Workflow step 8's "skip this step entirely" branch only applies once `max_rounds` is
   already reached (i.e., after round 3 itself is triaged, not before it starts). Round 3 is also above
   `min_rounds` (1), so it isn't in the "another round is required, proceed without asking" floor case
   either — ordinarily this middle zone (`min_rounds` ≤ completed rounds < `max_rounds`) is where step 8
   says to "ask via `AskUserQuestion` whether to run another round at all."

2. **But the reviewer/mode (and implicitly the "whether to continue") decision is already fixed for this
   conversation.** SKILL.md's Workflow step 8 states: *"The reviewer/mode choice, and the exact
   validated string behind it, are fixed once per conversation, not re-derived once per round... If this
   conversation hasn't already asked which reviewer(s) and mode to use for the rounds still to come, ask
   now... Remember both the choice and the exact string shown for it, and reuse that same string for
   every later round this run goes on to trigger."* The user's round-1 answer was explicitly "for all
   remaining rounds" — this conversation has already asked and already has an answer covering round 3.

3. **This is a named testing scenario, decided explicitly in the skill's own reference material.**
   `references/testing-scenarios.md` lists: *"Round 2's trigger-ask already happened earlier in the
   conversation; round 2 is now triaged and the budget allows round 3 — the skill reuses the earlier
   answer and posts round 3's trigger comment without asking again."* This is exactly the situation
   here — round 2's trigger-ask already happened, round 2 is now fully triaged, and the budget (3)
   still allows round 3.

4. **Conclusion: do not fire `AskUserQuestion` again.** Proceed directly to triggering round 3 by
   reusing the earlier, already-validated trigger string `@codex full review` (Codex's
   `full_review_trigger`, previously confirmed and shown to the user in round 1's ask). Per the
   Boundaries section, this skill "never asks the reviewer/mode question more than once per
   conversation — Workflow step 8 reuses the first answer for every later round," which applies
   directly here.

## What happens next (mechanically, in a non-simulated run)

Since this is a simulated exercise, no `gh`/API calls or `AskUserQuestion` calls are actually made. In a
real run, the skill would:

1. Re-validate that the remembered trigger string is still the one to use (no re-validation from
   settings is needed mid-conversation unless a *new*, not-yet-validated reviewer/mode is being
   introduced — it isn't here).
2. Write the fresh `gh-pr-review` marker
   (`"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review handling-review-findings`)
   immediately before the posting call.
3. Write `@codex full review` to its own scratchpad file (e.g. `trigger-codex.txt`) and post it with
   `gh pr comment 170 -R "<owner>/<repo>" --body-file "<scratchpad-path>/trigger-codex.txt"` — never
   inlined directly into the command line.
4. End this skill's run for this round without polling for Codex's round-3 response — re-invoking this
   skill once that review actually posts is how round 3's findings get triaged next.

## Note on round 3 being the last budgeted round

Because `max_rounds` is `3`, round 3 is the **last** round this skill will proactively trigger. Once
round 3 itself is triaged, Workflow step 8 will be skipped entirely on any subsequent invocation for
this PR — a further finding that shows up after round 3 would then be handled per
`review_findings_generate_issues` (fixed anyway if `false`/default, filed as an issue if `true`), not by
triggering a round 4.
