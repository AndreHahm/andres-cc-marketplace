# Intake Payload Schema

The structured payload a calling plugin's own workflow hands to `plugin-integration-intake` via
the host. This is the payload's logical shape, machine-enforced at the envelope level by
`assets/intake-payload.schema.json` (Draft 2020-12, `additionalProperties: false` on the envelope
and on `suggested_mapping`). That schema deliberately does **not** fully encode `content`'s
per-`target_system` shape — only `type: object, minProperties: 1` — to avoid restating the full
per-record-type field list a third time (see `content` shape below for why the reference files
stay the actual source of truth for that part). This reference document is still the authoritative
statement of the fields and validation rules a caller must satisfy overall; the schema file
mechanically catches a malformed envelope before this skill's own procedure (see SKILL.md) runs
the parts a static schema can't express (the existence check, the ambiguous-target check).

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
  commonly a Report — required fields `title`, `summary`, **and** `body`, not just "one of summary
  or body"). Extra fields not recognized by the target record type are rejected as malformed
  content, not silently dropped or ignored. **Authoritative source of the full per-type field
  list:** `notion-knowledge-management`'s `references/notion-record-types.md` — the minimal Report
  fields above are restated here for a quick check only; if that reference and this list ever
  disagree, the reference wins.
- **`linear`**: must resemble a valid Issue-level submission (required fields `title`,
  `description`, **and** `status`). `plugin-integration-intake` never accepts a submission
  proposing a new Goal/Roadmap/Project/Milestone directly; those require the deliberate
  `idea-to-implementation` promotion flow, not a direct cross-plugin submission. **Authoritative
  source of the full per-type field list:** `linear-work-management`'s
  `references/linear-entity-fields.md` — the minimal Issue fields above are restated here for a
  quick check only; if that reference and this list ever disagree, the reference wins.

### `suggested_mapping` shape

| Field | Required | Notes |
|---|---|---|
| `notion_database` or `linear_target` | Yes (one, matching `target_system`) | The calling plugin's own guess at the specific database/entity |
| `rationale` | No | Why the calling plugin believes this mapping is correct |

## Validation Rules

1. **Unknown source**: `source_plugin` must match a real, currently-installed plugin in this
   repository, and `source_skill` must match a real skill (a directory containing a `SKILL.md`)
   inside that specific plugin. Either value failing to resolve is rejected as unknown source.
   **This is an existence check on the caller's claim, not authentication of the caller** —
   `source_plugin`/`source_skill` are caller-asserted, not host-attested (see SKILL.md's Trust
   Model section). Passing this check only means the claimed names are real; it does not confirm
   that plugin/skill actually sent the payload.
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
