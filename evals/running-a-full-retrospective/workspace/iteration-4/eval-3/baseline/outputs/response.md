# Baseline Plan: Fixing Phase 3 Retrospective Findings

Scope going in: Phase 3 produced a consolidated report with three open findings across
**two different plugins**:

- P1 — `git-kit` — `skills/merge-pr/SKILL.md`
- P1 — `git-kit` — `skills/commit/SKILL.md`
- P2 — `plugin-devkit` — `skills/plugin-validator/SKILL.md`

Tools available for this exercise: `AskUserQuestion`, `Skill()` (only for dispatching the
`plugin-lifecycle-downstream` pipeline), `Write`, `Edit` — plus ordinary read/search capabilities.
No orchestration skill is doing this planning for me, so the sequencing below is my own reasoning
about how to use those tools safely and in a sensible order.

Below is the exact order of tool calls I would make, each described rather than executed.

---

## Step 1 — Read the consolidated report (no tool listed above, but a basic read)

Before calling anything, I read the Phase 3 consolidated report itself to pull the precise finding
text, IDs, and evidence for all three findings. I need the exact wording to hand to the fix
pipeline later (so it fixes the *actual* flagged issue, not a re-derived guess at what's wrong),
and to have a baseline to check the fixes against afterward.

## Step 2 — `AskUserQuestion` #1: confirm approach and sequencing

I do **not** immediately fire off `Skill(plugin-lifecycle-downstream)` twice. Two things are
genuinely ambiguous and worth a human decision rather than a silent default:

1. **Scope mismatch.** `plugin-lifecycle-downstream` is a 12-phase pipeline (Validate → Fix →
   Audit → Deep Test → Grading → Docs/Handoff) that operates on *one given plugin*. The two P1
   findings share a plugin (`git-kit`) and can be resolved in a single pipeline run; the P2
   finding is a different plugin (`plugin-devkit`) and needs its own run. Running the full
   12-phase pipeline for a single already-localized finding is arguably heavier than the finding
   warrants (CLAUDE.md's Simplicity-First guidance), so it's worth surfacing that tradeoff rather
   than silently picking the heavy option.
2. **Ordering.** P1 should be fixed before P2, but I confirm rather than assume, since the user
   may want both plugins touched together for a single combined commit later.

Question asked: *"Phase 3 flagged 2 P1 findings in git-kit (merge-pr, commit) and 1 P2 finding in
plugin-devkit (plugin-validator). How should I fix these?"*
Options offered:
- **A.** Run `plugin-lifecycle-downstream` on `git-kit` first (resolves both P1s in one pass),
  then on `plugin-devkit` for the P2.
- **B.** Run `plugin-lifecycle-downstream` on `plugin-devkit` first, `git-kit` second.
- **C.** Skip the full pipeline — apply the fixes directly via `Edit` against the finding text,
  since both files and both problems are already identified.

I proceed below assuming **A** is chosen (P1-before-P2 is the sane default and matches what the
report's own severity tags imply), while noting the branch points where C would change the plan.

## Step 3 — `Skill(plugin-lifecycle-downstream)` targeting `git-kit`

Dispatch the pipeline scoped to the `git-kit` plugin, passing in the two known P1 findings (file
paths + finding text pulled in Step 1) as the input to work from, rather than asking it to
rediscover issues from a blank Validate pass. This lets its Fix phase go straight at the two
flagged files (`skills/merge-pr/SKILL.md`, `skills/commit/SKILL.md`), and lets its own Audit /
Grading phases verify the fix didn't introduce a new Critical/Major issue — I don't have a
separate rulebook-check tool available in this exercise, so I'm relying on the pipeline's internal
Audit phase to cover that "before finalizing" compliance check rather than skipping it.

## Step 4 — Read the pipeline's resulting report for `git-kit`

After the dispatch returns, read its handoff/report output. I'm checking three things specifically:
- Both P1 findings are marked resolved (not just "attempted").
- The Audit phase didn't surface a new Critical/Major finding as a side effect of the fix.
- Nothing in the Fix phase was left for a human decision it couldn't make on its own.

## Step 5 — Conditional: `AskUserQuestion` #2 (only if Step 4 surfaces an open decision)

If the pipeline's own Fix phase punted on part of either P1 finding because it required a
judgment call (e.g., a behavioral tradeoff it isn't positioned to decide), I ask the user that
specific question directly rather than guessing at it myself. I don't fabricate an answer on the
pipeline's behalf.

## Step 6 — Conditional: `Edit` on the affected `git-kit` file(s)

Only if Step 5 produced an answer the pipeline itself didn't apply, I make the specific,
surgical edit to `skills/merge-pr/SKILL.md` or `skills/commit/SKILL.md` myself — touching only the
lines that trace directly to the human's answer, per CLAUDE.md's Surgical Changes guidance. If the
pipeline's own Fix phase already fully resolved both P1s, this step is skipped entirely (and I'd
say so explicitly rather than silently no-op'ing it, per the "disclose skipped phases" convention
in this repo's rules).

## Step 7 — `Skill(plugin-lifecycle-downstream)` targeting `plugin-devkit`

With `git-kit`'s P1s closed, dispatch the pipeline a second time, this time scoped to
`plugin-devkit`, passing in the one P2 finding (file: `skills/plugin-validator/SKILL.md`, finding
text from Step 1) as the input. Same rationale as Step 3: let the Fix phase target the flagged
file directly, and let Audit/Grading confirm no regression.

## Step 8 — Read the pipeline's resulting report for `plugin-devkit`

Same check as Step 4, scoped to the single P2 finding: resolved, no new Critical/Major issue
introduced, nothing left for a human call. If something is left open, repeat the Step 5/6 pattern
(ask, then `Edit` only the specific remaining piece).

## Step 9 — Cross-check against the original report

Re-read the Phase 3 consolidated report's three finding entries against both pipeline outputs
together, rather than trusting either pipeline run's self-report in isolation. This mirrors the
retrospective's own "re-verify stated open items against current repo state rather than trusting
them at face value" convention — a pipeline reporting "fixed" is a claim, not proof, until checked
against the same finding text that opened it.

## Step 10 — `AskUserQuestion` #3: next step (commit)

At this point all three findings (2 P1 + 1 P2) are closed in the working tree, but nothing has
been committed. Since the only tools granted for this exercise are `AskUserQuestion`,
`Skill(plugin-lifecycle-downstream)`, `Write`, and `Edit` — not a git/commit skill — I don't
hand-roll a raw `git commit`. Instead I ask the user how they want to proceed: commit the git-kit
fix and the plugin-devkit fix as one combined change, as two separate changes (since they're two
unrelated plugins), or hold off entirely pending further review. This also respects the
one-topic-one-worktree consideration noted in this repo's conventions: git-kit and plugin-devkit
are different plugins, so if separate commits/branches are wanted, that's a decision for the
user to make explicitly rather than something I default silently.

---

### Why this order

- **Read before asking**: I need the exact finding text before I can ask a well-formed question
  or hand a useful instruction to the pipeline.
- **Ask before dispatching anything expensive**: `plugin-lifecycle-downstream` is a heavy,
  multi-phase pipeline; running it twice without checking whether that's even the wanted approach
  (vs. a direct edit) would be presumptuous given the size of the fix relative to the tool.
- **P1 before P2**: severity-ordered, and confirmed rather than assumed.
- **One dispatch per plugin, not per finding**: both P1s share a plugin, so one `git-kit` run
  covers both — avoids redundant pipeline runs for findings that live in the same place.
- **Verify, don't trust**: each pipeline's own "resolved" claim gets checked against the original
  report text before being treated as done.
- **No silent commit**: committing is out of scope for the tools granted here, so the last step is
  an explicit ask rather than a fabricated git action.
