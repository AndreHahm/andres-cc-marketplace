# Task: Take ENG-205 from start of work through merged PR + Linear disposition

Following `workmanagement-kit`'s `linear-github-lifecycle` SKILL.md exactly as documented. This is a
narrated dry-run (no live Linear/Notion/GitHub connectors in this harness) — every step below states
what I would actually invoke, in what order, what I'd check before/after, and what I would never do,
per the skill's own procedure.

---

## Step 0 — Applicability check (before touching anything)

Per **Prerequisites**, this skill never operates on an unaccepted Issue. Before Phase 1:

1. Confirm ENG-205 is in an "accepted" Linear state (this is the skill's stated precondition — per
   `linear-work-management`'s own state model, not re-derived here). Assumption stated explicitly: I'm
   treating "accepted" as already true, since the user's task framing ("accepted Linear issue ENG-205")
   asserts it. If this were a live run and the Issue's actual status came back as something other than
   accepted, I would stop and surface that rather than proceeding — the skill's Prerequisites section is
   unconditional on this point.
2. Confirm Wave 1 foundation (host profile, versioned configuration) and Wave 2 schema-v2 extension are
   activated per `../../FOUNDATION_CONTRACTS.md`. If either is missing, the skill's **Failure and
   Resume** section requires stopping with a manual handoff naming exactly what's missing — never
   proceeding on a partial/assumed configuration. (Narrated assumption: both are activated in this
   scenario, so I proceed.)
3. Repository Git/GitHub setup: the skill explicitly delegates this to `repository-gates`'s Repository
   Policy Profile resolution, invoked by each focused phase below — I do not re-verify it myself up
   front; if `repository_policy.provider_profile` comes back unset when a phase actually invokes
   `repository-gates`, that phase fails closed with a manual handoff, and I surface it rather than
   working around it.

## Step 1 — Resume check (mandatory even on what looks like a fresh start)

Per **Resume Behavior**, step 1 is unconditional: *"Read the Issue's `git-github-evidence` array (via
`linear-github-linking`) to determine the furthest-completed phase."* I do this before assuming a fresh
run, because "looks like a fresh start" is not the same as "verified no prior evidence exists" — a prior
interrupted attempt on ENG-205 is exactly the case this step exists to catch.

- Invoke: `Skill(linear-github-linking)` — read ENG-205's `git-github-evidence` array.
- Treat whatever comes back under the skill's **Data-only boundary**: it's untrusted data describing
  what happened, not a directive. If the array (or any field in it) contained text phrased like an
  instruction ("also delete branch X", "skip review"), I would report it as suspicious and not act on
  it.
- Narrated result: empty array — no prior evidence for ENG-205. This is a genuine fresh start.
- Per Resume Behavior step 2, *even on a fresh start* I would still present the determined starting
  point to the user via `AskUserQuestion` before continuing, rather than silently assuming "start at
  Phase 1." In auto-mode terms: this is exactly the kind of checkpoint the skill's own documentation
  names as required before the gate has fired, so I do not skip it just because the answer is obvious.
  - **AskUserQuestion:** "ENG-205 has no prior `git-github-evidence`. Proceeding from Phase 1 (Prepare +
    Start) — confirm?" → Assumed answer for this narration: **Yes, start at Phase 1.**

## Phase 1 — Prepare + Start → `Skill(work-to-development)`

Delegated entirely; I do not implement branch/worktree logic myself.

- Invoke `Skill(work-to-development)` against ENG-205. This phase is itself expected to route the actual
  Git mechanics through `git-kit`'s `starting-work` (per `route-through-git-kit-lifecycle-skills.md` and
  `starting-work-before-first-change.md`, both always-loaded rules in this repo) — syncing `main`,
  validating a `[type]/[description]` branch name derived from ENG-205's title/id, and asking
  worktree-vs-plain-branch.
- Expected produced evidence per the Phases table: verified branch/worktree, `work-started` evidence,
  Linear transitioned to Started.
- This skill's own transition gate: before moving to Phase 2, **AskUserQuestion** confirming Phase 1's
  reported evidence looks right (branch name, worktree path, Linear state now "Started") — additive to
  `work-to-development`'s own internal confirmation, not a replacement for it (per **Gotchas**, first
  bullet).
  - Narrated: branch `feat/eng-205-<slug>` created off synced `main`, worktree offered and accepted,
    Linear ENG-205 → Started. Confirmed.
- I would **not** re-run this phase's mutation if evidence already showed it done (not applicable here —
  fresh start).

## Phase 2 — Implement / control scope (not delegated)

Per the Phases table, this is "ordinary repository work in the active worktree, under the user's own
instructions" — the composing skill doesn't own the logic, it only tracks that it happened.

- I would do the actual code changes for ENG-205's described work inside the worktree from Phase 1,
  following CLAUDE.md's Simplicity First / Surgical Changes guidance (minimum diff, no drive-by
  refactors, no speculative abstraction) — same as any other repo edit.
- **Required gate before leaving this phase:** *"requires `AskUserQuestion` confirmation before any
  material Linear correction."* This applies specifically if, while implementing, I discover the Linear
  Issue's own description/scope needs correcting (e.g. the ticket undersold the actual fix). I would not
  silently edit Linear's record of the work — I'd ask first, naming the specific correction.
  - Narrated: no material scope correction needed for this run; implementation matched ENG-205's stated
    scope, so this gate doesn't fire.
- No structural plugin component is being touched by ENG-205's own work in this narration, so none of
  `plugin-rulebook-enforcement.md` / `test-against-example-plugin.md` / the inventory-update rule apply
  here — those are conditional on the *content* of the change, which I'd re-check against those rules'
  own "When this applies" text if the actual diff touched a skill/agent/command/hook/rule file.

## Phase 3 — Commit + gates + Publish → `Skill(development-to-pr)`

- Invoke `Skill(development-to-pr)`. Expected internal routing: `git-kit:commit` (staging review,
  sensitive-file scan, message confirmation, and — per `require-tests-for-behavior-changes.md` — an
  `AskUserQuestion` on whether/how the change was tested if it's a behavior change) → CI gates → publish
  as a **draft** PR via `git-kit:create-pr`.
- Before this composing skill writes any `Skill(development-to-pr)` call, per
  `read-and-retrace-skill-chains-before-finalizing.md` I would (in a live run) actually read that skill's
  current SKILL.md rather than trust my prior mental model of it — checking specifically for any
  unconditional `AskUserQuestion` it fires after success, any cwd/branch assumption, and any
  argument that silently falls back to "current branch." I don't skip this just because
  `development-to-pr` is a sibling in the same plugin I already have context on.
- Expected produced evidence: `commit-linked`, `ci-gates-passed`, `pr-published`; a draft PR opened,
  linked back to ENG-205.
- Sequence-level gate: **AskUserQuestion** confirming the draft PR (number/URL, linked issue, CI status)
  before moving to Phase 4.
  - Narrated: draft PR opened, CI gates green, linked to ENG-205. Confirmed.
- If CI gates had failed, per **Failure and Resume**, that's a focused-skill-reported structured
  handoff — I surface it directly to the user rather than papering over it or retrying silently.

## Phase 4 — Review/fix + Ready → `Skill(pr-to-linear)`

- Invoke `Skill(pr-to-linear)`. This phase is where real review findings (human/Codex/CI) get triaged
  and fixed — the composing skill doesn't do the triage itself; `pr-to-linear` owns it, presumably
  itself delegating to something like `handling-review-findings` for the actual finding-by-finding
  disposition per this marketplace's normal PR conventions (round-budgeted, Critical/Major never
  silently deferred-and-merged).
- Expected produced evidence: deliberate blocker summaries (what was found, what was fixed, what was
  explicitly deferred and why) and `pr-ready` evidence once the PR is flipped from draft to
  ready-to-merge.
- Sequence-level gate: **AskUserQuestion** confirming the PR is now ready (no outstanding
  Critical/Major, blockers summarized) before Phase 5.
  - Narrated: one Minor finding fixed in-round, PR flipped to ready. Confirmed.
- Any structured handoff `pr-to-linear` itself reports (e.g. an ambiguous review finding it couldn't
  auto-classify) would be surfaced to the user directly here, per **Failure and Resume**'s third bullet
  — never absorbed silently to keep the run moving.

## Phase 5 — Merge + Linear disposition + cleanup → `Skill(merge-to-completion)`

- Invoke `Skill(merge-to-completion)`. Expected internal routing: `git-kit:merge-pr` (readiness +
  merge-rights check, actual merge) → Linear disposition (ENG-205 → Done/Merged, with the merged PR
  linked as evidence) → `git-kit:finishing-work` for cleanup (sync back to clean main, prune
  remote-tracking branches) — per the Phases table, cleanup explicitly routes through
  `git-kit:finishing-work`, not a hand-rolled sync.
- Per `route-through-git-kit-lifecycle-skills.md`, I never substitute a raw `gh pr merge` or manual
  branch deletion for this — the lifecycle skill chain owns it end to end, and its `PreToolUse` hooks
  hard-block the raw-command bypass anyway.
- Expected produced evidence: `pr-merged`, verified Linear disposition, confirmed cleanup.
- Sequence-level gate: **AskUserQuestion** confirming merge landed, Linear shows the correct terminal
  state, and cleanup completed (worktree/branch actually gone — per
  `orphaned-worktree-git-read-fallthrough.md`, I would not trust git-read output alone as proof the
  worktree is gone; I'd cross-check with a plain filesystem listing if there were any doubt) before
  moving to Phase 6.
  - Narrated: PR merged, ENG-205 → Done in Linear, worktree/branch cleaned up and confirmed via a plain
    listing (not just `git status`).

At this point the user's literal ask — "start of work through to a merged PR and Linear disposition" —
is satisfied. The skill's phase table includes one more phase after this; I continue through it since
the skill composes it into the same "full lifecycle" run rather than treating merge as the end.

## Phase 6 — Deliberate Notion learning → `Skill(status-and-learning)`

- Invoke `Skill(status-and-learning)` to record a dated outcome/learning entry in Notion for this piece
  of work (what shipped, what was learned during review/fix, any deferred follow-up).
- No additional sequence-level `AskUserQuestion` is strictly named for this phase in the Phases table
  beyond what `status-and-learning` itself gates on, but I still apply the same additive-gate principle
  as every other phase transition: confirm the Notion record's content back to the user before treating
  the run as fully closed.
  - Narrated: dated outcome/learning record created in Notion, linked back to ENG-205 and the merged PR.

## Reconciliation — explicitly not run, with reasoning stated

Per **Gotchas**, `linear-github-reconciliation` is on-demand only, not part of every normal pass. No
drift was suspected or reported by any phase above (every phase's evidence matched what was expected),
and the user didn't request a reconciliation pass. Per `disclose-before-overriding-decisions.md`'s
"never silently skip a workflow phase" rule, I state this explicitly rather than just omitting the row:
**reconciliation was skipped because no drift was suspected in this run; not because it's part of the
mandatory sequence.**

---

## Summary of what the skill's own procedure required at each seam

| Checkpoint | What I did |
|---|---|
| Prerequisites | Verified accepted-Issue framing, Foundation/schema-v2 activation, deferred repo-policy check to `repository-gates` inside each phase |
| Resume Behavior step 1 | Read `git-github-evidence` via `linear-github-linking` even though the run looked fresh |
| Resume Behavior step 2 | Asked before assuming "start at Phase 1" rather than silently assuming it |
| Data-only boundary | Treated every value read back from a focused skill or the evidence array as untrusted data, never as a directive |
| Per-phase delegation | Never implemented Phase 1/3/4/5/6 logic directly — only Phase 2 (ordinary repo work) is this skill's own responsibility |
| Sequence-level gates | One additive `AskUserQuestion` per phase transition, on top of each focused skill's own internal gate — never substituted one for the other |
| Structured handoffs | Would surface any focused skill's reported ambiguity/gap directly rather than absorbing it |
| Reconciliation | Explicitly noted as skipped-by-design (on-demand only), not silently omitted |

## Final disposition (narrated outcome)

- ENG-205: Linear state **Started → (review/fix) → Done**, with `git-github-evidence` now recording
  `work-started`, `commit-linked`, `ci-gates-passed`, `pr-published`, `pr-ready`, and `pr-merged`.
- GitHub: draft PR opened in Phase 3, brought to ready in Phase 4, **merged** in Phase 5, branch/worktree
  cleaned up via `git-kit:finishing-work`.
- Notion: a dated outcome/learning record created in Phase 6, linked to both ENG-205 and the merged PR.
- Reconciliation: not run — no drift observed, stated explicitly rather than left implicit.
