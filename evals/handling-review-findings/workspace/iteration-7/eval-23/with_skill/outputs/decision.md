# Decision — PR #501, Workflow Step 8b

## Inputs given

- `review_findings_min_rounds` = 2, `review_findings_max_rounds` = 3
- Triggered-cycle count (8a) = 1 (round 1's automatic CI trigger only) — **below `min_rounds`**
- 8c validation survivors: **only Codex** (CodeRabbit dropped — `enabled: false`, excluded before any
  other check per 8c's "drop every entry whose `enabled` field is `false` — before any other check";
  Devin dropped — its trigger string fails the handle-token check, and per 8c's fallback rule this means
  the git-tracked `git-kit.settings.json` value was tried and also failed, so Devin is excluded entirely)

## Reasoning

Two 8b rules interact here and must be applied in the right order:

1. **The below-`min_rounds` rule** (8a, and 8b's opening bullet): below `min_rounds`, another cycle is
   required — proceed without asking *whether*, only *which*. Normally this means Question 1's "No
   further round for now" option is **omitted entirely**, since stopping isn't a real choice yet.
2. **The one-survivor rule** (8b's "Fewer than 2 reviewers survive 8c" section): `AskUserQuestion`
   requires 2-4 options per question. With only one reviewer (Codex) surviving 8c, Question 1 as a bare
   single-option list can't be asked at all. The explicitly documented exception fires: *"Exactly one
   reviewer survives. Question 1 still includes the 'No further round for now' option alongside it (2
   options total) **even below `min_rounds`**."*

So the one-survivor rule overrides the normal below-floor omission specifically to reach the tool's
2-option minimum — it doesn't restore "No further round for now" as a real stop choice, just as a
selectable option that gets special (non-authoritative) handling if picked.

## Answer: what Question 1 presents

Exactly **2 options** (the `AskUserQuestion` per-question minimum), no more:

1. **"Codex"** — the single reviewer entry that survived 8c's validation (drops the exact trigger
   string; Question 1 names the reviewer plainly, not yet the literal trigger text, which is resolved
   from Question 2's answer).
2. **"No further round for now"** — included solely to satisfy the 2-option floor, per the one-survivor
   exception above; it is *not* being offered as a genuine "stop" choice the way it would be at/above
   `min_rounds`.

Question 2 (review profile) is asked as usual alongside Question 1 in the same `AskUserQuestion` call:
single-select, exactly 2 options, "Default review" / "Full review," applied to whichever reviewer is
ultimately triggered.

## Answer: what happens if the user selects "No further round for now"

Because the triggered-cycle count (1) is still below `min_rounds` (2), this selection is **not**
treated as authoritative the way it would be at/above the floor. Per 8b's explicit carve-out:

> "below the floor, selecting 'No further round for now' doesn't silently end the run the way it does
> at/above the floor: report that the round floor requires another cycle, no second validated reviewer
> is available to offer a real choice between, and stop for the user to either confirm triggering the
> one remaining reviewer or fix the reviewer configuration (enable/repair another entry) before
> continuing."

Concretely, on this selection the skill:

- Does **not** stop the round-trigger process outright and does **not** proceed to post a trigger
  comment either.
- Reports plainly that `review_findings_min_rounds` (2) requires another triggered cycle, and that
  only one reviewer (Codex) currently passes validation, so there's no genuine multi-way choice to make.
- Stops and asks the user to pick one of two paths forward:
  - Confirm triggering the one remaining validated reviewer (Codex), or
  - Fix the reviewer configuration first (e.g. re-enable CodeRabbit, or repair Devin's trigger string
    so it passes the handle-token check), then re-run 8c/8b with a fuller candidate set.

Nothing is posted to the PR as a result of selecting "No further round for now" in this below-floor,
one-survivor scenario — it functions as a request for clarification/reconfiguration, not as the normal
authoritative stop it would be once the triggered-cycle count reaches `min_rounds`.
