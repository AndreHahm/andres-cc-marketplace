# Drift Check: CSV Export Work (Notion ↔ Linear)

## Result: Cannot run — reporting as a structured handoff, not resolving silently

I used the `work-linking` skill to handle this request, but the check itself can't be executed
right now. Here's why, and what it would take to unblock it.

## Why the check can't run

`work-linking` has no Notion/Linear connector access of its own. Per its own instructions, every
read of either system's current state has to go through `notion-knowledge-management` (Notion) or
`linear-work-management` (Linear) — it never calls a connector directly.

I checked both of those skills, and both are explicit that their backing connectors aren't wired
up yet:

- `notion-knowledge-management`: "The `mcp__workmanagement-kit__notion_read`/`notion_write` tools
  in this file's own `allowed-tools` have no backing MCP server configuration yet — that's pending
  Foundational Setup (connector installation, workspace/database scoping)."
- `linear-work-management`: "The `mcp__workmanagement-kit__linear_read`/`linear_write` tools ...
  have no backing MCP server configuration yet — that's pending Foundational Setup."

The plugin's own README confirms this at the plugin level: this is Wave 1, and "Live Notion/Linear
mutation requires the Foundational Setup steps described in this plugin's design documents to be
completed (connector installation, workspace/team scoping, test scopes) before first live use." The
same setup gap blocks reads, not just writes — there's no configured, approved workspace/database
or organization/team scope for either skill to resolve `notion.read`/`linear.read` against yet.

Both skills also state plainly: **"Tool presence in this session is never proof of permission or
scope."** This session does have generic Notion and Linear MCP tools available
(`mcp__claude_ai_Notion__*`, `mcp__claude_ai_Linear__*`), but those are not the
`mcp__workmanagement-kit__notion_read/write` / `linear_read/write` tools these skills are scoped
to, and using them instead would bypass the plugin's own host-profile resolution and approved-scope
check — exactly the shortcut both skills warn against. I did not substitute them.

## Classification

Per `work-linking`'s Drift Classification table, this is **Unknown** — insufficient evidence to
classify, reported rather than guessed. I have no fresh read of Notion's side of "CSV export work,"
no fresh read of Linear's side, and no way to confirm whether a link even exists between them yet
(link creation/lookup goes through the same two blocked skills).

## What would unblock this

1. Complete Foundational Setup for `workmanagement-kit`: install/configure the
   `mcp__workmanagement-kit__notion_read`/`notion_write` and `linear_read`/`linear_write` connector
   backends, and scope them to the approved Notion workspace/database and Linear
   organization/team/project.
2. Once that's live, re-run this same request. `work-linking` will then:
   - Read the recorded link for "CSV export work" (if one exists) via
     `notion-knowledge-management` and `linear-work-management`.
   - Compare the linked Notion record's state against a fresh Linear read.
   - Classify the result as exactly one of: Consistent, Stale summary, Broken link, Conflicting
     authority, Partial result, or Unknown.
   - If it's a `Broken link`, re-resolve by stable ID within the owning system before concluding a
     record was actually deleted (a moved Linear Issue can look broken without being gone).
   - Repair only the non-authoritative side if something needs fixing — never by newest timestamp,
     and never in a way that would re-drift the just-repaired side on the next check.
3. If no link record exists at all for "CSV export work," that's also worth surfacing once reads
   are possible — it may mean the work was never linked, not just that it drifted.

## No approval needed for this step

Running a drift check and classifying the result needs no approval per `work-linking`'s
Confirmation and Safety section — this response is a read-only status report, not a repair, so
nothing here required a live approval gate.
