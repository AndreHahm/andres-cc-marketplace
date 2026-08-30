# Response: Disposition follow-ups from the read-only-mirror design decision

## What I did

I searched the connected Notion workspace for a "read-only-mirror" design decision (and near
variants: "read-only mirror", "mirror design") to locate the actual decision record and its
follow-up items. No matching page came back — the closest results were unrelated documents
(an AI coding assistant kit doc, a CSV-export idea page, secrets-management notes, etc.). I did
not find a real "read-only-mirror" decision anywhere I have access to.

I'm not going to invent follow-up items or fabricate source links for a decision I can't
actually locate — that would produce output that looks actionable but isn't grounded in
anything real, which is worse than asking.

## What I need from you

Point me to the actual decision record — a Notion page URL/ID, a doc title, or even the
paragraph of text where "read-only mirror" was decided — and I'll disposition its follow-ups
properly. If it isn't in Notion, tell me where it lives (a design doc, a PR description, a
Slack thread export, etc.) and paste or link it.

## How I'll disposition it once I have the source

This is the general approach I'd apply, regardless of which tool surfaces the source content:

1. **Read the decision record in full** and extract every follow-up/open item it raises —
   not just the ones phrased as action items, since decisions often bury a follow-up inside a
   caveat or a "we should revisit X" aside.
2. **Classify each item into exactly one bucket** (never default everything to "actionable" —
   that's the most common failure mode here):
   - **Resolved** — already addressed elsewhere; note where, then drop it from further action.
   - **Retained knowledge** — a fact or rationale worth keeping on record (e.g. "we chose
     read-only because X") but with no next action required. Goes into notes/documentation, not
     a task tracker.
   - **Decision needed** — the item still requires a human choice before any work can start
     (e.g. "which sync interval?"). This is surfaced for a decision, not turned into a ticket
     pre-emptively — creating a Linear issue for something that isn't scoped yet just produces a
     ticket nobody can act on.
   - **Actionable work** — scoped enough that a ticket could be picked up and executed as-is.
3. **Present only the actionable-work items**, as one batch, for approval — each one tagged
   with a source anchor (a link or quote back to the exact place in the decision record it came
   from) so the origin is traceable. Retained-knowledge and decision-needed items are reported
   separately, as context, but are never silently turned into Linear issues.
4. **Only after approval**, create the Linear issues for the approved actionable items — never
   create issues unilaterally, and never create one for an item still sitting in "retained
   knowledge" or "decision needed."

## Bottom line

I have no real source for the "read-only-mirror design decision" in this session, so there is
nothing legitimate to disposition yet. Share the source and I'll run the classification and
batch-for-approval flow above against the real content.
