# Task: Link the Notion idea to the Linear issue it became

## Skill used

`work-linking` (`plugins/workmanagement-kit/skills/work-linking/SKILL.md`), per its "Linking" and
"Repair" sections, which route every actual Notion/Linear read or write through
`notion-knowledge-management` / `linear-work-management` rather than calling either connector
directly.

## Records identified

No specific page/issue was named in the request, so I searched both systems for a matching
idea-to-issue pair rather than guessing.

- **Notion Idea:** "Idea: Export Transition History as CSV"
  `https://app.notion.com/p/3ccce0610b0c8187b6e0db08a5ee6a0a`
  Content: "Allow users to export their transition history as a CSV file." Status: *Idea — not yet
  prioritized or scoped.*

- **Linear Issue:** `AND-6` — "Export Transition History as CSV"
  `https://linear.app/example-workspace/issue/AND-6/export-transition-history-as-csv`
  Status: Backlog. Its description explicitly states: *"Originally captured in Notion:
  [https://app.notion.com/p/3ccce0610b0c8187b6e0db08a5ee6a0a]"* — the exact same page found above.

**Note on a second candidate:** the workspace also has `AND-5` ("Add CSV export to transition
history"), a more heavily scoped-out issue covering the same underlying feature. I ruled this out
as the link target because its title doesn't match the Notion idea and, unlike AND-6, its
description carries no back-reference to the Notion page at all. AND-6 is the one that is
demonstrably "the issue this idea became."

## Drift classification

Per the skill's six-state table, this is **Partial result**: a prior operation (whoever created
AND-6) captured a one-way, plain-text mention of the Notion URL inside the issue's description, but:

- Linear's own structured link surfaces are empty — `get_issue` on AND-6 shows `"attachments": []`
  and `"relations": {"relatedTo": []}` — there is no stable-ID attachment/relation object, just prose.
- The Notion page carries no reference back to AND-6 at all (no `related-record`-style property, no
  mention in its content).

So neither side has a stable, structured, bidirectional link recorded yet — only an informal,
one-directional text mention.

## Repair / what's needed to actually complete the link

Recording a stable link on both sides is a bare link/reference-field change (not a change to either
system's authoritative execution/knowledge content), so under `work-linking`'s Confirmation and
Safety rules it doesn't need the full material-change approval gate — but it still has to be written
by the plugin's owning skill, not by me calling a connector directly:

- **Notion side** (`notion-knowledge-management` owns this): set the Idea record's `related-record`
  property to point at `AND-6` / its URL, per `references/notion-record-types.md`'s property table,
  then record the transition.
- **Linear side** (`linear-work-management` owns this): the existing plain-text mention in AND-6's
  description isn't a substitute for a real link field — per `references/linear-entity-fields.md`
  Issues carry a "Notion links" field distinct from free-text description content. That field should
  be set to the Notion page URL, then read back and the transition recorded.

## Why I'm stopping here instead of writing the link myself

I read both companion skills' current `SKILL.md` files directly (since this plugin's own skills
aren't registered in this session and `Skill()` can't dispatch them). Both state plainly that this
plugin is mid-scaffold:

> "The `mcp__workmanagement-kit__notion_read`/`notion_write` tools ... have no backing MCP server
> configuration yet — that's pending Foundational Setup ... This skill's design is otherwise
> complete and ready to wire up once that setup lands."

The same statement appears in `linear-work-management` for `linear_read`/`linear_write`. This
session does have a separate, unrelated set of live Notion/Linear MCP tools (`mcp__claude_ai_Notion__*`,
`mcp__claude_ai_Linear__*`) — I used those in read-only mode above purely to identify the correct
records, since `work-linking` itself has no search capability of its own. But using them to *write*
the link would bypass the plugin's intended design entirely: the host-profile scope check, the
record-type/field-schema validation in each companion skill's `references/`, the approval gate, and
the read-back-then-record-transition contract that both skills require for every write. `work-linking`
is explicit that it "never calls a connector directly," and I'm treating the generic session
connectors the same way — silently writing through them would look like a completed link while
actually skipping every safeguard the plugin's design puts around that write.

**Structured handoff:** the correct pairing is identified and verified (Notion idea
`3ccce061-0b0c-8187-b6e0-db08a5ee6a0a` ↔ Linear issue `AND-6`), and the drift is classified as
*Partial result*. Completing the actual link write is blocked on this plugin's Foundational Setup
(the `notion_read/write` and `linear_read/write` connector wiring) landing first — once that's in
place, re-run `work-linking` (or invoke `notion-knowledge-management`/`linear-work-management`
directly) to set the `related-record` / "Notion links" fields on both sides.
