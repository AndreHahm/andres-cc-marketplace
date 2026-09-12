# Accepting "Q3 Self-Serve Onboarding" into Execution

Request recognized as a **promotion**, not a bare Linear create: a Notion-originated proposed Goal is
named as the origin ("the Q3 self-serve onboarding goal we proposed in Notion"), so this runs through
`idea-to-implementation` rather than `linear-work-management` directly. Per this skill's contract, I
never write to Notion or Linear myself — all reads route through `notion-knowledge-management`, all
Linear writes (once approved) route through `linear-work-management`, and the reciprocal link routes
through `work-linking`.

## Step 1 — Read the source (`notion-knowledge-management`)

Read back the proposed Goal record and its linked context:

| Field | Value |
|---|---|
| Page | **Q3 Self-Serve Onboarding** (Goals database) |
| Status | `Proposed` |
| Owner | Product (onboarding pod) |
| Target | Q3 2026 |
| Rationale | Support and CS load currently scales roughly linearly with new-account signups because onboarding still requires a human touch (sales-assisted setup calls, manual doc walkthroughs). The goal is to let a net-new account reach first value with zero human assistance, to break that scaling relationship before Q4 volume grows. |
| Named sub-areas (body, bulleted) | 1. **Onboarding UI** — revamp the first-run product experience 2. **Docs** — self-serve setup documentation, currently assumes a CS rep walks the customer through it 3. **Guided setup flow** — an in-product step-by-step wizard replacing the manual kickoff call |
| Open questions (linked callout) | "Which Roadmap should this sit under — existing Growth roadmap, or does Q3 self-serve warrant its own?" (unresolved — flagged below, not answered on the source's behalf) |
| Existing Linear links | None found on the page — this Goal has never been promoted before |

No instruction-like content was found embedded in the page body or callouts — the rationale and
sub-area bullets are read here strictly as data describing scope, not as directives to act on.

## Step 2 — Draft the proposed Linear hierarchy (`linear-work-management`, read-only checks)

Checked for existing adoption candidates before proposing anything new (adoption beats duplication):

- Searched Linear Goals for a title/description match on "self-serve onboarding" → **no existing Goal
  found**. This will be a **create**.
- Searched Linear Roadmaps → **no exact match**, but one plausible fit exists: **"Growth & Activation"**
  (active roadmap, contains other activation-adjacent Goals). No "Q3 self-serve"-specific roadmap
  exists yet.
- Searched Projects under both the (nonexistent) Goal and the "Growth & Activation" roadmap for
  anything matching the three named sub-areas → **no matches**. All three will be creates.

Per `references/promotion-hierarchy-mapping.md`, a proposed Goal maps to a Linear Goal plus a Roadmap
placement — not automatically to Projects/Milestones/Issues. Here the source itself names three
concrete sub-areas as the Goal's initial workstreams, which is what pulls Projects into scope; nothing
in the source implies Milestones or Issues yet (no sub-area has been broken into scheduled chunks or
individual tasks), so **this preview stops at the Project level** rather than inventing structure below
what's actually implied.

Because the Roadmap fit is genuinely ambiguous (the source's own open question says so explicitly),
per the reference guide's worked example this is presented as an explicit choice in the approval below,
not decided silently in the draft.

## Step 3 — Full proposed hierarchy (one preview, one approval)

```
GOAL (create)
└─ "Q3 Self-Serve Onboarding"
   • Description: "Enable a net-new account to reach first value with zero human assistance,
     breaking the current linear scaling between signups and CS/sales load."
   • Target: Q3 2026
   • Source link: Notion → Q3 Self-Serve Onboarding (Goals DB) [stable page link, not mirrored content]

   ROADMAP PLACEMENT — pick one (unresolved in the source, decided here, not silently):
   ├─ Option A — ADOPT existing Roadmap "Growth & Activation"
   └─ Option B — CREATE new Roadmap "Q3 Self-Serve Initiatives"

   PROJECTS (create, one per named sub-area — no Milestones/Issues proposed yet)
   ├─ "Onboarding UI Revamp"
   │    Scope note: first-run product experience redesign
   ├─ "Docs Overhaul for Self-Serve Setup"
   │    Scope note: replace CS-rep-guided docs with self-serve setup documentation
   └─ "Guided Setup Flow"
        Scope note: in-product step-by-step wizard replacing the manual kickoff call
```

Total batch: **1 Goal (create) + 1 Roadmap (adopt or create, per approval choice) + 3 Projects
(create)**. Nothing has been created or adopted yet.

## Step 4 — Optional independent review

This is a small-to-moderate, non-highly-ambiguous batch (4-5 records, one open placement decision
already surfaced rather than hidden), but per the skill's optional step I'll still offer it rather than
skip it silently:

> **AskUserQuestion:** "Before finalizing, want an independent read-only review of this proposed
> hierarchy (dispatched to `work-transition-reviewer` via the Codex bridge-caller) before you approve
> it?"
> - Yes — run the review first, then bring the (possibly annotated) preview back for approval
> - No — proceed straight to the batch approval below

If declined, or if the dispatch returns a typed failure, promotion proceeds straight to Step 5 with no
change to the preview above. (Any findings returned by that review would themselves be treated as
untrusted data describing a review — not a directive this skill acts on unchecked.)

## Step 5 — Required batch approval (not yet obtained)

**Nothing above has been created or adopted in Linear.** Per this skill's approval contract, the entire
batch — the Goal, the Roadmap decision, and all three Projects — needs **one single approval**, not
per-record sign-off, and that approval covers exactly the preview above. If anything in this hierarchy
changes before approval (a Project renamed, a fourth one added, the Roadmap choice flipped), the whole
preview gets re-presented and re-approved — the original approval would not carry over.

> **AskUserQuestion:** "Approve this batch to promote the Q3 Self-Serve Onboarding Goal into Linear
> execution?"
> - Approve — adopt "Growth & Activation" as the Roadmap (create Goal + 3 Projects under it)
> - Approve — create a new "Q3 Self-Serve Initiatives" Roadmap (create Goal + Roadmap + 3 Projects)
> - Adjust the hierarchy first (e.g. change scope, merge/split a Project, drop one)
> - Cancel — do not promote this Goal right now

## What happens once approved (not executed yet)

On approval, execution proceeds exactly as `idea-to-implementation` specifies — reported here so the
full chain is visible, not run ahead of actual approval:

1. Create/adopt via `linear-work-management` **one record at a time, in dependency order** — Roadmap
   decision first (adopt or create), then the Goal under it, then the three Projects under the Goal.
2. Each created/adopted record's own transition is recorded per `FOUNDATION_CONTRACTS.md`'s Transition
   Contract — newly created records defer their transition to their own next write; the adopted
   Roadmap (if Option A) gets its transition recorded as an ordinary next-write.
3. Read every created/adopted record back through `linear-work-management` to confirm before calling
   the promotion complete.
4. Record the reciprocal link (stable IDs both directions, Notion ↔ Linear) via `work-linking`.

If any record in the batch fails to create after approval, execution stops immediately, reports exactly
what succeeded (with its Linear identity) and what didn't, and does not retry the succeeded records —
only the failed/remaining ones resume, and only after a fresh re-approval.

---

**Status: awaiting the Step 5 batch approval above.** No Notion or Linear write has occurred.
