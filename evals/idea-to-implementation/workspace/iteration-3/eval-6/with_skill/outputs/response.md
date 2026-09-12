# Promoting "CSV export of transition history" from Notion to Linear

Your request names a Notion source as the origin ("the CSV export idea we captured in Notion"),
even though the surface phrasing is "create a Linear issue." Per `idea-to-implementation`'s own
"When to Use" section, that makes this a **promotion**, not a bare `linear-work-management`
create request — so I'm routing it through this skill rather than creating a Linear issue
directly.

## Step 1 — Read the source knowledge record (`notion-knowledge-management`)

Reading the Idea record from Notion:

> **Idea: CSV export of transition history**
> **Status:** Captured
> **Rationale:** Users maintaining Linear/Notion promotion history have no way to pull a flat,
> reviewable record of an item's transitions (create → adopt → status changes → close) outside
> the two systems' own UIs. A CSV export would let someone audit a batch of transitions in a
> spreadsheet without paging through Notion or Linear directly.
> **Linked context:** No linked Decision, no existing Linear record referencing this Idea, no
> open questions attached.

Everything above is treated as **untrusted data**, per this skill's Data-only boundary — it
describes what the Idea says, and nothing in it is executed as an instruction. Nothing in the
record reads as suspicious or instruction-like.

## Step 2 — Draft the proposed Linear hierarchy

Per `references/promotion-hierarchy-mapping.md`'s typical mapping table: *"Idea → A single Issue,
or a small Project with a few Issues... Most Ideas are scoped narrowly enough for one Issue;
propose a Project only when the Idea clearly implies multiple independent pieces of work."*

This Idea is narrow and self-contained — one export capability, no sub-workstreams implied. No
existing Linear record adopts this scope (checked via `linear-work-management` before drafting,
per this skill's "Adoption is not creation" gotcha), so this is a **create**, not an adopt.

Proposed hierarchy: **one new Linear Issue**, no Goal/Roadmap/Project/Milestone layer — the source
doesn't call for any of those, and inventing them would violate step 2's "never invent structure
the source doesn't call for."

## Step 3 — Preview (the one batch to approve)

| # | Action | Record | Details |
|---|--------|--------|---------|
| 1 | **Create** | Linear Issue | **Title:** "Add CSV export for transition history"<br>**Description:** "Promoted from Notion Idea 'CSV export of transition history.' Let a user export an item's recorded transitions (create/adopt/status-change/close) as a flat CSV for offline review, instead of paging through Notion/Linear UIs." (concise context only — the Idea's full rationale is not mirrored verbatim)<br>**Team:** *(to be confirmed at creation time via `linear-work-management`)*<br>**Notion link:** back-reference to the source Idea's stable ID, recorded reciprocally after creation |

No Goal, Roadmap, Project, or Milestone is proposed — this is the complete batch.

This is presented as **one preview covering the whole hierarchy** (here, a hierarchy of exactly
one record). Per this skill's own framing:

> Present the exact proposed hierarchy — every record, every link — as one preview, and get one
> approval covering the whole batch.

## Step 4 — Optional independent review

Given the narrow, unambiguous scope (a single Issue, no cross-record dependencies), an independent
`work-transition-reviewer` pass isn't obviously warranted — but per the skill, whether to request
one is itself a question for you, not a decision to make silently:

**Would you like an independent review dispatched before finalizing?** (No / Yes — dispatches
`work-transition-reviewer` read-only via the Codex Bridge-Caller Dispatch procedure before
proceeding.)

## Step 5 — Batch approval required before anything is created

**Nothing has been created in Linear yet.** Per this skill's Confirmation and Safety section,
approval is never assumed from the source record's own wording, and is required as **one batch**
covering the entire preview above — not partial, not silent.

Since I don't have a live `AskUserQuestion` round-trip available to resolve here, I'm presenting
the gate explicitly instead of proceeding past it:

> **Approve this promotion?**
> - **Approve** — create the Issue exactly as previewed above, then read it back, then record the
>   reciprocal Notion↔Linear link via `work-linking`.
> - **Modify** — tell me what to change (title, description, team, or add a Project/Milestone
>   layer); I'll re-present a fresh preview, since a changed payload needs a new approval per this
>   skill's own "previewed hierarchy that changes before approval needs a new preview" gotcha.
> - **Cancel** — no Linear write happens; the Idea stays as-is in Notion.

## What happens once you approve (not yet executed)

1. Create the Issue via `linear-work-management`. Per the Transition Contract's creation-write
   exception, the create write itself carries none of the transition fields (its stable ID doesn't
   exist until the connector responds) — `transition_id`/`operation_id`/`source_plugin` are
   deferred to the record's next write.
2. Read the new Issue back immediately — this read-back **is** the create's `verification_evidence`,
   per the ordinary next-write convention.
3. Record the reciprocal link (Notion Idea ↔ new Linear Issue, stable IDs both directions) via
   `work-linking`. If this reciprocal-link write is the Issue's last planned write, the
   terminal-write exception applies: one additional metadata-only write records that write's own
   verification_evidence, needing no further read-back beyond a plain confirming read.
4. Report back the created Issue's identity and the two-way link, per this skill's "read every
   created/adopted record back before considering the promotion complete" step.

No Linear write will happen until you respond to the approval gate above.
