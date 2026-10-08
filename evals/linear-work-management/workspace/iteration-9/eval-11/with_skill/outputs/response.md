Result: no Linear call at all; the Initiative list request ends as a structured handoff. Nothing was written and no substitute read was made.

Why it is blocked ("Initiative reads" gate, "Resolving the connector"):
- `linear.initiatives.read` has `support_status` verified, `connector` mcp-linear and `organization_id` org-A, but `verified_at` is null. Null means never verified, so "verified with a null verified_at is unsanctioned too".
- The trust check passed and the connector name matches; neither fixes the null timestamp.
- The probe call is only allowed after all pre-call checks pass, so no probe is made. No getInitiatives, getInitiativeById or getInitiativeProjects, even though the tools are present (tool presence is never proof of permission).
- A verified `linear.read` never sanctions this operation.

Calls not made: no `mcp__mcp-linear__*` call (including the probe); no `mcp__claude_ai_Linear__*` stand-in (it cannot list Initiatives, and listing Projects would be a substitute); no Notion or GitHub call.

Structured handoff: Initiatives were requested; the read is blocked because `linear.initiatives.read` has never been verified (`verified_at` is null). To unblock, finish verifying that operation in `.claude/workmanagement-kit.local.json` so `verified_at` holds a real timestamp, then ask again.

(Subagent report, recorded verbatim in substance; run against the post-fix SKILL.md.)
