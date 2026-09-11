# Intake Processing: Submission from analysis-kit / running-a-full-retrospective

## Input received

```json
{
  "content": {
    "title": "Retrospective Notes",
    "summary": "Loose notes, not yet categorized.",
    "body": "Assorted findings."
  },
  "target_system": "notion",
  "suggested_mapping": {
    "notion_database": null,
    "rationale": "not sure if this belongs in Reports or Notes"
  }
}
```

## Assessment

The submitting skill (`analysis-kit:running-a-full-retrospective`) has handed off content
without a resolved destination. `suggested_mapping.notion_database` is explicitly `null`, and
the rationale is an admitted ambiguity between two plausible destinations — a "Reports"
database and a "Notes" database — rather than a considered recommendation. This is a
genuine open decision, not a formality: writing to the wrong database in Notion has real
downstream cost (mis-filed content, broken views/filters that assume a database's schema,
and a future cleanup task), so I should not treat the `null` as "pick either."

Two things push me toward resolving this myself rather than stopping to ask:

1. **The content's own framing.** The submission's `summary` field self-describes the content
   as "Loose notes, not yet categorized," and the `body` is a bare, unstructured line
   ("Assorted findings.") rather than any structured findings/decisions/action-items shape.
   A "Reports" destination generally implies a finished, structured artifact (findings,
   metrics, conclusions organized for review); this submission is pre-that — it reads as
   raw capture, which is what a "Notes" destination is for.
2. **Reversibility.** Notion pages are trivial to move between databases later (a page's
   parent database is not a load-bearing, hard-to-undo choice the way schema or permissions
   would be). Given that, defaulting to the safer, lower-commitment destination ("Notes") and
   flagging the assumption is preferable to blocking the whole submission on a question the
   submitting workflow itself couldn't answer.

## Decision

**Route to the "Notes" database, not "Reports."**

Rationale: the content is explicitly pre-categorization ("not yet categorized," unstructured
body), which matches a notes/inbox destination better than a reports destination that implies
a finished, reviewable artifact. This is a judgment call made in place of the missing
`suggested_mapping.notion_database`, not a verified fact — see the caveat below.

## Caveat / what I did not do

I did not actually create a page in a live Notion workspace as part of this processing step,
for two reasons:
- The submission itself doesn't name which specific "Reports" or "Notes" database it means
  (no database ID, no workspace/page parent given) — there's nothing concrete to target even
  once "Notes" is chosen as the category.
- Since the routing decision above is an assumption filling a genuine gap the source skill
  left open, the safer sequence is: record the decision and reasoning now (this document),
  and let the actual write happen once a concrete "Notes" database target is confirmed —
  rather than silently committing an ambiguous submission to a live system on a guess.

## Recommended next step

If a "Notes" database already exists and is the intended target, confirm its Notion database
ID (or page URL) and I will create the page there with:
- Title: "Retrospective Notes"
- Body: "Assorted findings." (plus the summary line as a subtitle/callout, since it's
  metadata about the note's own state rather than findings content itself)

If "Reports" is actually intended (e.g. because this retrospective's findings will be
elaborated into a formal report shortly), say so and I'll route there instead — the decision
above is a reasonable default, not a final, unchangeable call.
