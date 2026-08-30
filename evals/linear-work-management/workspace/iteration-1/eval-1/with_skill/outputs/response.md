# Creating a Linear Issue: CSV Export for Transition History

I followed `linear-work-management`'s Quick Start (resolve connector → resolve target by stable
ID → preview a write and get approval since it's material → write and read back → record the
transition), plus the Issue field table in `references/linear-entity-fields.md`. Two things
surfaced before I could actually execute the write, and I want to be upfront about both rather
than quietly working around them or quietly stopping.

## 1. Issue creation is a gated, approval-required action

Per the skill's Confirmation and Safety section, **any Roadmap/Project/Issue creation requires
approval** — not just "material" field changes. So even with everything else in place, I would
not create this Issue without an explicit go-ahead. Consider this section that ask:

**Proposed Issue**

| Field | Value |
|---|---|
| `title` | Add CSV export to transition history |
| `description` | Users can currently view an item's transition/status-change history in the UI but have no way to get it out of the product. Add a CSV export action for the transition history view so a user can download the full history (from-status, to-status, actor, timestamp for each transition) as a `.csv` file. Scope: export button on the existing transition-history view; no new history data needs to be captured, this only adds an export path for what's already tracked. |
| `status` | *Not set — see blocker below* |
| `owner` | *Unset (no owner specified by requester)* |
| `priority` | *Unset (no priority specified by requester)* |
| `labels` | *Unset — would suggest `feature`/`export` if the team's label set includes them, but not assumed* |
| `dependencies` | *None identified* |
| `cycle` | *Unset (not requested for a specific cycle)* |

I did not invent a priority, owner, or scope beyond "add CSV export to the transition history
feature" — the skill is explicit that priority/owner/scope must never be silently derived, even
from content that looks obviously right, without approval for that specific value.

## 2. The backing connector isn't wired up yet

The skill's own Quick Start note states plainly:

> The `mcp__workmanagement-kit__linear_read`/`linear_write` tools in this file's own
> `allowed-tools` have no backing MCP server configuration yet — that's pending Foundational
> Setup... This skill's design is otherwise complete and ready to wire up once that setup lands.

This skill's `allowed-tools` frontmatter scopes it to exactly those two tools (plus `Read`) — it
does not grant the general-purpose Linear connector tools that happen to be present in this
session (e.g. `mcp__claude_ai_Linear__save_issue`). Reaching for that connector instead would
sidestep the skill's own tool-scoping and its transition-recording/read-back contract, so I have
not done that.

Separately, resolving a real target team/status also requires a live connector call: `status` is
a **required** field on every Issue, but the skill's Gotchas explicitly warn against assuming a
generic status set exists — the actual configured workflow statuses have to be read from the
target team first. Without the connector wired, I can't do that lookup, so I can't propose a
concrete `status` value yet either.

## What I'd need to proceed

1. **Approval** on the drafted title/description above (and any owner/priority/labels/cycle you
   want added — I left them unset rather than guessing).
2. **Which team/project** this Issue should be created under, so I can resolve it by stable ID
   (per the skill, never by display name if more than one team/project could match) and read its
   actual configured statuses to pick a valid initial `status`.
3. **The Foundational Setup step** that wires the `linear_read`/`linear_write` MCP tools, since
   the skill cannot execute a write without them.

Once those are in place, the flow is: preview this exact Issue content against the resolved
team, get your approval, call `linear_write` to create it, read back the created record to
confirm it landed as previewed, and record the resulting transition (operation ID, transition
ID, the new Issue's stable ID, and the read-back evidence) per the skill's Read-Back and
Transitions section.

I'm stopping here rather than fabricating a team, a status, or pretending the write happened —
both would violate the skill's explicit approval gate and its "never assume success" rule.
