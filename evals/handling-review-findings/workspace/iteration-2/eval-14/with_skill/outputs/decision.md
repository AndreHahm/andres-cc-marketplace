# Round-2 trigger decision — PR #170

**Note:** this is the simulated exercise described in the prompt. No `gh`/API calls were made, and
`AskUserQuestion` was not actually invoked — everything below is a description of what would be asked
and done, per `handling-review-findings`'s Workflow step 8.

## Why this is an "ask," not an auto-trigger or a skip

Round 1 (CI-triggered) is fully triaged: 1 finding, fixed/verified/replied/resolved. Checking the three
bands in Workflow step 8:

- `review_findings_min_rounds` = `1`, already satisfied by round 1 → **not** the "below min_rounds,
  proceed without asking" case.
- `review_findings_max_rounds` = `3`, and we're about to consider round 2 → **not** the "at max_rounds,
  skip step 8 entirely" case.
- We're strictly between `min_rounds` and `max_rounds` → per step 8, **ask via `AskUserQuestion` whether
  to run another round at all.**

This is also the first next-round decision in this conversation, so there is no earlier answer to reuse
(the reviewer/mode choice is "fixed once per conversation," not re-derived every round, but only once it
has actually been asked once).

## Trigger-string validation done before offering anything (Workflow step 8's 3-step order)

All three seed reviewers in `review_findings_reviewers` are enabled, using their **tracked** default
trigger strings (no untracked `.claude/git-kit.local.json` override in play here, so the tracked-ness
gate is trivially satisfied — nothing to fall back on).

| Reviewer | `default_review_trigger` | `full_review_trigger` | Handle-token check | Regex check |
|---|---|---|---|---|
| codex | `@codex review` | `@codex full review` | `codex` == name `codex` ✓ | matches `^[@/][A-Za-z0-9_-]{1,39}( [a-z]{1,12}){1,2}$` ✓ |
| coderabbit | `@coderabbitai review` | `@coderabbitai full review` | `coderabbitai` matches `^coderabbit[a-z0-9]*$` (case-insensitive) ✓ | matches ✓ |
| devin | `/devin review` | `/devin review` (identical to default — Devin has no distinct full mode) | `devin` == name `devin` ✓ | matches ✓ |

All three survive validation, so all three are eligible options.

## What I would actually ask

One `AskUserQuestion` call, single question, multi-select, **within the tool's real 4-options-per-question
cap** (`ask-user-question-patterns.md`'s documented `maxItems: 4`) — with 3 reviewers plus an explicit
opt-out, that's exactly 4 options, so everything fits in one question with no need to split or batch a
second question:

> **Question:** "Round 1 is fully triaged (1 finding fixed, verified, replied-to, and resolved). The
> review budget allows up to 2 more rounds (max 3, none used past round 1). Trigger another review round
> now?"
>
> **Options (multi-select):**
> 1. **Codex** — posts the literal comment `@codex review`
> 2. **CodeRabbit** — posts the literal comment `@coderabbitai review`
> 3. **Devin** — posts the literal comment `/devin review`
> 4. **No further round for now** — stop here; don't trigger anything this run

Each option's description states the exact literal text that would be posted (not just the reviewer's
name), since the user is confirming a specific string, per Workflow step 8. The 3 reviewer options
default to each tool's `default_review_trigger` — a plain, standard-depth pass. I would not additionally
offer the separate `full_review_trigger` variants (`@codex full review`, `@coderabbitai full review`) as
their own options in this same question: doing so for Codex and CodeRabbit alongside their default
variants, plus Devin's single option, would be 5 distinct trigger strings, which exceeds the tool's real
4-option cap for one question. If the user wants a "full review" pass instead of the default for any
selected reviewer, I'd say so plainly when presenting the options and let them say so in their answer
(e.g. "Codex, but full review") — at which point I'd substitute that reviewer's already-validated
`full_review_trigger` string instead of the default one, rather than opening a second `AskUserQuestion`
call for it.

Option 4 exists because the question is genuinely "whether," not just "which" — selecting nothing isn't
a valid multi-select outcome, so an explicit decline option is required to represent "no round now."

## What I would do after the user answers

**If option 4 ("No further round for now") is chosen** (alone, or the user otherwise declines): stop
here. This run's final word is the round-1 disclosure already reported (fixed/verified/replied/resolved,
nothing deferred). Nothing gets posted, and no further round is triggered by this skill this run — a
later invocation of this skill can still ask again, since only the "no" answer for *this* ask was given,
not a standing refusal.

**If one or more reviewers are chosen** (say Codex and Devin): for each selected reviewer, in order:
1. Reuse the already-validated string from the table above (no re-validation needed — it already passed
   the 3-step check).
2. Write that reviewer's exact trigger text to its own scratchpad file (e.g. `trigger-codex.txt`,
   `trigger-devin.txt` — never a shared filename across reviewers), immediately before that reviewer's
   own post.
3. Immediately before posting, run
   `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review handling-review-findings` — a
   fresh marker per `gh pr comment` call, since the marker is single-use and consumed by the very next
   shell call regardless of match. Selecting 2 reviewers means 2 separate marker-write-then-post pairs.
4. Post with `gh pr comment 170 -R "<owner>/<repo>" --body-file "<scratchpad-path>/trigger-<name>.txt"` —
   never inlining the trigger string into the command line.
5. Do **not** poll for the new review to come back — this skill's run ends here for this round (there's
   no uniform, fast, queryable signal across Codex/CodeRabbit/Devin the way `codex-review-recovery` has
   for its own narrower stuck-check case). Tell the user plainly which trigger comment(s) were posted,
   and that re-invoking this skill once the review actually posts is how round 2 gets triaged.

Either way, the reviewer/mode choice made here (including which reviewers were picked and which trigger
strings were used) is remembered for the rest of *this* conversation — if this same conversation later
needs to trigger round 3, Workflow step 8 reuses this answer and posts the matching trigger comment(s)
without asking again. A separate, fresh conversation with no memory of this exchange would ask again from
scratch, since this skill keeps no persisted round-counter or decision file (`references/round-and-dedup-
rules.md`'s "No persisted round-counter file" section).

No `gh`/API calls and no actual `AskUserQuestion` call were made in producing this description, per the
prompt's constraint that this is a simulated exercise only.
