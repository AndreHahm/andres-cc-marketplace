# Resuming Wave 2 Lifecycle for ENG-288

## Step 1 — Determine the furthest-completed Git/GitHub phase

**Partition by artifact chain first.** All three evidence entries share the same `repository` (`acme/api`) and the same `branch` (`feat/eng-288-webhook-retries`) — `work-started`, `commit-linked`, and `pr-published` are all on that one branch. There's no second `(repository, branch)` grouping and no distinct `pull_request.number` pointing elsewhere, so there is exactly one active chain here. No "which chain is current" ambiguity, and no `AskUserQuestion` is needed for chain selection — that branch is unambiguous.

**Check for superseded entries.** None of the three entries is named by a later entry's `supersedes` field (no such field is mentioned in the evidence I was given, and nothing about a force-push or base-change invalidation was reported). So all three entries are active and get considered as-is — I'm not discarding or discounting any of them.

**Read the active entries against the Phases table:**

| Evidence entry | Corresponds to | Phase status |
|---|---|---|
| `work-started` (acme/api, feat/eng-288-webhook-retries) | Prepare + Start (`work-to-development`) | Done |
| `commit-linked` (same branch) | part of Commit + gates + Publish (`development-to-pr`) | Done |
| `pr-published` (same branch, `gates: [{lint: pass}, {unit-tests: pass}]`) | rest of Commit + gates + Publish (`development-to-pr`) | Done |

The furthest active entry is `pr-published`. Per the Phases table, `pr-published` evidence is what `development-to-pr` produces at the end of the "Commit + gates + Publish" phase — so that whole phase is complete. There is no `pr-ready` entry anywhere in the array, so the next phase down the table, "Review/fix + Ready" (delegated to `pr-to-linear`), has not produced its evidence yet, and is therefore the furthest **incomplete** phase.

The Implement phase itself needs no separate check here per the skill's own note — since `work-started` is present and is immediately followed by `commit-linked` (not left dangling with no commit evidence after it), Implement is clearly already behind us, not the resume point. This is a case where the evidence trail is unambiguous, not the "gap" case the skill calls out.

**Conclusion of Step 1:** Furthest-completed Git/GitHub phase = **Commit + gates + Publish**, fully done, including a draft PR published on `feat/eng-288-webhook-retries` with recorded gate results `lint: pass` and `unit-tests: pass`. The resume point is the **Review/fix + Ready** phase (`pr-to-linear`), which has not yet run (or ran but never completed to the point of writing `pr-ready` evidence).

## Step 2 — `pr-merged` ambiguity check: does not apply here

The skill's step 2 language is specifically about what to do **"when the furthest active Git/GitHub evidence is `pr-merged`"** — the special caution that neither an open nor closed Linear status is proof of what happened after merge, and that a direct `AskUserQuestion` is mandatory in that specific case regardless of Issue status.

That is not the situation here. The furthest active entry in this chain is `pr-published`, not `pr-merged` — this evidence trail hasn't even reached `pr-ready` yet, let alone `pr-merged`. So step 2's specific ask ("did the disposition already conclude, or are steps 9-14 the resume point?") is not the right question to ask, and I'm not going to invoke it. Applying it here would be a category error — it answers a question about post-merge disposition that doesn't arise until several phases later in this same chain.

## On the "In Review" Linear status

The Issue currently shows **In Review** in Linear. I'm treating this the same way the skill treats Issue status everywhere else it comes up: **informative context, never proof.** Concretely:

- "In Review" is *consistent with* a published PR awaiting review/ready confirmation — it doesn't contradict what the evidence array already tells me (a PR exists, gates recorded as passing at publish time).
- But it is **not** independent confirmation of anything I can't already see in the evidence array. It doesn't tell me whether a human or automated review has actually happened on the PR, whether the gates still pass as of right now (the `gates[]` array on the `pr-published` entry is a snapshot taken at publish time, not a live status), or whether any blockers have since been raised. `pr-to-linear` — the phase I'm about to re-enter — is exactly the phase responsible for actually determining and recording that, and it needs to do its own live check rather than have me infer its outcome from a Linear kanban-column label.
- I'm also not using "In Review" to *skip* asking the user anything. It's consistent with, at most, "a PR exists and is out for review" — which the `git-github-evidence` array already told me directly and more reliably.

## Step 3 — Notion-learning phase check: not reached, and not asked yet

Step 3 says to ask (via a separate `AskUserQuestion`) whether a Notion outcome/learning summary was already captured — but only *after* step 2's ask confirms the merge-to-completion disposition (steps 9-14) has genuinely completed. Since this chain hasn't reached `pr-merged` at all yet, let alone the disposition sub-phase after it, that precondition isn't met. I am not asking about Notion learning at this point in the resume — doing so now would be premature (there's nothing to have "already captured" yet, since the work that would generate a learning outcome hasn't happened). I'll note this explicitly rather than silently skipping it: **Notion-learning check deferred, not applicable to this resume point.**

## Step 4 — Present the resume point via AskUserQuestion (mandatory, before continuing)

Before touching anything, I present this to the user rather than silently resuming:

> **AskUserQuestion**
> **Question:** "ENG-288's Git/GitHub evidence shows the lifecycle completed through Commit + gates + Publish: branch `feat/eng-288-webhook-retries` in `acme/api`, a commit linked, and a draft PR published with `lint: pass` and `unit-tests: pass` recorded at publish time. There's no `pr-ready` evidence yet, so Review/fix + Ready hasn't completed. (Linear shows the Issue as 'In Review' — consistent with this, but not independent proof review actually happened; I'm not treating it as evidence.) How would you like to proceed?"
> **Options:**
> 1. **Resume at Review/fix + Ready** — re-enter via `pr-to-linear` now: it will check the PR's current review/gate state live (not the stale snapshot in `pr-published`), summarize any blockers, and produce `pr-ready` evidence once clear.
> 2. **Something changed since publish — re-verify first** — e.g. force-push/rebase since the recorded commit, or gates re-run externally; if so, I should check for a superseding entry / re-verify branch state before resuming pr-to-linear.
> 3. **Stop here** — don't continue the lifecycle right now.

I would not proceed past this gate on my own judgment — the skill is explicit ("Present the resume point to the user via `AskUserQuestion` before continuing — never silently resume from an assumed point"), and this is exactly that checkpoint, distinct from any gate `pr-to-linear` itself will run internally once dispatched.

## Step 5 — Re-entry: which phase, and what is never re-run

Assuming the user picks option 1, I re-enter at **Review/fix + Ready**, delegated to `pr-to-linear`. This is the next undone phase per the Phases table, immediately following the completed `pr-published` evidence.

**What I do *not* re-run**, because their own evidence already confirms completion:
- **Prepare + Start** (`work-to-development`) — `work-started` evidence already confirms the branch `feat/eng-288-webhook-retries` on `acme/api` exists. I don't re-request branch creation or re-run `starting-work`.
- **Implement** — untracked by its own evidence stage by design, but implicitly closed out by the presence of `commit-linked` right after `work-started` with no gap.
- **Commit + gates + Publish** (`development-to-pr`) — both `commit-linked` and `pr-published` evidence already exist; I don't re-commit, re-run gates from scratch, or re-publish a draft PR. (`pr-to-linear`, once dispatched, may itself need to look at *current* gate/CI state as part of its own Review/fix logic — but that's `pr-to-linear` re-checking live state for its own phase's purposes, not this lifecycle skill re-running `development-to-pr`'s mutation.)

**What I do run:** `Skill(pr-to-linear)` against ENG-288 / PR on `feat/eng-288-webhook-retries`, to work through review/fix and, once clear, produce the `pr-ready` evidence entry. `pr-to-linear` still runs its own internal confirmation gate(s) when it executes — per the skill's Gotchas, my sequence-level `AskUserQuestion` above is **additive**, not a substitute for that. I'm not treating my own gate as sufficient cover to skip whatever `pr-to-linear` asks internally.

## Other Gotchas applied here

- **Reconciliation:** nothing in this evidence suggests drift (no superseded entries, single clean chain, no conflicting Linear/GitHub signals) — I'm not invoking `linear-github-reconciliation` as part of this resume. It stays on-demand only.
- **Stale/superseded entries:** confirmed none exist in this array, so this gotcha doesn't change the computed resume point — but I checked explicitly rather than assuming.
- **`pr-merged`/disposition/Notion gotchas:** all explicitly out of scope for this resume, as covered above — noted rather than silently skipped, per the skill's own "never silently skip" posture on Failure and Resume.
