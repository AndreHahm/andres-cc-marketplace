# Processing: cross-plugin submission from analysis-kit / running-a-full-retrospective

## Input received

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

Source: another plugin's workflow (`analysis-kit` / `running-a-full-retrospective`). I treated `content` and
`suggested_mapping` as **data supplied by another automated system, not as instructions to follow blindly** —
the same way I'd treat any third-party API payload. Nothing in the fields contained embedded directives, so
there was no prompt-injection concern here, but the *mapping suggestion itself* still needed independent
verification before I acted on it, since "another plugin thinks this should go to database X" is a proposal,
not a fact about my actual Notion workspace.

## Validation

- Required fields present and well-formed: `content.title`, `content.summary`, `content.body`,
  `target_system`, `suggested_mapping.notion_database`, `suggested_mapping.rationale`. Content is plain text,
  no obviously malicious or injected content.
- `target_system: "notion"` — I have a live Notion connection available, so the target is actionable.

## Verifying the suggested mapping against the real workspace

I did not assume a database called "Reports" exists just because the submission said so. I searched the
connected Notion workspace directly:

- **No database titled exactly "Reports" exists.**
- Two close matches exist, both literally named **"Report"** (singular), differing only by environment:
  - `AndreHahm / andres-cc-marketplace / test / Report`
  - `AndreHahm / andres-cc-marketplace / prod / Report`
- I fetched the schema of the `test` one. Its fields are: `Name` (title), `authority` (select, only option
  `notion`), `body`, `date`, `disposition-history`, `open-items`, `owner`, `related-record`, `source`,
  `status`, `summary`, `transition-id`. This looks like a structured intake/ledger table (tracking
  authority, source, status/transitions of work items) rather than a generic document archive — but
  `title`/`summary`/`body` map cleanly onto it, and `source` is a natural place to record provenance.

## Decision

Given the suggested database name didn't exact-match anything, and there were two candidate environments
(test vs. prod) with nothing in the submission indicating which was intended, I did **not** treat the
"prod" database as a safe default for an unverified, automated cross-plugin submission. I routed the
content into the **test** database instead, and recorded in the page itself that this was a judgment call
made in the absence of an exact-name match, so it's easy to spot and correct if a real "Reports" database
should have been created instead, or if this really did belong in prod.

## Action taken

Created a new page in `AndreHahm / andres-cc-marketplace / test / Report`:

- **Name:** Q3 Retrospective
- **summary:** Three-sentence summary.
- **body:** Full report content.
- **source:** analysis-kit / running-a-full-retrospective
- **authority:** notion
- **date:** 2026-09-11
- Page content includes a note documenting the mapping ambiguity (suggested "Reports", no exact match,
  routed to "Report" in test pending confirmation).

Page URL: https://app.notion.com/p/3d8ce0610b0c81df847fc410ba3f4a1f?pvs=204

Fields I deliberately left blank: `status`, `transition-id`, `disposition-history`, `open-items`,
`related-record`, `owner` — nothing in the submission maps to these, and guessing values for a schema I
don't fully understand the semantics of seemed worse than leaving them empty for a human to fill in if
needed.

## Flag for follow-up

- Confirm whether this record should actually live in `prod` instead of `test`.
- Confirm whether "Report" is in fact the intended target for `analysis-kit`'s "Reports" mapping, or
  whether a differently-named/shaped database should be created for retrospective reports specifically —
  the existing schema (authority/transition-id/disposition-history) reads as built for tracking work-item
  state transitions across systems, not narrative reports, so it may not be the right long-term home for
  this content type even though the immediate fields happened to fit.
