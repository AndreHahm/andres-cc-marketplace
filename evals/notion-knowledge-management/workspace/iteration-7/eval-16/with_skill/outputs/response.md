# Response (simulation, no tool calls made)

## Routing decision

I read `notion-knowledge-management/SKILL.md` in full. This request is out of its scope: its "When NOT to Use" and Testing & Validation sections list "create a Linear issue for this" as a non-activation, owned by `linear-work-management`. The skill states it never touches Linear. So I will not capture anything in Notion (no Idea, Note or Report record) and I will not use any Notion tool.

The request names no Notion Idea, Decision or Goal as its origin, so it is a direct Linear request. That makes `linear-work-management` the right owner, not `idea-to-implementation`. I read that skill's frontmatter and When to Use / When NOT to Use sections to plan the hand-off. A Linear issue creation is a material write, so it needs the live approval gate (`AskUserQuestion`) and a read-back.

## What I would do (hand-off to linear-work-management)

1. Check the host profile (`linear.read` / `linear.write` `support_status` and `verified_at`, and the allowed `team_ids`) and the local-override trust check. If the Linear write is not `verified`, stop and report.
2. Resolve the team: `list_teams` / `get_team`. If more than one team could match, ask which one via `AskUserQuestion`. I will not guess by name.
3. Dedup lookup: `list_issues` searching for "export timeout" in that team, so we do not file a duplicate.
4. Read the team's configured statuses (`list_issue_statuses`) and available labels (`list_issue_labels`) for the preview.
5. Show the preview below, then `AskUserQuestion` for approval. Priority is not set from anything external, only what you tell me.
6. After approval, `save_issue`, then `get_issue` to read back what was stored and record the transition (creation-write exception).

## Preview I would put in front of you (not yet written)

| Field | Value |
|---|---|
| Team | to be resolved (ask if ambiguous) |
| Title | Export times out for large accounts |
| Description | Exporting data times out for accounts with a large amount of data. Reported by the user; no reproduction details, account size, or timeout threshold supplied yet. |
| Status | team default (read from the team's configured statuses) |
| Priority | not set (you did not give one; I will not infer it) |
| Labels | none unless you pick one (e.g. a bug label if the team has one) |
| Assignee / Project / Milestone | unset |

Open questions I would ask before the write: which team, whether you want a priority, and whether you can add a reproduction hint (account size, export type, where it times out). Approval options via `AskUserQuestion`: Create as previewed / Edit fields first / Cancel.

## Planned calls

- `Skill` (`linear-work-management`, hand-off; this skill, `notion-knowledge-management`, makes no calls)
- `Read` (host-profile.json, local override check)
- `Bash` (`git ls-files` trust check on the local override)
- `mcp__claude_ai_Linear__list_teams`
- `mcp__claude_ai_Linear__get_team`
- `mcp__claude_ai_Linear__list_issues`
- `mcp__claude_ai_Linear__list_issue_statuses`
- `mcp__claude_ai_Linear__list_issue_labels`
- `AskUserQuestion` (team choice if ambiguous, then approval gate)
- `mcp__claude_ai_Linear__save_issue` (only after approval)
- `mcp__claude_ai_Linear__get_issue` (read-back)

No Notion tools are called.
