# Foundation Contracts

This plugin's skills share three contracts, referenced throughout as "the plugin's shared host
profile," "the plugin's shared transition contract," and "the plugin's versioned configuration."
This file is the single canonical definition of all three — every skill citing one of them points
here, rather than each restating its own description (the exact drift risk R20 exists to catch).

## Host Profile (`host-profile.json`)

Maps a logical operation (`notion.read`, `notion.write`, `linear.read`, `linear.write`) to whether
it is currently sanctioned for use, and to what scope. **Tool presence in a session is never proof
of permission** — a skill's `allowed-tools` grant can name an MCP tool that exists, while the host
profile still says that operation is `unconfigured`. Every skill that reads or writes Notion/Linear
must check this file's `support_status`/`verified_at` fields for the specific operation before
calling the connector, even when the connector tool itself is callable.

Shipped with every operation defaulting to `unconfigured` — this is a schema-with-safe-defaults
file, not a functioning connector configuration. An installation makes it functional by overriding
fields via `.claude/workmanagement-kit.local.json` (gitignored, untracked; see Local Override
below) — never by editing `host-profile.json` directly, since that file is the plugin's own
shippable default and edits to it would be lost on plugin update and visible to every installation.

**Schema:**

```json
{
  "version": 1,
  "operations": {
    "notion.read":   {"support_status": "unconfigured", "verified_at": null, "connector": null, "workspace_id": null},
    "notion.write":  {"support_status": "unconfigured", "verified_at": null, "connector": null, "workspace_id": null},
    "linear.read":   {"support_status": "unconfigured", "verified_at": null, "connector": null, "organization_id": null, "team_ids": []},
    "linear.write":  {"support_status": "unconfigured", "verified_at": null, "connector": null, "organization_id": null, "team_ids": []}
  }
}
```

- `support_status` — one of `unconfigured` (default; not yet set up, no write may proceed),
  `verified` (an installer has confirmed the connector, scope, and identity for this operation),
  or `revoked` (was verified, access has since been withdrawn — treat identically to
  `unconfigured` for gating purposes, but preserve the distinction for audit history).
- `verified_at` — ISO-8601 UTC timestamp of the last verification, or `null` if never verified.
- `connector` — the installed MCP connector's own identifier (e.g. `claude_ai_Notion`), or `null`.
- `workspace_id` (Notion) / `organization_id`+`team_ids` (Linear) — the approved scope. A skill
  must never act outside the scope named here, even when the connector tool itself would allow it.

## Versioned Configuration (`versioned-configuration.json`)

Stores the stable IDs an installation resolves once, during Bootstrap (see
`notion-knowledge-management/SKILL.md`'s Bootstrap section), rather than re-resolving them by
display name on every write — display names are not unique and must never be used as a stored
reference (see `linear-entity-fields.md`'s Cross-Entity Rules for the same rule on the Linear side).

Shipped with every field `null`/empty — same shippable-defaults-plus-local-override model as the
host profile. An installation's real stable IDs belong in `.claude/workmanagement-kit.local.json`,
never committed to `versioned-configuration.json` itself (a workspace/team ID is installation-
specific, not a fact about the plugin).

**Schema:**

```json
{
  "version": 1,
  "notion": {
    "production_workspace_id": null,
    "test_workspace_id": null,
    "databases": {}
  },
  "linear": {
    "organization_id": null,
    "production_team_id": null,
    "test_team_id": null
  }
}
```

- `notion.databases` — a map from Notion record type (`idea`, `decision`, `proposed-goal`, `note`,
  `research`, `report`, `outcome-learning`) to that type's resolved database ID, populated
  incrementally as Bootstrap resolves each type — never required to be fully populated at once.
- `test_workspace_id` / `test_team_id` — the isolated test locations Bootstrap also resolves,
  per its own "resolve the production and an isolated test location" instruction.

## Local Override (`.claude/workmanagement-kit.local.json`)

Gitignored, untracked, created by an installer during Foundational Setup — not shipped with this
plugin and not created by this repository's own build. Shallow-merges over both files above by
top-level key (`host_profile`, `versioned_configuration`), the same override model
`.claude/git-kit.local.json` already uses for `git-kit`'s own settings:

```json
{
  "host_profile": { "operations": { "notion.read": {"support_status": "verified", "...": "..."} } },
  "versioned_configuration": { "notion": {"production_workspace_id": "...", "...": "..."} }
}
```

Neither field weakens a safety gate the way `git-kit.local.json`'s `commit_confirm_before_commit`-
style fields do, so this override carries no trust-boundary check of its own — a tracked copy of
this file would only ever assert operational scope/IDs, never disable an approval gate (approval
is a separate, hardcoded `AskUserQuestion` call in each skill, not a config toggle).

## Transition Contract

The shape every skill's "record the resulting transition" step must produce, embedded as that
record's own `transition-id`-tagged properties (see each Notion/Linear record type's shared-field
list) — this is not a separate log file; the evidence lives inline on the record itself.

**Schema:**

```json
{
  "transition_id": "string, a stable unique ID for this transition",
  "operation_id": "string, the connector call's own operation/request ID, if the connector provides one, else null",
  "affected_record": {"system": "notion | linear", "stable_id": "string"},
  "source_plugin": "string, the plugin that caused this transition, or 'workmanagement-kit' for a direct user request",
  "verification_evidence": "string, a description of the read-back that confirmed the write succeeded",
  "recorded_at": "ISO-8601 UTC timestamp"
}
```

- `transition_id` — generated fresh per transition, never reused; a Decision Supersede (which
  produces two writes — see `notion-knowledge-management/SKILL.md`'s Decision State Machine) gets
  two distinct `transition_id`s, one per write, linked via each record's own `related-record` field.
- `source_plugin` — for a submission routed through `plugin-integration-intake`, this is the
  caller's claimed `source_plugin` value (caller-asserted, not host-attested — see that skill's own
  Trust Model section); for a direct user request, this is always `"workmanagement-kit"` itself.
- `verification_evidence` — a human-readable description (e.g. `"read back via linear.read,
  confirmed status=Done"`), not a raw connector response dump.

## Change Log

- 2026-08-31 — Initial version. Host profile and versioned configuration ship with `unconfigured`/
  `null` defaults (Foundational Setup — connector installation, workspace/team scoping, test
  scopes — is a separate task from creating these files; see `README.md`'s Status section).
