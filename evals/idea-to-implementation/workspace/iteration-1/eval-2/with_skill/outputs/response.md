# Promoting the accepted decision: "read-only mirror design for promptlibrary-kit"

I used `idea-to-implementation` (workmanagement-kit) for this, since the request is exactly its
trigger case — "turn this accepted decision into tracked work." Per that skill, this is a
deliberate, approval-gated bridge from Notion (knowledge authority) into Linear (execution
authority); it never writes to either system directly, and it never runs automatically just
because a Decision looks accepted.

## Step 1 — Read the source Decision (blocked, disclosed)

The skill's first step is to read the accepted Decision record via `notion-knowledge-management`,
plus any linked context (open questions, dependencies, readiness notes), before drafting anything.

I attempted this and hit a real blocker, not a guess I'm routing around:

- `notion-knowledge-management`'s own `mcp__workmanagement-kit__notion_read` tool has **no backing
  MCP server configured yet** — the plugin README's Status section confirms this is Wave 1 of a
  two-wave design, and live Notion/Linear mutation (and, in practice, live reads) require the
  Foundational Setup steps (connector installation, workspace/team scoping) that haven't landed.
- So I cannot actually fetch the Decision's stored rationale, its linked open questions, or
  whether it references any prior design work for `promptlibrary-kit` that this one might
  supersede.

Per the skill's own data-only-boundary and no-guessing gotchas ("ambiguous target = stop, don't
guess"), I'm not fabricating that content. Everything below is built only from what's in your
request ("adopt the read-only mirror design for promptlibrary-kit"), clearly marked provisional,
and gated on your confirmation before anything is created.

## Step 2 — Draft proposed hierarchy (provisional)

Per `references/promotion-hierarchy-mapping.md`'s typical mapping table:

| Notion source | Typical Linear target |
|---|---|
| Accepted Decision | Usually a single Issue (the decision's follow-through action) |

A Decision that itself doesn't imply new work produces no promotion at all — but "adopt the
read-only mirror design" reads as an implementation commitment, so the default mapping is **one
Linear Issue**, not a Goal/Roadmap/Project/Milestone structure. I'm not proposing anything heavier
than that unless you tell me the decision implies multiple independent pieces of work.

**Proposed batch (draft, not yet created):**

- **New Linear Issue** — "Adopt read-only mirror design for promptlibrary-kit" — the decision's
  follow-through action. Needs from you: which Team/Project this should live under (I won't guess
  from a display-name match if `promptlibrary-kit` maps to more than one Linear Project).
- **Reciprocal link** — Decision record ↔ new Issue, via `work-linking`, recorded after the Issue
  exists and is read back.

**One thing worth checking before this goes further** — the reference file's own worked example
for exactly this shape: *"A Decision that supersedes an already-promoted Idea's Linear work... the
promotion preview must show the existing linked work and ask explicitly whether to close/cancel
it."* If `promptlibrary-kit` already has a prior design decision promoted to Linear (e.g. an
earlier read-write or bidirectional-sync mirror design), adopting the read-only design likely
supersedes it. I don't have Notion/Linear read access to check this myself right now — can you
confirm whether prior linked work exists, so the preview can include it rather than leaving it
running alongside the new Issue?

## What happens next

- **No Linear or Notion write has been made.** Per the skill's Confirmation and Safety section,
  the full batch above needs your approval as one preview before anything is created — a partial
  approval isn't accepted, and I won't create the Issue and then separately ask about linking.
- **Even with approval, execution is currently blocked at the tool layer**, independent of your
  answer — both `notion-knowledge-management` and `linear-work-management`'s connector tools have
  no backing MCP server yet (Wave 1 scaffold status). Once Foundational Setup completes, the same
  approved preview can be executed without re-deriving it.
- To move this forward now, the fastest path is either: (a) point me at the actual Decision record
  (or paste its rationale/open questions) so Step 1 can be done for real once reads are wired up,
  or (b) confirm/correct the provisional single-Issue draft above (target Team/Project, and whether
  prior `promptlibrary-kit` design work needs to be superseded) so the exact batch is ready to fire
  the moment the connector is live.

I have not invented any hierarchy level beyond the single Issue the Decision plausibly implies,
and I have not treated the request's own wording as authorization to create anything — per the
skill, that's never inferred from how "obviously accepted" a decision reads.
