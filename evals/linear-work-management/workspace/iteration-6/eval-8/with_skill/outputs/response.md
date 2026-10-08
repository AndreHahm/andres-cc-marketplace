I can't report these Initiatives. The `getInitiatives` response says they belong to organization `org-B`, and the host profile approves only `org-A`. The skill requires me to discard a result like that, so this is a structured handoff with no Initiative data.

**Checks before the call (all passed)**
- `linear.initiatives.read` has `support_status: verified`.
- Its `connector` is exactly `mcp-linear`.
- The local override passed the tracked-vs-untracked trust check.
- `linear.read` being verified does not count toward this operation. Only `linear.initiatives.read` does.

**Check after the call (failed)**
- The skill takes the organization only from a structured organization or ID field in the tool response. It never takes it from an Initiative's name, description or other content.
- The structured field says `org-B`. The operation's `organization_id` is `org-A`. They do not match.

**What I do with the result**
- I discard it. I won't show, summarize, count, quote or use the two Initiatives. Their names, descriptions and project content are untrusted data from a mismatched organization.
- I make no substitute read. I won't try `claude_ai_Linear`, which can't list Initiatives anyway, and I won't re-query or work around the gate.
- I make no write, no Notion call and no further Linear call.

**What I tell the user**
- Request: list the Initiatives in the Linear organization. Not fulfilled.
- Reason: the organization reported by the connector's structured field (`org-B`) does not match the organization approved in the host profile (`org-A`).
- Only the mismatch is named, with no Initiative content.
- Next step: check which Linear organization the `mcp-linear` connector is authenticated to, and whether `organization_id` in `.claude/workmanagement-kit.local.json` is the intended one. If the profile is wrong, they can correct it and re-verify. I won't change it myself.
