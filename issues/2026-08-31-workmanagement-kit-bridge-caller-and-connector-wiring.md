## Summary
Build workmanagement-kit's Codex bridge-caller script and wire real Notion/Linear MCP connectors — both currently disclosed as not-yet-built, deferred from this session's `plugin-lifecycle-downstream` QA run.

## Context
- **Product/Service**: `workmanagement-kit` plugin (`plugins/workmanagement-kit/`)
- **Related work**: `plugin-lifecycle-upstream`/`plugin-lifecycle-downstream` runs, 2026-08-30/31

## Scoped Work

1. **Codex bridge-caller script** (new file(s) under `plugins/workmanagement-kit/`) — dispatches `work-transition-reviewer` and `work-intake-classifier` live via `codex-kit`'s `codex-review-bridge`, conforming to that skill's `references/envelope-schema.md`/`references/semantic-validation.md` contract. Both agents' own Output Format was already updated this session to emit a schema-compatible envelope, so this work is unblocked on that side.
   - **Language decision needed first**: `codex-review-bridge`'s own invocation script is `.mjs`, but `plugins/workmanagement-kit/CONTRIBUTING.md` declares Python as this plugin's scripting language. Per `.claude/rules/require-declared-plugin-language.md`, mixing languages needs an explicit, stated reason — not silent inconsistency.

2. **Real Notion/Linear MCP connector wiring** (Foundational Setup: connector installation, workspace/team scoping, test scopes). This activates the foundation-contract files already built this session:
   - `plugins/workmanagement-kit/host-profile.json` — every operation currently ships `support_status: "unconfigured"`.
   - `plugins/workmanagement-kit/versioned-configuration.json` — every field currently `null`/empty.
   - Both are activated per-installation via `.claude/workmanagement-kit.local.json` (gitignored; does not exist yet — see `plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md`'s Local Override section for the exact merge shape expected).

3. **Follow-up once both land**: re-run `security-reviewer` on `plugin-integration-intake`'s trust-boundary gate. Its most recent pass (2026-08-30, during the downstream QA run) reviewed the skill's specification and fixed a real Critical finding (an unauthenticated identity check), but necessarily reviewed a specification, not a wired connector — see that skill's own `SKILL.md` Testing & Validation section, which already tracks this as a stated follow-up.

## Impact
**Medium** — blocks the plugin's two Codex reviewer agents from ever running live, and blocks all 7 skills' actual Notion/Linear read/write capability. No workaround exists for live use; the plugin's standalone Codex CLI export path and documentation-only design remain usable in the meantime.

## Additional Context
References: `plugins/workmanagement-kit/README.md`'s Status section, `plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md`. Both deferred items were decided together with the user on 2026-08-31 since they're closely related (the bridge-caller's live path and the connector wiring both depend on the same host-profile activation).
