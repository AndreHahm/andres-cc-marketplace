# Worked Example: Wiring a Caller

A hypothetical scenario: `analysis-kit`'s `running-a-full-retrospective` skill finishes producing a
retrospective report and the user wants it stored in Notion for later reference, instead of only
living in `analysis-kit`'s own local output directory.

## What `analysis-kit`'s skill does

`running-a-full-retrospective` does **not** call any Notion connector itself — it has none, and
per this repository's own rule, it never implements one. Instead, once the report is finished, it
asks the host to invoke `plugin-integration-intake` with a structured payload:

```json
{
  "source_plugin": "analysis-kit",
  "source_skill": "running-a-full-retrospective",
  "content": {
    "title": "Q3 Retrospective: plugin-devkit build velocity",
    "summary": "Three-sentence executive summary of the retrospective's findings.",
    "body": "Full retrospective report content..."
  },
  "target_system": "notion",
  "suggested_mapping": {
    "notion_database": "Reports",
    "rationale": "This is a completed retrospective report, matching the Report record type."
  }
}
```

`"Reports"` above is illustrative shorthand for readability — a real `notion_database`/
`linear_target` value is always a stable ID, never a display name (see `linear-entity-fields.md`'s
Cross-Entity Rules; the same rule applies on the Notion side). `content` above also omits the
shared record properties (`source`, `related-record`, `authority`, `transition-id`, `status`,
`owner`, `date`) that every Notion record carries — the caller never supplies these;
`notion-knowledge-management` populates them itself when it executes the write in step 5 below.

`analysis-kit`'s own skill has no further involvement past this point — it does not see the
approval prompt, does not know whether the user approves or rejects it, and does not receive
confirmation of the write beyond whatever the host chooses to relay back to it.

## What `plugin-integration-intake` does with this

This walks through the same numbered Quick Start as the parent SKILL.md — step 2's three validation
checks are broken out below as 2a/2b/2c for illustration, since this example shows each check's
concrete result rather than the general rule:

1. Receives the payload above.
2. Validates it:
   - **2a.** `source_plugin: "analysis-kit"` checked against the installed plugin list (an
     existence check on the claim, not authentication of the sender — see SKILL.md's Trust Model)
     — it is a real, installed plugin, so this passes.
   - **2b.** `content` against the Report record shape (`title`, `summary`, and `body` all present,
     no unrecognized fields) — this passes.
   - **2c.** `suggested_mapping` resolves to exactly one Notion database (`Reports`) — this passes,
     assuming exactly one database with that role is configured.
3. Builds the exact preview a direct user-initiated Report capture would show — the same form
   `notion-knowledge-management` would present if the user had pasted this content directly and
   asked to save it as a Report.
4. Presents this preview to the user for live approval. `analysis-kit`'s own retrospective run may
   have already been approved by the user to execute — that approval does not carry over here; the
   user sees and approves this specific Notion write independently.
5. On approval, writes via `notion-knowledge-management` and reads the result back.
6. Records the transition tagged with both the new Notion record and `source_plugin:
   "analysis-kit"`, per `../../../FOUNDATION_CONTRACTS.md`'s Transition Contract schema.

## What Would Happen on a Bad Payload

If `analysis-kit`'s hypothetical skill instead submitted `source_plugin: "analysis-kit-v2"` (a name
that isn't actually installed), the payload fails the unknown-source check and a structured
handoff is returned to the caller — no preview is ever built, and no approval prompt is ever shown
to the user for a submission from an unverifiable source.
