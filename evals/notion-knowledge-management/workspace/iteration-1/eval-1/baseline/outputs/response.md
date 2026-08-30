# Task

Capture this as an idea in Notion: we should let users export their transition history as a CSV.

# Approach

No existing Notion page or database in the workspace was clearly intended for product/feature ideas
(searched for "ideas backlog product" and "feature requests product backlog"). The one database titled
"ideas" that turned up belongs to a personal blogging/content-idea collection ("my ideas" > "blogger's
central" > templates, with a `type` property of idea/article/tutorial/guide/etc.) — not a fit for a
software feature idea. Since there was no clear existing home for this kind of idea, I created a new
standalone Notion page to capture it, rather than force it into an unrelated database.

# What was created

A new Notion page titled **"Idea: Export Transition History as CSV"**:
https://app.notion.com/p/3ccce0610b0c8187b6e0db08a5ee6a0a?pvs=204

Content captured:

```
## Idea
Allow users to export their transition history as a CSV file.

## Context
Captured as a raw product idea for future consideration — no design or scoping done yet.

## Notes / Open Questions
- What counts as "transition history" (e.g., status changes on tasks/tickets/workflow items) needs to be defined precisely.
- Scope: export for a single item vs. bulk export across a project/workspace.
- Fields to include (timestamp, from-state, to-state, actor, item ID, etc.).
- Any filtering needed (date range, specific workflows) before export.

## Status
Idea — not yet prioritized or scoped.
```

# Notes / caveats

- This was done with standard Notion MCP tool calls (search + create-pages) only — no specialized
  methodology, template, or idea-capture skill was used to decide structure, placement, or metadata.
- Because no idea-tracking database exists in this workspace, the new page is a private, unfiled page at
  the workspace level rather than a row in a structured backlog. If the user has (or wants) a dedicated
  product-ideas/feature-request database, this page should be moved/converted into a row there so it's
  tracked alongside other similar ideas.
- No effort was made to deduplicate against any existing "export" or "CSV" related ideas beyond the two
  searches performed above; a more thorough check would search for those specific terms too.
