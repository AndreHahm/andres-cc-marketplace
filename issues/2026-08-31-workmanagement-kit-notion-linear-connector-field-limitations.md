## Summary
Real Notion/Linear connectors reject or don't support parts of workmanagement-kit's documented record-field design, discovered live during Foundational Setup

## Environment
- **Product/Service**: `workmanagement-kit` plugin (`plugins/workmanagement-kit/`) — Notion connector (`claude_ai_Notion`) and Linear connector (`claude_ai_Linear`)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps

**Finding 1 — Notion `update-page` rejects a leading-`{` property value:**
1. Call the Notion `update-page` tool's `update_properties` command with a rich-text property value that itself starts with `{` (i.e. looks like JSON), e.g. `{"a":1}`.
2. Observe: `Invalid input validation error` — the write is rejected outright.
3. Re-encode the identical semantic content as flat text (no leading `{`), e.g. `transition_id=wmk-test-tx-001; operation_id=null; affected_record.system=notion; affected_record.stable_id=...; source_plugin=workmanagement-kit; verification_evidence=...; recorded_at=...`.
4. Observe: the write succeeds.

**Finding 2 — Linear connector has no generic custom-field mechanism:**
1. Call the Linear `save_issue` tool to create/update an Issue, attempting to set a field named e.g. `notion-link` or `open-item-source` as documented in `linear-entity-fields.md`.
2. Observe: `save_issue`'s schema exposes only Linear's native fields (title, description, state, labels, priority, links/attachments, estimate, cycle, etc.) — there is no generic custom-field parameter.
3. Confirm the workspace has no Linear custom fields configured (a paid Linear feature) that could be mapped to these names.

## Expected Behavior
`FOUNDATION_CONTRACTS.md`'s Transition Contract (and the Disposition Record it also defines) can be embedded directly as documented — "embedded as that record's own `transition-id`-tagged properties" — into a Notion rich-text property. Separately, `linear-entity-fields.md`'s documented Issue fields (`notion-link`, `disposition-history`, `open-item-source`, `transition-id`) should be settable as real, queryable fields on a Linear Issue via the connector.

## Actual Behavior
- Notion: any rich-text property value beginning with `{` is rejected by the `update-page` tool with an "Invalid input" validation error, regardless of whether the string is valid JSON — this blocks literal JSON embedding as `FOUNDATION_CONTRACTS.md` describes.
- Linear: none of `notion-link`/`disposition-history`/`open-item-source`/`transition-id` can be created as real typed Issue fields through the connector's `save_issue`/`get_issue` tools — only Linear's native fields are exposed, and this workspace has no custom fields configured.

Both were worked around live during Foundational Setup's test-artifact exercise (not blocking):
- Notion: flat `key=value; key=value` text encoding instead of JSON for `transition-id` and `disposition-history` properties.
- Linear: native `links` (attachments) for `notion-link`/`open-item-source`, and description-embedded text for `transition-id`/disposition metadata.

## Impact
**Medium** — doesn't block usage (both workarounds were exercised successfully end-to-end), but every future write through `notion-knowledge-management`/`linear-work-management`/`open-item-management` needs to know to use the workaround encoding rather than the documented JSON/custom-field shape. As written, `FOUNDATION_CONTRACTS.md` and `linear-entity-fields.md` mislead an implementer into expecting the literal documented shape to work against the real connectors.

## Additional Context
- Found during: `.draft/prompts/workmanagement-kit/foundation-setup-wave1.md`'s live Bootstrap + test-artifact exercise, 2026-08-31 (worktree `chore/workmanagement-kit-foundation-setup-wave1`).
- Related but not a duplicate of #251 (the general "wire up connectors" tracking issue) — that issue tracked the fact that connectors weren't wired at all yet; this issue is a design gap discovered only once they were actually wired and exercised live.
- Proposed scope: either (a) adopt the text/link-attachment workarounds as the documented design, updating `FOUNDATION_CONTRACTS.md` and `linear-entity-fields.md` accordingly, or (b) investigate provisioning real Linear custom fields during Bootstrap and find a Notion property encoding that survives the leading-`{` rejection.
- Relevant files: `plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md`, `plugins/workmanagement-kit/skills/linear-work-management/references/linear-entity-fields.md`, `plugins/workmanagement-kit/skills/notion-knowledge-management/SKILL.md`, `plugins/workmanagement-kit/skills/open-item-management/SKILL.md`.
