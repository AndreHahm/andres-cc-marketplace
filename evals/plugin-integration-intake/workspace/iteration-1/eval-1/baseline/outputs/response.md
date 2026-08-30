# Processing Submission from analysis-kit / running-a-full-retrospective

## 1. Intake / Schema Validation

Received payload:

```json
{
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

Checks performed:

- **Required content fields** — `title`, `summary`, `body` are all present and non-empty (as placeholders in this
  example, but structurally valid). No missing required fields.
- **`target_system`** — `"notion"` is a recognized, supported destination (a Notion MCP connection is available in
  this environment).
- **`suggested_mapping`** — the submitting skill proposes a destination database (`"Reports"`) and gives a rationale
  ("completed retrospective report"). This is a *suggestion*, not a guaranteed-correct routing decision — the
  submitting plugin (analysis-kit) doesn't necessarily know the receiving system's actual database names, schema, or
  whether a database called "Reports" even exists in the connected workspace.

Verdict: **structurally valid submission**, safe to proceed to routing/mapping evaluation.

## 2. Mapping Evaluation

Treating `suggested_mapping` as advisory input rather than an instruction to execute blindly, for a few reasons:

1. I have no confirmed record (from this session) of a Notion database literally named "Reports" existing in the
   connected workspace, nor its property schema (does it expect a `Title` property, a `Summary`/`Status`/`Tags`
   property, a relation back to a "Quarter" or "Team" database, etc.). Creating a page against an assumed schema
   risks either a failed write or a page that doesn't fit the database's real structure.
2. The rationale given ("completed retrospective report") is reasonable on its face — a finished retro report is a
   plausible fit for a "Reports"-type database — but plausibility isn't the same as verification.
3. This is an automated, cross-plugin submission with no human present in the loop at the moment of intake. Per
   general good practice for automated writes to an external system of record (not a scratch/ephemeral store),
   the safer default is: **validate and stage the mapping, then either confirm the target exists before writing, or
   surface the mapping decision for confirmation** — rather than auto-creating content in a live, shared Notion
   workspace on the strength of one plugin's own guess about another system's schema.

## 3. Recommended Processing Outcome

Given the above, the submission is **accepted and staged**, with the following resolution path:

- **Step A (verify target):** Search the connected Notion workspace for a database named "Reports" (or a
  close match). If found, confirm its property schema is compatible with the incoming fields (a title property for
  `content.title`, and a body/rich-text destination for `summary` + `body` — Notion pages typically want the
  long-form content as page body blocks rather than a single property, with `summary` perhaps also mirrored into a
  short-text property if one exists).
- **Step B (create):** If a compatible database is confirmed, create a new page in it with:
  - Title property = `"Q3 Retrospective"`
  - Page body = the `body` content, optionally prefixed with the `summary` as an italicized/callout intro block.
  - Any additional properties the database schema requires but the payload didn't supply (e.g. date, source,
    status) would need a default or a follow-up question — not fabricated silently.
- **Step C (no match / schema mismatch):** If no "Reports" database exists, or its schema doesn't line up, do not
  invent a new database or force the content into an incompatible one. Instead, respond back to the source
  (analysis-kit) indicating the suggested mapping could not be honored as-is, with the reason, so the caller (or a
  human) can pick an alternate destination.

## 4. Response Contract Back to Source Plugin

```json
{
  "status": "accepted_pending_verification",
  "source_plugin": "analysis-kit",
  "source_skill": "running-a-full-retrospective",
  "target_system": "notion",
  "resolved_mapping": {
    "notion_database": "Reports",
    "confidence": "unverified",
    "note": "Suggested mapping is plausible given the content is a completed retrospective report, but the target database's existence and schema have not been confirmed in this session. Recommend verifying before write, or confirming with a human if this is a first-time integration between these two plugins."
  },
  "next_action": "verify_target_then_create_or_escalate"
}
```

## 5. Open Questions / Assumptions Surfaced

- Is "Reports" an existing, intentionally-designated database for cross-plugin report submissions, or just
  analysis-kit's own best guess at a plausible name? No shared routing/registry contract between analysis-kit and
  the receiving system was available to consult here.
- Should `summary` and `body` both land in the Notion page, or is `summary` meant only as a preview/notification
  string (e.g., for a Slack ping) and `body` the sole page content? The payload doesn't disambiguate.
- No deduplication key (e.g., a stable report ID) is included — if `running-a-full-retrospective` runs again for
  the same quarter, nothing in this payload prevents a duplicate "Q3 Retrospective" page from being created. Would
  recommend the source plugin include an idempotency key in future submissions.

These were resolved by defaulting to the cautious path (verify before writing, disclose assumptions) rather than
guessing silently, consistent with treating an external, shared system of record as something that shouldn't be
written to on inference alone.
