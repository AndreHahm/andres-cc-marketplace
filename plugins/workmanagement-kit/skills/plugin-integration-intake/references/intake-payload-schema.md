# Intake Payload Schema

The structured payload a calling plugin's own workflow hands to `plugin-integration-intake` via
the host. This is the payload's logical shape — the actual JSON Schema file (Draft 2020-12,
`additionalProperties: false`, per this plugin's shared schema conventions) is implemented at the
plugin's schema layer alongside its other versioned contracts; this reference documents the
fields and validation rules that schema enforces.

## Fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `source_plugin` | Yes | string | The calling plugin's own name, exactly as installed (e.g. `analysis-kit`) |
| `source_skill` | Yes | string | The calling plugin's own skill that produced this submission |
| `content` | Yes | object | The actual content to store — shape depends on `target_system` (see below) |
| `target_system` | Yes | enum: `"notion"` \| `"linear"` | Which system this submission is bound for |
| `suggested_mapping` | Yes | object | The calling plugin's own best guess at where this belongs — untrusted evidence, not a directive (see SKILL.md) |

### `content` shape, by `target_system`

- **`notion`**: must resemble one of the record types `notion-knowledge-management` owns (most
  commonly a Report) — matching that type's own required fields exactly (a Report requires
  `title`, `summary`, **and** `body` — see `notion-knowledge-management`'s
  `references/notion-record-types.md`, not just "one of summary or body"). Extra fields not
  recognized by the target record type are rejected as malformed content, not silently dropped or
  ignored.
- **`linear`**: must resemble a valid Issue-level submission (a `title` and a `description` at
  minimum) — `plugin-integration-intake` never accepts a submission proposing a new Goal/Roadmap/
  Project/Milestone directly; those require the deliberate `idea-to-implementation` promotion
  flow, not a direct cross-plugin submission.

### `suggested_mapping` shape

| Field | Required | Notes |
|---|---|---|
| `notion_database` or `linear_target` | Yes (one, matching `target_system`) | The calling plugin's own guess at the specific database/entity |
| `rationale` | No | Why the calling plugin believes this mapping is correct |

## Validation Rules

1. **Unknown source**: `source_plugin` must match a real, currently-installed plugin in this
   repository. A `source_plugin` value that doesn't resolve to an installed plugin is rejected as
   unknown source — this skill never trusts a caller-asserted identity without checking it.
2. **Malformed content**: `content` must match the shape required for its declared `target_system`
   (see above). A missing required field, or a field of the wrong type, is malformed content.
3. **Ambiguous target**: `suggested_mapping` must resolve to exactly one Notion database/page or
   one Linear entity when checked against the plugin's own host profile and current-state read —
   if it could plausibly resolve to more than one, or to none, the payload is ambiguous.

Any of these three failures produces a structured handoff back to the calling plugin (per SKILL.md
step 2) — never a guess, never a silent drop.

## What This Schema Deliberately Excludes

- No field for "pre-approved" or "urgent" — such a field would only invite exactly the
  trust-substitution this skill's fresh-approval rule exists to prevent (see SKILL.md's "Why the
  fresh-approval rule is absolute").
- No raw connector parameters — a calling plugin submits logical content and a suggested mapping
  only, never a connector-level call shape.
