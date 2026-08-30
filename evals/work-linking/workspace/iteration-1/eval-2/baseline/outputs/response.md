# Notion vs. Linear Drift Check: CSV Export Work

I found one matching pair of items on each side and compared them directly.

- **Notion:** "💡 Idea: Export Transition History as CSV" — https://app.notion.com/p/3ccce0610b0c8187b6e0db08a5ee6a0a (created/last edited 2026-08-30T19:22)
- **Linear:** AND-5 "Add CSV export to transition history" — https://linear.app/andrehahm/issue/AND-5/add-csv-export-to-transition-history (status: Backlog, created 2026-08-30T19:22:22)

Both were created at essentially the same timestamp, so this looks like the Linear issue was spun up directly from the Notion idea. However, they've already drifted:

## Drift found

1. **Stage/status contradiction.** The Notion page still says: *"Captured as a raw product idea for future consideration — no design or scoping done yet"* and *"Status: Idea — not yet prioritized or scoped."* But the Linear issue already has a full Proposed Scope section, a 5-item Acceptance Criteria checklist, and specific field/behavior decisions (CSV columns, escaping rules, streaming for large histories). Scoping has clearly happened on the Linear side, and Notion was never updated to reflect it — Notion is stale relative to Linear.

2. **No cross-link between the two.** The Linear issue has an empty `attachments` list (no link back to the Notion page), and the Notion page's content has no reference to AND-5 or to Linear at all. There's no traceable connection except the shared timestamp and near-identical title wording — if someone only looked at one system, they'd have no way to find the other.

3. **Open questions partially duplicated, partially resolved inconsistently.**
   - Notion asks: "What counts as transition history?", "single item vs. bulk export?", "which fields to include?", "any filtering needed?"
   - Linear's Proposed Scope answers the fields question (item identifier, from-state, to-state, changed-by, timestamp) and the filtering question (respect existing filters/date range) — but Notion still lists these as open.
   - Both sides still leave "single item vs. bulk/multi-item export" genuinely unresolved (Linear repeats it under its own Open Questions), so that one point is at least consistent — it just hasn't been carried back to Notion as "still open, now confirmed as the key open question" rather than one of four vague ones.

4. **Ownership/priority not reflected in Notion.** Linear shows a concrete owner (created by André Hahm, team "AndreHahm"), a Backlog status, and a "Feature" label. Notion has none of this — it reads as an anonymous, unowned idea, so anyone consulting Notion alone would not know this has already moved into a real team's backlog.

## Bottom line

The Linear issue (AND-5) is more current and more detailed than the Notion idea page. Notion has not been updated since the idea was promoted into a scoped, backlogged Linear issue, and there is no link connecting the two records. Recommended fix: either update the Notion page's Status/Context to "Scoped — see AND-5" with a link to the Linear issue, or archive/redirect the Notion idea page now that AND-5 is the source of truth, and add a back-reference (attachment/comment) from AND-5 to the Notion page for provenance.

## Caveats

- This check relied on keyword search ("CSV export") in both Notion and Linear; if there are other related pages/issues that don't share that phrase (e.g., a differently-worded duplicate, or a design doc under a different title), they wouldn't have surfaced here.
- I did not check Slack, GitHub, or other connected sources for related discussion that might further explain the scoping that happened between the two timestamps.
