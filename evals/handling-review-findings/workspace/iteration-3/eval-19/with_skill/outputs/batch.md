# PR #200 — Round-2 Trigger Posting (Workflow Step 8)

## What gets posted

**Two separate `gh pr comment` calls** — one per reviewer selected in Question 1 (Codex, Devin), never one combined comment. Posting one comment per selected reviewer is deliberate (per `references/github-api-mechanics.md`'s "Posting a review-trigger comment"): combining multiple reviewers' trigger strings into a single comment risks one reviewer's connector misparsing text meant for another.

Before any posting, the three preconditions are freshly re-verified (never reused from the earlier `AskUserQuestion` answer or an earlier check in this same step): `gh pr view 200 -R "<owner>/<repo>" --json state,isDraft,headRefOid`, confirming `state == OPEN`, `isDraft == false`, and `headRefOid` equals this checkout's current `git rev-parse HEAD`. Only once all three pass does anything get posted.

One `<batch-id>` is generated **once for this decision** (`date -u +%Y%m%dT%H%M%SZ`) and reused verbatim across both comments — never regenerated per reviewer.

For each of the two reviewers, immediately before its post:
1. A fresh `write-git-kit-marker.sh gh-pr-review handling-review-findings` marker is written (single-use, consumed by the very next shell call — so this happens twice, once per `gh pr comment` call, never once shared).
2. That reviewer's own validated trigger string is written to its own scratchpad file (`trigger-codex.txt`, `trigger-devin.txt` — never a shared filename), with this exact shape:
   ```
   <reviewer's validated default_review_trigger string>

   <!-- handling-review-findings-trigger:<batch-id> -->
   ```
   Since Question 2's answer was "Default review", each reviewer's posted string is its `default_review_trigger` (e.g. Codex's configured `@codex review`, Devin's configured `/devin review` — the exact literal values from `review_findings_reviewers`, already validated through Workflow step 8's three-step check: tracked-ness gate, anchored-regex content check, handle-token match). Devin's default and full triggers are identical strings per the skill's own note, but "Default" is what Question 2 resolved to regardless.
3. Posted via `gh pr comment 200 -R "<owner>/<repo>" --body-file "<scratchpad>/trigger-<name>.txt"` — never inlined into the command line, even though the string already passed validation.

So: **2 `gh pr comment` calls total**, each body = one reviewer's validated default-review trigger string + a blank line + the same `<!-- handling-review-findings-trigger:<batch-id> -->` marker (identical batch-id in both). The skill's run ends here for this round — it does not poll for the review to post back.

## Effect on the triggered-cycle count for the round-3 decision

The triggered-cycle count is never a raw comment count — it's derived at Workflow step 8 as **1 (round 1's automatic CI trigger) plus the number of distinct `<batch-id>` values** found in the marker across the freshly re-fetched comment list at the time of the count.

Because both of this round-2 decision's comments share the *same* batch-id, they count as **exactly one** triggered cycle, not two. So immediately after this posting:

- Triggered-cycle count = 1 (round 1) + 1 (this batch) = **2**.

When the round-3 decision point is later reached, step 8 re-fetches the comment list and recomputes this count fresh (never reusing the value computed here) — it will again find 2 distinct batch-ids (round 1's implicit trigger has no batch-id/marker of its own — it's the fixed "+1" — plus this one batch), landing on 2. Since 2 < `review_findings_max_rounds` (3), another round is still permitted: `max_rounds` isn't reached yet, so step 8 doesn't skip entirely.

Because the reviewer(s)/mode choice was already asked and answered once this conversation, it is **not re-asked** at round 3 — the same decision (Codex + Devin, Default profile) is reused verbatim, with each reviewer's trigger string resolved from the same already-validated settings values (no re-validation from scratch, since Workflow step 8 explicitly says not to re-derive an already-confirmed choice).

If round 3 is triggered, it is treated as a **new decision/posting event** for batch-id purposes: a fresh `<batch-id>` is generated for round 3's post (not the same one reused from round 2), the three posting preconditions (open/non-draft/headRefOid-matches-HEAD) are re-verified fresh again, and a fresh `gh-pr-review` marker is written immediately before each of that round's `gh pr comment` calls. Once round 3's batch posts, the triggered-cycle count becomes 1 + 2 = **3**, which equals `max_rounds` — this makes round 3 the last round this skill proactively triggers. Any further finding that shows up afterward is no longer handled via a new Workflow step 8 trigger; it's routed per `review_findings_generate_issues` (Fix if `false`, Issue if `true`) the next time this skill is invoked, per Workflow step 3's budget-exhaustion rule.

One secondary effect: since the count (2) at round-3 decision time already meets/exceeds `review_findings_min_rounds` (default 1), Question 1 would have included a "No further round for now" option had a fresh ask been needed — but it isn't needed here, since the reviewer/mode choice is already fixed for this conversation and reused instead of re-asked.
