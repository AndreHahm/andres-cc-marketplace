# Recording a Decision — promptlibrary-kit In-Repo Copy Design

Following `notion-knowledge-management` (this plugin's sole authority for Decision records), here's
what capturing this as a Decision looks like, and what's actually blocking the write.

## Step 1 — Resolve the connector

Per the skill's "Resolving the connector" section, every read/write must go through the plugin's
shared host profile (`notion.read`/`notion.write` mapped to an installed connector, service identity,
and approved workspace/database scope) — never assumed from tool presence alone.

**Result: blocked.** This skill's own `allowed-tools`
(`mcp__workmanagement-kit__notion_read`/`notion_write`) have **no backing MCP server configuration
yet** — that's pending this plugin's Foundational Setup (connector installation, workspace/database
scoping), per the plugin README's Status section. The skill's design is otherwise complete.

Note: a generic Notion MCP connector happens to be available in this session
(`mcp__claude_ai_Notion__*`). I'm deliberately not substituting it here — per the skill's own
warning, "tool presence in this session is never proof of permission or scope," and using an
unscoped, unrelated connector would bypass the host profile's workspace/database approval boundary
entirely. So this write cannot be persisted right now; what follows is the record built and
previewed as the skill prescribes, ready to file the moment Foundational Setup lands.

## Step 2 — Build the Decision record

Per `references/notion-record-types.md`'s Decision property table:

| Property | Value |
|---|---|
| `title` | promptlibrary-kit in-repo copy: read-only mirror, not dual-write |
| `context` | promptlibrary-kit needs an in-repo copy of prompt-library content alongside its source of truth. Two designs were on the table for how that copy stays current. |
| `alternatives` | (1) **Read-only mirror** — the in-repo copy is a one-way sync target; all edits happen at the source of truth and flow down. (2) **Dual-write** — both the source of truth and the in-repo copy accept writes directly, requiring reconciliation/conflict-resolution logic between them. |
| `consequences` | Chosen: read-only mirror. One authoritative write path, no divergence/merge-conflict risk between two writable copies, simpler sync logic (pull-and-overwrite rather than bidirectional reconciliation). Tradeoff accepted: the in-repo copy can only be updated by re-syncing from source, never edited in place. |
| `decision-state` | `accepted` — the request states this as a settled choice ("we're going with X"), not a proposal for later review. |
| `related-artifact` | — none supplied |
| `supersedes` / `superseded-by` | — none (first Decision record for this topic) |

Shared fields: `source` = user request (this conversation); `authority` = `notion`; `owner`,
`date`, `transition-id` — populated at actual write time, not fabricated here.

## Step 3 — Approval gate

Per the Decision State Machine, recording a Decision as `accepted` (as opposed to `proposed`)
**requires the plugin's live approval gate** — it's a consequential state, not passive knowledge
capture. I'm treating "we're going with the read-only mirror design... not dual-write" as your
approval of the decision *content and outcome* itself, but the gate here is procedural per the
skill's own design, not optional to skip silently:

**Confirming before this would be written:** record this Decision as `accepted`, with the content
above, once the Notion connector is actually wired up? (No action needed today, since the write is
mechanically blocked — flagging so approval is on record for whenever Foundational Setup completes.)

## Step 4 — Read-back and transition (not yet applicable)

Once the connector is live, the skill requires reading back what was actually stored (never
assuming success from a clean-looking call) and recording the transition (operation ID,
transition ID, affected record, verification evidence) through the plugin's shared transition
contract. Neither can happen yet since no write has occurred.

## Summary

- The Decision record is fully drafted and ready (table above).
- It cannot be persisted to Notion yet — `notion-knowledge-management`'s connector has no backing
  MCP server configuration until this plugin's Foundational Setup step lands.
- When that setup completes, this same content (state `accepted`) is ready to file, pending your
  confirmation on the approval gate noted in Step 3.
