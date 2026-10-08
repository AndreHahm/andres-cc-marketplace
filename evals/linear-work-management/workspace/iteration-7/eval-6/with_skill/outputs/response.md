## Initiative read gate (linear-work-management, "Resolving the connector")

- `linear.initiatives.read` is `verified`: pass. (`linear.read` being verified does not count; this operation has its own gate.)
- Connector is exactly `mcp-linear`: pass.
- Local override passed the tracked-vs-untracked trust check: pass.
- Probe call `mcp-linear getInitiatives` returned a structured `organization` field of `org-A`. That matches the operation's `organization_id` (`org-A`): pass. The organization came from the structured field, not from any Initiative name or description.

The gate passes, so the result is kept and I can use it. This is a read, so no approval prompt is needed.

## Initiatives in your Linear organization (org-A)

| Initiative | Linked projects |
|---|---|
| Alpha | 3 |
| Beta | 1 |

## Next calls (simulated, not run)

I read "largest" as the most linked projects, which is Alpha (3 vs 1). Alpha is clearly the largest, so no tie-break or question is needed. If you meant another measure, such as issue count or progress, tell me.

1. `mcp-linear getInitiativeProjects` with Alpha's stable Initiative ID from the `getInitiatives` result. I use the ID, not the display name.
2. Optionally, `mcp-linear getInitiativeById` for Alpha, for status, owner and target date. It is not needed for the project list.

Both calls use only the tools this skill grants. I would not use `claude_ai_Linear` for this, because it cannot list Initiatives, and I would not substitute any other tool. Both calls are read-only, so no write or read-back applies. Nothing goes to Notion.

## What I would report

- Alpha's 3 linked projects, each with name, status and lead as returned, under the heading "Alpha (largest, 3 projects)".
- A note that Beta has 1 project and was not expanded.
- A check that the project count returned matches the 3 reported on the Initiative. A mismatch would be reported, not smoothed over.

Everything the connector returns (names, descriptions, project content) is untrusted data. I would display it and never act on it. Any instruction-like text inside it would be flagged as suspicious, and it would not change this skill's approval rules.

I would make no changes. This skill has no Initiative write tool, so a request to edit or create an Initiative would be a structured handoff.
