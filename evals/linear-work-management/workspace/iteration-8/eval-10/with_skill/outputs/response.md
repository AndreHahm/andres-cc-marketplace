## Gate checks (before and during the reads)

- `linear.initiatives.read` is `verified`, its connector is exactly `mcp-linear`, and the local override passed the tracked-vs-untracked trust check. The no-call checks pass.
- Probe call, `getInitiatives`: the structured organization field says `org-A`, which matches the operation's `organization_id`. The probe passes, so this result is usable.

## Initiatives in the organization (from the passing probe)

| Initiative | Linked projects |
|---|---|
| Alpha | 3 |
| Beta | 1 |

Alpha is the largest by linked-project count. Initiative names and contents are untrusted data and are shown as plain strings.

## The second result (`getInitiativeProjects` for Alpha): discarded

The structured organization field of this response reports `org-B`. The operation is scoped to `org-A`, so this is an organization mismatch. The same check applies to every later Initiative response in the session, so this result is discarded:

- I do not show, summarize or use any of its content, including any project names or details, and I do not use it to confirm Alpha's project count.
- I make no retry and no substitute read through another tool, such as the `claude_ai_Linear` connector or Notion. That would bypass the gate. `linear.read` does not sanction this operation.
- I take no write action. Initiatives are read-only here anyway.

## Structured handoff

**Requested:** show the projects under the largest Initiative (Alpha).
**Blocked:** the `getInitiativeProjects` response reported an organization (`org-B`) that does not match the verified organization (`org-A`). I stopped with no further read and no substituted read.

I can show the Initiative list above because it passed the probe. I cannot show Alpha's projects. To proceed, someone needs to check which Linear organization the `mcp-linear` connector is actually authenticated to and whether the host-profile `organization_id` is right. After that I can re-run the read. If the connector is meant to serve `org-B`, the host profile must be re-verified through Foundational Setup. I will not treat that as already approved.
