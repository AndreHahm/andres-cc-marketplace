Baseline = the SKILL.md as it stood at commit 47716a6f (before the verified_at fix).

Result: under the gate as then written, one probe call is made.

- `support_status` is verified, `connector` is exactly mcp-linear and the trust check passed, so the gate's three listed conditions hold.
- `verified_at` is null. The gate lists only those three conditions and does not make a non-null `verified_at` a blocker, so it is noted only as a loose end (marked verified but no verification timestamp).
- Would make one `mcp__mcp-linear__linear_getInitiatives` call (read-only, no approval needed), then check the structured organization field against org-A. If it matches, list the Initiatives; otherwise discard and hand off.
- getInitiativeById / getInitiativeProjects only on a follow-up request. No Notion or GitHub call, no write path.

(Subagent report, recorded in substance.)
