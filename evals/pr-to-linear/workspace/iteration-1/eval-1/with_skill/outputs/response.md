# Walkthrough: PR #50 / ENG-202 — `pr-to-linear`

**Request:** "PR #50 (linked to Linear issue ENG-202) has review comments and a merge-blocking Codex
finding. Summarize its review status to Linear and get the blocking finding resolved."

This is two asks bundled into one sentence. Before touching any tool, I parse them against the
skill's own step 1.5 intent gate:

- "Summarize its review status to Linear" → a pure reflect/summarize ask.
- "get the blocking finding resolved" → an explicit triage/fix/resolve ask.

Because the second clause is present and unambiguous, step 1.5 routes this whole request through
**step 2** (the `handling-review-findings` delegation), not the shortcut branch. I don't try to
satisfy "summarize" with a cheap step-1-only read and separately debate whether "resolved" implies
delegation — the request itself already contains the trigger phrase step 1.5 names as the deciding
case ("If the request explicitly asks to triage, fix, reply to, or resolve findings ... proceed to
step 2"). This is also explicitly **not** a "mark ready" request — nothing here asks me to flip
draft state — so I do not touch the Marking Ready section (steps 5-10) at all.

---

## Step 1 — Read current GitHub state

I read, but do not yet act on:

- `gh pr view 50 --json headRefOid,mergeable,reviews,statusCheckRollup,title,body,url` — current head
  SHA, mergeability, the review list (approvals / change-requests / comments), and the check-rollup
  summary.
- `gh pr checks 50` — the required-checks list and pass/fail state, specifically confirming which
  check is the "merge-blocking Codex finding" the user referenced (likely a required status check
  tied to Codex's automated review, currently failing or in a blocking state).
- `Skill(repository-gates)` — repository policy: what's actually required to merge (required checks,
  required approvals, branch protection), so I know what "blocking" means for *this* repo rather than
  assuming a generic rule.

At this point I explicitly do **not** try to read thread-resolution state myself. Per the skill's own
step 1 caveat, `gh pr view`'s JSON has no thread-resolution field — only GraphQL's
`reviewThreads.isResolved` exposes that, and this skill holds no `gh api graphql` grant. I note this
gap now rather than fudging it, but since step 1.5 has already routed me to step 2, the gap will be
filled by `handling-review-findings`'s own report rather than left open.

## Step 1.5 — Intent resolution (already decided above)

Recorded explicitly: this is a triage/fix request, not a pure-summary request. Proceed to step 2.

## Step 2 — Delegate the actual triage/fix/reply/resolve cycle

`Skill(git-kit:handling-review-findings)`, pointed at PR #50.

This is the one call in the whole run that does real mutating work, and it's not mine to do — I
hand the merge-blocking Codex finding and the other review comments to it entirely:

- It classifies each finding (the Codex blocker, plus whatever else is in the review comments) —
  Critical/Major/Minor, in-scope vs. out-of-scope, fixable-this-session vs. not.
- It decides fix vs. file vs. decline per finding, per its own round budget (default 1-3 rounds).
- If it fixes something, that fix goes through `git-kit:commit` (its own delegation, not something
  I invoke myself).
- It replies to and resolves the corresponding GitHub review threads.
- It has the `gh api graphql` grant this skill lacks, so it's also the only reliable source for
  unresolved-thread state afterward.

What I explicitly do **not** do here: I do not read the Codex finding's text and decide myself
whether it's a real bug or a false positive. I do not call `gh pr review` or `gh pr comment` myself.
I do not resolve the thread myself even if, skimming it, the fix looks trivially obvious — the
skill's own Gotchas section calls this out by name as the "obviously handled" trap, and this run
treats it as a hard boundary, not a judgment call.

At the end of this step, `handling-review-findings` hands back a per-finding report: something like
*"Codex blocking finding — fixed (commit abc123, thread resolved); review comment #1 — filed as
follow-up issue #212 (out of scope for this PR); review comment #2 — declined with reply (not
reproducible / working as intended)."* I treat this report as the sole source of truth for
thread-resolution state going forward — I do not re-derive it.

## Step 3 — Re-read GitHub's resulting state

Since step 2 ran, I re-read `gh pr view 50` and `gh pr checks 50` again — fresh calls, not a reuse
of step 1's numbers. I'm checking two things:

1. Did the fix commit actually land, and did the previously-failing Codex check flip to passing?
2. What's the new head SHA (the fix commit moved it) and current mergeability?

I do **not** re-derive unresolved-thread state here — that stays exactly what
`handling-review-findings`'s own report said in step 2, because re-confirming it would mean
dispatching that skill a second time, which isn't what this step is for.

## Step 4 — Reflect only the meaningful blockers to Linear

`Skill(linear-work-management)`, targeting ENG-202. What goes into Linear is a short, deliberate
translation of what actually happened — never a transcript dump. Concretely, something like:

> **PR #50 review status (as of `<new head SHA>`):**
> - Codex merge-blocking finding: fixed and check now passing (commit `abc123`).
> - 1 review comment: filed as follow-up issue #212 (out of scope for this PR).
> - 1 review comment: declined with reasoning (see PR thread).
> - Remaining required checks: `<pass/fail summary from step 3>`.
> - Unresolved threads: none outstanding, per `handling-review-findings`'s round report.

What I deliberately leave **out** of that Linear update:

- The full text of Codex's finding or the reviewer's comment bodies.
- The full diff of the fix commit.
- Any raw check-log output.
- My own restatement of `handling-review-findings`'s triage *reasoning* beyond the one-line
  disposition (fixed/filed/declined) — the "why" lives in the PR thread, GitHub stays authoritative
  for it.

If, hypothetically, `handling-review-findings` had come back with something still unresolved past its
round budget (a Critical finding it couldn't close), I would reflect that plainly as an open blocker
in Linear rather than reporting the PR as clear — the skill's Confirmation and Safety section requires
exactly this "structured handoff" framing, and I would *not* silently treat the PR as ready.

## What I do not do in this run

Because the user never asked to mark the PR ready, I stop after step 4. I do not invoke
`AskUserQuestion` for a readiness handoff, I do not touch `gh pr ready`, and I do not move Linear's
workflow status to In Review/Ready — that's steps 5-10, gated on a distinct request this task didn't
make. If the user follows up with "now mark it ready," that's the point I'd re-verify draft state,
head SHA, and required checks fresh (step 5) rather than reusing anything read in this run, since
time will have passed and the SHA-bound `pr-ready` record can't be based on a stale read.

## Summary of sub-skill calls made, in order

1. `gh pr view 50` (read)
2. `gh pr checks 50` (read)
3. `Skill(repository-gates)` (read policy)
4. `Skill(git-kit:handling-review-findings)` — the only mutating step; owns triage, fix, commit
   (via its own `git-kit:commit`), reply, and resolve for the Codex blocker and the review comments
5. `gh pr view 50` / `gh pr checks 50` again (confirm resulting state)
6. `Skill(linear-work-management)` — write the concise blocker/resolution summary to ENG-202

No raw `gh pr review`/`gh pr comment` calls were made directly by this skill, and no full transcript
was copied into Linear at any point.
