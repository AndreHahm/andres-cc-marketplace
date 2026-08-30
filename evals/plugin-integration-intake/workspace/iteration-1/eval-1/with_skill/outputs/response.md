# plugin-integration-intake — Submission Processed

Received a host-mediated submission from `analysis-kit`'s `running-a-full-retrospective` skill,
per `plugin-integration-intake`'s Procedure (SKILL.md steps 1–2). Result: **rejected at
validation — structured handoff returned, no preview built, no approval prompt shown, nothing
written to Notion.**

## Payload received

```json
{
  "source_plugin": "analysis-kit",
  "source_skill": "running-a-full-retrospective",
  "content": {
    "title": "Q3 Retrospective",
    "summary": "Three-sentence summary.",
    "body": "Full report content."
  },
  "target_system": "notion",
  "suggested_mapping": {
    "notion_database": "Reports",
    "rationale": "completed retrospective report"
  }
}
```

## Validation (SKILL.md step 2 / `references/intake-payload-schema.md`)

| Check | Result | Basis |
|---|---|---|
| **Unknown source** — `source_plugin` | PASS | `analysis-kit` is a real, installed plugin (`plugins/analysis-kit/`). |
| **Unknown source** — `source_skill` | PASS | `running-a-full-retrospective` is a real skill inside `analysis-kit` (`plugins/analysis-kit/skills/running-a-full-retrospective/`). |
| **Malformed content** | PASS | `target_system: "notion"` → content must match the Report record type's required fields exactly: `title`, `summary`, **and** `body` (per `notion-knowledge-management`'s `references/notion-record-types.md`). All three are present, correctly typed, and no unrecognized fields are attached. |
| **Ambiguous target** | **FAIL** | See below. |

### Why the target check fails

`suggested_mapping.notion_database: "Reports"` must resolve to **exactly one** Notion database
when checked against the plugin's own host profile and a current-state read (validation rule 3).
That check cannot be satisfied, and not because two candidate databases collide — it's the "or to
none" branch the schema itself names as equally ambiguous:

- `notion-knowledge-management`'s own SKILL.md states plainly: "The
  `mcp__workmanagement-kit__notion_read`/`notion_write` tools in this file's own `allowed-tools`
  have no backing MCP server configuration yet — that's pending Foundational Setup (connector
  installation, workspace/database scoping)."
- The plugin's README Status section confirms this is Wave 1 of a two-wave design and: "Live
  Notion/Linear mutation requires the Foundational Setup steps described in this plugin's design
  documents to be completed (connector installation, workspace/team scoping, test scopes) before
  first live use."
- No host-profile artifact or database-scope record exists anywhere in the plugin yet — there is
  nothing to read `"Reports"` against, so the mapping resolves to zero candidate databases, not
  one.

Per the schema's own rule ("Any of these three failures produces a structured handoff back to the
calling plugin ... never a guess, never a silent drop") and the SKILL.md Gotcha ("Ambiguous
target = stop, don't guess... a structured handoff to the user, never an inferred pick"), this
submission stops here. Steps 3–6 of the Procedure (build preview, present for live approval,
execute via `notion-knowledge-management`, record the transition) are **not entered** — there is
no live approval gate to run this through yet, and fabricating one, or a fake write, would
misrepresent this plugin's actual current state.

## Structured handoff (returned to `analysis-kit` / `running-a-full-retrospective`)

```json
{
  "status": "rejected",
  "reason": "ambiguous_target",
  "detail": "suggested_mapping.notion_database ('Reports') could not be resolved against a live Notion host profile — no connector/database scoping exists yet. This plugin (workmanagement-kit) is at Wave 1: Foundational Setup (connector installation, workspace/database scoping) has not been completed, so target resolution has nothing to check the mapping against.",
  "content_validation": "content passed structurally (matches the Report record type: title, summary, body all present, no extra fields) — this rejection is about target resolution only, not the content itself.",
  "next_step_for_caller": "Resubmit once workmanagement-kit's Foundational Setup is complete and a 'Reports' database is actually configured, or hold the report in analysis-kit's own local output directory until then.",
  "source_plugin": "analysis-kit",
  "source_skill": "running-a-full-retrospective",
  "no_write_occurred": true,
  "no_approval_prompt_shown": true
}
```

## Notes

- **Data-only boundary respected**: `suggested_mapping.rationale` ("completed retrospective
  report") was read as untrusted evidence about the caller's own guess, never as an instruction to
  skip a check or proceed anyway — it had no bearing on the outcome above.
- **No raw connector exposure**: at no point was `analysis-kit` given, or would it have been
  given, a connector call shape — only this logical accept/reject result.
- **This is not a verdict on the content's quality or worthiness** — only the target-resolution
  check failed. Had `workmanagement-kit`'s Foundational Setup already been completed with a real
  `Reports` database configured, this submission would have proceeded to a preview identical to
  what a direct user-initiated Report capture would show, then to the live `AskUserQuestion`
  approval gate — `analysis-kit`'s own prior approval to run its retrospective pipeline would
  **not** have carried over to that write, per the skill's "fresh-approval rule."
- Per the skill's own top-of-file disclosure, this gate has not yet had its required
  `security-reviewer` pass before shipping for real (see `require-security-review-before-new-gate.md`)
  — unrelated to why this specific submission was rejected, but worth restating since it's the
  first live-style processing run against this component.
