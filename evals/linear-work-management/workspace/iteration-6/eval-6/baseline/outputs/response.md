# Linear Initiatives and the largest Initiative's projects (simulated)

Simulation only. No real Linear, Notion, GitHub or MCP call was made. Below is what I would call and what I would show.

## Assumptions
- Linear is read through the second Linear connector, `mcp-linear`. Both `linear.read` and `linear.initiatives.read` are verified in the host profile.
- `organization_id` is a placeholder. I would not pass it as a real filter. These tools act on the authenticated workspace, so I would omit it, or confirm the real value with the user first. I would also state that the result has not been checked against a specific organization.
- "Largest" is ambiguous. Linear has no single size field for an Initiative. I would define it as the Initiative with the most linked projects, and say so in the answer. Alternatives are issue count or total scope. If the counts tie or the user wants another measure, I would ask.
- All calls are read-only, so no write confirmation is needed.

## Planned calls

1. `mcp__mcp-linear__linear_getInitiatives` (no filter, paginated)
   - Follow pagination until it is exhausted.
   - Collect each Initiative's id, name, status, owner and target date.
2. For each Initiative, `mcp__mcp-linear__linear_getInitiativeProjects` with that `initiativeId`
   - This gives the project count per Initiative. I would run these in parallel.
   - Pick the Initiative with the most projects as the largest.
3. `mcp__mcp-linear__linear_getInitiativeById` for the winner, only if the list response lacks detail such as description or health.
4. Show the winner's projects from step 2. For each project: name, status, lead, target date, progress.

## Output format I would present

**Initiatives (N total)**

| Initiative | Status | Owner | Target date | Projects |
|---|---|---|---|---|
| (from getInitiatives) | | | | (count from getInitiativeProjects) |

**Largest by project count: `<Initiative name>`** (state the measure used)

| Project | Status | Lead | Target | Progress |
|---|---|---|---|---|
| (from getInitiativeProjects) | | | | |

## Caveats to report
- No data is shown here, because nothing was executed. The tables are templates.
- The size measure is my own choice. Tell me if you want issue count instead.
- `organization_id` is a placeholder, so I would confirm the workspace before treating results as authoritative.
- Archived or completed Initiatives may be excluded or included depending on connector defaults. I would state which.
- If a tool errors or is rate-limited, I would report that and not guess.
