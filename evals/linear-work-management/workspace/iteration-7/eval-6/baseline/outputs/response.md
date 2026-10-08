# Linear Initiatives (simulated, no further real calls)

## Preconditions
- Host profile: linear.read and linear.initiatives.read are verified; connector is mcp-linear (the second Linear connector); organization_id is org-A.
- Local override passed the tracked-vs-untracked trust check, so it is honored.
- getInitiatives, getInitiativeById and getInitiativeProjects are present on mcp-linear.
- Org check: getInitiatives returned an organization field of org-A, which matches the profile. Safe to proceed. If it had differed, I would stop and report a mismatch.

## Initiatives in org-A (from getInitiatives)
| Initiative | Linked projects |
|---|---|
| Alpha | 3 |
| Beta | 1 |

Largest by linked-project count: **Alpha** (3 vs 1, no tie).

## Next calls (read-only, not executed)
1. mcp-linear getInitiativeProjects with Alpha's initiative id, to list its 3 projects. Paginate if needed.
2. Optionally getInitiativeById for Alpha, only if I need its description, status or owner. Not needed for the project list.
3. Check that the returned project count is 3 and that the organization is still org-A.

## What I would report
- The two Initiatives with counts, as in the table above.
- Alpha's 3 projects, each with name, status/state, lead and target date if returned.
- A note that "largest" means most linked projects, and that this is read-only: nothing was created or changed.
- Caveat: the project names are not known yet, because I have not made the getInitiativeProjects call. I will not invent them.
