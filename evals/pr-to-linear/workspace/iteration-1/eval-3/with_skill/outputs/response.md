# Walkthrough: "PR #77 (linked to ENG-230) looks done — mark this PR ready for review"

## Step 0 — Skill selection

The request matches `pr-to-linear`'s own "When to Use" ("marking the PR ready once requirements are met") and is explicitly listed in its Testing & Validation activation examples ("mark this PR ready for review"). It is not `development-to-pr` (publishing an initial draft) and not `merge-to-completion` (merging). I load `pr-to-linear`'s procedure and follow it in order.

## Step 1 — Read current state

Per step 1, I read the PR's current state: head SHA, mergeability, reviews, and check-rollup via `gh pr view` (I'd run `gh pr view 77 --json headRefOid,mergeable,reviews,statusCheckRollup,isDraft,url`), required checks via `gh pr checks 77`, and repository policy via `Skill(repository-gates)`. I explicitly note the skill's disclosed limitation here: it cannot read unresolved-thread state itself — `gh pr view` has no thread-resolution field, only GraphQL's `reviewThreads.isResolved` exposes that, and this skill holds no `gh api graphql` grant. So thread-resolution has to come from `handling-review-findings`'s own report, not from anything I read directly in step 1.

## Step 1.5 — Resolve intent (the critical routing step)

This is the step the task is specifically asking me to demonstrate correctly, so I trace it carefully.

Step 1.5 first distinguishes a *pure summarize/reflect* request (needs only step 1's read, skip step 2) from a *triage/fix/reply/resolve* request (needs step 2's delegation). But the skill is explicit that **"mark this PR ready for review" is neither branch** — it says so in its own words: *"A 'mark this PR ready for review' request is neither branch above — route it explicitly, never by falling through either one."*

Reasoning through why: this isn't a pure status summary (the user wants a state mutation, not just a report), and it isn't phrased as "triage" or "fix" either. But the skill's own step 5 precondition (in the Marking Ready section) *requires* step 2's completed `handling-review-findings` report as its basis for the "no unresolved findings" check. So the skill's instruction is unambiguous: **always run step 2 first for a readiness request, exactly as if it had explicitly asked for triage**, and only then continue into the Marking Ready section (step 5 onward). I do not treat "looks done to me" as license to skip step 2 — the user's own assessment isn't a substitute for `handling-review-findings`'s actual per-finding report.

So: I proceed to step 2, not step 3/4.

## Step 2 — Delegate triage and fix

I invoke `Skill(git-kit:handling-review-findings)` against PR #77. This is the skill that owns the actual finding classification, fix/file/decline decisions, fix application (via its own `git-kit:commit` delegation), and reply/resolve mechanics on GitHub threads. Per `pr-to-linear`'s own boundary, I do not perform any of that myself — no raw `gh pr review`, no raw `gh pr comment`, no re-classifying a finding on my own judgment. `handling-review-findings` holds the `gh api graphql` grant this skill lacks, and its end-of-run report (fixed / filed / declined / left-unresolved per finding) becomes `pr-to-linear`'s sole source of truth for thread-resolution state going forward.

*(In this synthetic run, I'd receive back a structured report — e.g. "3 findings: 2 fixed and pushed as new commits, 1 declined as out-of-scope with reviewer reply posted; 0 left unresolved" — and I take that as the ground truth for what follows.)*

## Step 3 — Re-read GitHub's resulting state (since step 2 ran)

Because step 2 actually ran, step 3 applies in its "step 2 ran" branch: I re-read checks/reviews via `gh pr view`/`gh pr checks` again, rather than assuming the triage outcome. I do not re-derive unresolved-thread state myself — that stays exactly what `handling-review-findings`'s report said, since re-confirming it would require dispatching that skill again (not something step 3 does on its own).

## Step 4 — Reflect blockers to Linear

I summarize what `handling-review-findings` actually did (fixed/filed/declined per finding) to the linked Linear issue ENG-230, via `Skill(linear-work-management)`. This is a deliberate, concise summary of the actionable implication — never a copy of raw check output, never a restatement of my own triage judgment (I didn't do any triage judgment; that was `handling-review-findings`'s job).

At this point steps 1–4 (the "Review and reflect loop") are done. Now I continue into the Marking Ready section, per step 1.5's explicit instruction not to treat the request as answered yet.

## Step 5 — Verify (immediately before acting)

I re-read, fresh, immediately before doing anything state-changing: draft state, current head SHA, required checks/reviews, and that the PR description/Linear link are current. This is a new read, not reuse of step 1's or step 3's earlier reads — the rule against stale-state side effects applies directly here.

Unresolved threads are *not* independently re-verified at this step (per step 1's disclosed limitation) — I rely on step 2's `handling-review-findings` report showing every finding fixed/filed/declined with nothing genuinely left open. Since no meaningful time has passed between step 2 and step 5 in this scenario, I don't re-dispatch `handling-review-findings` again. (If it had — e.g. a long gap where a new inline comment could plausibly have landed — the skill requires dispatching it again rather than trusting the earlier report.)

## Step 6 — Revalidate Linear context

Via `Skill(linear-work-management)`, I revalidate ENG-230's acceptance criteria and any known blockers recorded there, to make sure Linear's own state doesn't contradict what GitHub just showed as ready.

## Step 7 — Present and confirm via AskUserQuestion

I present the readiness action and any remaining gaps to the user via `AskUserQuestion` — e.g., "PR #77 head SHA `abcd123`, all required checks green, 0 reviews requesting changes, 0 unresolved findings per handling-review-findings's report. Linear ENG-230 acceptance criteria match. Ready to proceed with marking this PR ready for review?" This is the approval gate the skill's Confirmation and Safety section calls out explicitly for the ready-state handoff.

## Step 8 — Structured handoff, not a raw mutation

This is the part the task asks me to be explicit about. The skill states plainly: **no `git-kit` skill currently owns a callable draft-to-ready conversion action.** `gh pr ready` is documented only as manual follow-up guidance under `git-kit:create-pr`'s Best Practices — not something `create-pr` or `collaborating-on-a-pr` performs on request — and `pr-to-linear` holds no tool grant for either of them for this purpose.

So instead of running it myself, I present this as a disclosed gap via `AskUserQuestion` and ask the user to run `gh pr ready 77` themselves, outside this skill's own delegated flow. **I never invoke `gh pr ready` or any other raw `gh pr` mutation command myself** — doing so would be exactly the raw-command fallback the skill's Wave 2 Non-Goals prohibit, and my own `allowed-tools` frontmatter doesn't grant any `gh pr` mutation Bash pattern in the first place (only `Bash(gh pr checks:*)` and `Bash(gh pr view:*)`, both read-only).

*(In this synthetic run, I'd wait here for the user to confirm they ran `gh pr ready 77` on their end.)*

## Step 9 — Read back and record `pr-ready`

Once the user confirms they ran it, I read back GitHub's actual state (`gh pr view 77 --json isDraft,headRefOid`) to confirm the draft state actually changed — I don't assume it did just because the user was asked and said yes. I then record `pr-ready` via `Skill(linear-github-linking)`, tied to the **exact current head SHA** confirmed in this same re-read (not the SHA from step 5, if any time has passed — I'd re-verify again if so).

Critically, per the skill's explicit instruction: `provider` is recorded as the literal string `"manual (gh pr ready, per pr-to-linear's disclosed handoff)"`, per `FOUNDATION_CONTRACTS.md`'s schema note — **never** a fabricated `git-kit:...` provider name, since no `git-kit` skill actually performed this mutation. The mutation was performed by the user's own manual `gh pr ready` invocation, and the recorded evidence must say so honestly rather than implying automated provenance that didn't happen.

## Step 10 — Move Linear status, only if policy calls for it

I check whether the repository's approved Linear workflow calls for a distinct, deliberate "move to In Review/Ready" step for ENG-230. I do not infer this from GitHub's own native automation (e.g., a Linear-GitHub integration auto-transitioning the issue) — if that happens on its own, that's drift per the skill's Failure and Resume section, to be reported for `linear-github-reconciliation` to investigate separately, not silently accepted as the expected outcome.

---

**Note: this is a synthetic evaluation run. No real `gh` or Linear tool calls were executed — PR #77 and ENG-230 do not exist in a live repository/workspace reachable from this session. Every command and tool invocation described above is a trace of what would be run, not an actual executed call.**
