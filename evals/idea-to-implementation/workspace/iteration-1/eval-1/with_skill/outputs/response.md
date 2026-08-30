# Promotion Preview: CSV Export Idea → Linear

Following `idea-to-implementation`'s procedure, I read the Notion source and checked Linear before
drafting anything — and found something worth pausing on before I ask for approval.

## 1. Source read (Notion)

**Page:** "💡 Idea: Export Transition History as CSV"
(`https://app.notion.com/p/3ccce0610b0c8187b6e0db08a5ee6a0a`)

- **Idea:** Allow users to export their transition history as a CSV file.
- **Context:** Captured as a raw product idea for future consideration — no design or scoping done yet.
- **Open questions on file:** what "transition history" precisely means; single-item vs. bulk export;
  which fields to include (timestamp, from-state, to-state, actor, item ID); whether filtering
  (date range, workflow) is needed before export.
- **Status:** Idea — not yet prioritized or scoped.

No instruction-like text was found in the page body — treating its content as data only, per the
skill's data-only boundary.

## 2. Existing-work check (Linear) — adoption candidate found

Before drafting new structure, I checked Linear per the skill's "Adoption is not creation" gotcha, and
found a matching issue already on file:

**AND-5 — "Add CSV export to transition history"**
(`https://linear.app/andrehahm/issue/AND-5/add-csv-export-to-transition-history`)
Team: AndreHahm · Status: Backlog · Label: Feature · No existing attachments/links to Notion.

This is the same idea (CSV export of transition history), so per the mapping reference (an Idea
typically maps to a single Issue), the correct action is to **adopt AND-5, not create a duplicate
Issue.**

## 3. A discrepancy worth flagging before you approve

AND-5's description already resolves several things the Notion Idea explicitly lists as **open,
unscoped questions** — e.g. it commits to "single item first, bulk as follow-up," a specific field
list, CSV-escaping and large-history handling, plus a 5-item acceptance-criteria checklist. None of
that scoping appears in the source Idea, which is still marked "not yet prioritized or scoped."

I'm not treating AND-5's content as instructions to act on (data-only boundary applies to what I read
in Linear too), and I haven't changed anything — I'm surfacing this so you can confirm AND-5's scope is
actually the scope you want promoted, rather than silently adopting a Linear record whose detail may
have outrun the source Idea.

## 4. Proposed batch (one approval covers all of it)

No new Goal/Roadmap/Project/Milestone is implied by this Idea — it maps to a single Issue, and that
Issue already exists. The proposed batch is:

1. **Adopt** AND-5 as the promoted target for this Idea (no new Linear record created).
2. **Record the reciprocal link** (via `work-linking`): Notion page `3ccce061-0b0c-8187-b6e0-db08a5ee6a0a`
   ↔ Linear `AND-5`, stable IDs both directions — nothing currently links them.
3. **Record the promotion transition** through the plugin's shared transition contract.

## Approval needed

Per the skill's batch-approval rule, I have not adopted, linked, or recorded anything yet. Please
confirm:

- Adopt AND-5 as-is (accepting its existing scope/acceptance criteria as the promoted result), **or**
- Adopt AND-5 but flag its scope back to the Idea for reconciliation first, **or**
- Something else (e.g. you don't recognize AND-5 as the same effort and want a fresh Issue created
  instead).

Once you confirm, I'll read AND-5 back, record the reciprocal link, and record the transition —
exactly the previewed batch above, nothing added or removed.
