# Checking status of the "Q3 roadmap" project in Linear

I used the `linear-work-management` skill (this plugin's sole execution authority for Linear
Goals/Roadmaps/Projects/Milestones/Issues) to handle this. Per that skill, checking a project's
status is a **read/status-check operation, so it needs no approval** — but I hit a hard blocker
before I could actually run the read, and I want to surface that rather than fabricate a result.

## What the skill requires for this operation

1. **Resolve the connector** through the plugin's shared host profile — map the logical
   `linear.read` operation to the installed connector, active service identity, and approved
   organization/workspace/team/project scope. The skill is explicit that *tool presence is never
   proof of permission*, so this check has to happen even before touching any Linear data.
2. **Resolve the target entity by stable ID** — never by display name. "Q3 roadmap" is a display
   name, not a stable ID. If a lookup by that name returns more than one candidate (e.g. multiple
   teams or workspaces each with their own "Q3 roadmap"-named Project or Roadmap), the skill
   requires treating that as a structured handoff back to you rather than guessing which one you
   mean.
3. Since this is a pure status check (no field is being changed), no `AskUserQuestion` approval
   gate applies — the skill's Confirmation and Safety section lists "checking status" explicitly
   under "No approval needed."

## Why I can't return a live answer right now

This skill's own `SKILL.md` (Quick Start, step 1, and the paragraph right after it) discloses a
known gap: the `mcp__workmanagement-kit__linear_read` / `linear_write` tools declared in its
`allowed-tools` **have no backing MCP server configuration yet** — that wiring is pending
"Foundational Setup," per the plugin README's Status section. The skill's design is otherwise
complete, but there is currently no live connector for this plugin to call.

I did not substitute a different, unrelated Linear-capable tool to route around this (e.g. a
generic Linear MCP connector not declared in this skill's `allowed-tools`), because:

- This skill states plainly that it is "the only place that reads or writes" Goals/Roadmaps/
  Projects/Milestones/Issues — using a different, unvetted tool would bypass the host-profile
  scope check the skill requires before any read.
- "Tool presence is never proof of permission" — even if another Linear tool happens to be
  reachable in this environment, that doesn't mean it carries the same verified
  organization/workspace/team/project scope this skill's connector resolution step is supposed to
  confirm.

## What I can tell you right now

I can't report the Q3 roadmap Project's actual current status (its Linear `status`, target dates,
contained Milestones, etc.) because there is no live, scoped connector this skill is authorized to
call yet.

## What I'd need to actually complete this

- Confirmation that Foundational Setup has wired a real MCP server behind
  `mcp__workmanagement-kit__linear_read` (and the host profile's `linear.read` mapping), or
- The stable Linear ID of the specific Project you mean by "Q3 roadmap" (in case more than one
  workspace/team has a similarly-named Project or Roadmap, which the skill requires disambiguating
  by ID rather than name), so the read is ready to run the moment the connector is available.

No data was fabricated, and no write/approval flow was triggered, since this was a read-only status
check with nothing to preview or confirm.
