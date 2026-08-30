# Task
Create a Linear issue for adding CSV export to the transition history feature.

# What I did

1. Listed Linear teams — found a single team, **AndreHahm** (id `a7270da5-1f7b-4215-88fa-5ea27341a021`).
2. Searched existing issues for "transition history" — no matches. The workspace only contains Linear's default onboarding issues (AND-1 through AND-4), so there was no existing "transition history" epic/project to attach this to or prior context to reuse.
3. Checked available labels — `Bug`, `Feature`, `Improvement` — and chose `Feature`.
4. Created the issue via `save_issue`.

# Result

**Issue created: [AND-5 — Add CSV export to transition history](https://linear.app/andrehahm/issue/AND-5/add-csv-export-to-transition-history)**

- Team: AndreHahm
- Label: Feature
- Status: Backlog
- Priority: No priority (not specified in the request)

## Issue content

**Title:** Add CSV export to transition history

**Description:**

### Summary
Add the ability to export an item's transition history (status/state change log) as a CSV file.

### Motivation
Users currently can only view transition history in the UI. Teams that need this data for audits, reporting, or analysis in external tools (Excel, Google Sheets, BI tools) have no way to get it out of the product except manual copy-paste.

### Proposed Scope
- Add an "Export to CSV" action on the transition history view (single item first; bulk/multi-item export can be a follow-up if out of scope here).
- CSV should include, at minimum: item identifier, from-state, to-state, changed-by (user), and timestamp.
- Respect any existing filters/date range applied to the transition history view when generating the export.
- Handle large histories without timing out or loading the full dataset into the browser at once (streaming or paginated export if needed).

### Acceptance Criteria
- [ ] User can trigger a CSV export from the transition history view.
- [ ] Exported file opens correctly in Excel/Google Sheets with correct column headers.
- [ ] Exported data matches what's shown on screen (including active filters).
- [ ] Special characters (commas, quotes, newlines in user names/comments) are properly CSV-escaped.
- [ ] Export works for histories with a large number of transitions without failing.

### Open Questions
- Should export be scoped to a single item, or also support exporting across multiple items/a whole project?
- Any file size or row limits we need to design around?

### Notes
Filed as a baseline feature request; scope/acceptance criteria above are a starting proposal and should be refined with the team before implementation.

# Assumptions / notes

- No plugin/skill was used — this was done with the standard Linear MCP tools directly (list_teams, list_issues, list_issue_labels, save_issue).
- Since the workspace had no prior "transition history" feature/project/epic to reference, I wrote a self-contained, reasonable description (summary, motivation, proposed scope, acceptance criteria, open questions) rather than guessing at product-specific details I couldn't verify. I flagged the two genuinely open scope questions (single vs. bulk export, size limits) directly in the issue rather than silently deciding them.
- Did not set priority, since none was requested and no severity/urgency signal was given.
