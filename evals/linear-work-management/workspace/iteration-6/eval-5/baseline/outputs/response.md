# Simulated run: list Linear Initiatives and show projects under the largest

No real tool calls were made. This describes what I would do.

## Plan and calls

1. `mcp-linear getInitiatives` (no filters, paginate until exhausted) to list every Initiative in the organization (name, id, status, owner, target date).
2. Decide "largest". The request is ambiguous, so I would state my assumption: largest = the Initiative with the most linked projects. To measure that, I would call `getInitiativeProjects` for each Initiative (or use a project count if `getInitiatives` returns one). If the user meant issue count or scope, I would say so and offer to recompute.
3. `getInitiativeById` for the chosen Initiative, for its description and health.
4. `getInitiativeProjects` for the chosen Initiative, to show its projects (name, state, lead, progress, target date).

All of these are read-only. I would write nothing to Linear, Notion or GitHub.

## Setup caveat

The host profile has `linear.read` verified, but `linear.initiatives.read` is unconfigured with connector null. The three initiative tools are present in this session, so I would use them. I would tell the user that the Initiative read capability is not formally configured or verified in the profile, so results come from the raw MCP tools and have not been checked against the profile. I would suggest configuring `linear.initiatives.read`.

## Output (illustrative shape only, no real data fetched)

| Initiative | Status | Owner | Projects |
|---|---|---|---|
| (from getInitiatives) | ... | ... | N |

Largest Initiative: (name, by project count)

| Project | State | Lead | Progress | Target |
|---|---|---|---|---|
| (from getInitiativeProjects) | ... | ... | ... | ... |

Because nothing was fetched, no actual Initiative names or counts are reported.
