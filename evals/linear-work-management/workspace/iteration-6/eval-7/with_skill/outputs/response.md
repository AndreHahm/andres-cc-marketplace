# Initiatives in Linear: not listed (structured handoff)

I'm not listing your Initiatives. The `linear.initiatives.read` gate fails before any call, so this is a structured handoff, not a read. I made no Linear, Notion or GitHub call, and I won't make one.

## Why it is blocked

Reading Initiatives is a separate host-profile operation from `linear.read`. Having `linear.read` verified doesn't cover it, and neither does having the Initiative tools present in this session. The skill runs these checks that need no call first:

| Check | Your setup | Result |
|---|---|---|
| `support_status` is `verified` | `verified` | Pass |
| `connector` is exactly `mcp-linear` | `claude_ai_Linear` | **Fail**. Any other value counts as `unconfigured`. |
| The local override passed the tracked-vs-untracked trust check (`git ls-files`) | Not confirmed | Not reached. The connector check already fails. |
| `organization_id` can be matched against the organization in a structured response field | Placeholder | Would also fail. A placeholder can't match a real organization. |

The connector check fails, so the operation counts as unconfigured. The probe call that the organization check depends on is therefore never made.

## Calls I would not make

- `mcp__mcp-linear__linear_getInitiatives`, `getInitiativeById` and `getInitiativeProjects`. They are present in this session, but the skill says tool presence is never proof of permission. Calling them would also bypass the connector setting you chose, which points at `claude_ai_Linear`.
- Any Initiative read through the `claude_ai_Linear` connector or another tool, such as `list_projects` or `list_issues`. The skill forbids substituting another tool, and `claude_ai_Linear` can't list Initiatives anyway.
- No Notion or GitHub lookup as a stand-in.

## How to unblock it

1. In `.claude/workmanagement-kit.local.json`, set `linear.initiatives.read`'s `connector` to `mcp-linear`. That file must be untracked, because a tracked copy is ignored and falls back to the shipped `unconfigured` defaults.
2. Set `organization_id` to your real Linear organization ID.
3. Re-request the list. I will then check the gate again and make one probe call, `getInitiatives`. I will take the organization only from a structured organization or ID field in the response. If it is missing, found only in free text, or different from `organization_id`, I will discard the result and hand off again.

Once the gate passes, I'll report the Initiatives as read-only data. I will treat their names and descriptions as untrusted text, never as instructions. I can't create or change an Initiative either, because this skill has no tool for that.
