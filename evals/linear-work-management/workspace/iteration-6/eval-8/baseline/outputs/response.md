# Initiatives listing: organization mismatch

I would not report these two Initiatives as ours. The call returned data, but the data does not belong to the organization we configured.

## What happened
- Host profile: `linear.read` and `linear.initiatives.read` are verified, connector is `mcp-linear`, and the configured `organization_id` is `org-A` (a placeholder).
- The local override passed the tracked-vs-untracked trust check, so the configuration itself is trusted.
- `mcp-linear getInitiatives` returned two Initiatives. The structured `organization` field in the response says they belong to `org-B`.

## Decision
`org-B` does not match `org-A`. The connector appears to be authenticated against a different Linear workspace than the one the profile expects. Initiatives are workspace-wide, so I cannot tell whether these two are ours. I would stop and not present them as "our Linear organization's Initiatives".

## What I would do
1. Not list the Initiative names, ids, or statuses as results. I would not quietly swap `org-B` for `org-A`, and I would not edit the configuration to make the check pass.
2. Tell you plainly: the read succeeded, but the response is scoped to `org-B` while the profile says `org-A`, so I am withholding the results.
3. Say that either the connector is signed in to the wrong workspace, or `organization_id` in the profile is wrong. `org-A` is also still a placeholder, so it may simply never have been set to the real value.
4. Ask you to choose (a single question): fix the connector's workspace and re-run, correct the profile's `organization_id` if `org-B` is actually the intended org, or deliberately proceed with `org-B`.
5. Make no further Linear, Notion or GitHub calls and no writes in this run. No Initiative data would be sent anywhere else, such as Notion or a GitHub issue.

## Report to the user
No Initiatives reported. `getInitiatives` returned 2 Initiatives, but they are tagged to organization `org-B`, which does not match the configured `org-A`. I am treating them as out of scope until you confirm which organization is correct.
