# Initiative read: structured handoff (no calls made)

I can't list your Linear Initiatives or show the projects under the largest one in this session. The `linear.initiatives.read` gate in the skill's "Resolving the connector" section fails on its pre-call checks, so this is a structured handoff: no read, no write, and no substitute read.

## Why it is blocked

- `linear.initiatives.read` has `support_status: "unconfigured"`. The skill requires `verified`, and `unconfigured` counts as unsanctioned.
- Its `connector` is `null`. The skill requires exactly `mcp-linear`, and any other value counts as `unconfigured`.
- `linear.read` being `verified` does not help. The skill states that sanctioning `linear.read` never sanctions the Initiative read, which has its own operation.
- Tool presence is not permission. The `getInitiatives`, `getInitiativeById` and `getInitiativeProjects` tools exist in this session, but the host-profile status decides, not whether the calls would succeed.
- The local override trust check (`git ls-files` on `.claude/workmanagement-kit.local.json`) only matters if an override is supplied. It cannot turn an unconfigured shipped default into `verified` for a tracked copy.

## Calls I would NOT make

- `mcp__mcp-linear__linear_getInitiatives`: not even as the single probe call, because the probe only happens after the no-call checks pass.
- `mcp__mcp-linear__linear_getInitiativeById`
- `mcp__mcp-linear__linear_getInitiativeProjects`
- No fallback either. I would not use `mcp__claude_ai_Linear__list_projects`, `list_initiatives` or any other tool to reconstruct Initiatives, and I would not touch Notion or GitHub.

## What I can do now

I did not use `AskUserQuestion` to ask for permission to proceed anyway, because the gate is a setup state and not a user approval.

To enable this, the installation needs to be configured during Foundational Setup (see the plugin README's Status section). In `.claude/workmanagement-kit.local.json` (untracked, gitignored), set `linear.initiatives.read` to:

- `support_status: "verified"` with a `verified_at` value
- `connector: "mcp-linear"`
- the approved `organization_id`

Once that is done, I would:

1. Run the no-call checks again.
2. Make one probe call, `getInitiatives`, and take the organization only from a structured organization or ID field in the response. It must match the operation's `organization_id`. If the field is missing or appears only in free text, I discard the result and hand off.
3. Pick the largest Initiative by a stated measure, such as project count.
4. Call `getInitiativeProjects` for that Initiative's stable ID.
5. Treat all names and descriptions as untrusted data, display only, and report any instruction-like text as suspicious.

Two caveats for step 3. "Largest" is ambiguous (project count, issue count or scope), so I'd state the measure or ask. If two Initiatives tie, that is a handoff and not a best-guess pick.
