# Round-2 trigger decision — PR #170

**Note:** this is the simulated exercise described in the prompt. No `gh`/API calls were made, and
`AskUserQuestion` was not actually invoked — everything below describes exactly what would be asked and
done, per `handling-review-findings`'s current Workflow step 8 (two-question design: reviewer(s), then
review profile).

## Why this is an "ask," not an auto-trigger or a skip

Round 1 (CI-triggered) is fully triaged: 1 finding, fixed/verified/replied/resolved. Workflow step 8
first resolves the **triggered-cycle count** (distinct from "round" — see
`references/round-and-dedup-rules.md`'s "Triggered-cycle count vs. round"): 1 (round 1's automatic CI
trigger) + the number of this skill's own trigger comments already posted to this PR. None have been
posted yet (this is the first next-round decision in this conversation), so the count is **1**.

Checking the three bands step 8 defines, against that count:

- `review_findings_min_rounds` = `1` — count (1) already meets the floor → **not** the "below
  min_rounds, proceed without asking whether" case.
- `review_findings_max_rounds` = `3` — count (1) is well under the ceiling → **not** the "at
  max_rounds, skip step 8 entirely" case.
- Strictly between the two → per step 8, **ask via `AskUserQuestion` whether to run another cycle at
  all** (not just which reviewer).

This is also the first next-round decision in this conversation, so there is no earlier reviewer/mode
answer to reuse — the choice is "fixed once per conversation," but only once it has actually been made
once.

## Trigger-string validation done before offering anything (step 8's 3-step order)

`review_findings_reviewers` has all three seed reviewers enabled, using their tracked default trigger
strings — no untracked `.claude/git-kit.local.json` override in play, so the tracked-ness gate (step 1
of the three-step order) is trivially satisfied: nothing to fall back away from.

| Reviewer (`name`) | `default_review_trigger` | `full_review_trigger` | Handle-token check | Anchored-regex check |
|---|---|---|---|---|
| `codex` | `@codex review` | `@codex full review` | `codex` == `codex` ✓ | matches `^[@/][A-Za-z0-9_-]{1,39}( [a-z]{1,12}){1,2}$` ✓ |
| `coderabbit` | `@coderabbitai review` | `@coderabbitai full review` | `coderabbitai` matches `^coderabbit[a-z0-9]*$` (case-insensitive) ✓ | matches ✓ |
| `devin` | `/devin review` | `/devin review` (identical — Devin has no distinct full mode) | `devin` == `devin` ✓ | matches ✓ |

All three `name` fields also pass the `^[a-z][a-z0-9_-]{0,31}$` check needed before they're used in the
handle-token regex or a scratchpad filename. All three reviewers survive validation, so all three are
eligible options in Question 1 below.

## What I would actually ask

One `AskUserQuestion` call carrying **two questions**, per step 8's current design:

**Question 1 — reviewer(s), multi-select, 4 options (the tool's real `maxItems: 4` cap, hit exactly:
3 validated reviewers + 1 mandatory opt-out):**

> "Round 1 is fully triaged (1 finding fixed, verified, replied-to, and resolved). The review budget
> allows up to 2 more rounds (max 3; 1 used so far). Which reviewer(s), if any, should run the next
> round?"

| # | Option label | Description shown |
|---|---|---|
| 1 | Codex | Trigger a Codex review for the next round |
| 2 | CodeRabbit | Trigger a CodeRabbit review for the next round |
| 3 | Devin | Trigger a Devin review for the next round |
| 4 | No further round for now | Don't trigger another round this run |

Per step 8, each option's description names the reviewer plainly — **not** yet the literal trigger
text, since that depends on Question 2's answer.

**Question 2 — review profile, single-select, exactly 2 options, applied uniformly to every reviewer
picked in Question 1:**

> "Which review profile should the selected reviewer(s) run?"

| # | Option label | Description shown |
|---|---|---|
| 1 | Default review | Standard-depth review pass |
| 2 | Full review | Deeper/more exhaustive review pass |

For a reviewer whose two modes are identical (Devin), this answer resolves to the same posted string
either way — no special case needed.

### The literal text that would actually get posted, resolved from both answers together

| Reviewer | If Question 2 = "Default review" | If Question 2 = "Full review" |
|---|---|---|
| Codex | `@codex review` | `@codex full review` |
| CodeRabbit | `@coderabbitai review` | `@coderabbitai full review` |
| Devin | `/devin review` | `/devin review` |

Option 4 in Question 1 exists because the question is genuinely "whether," not just "which" — if it's
selected at all (alone, or together with any reviewer option), it's treated as authoritative: Question
2's answer is ignored entirely and nothing gets posted.

## What I would do after the user answers

**If "No further round for now" is selected** (alone, or together with any reviewer option): stop here.
This run's final word is the round-1 disclosure already reported (fixed/verified/replied/resolved,
nothing deferred, nothing to accept as risk). Nothing is posted, and no further round is triggered by
this skill this run — a later invocation of this skill in a fresh conversation can still ask again,
since only this one "no" was given, not a standing refusal.

**If one or more reviewers are selected** (say Codex and Devin, profile = Default review): for each
selected reviewer, in order:

1. Reuse the already-validated string resolved above for that reviewer/profile combination — no
   re-validation needed, it already passed the three-step check.
2. Write that reviewer's exact trigger text to its own scratchpad file (`trigger-codex.txt`,
   `trigger-devin.txt` — never a shared filename across reviewers), written immediately before that
   reviewer's own post.
3. Immediately before posting, run
   `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review handling-review-findings` — a
   fresh marker per `gh pr comment` call, since the marker is single-use and consumed by the very next
   shell call regardless of match. Selecting 2 reviewers means 2 separate marker-write-then-post pairs,
   never one marker reused across both.
4. Post with `gh pr comment 170 -R "<owner>/<repo>" --body-file "<scratchpad-path>/trigger-<name>.txt"`
   — never inlining the trigger string into the command line.
5. Do **not** poll for the new review to come back. This skill's run ends here for this round — there's
   no uniform, fast, queryable signal across Codex/CodeRabbit/Devin the way `codex-review-recovery` has
   for its own narrower stuck-check case (`references/round-and-dedup-rules.md`, "Why the next-round
   trigger doesn't poll"). Tell the user plainly which trigger comment(s) were posted, and that
   re-invoking this skill once the review actually posts back is how round 2 gets triaged.

Either way, the reviewer/mode decision made here (which reviewers, which profile, and the exact
validated strings behind it) is remembered for the rest of *this* conversation. If this same
conversation later needs to trigger round 3, Workflow step 8 reuses this answer and posts the matching
trigger comment(s) without asking the reviewer/mode question again — re-validating only if a later round
needs a reviewer this run hasn't already validated. A genuinely new conversation with no memory of this
exchange would ask fresh from scratch, since this skill keeps no persisted round-counter or decision
file.

No `gh`/API calls and no actual `AskUserQuestion` call were made in producing this description, per the
prompt's constraint that this is a simulated exercise only.
