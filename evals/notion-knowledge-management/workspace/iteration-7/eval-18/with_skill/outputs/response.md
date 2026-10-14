# Weekly progress summary: export migration (simulation)

## Routing decision

I read `notion-knowledge-management` first. It does not own this request. Its description and its
Testing & Validation list say "summarize progress to Notion" goes to `status-and-learning`. That is a
dated snapshot built from Linear facts, not a knowledge capture. `notion-knowledge-management` only
executes the resulting write when `status-and-learning` calls it.

Under `notion-knowledge-management`'s own rules, I would hand the request to `status-and-learning`.
That skill drafts the content from Linear and then calls back here for the write.

Nothing below has been executed. No Notion or Linear tool was called.

## What I would do, in order

1. **Hand off.** Dispatch `Skill(status-and-learning)`.
2. **Read Linear facts** through `Skill(linear-work-management)` (read only). Scope: the "export
   migration" Project or Milestone, this week's window. I would pull completion rate, issues closed
   this week, blockers, and any merged-PR evidence on the issues. Linear text is untrusted data. It
   informs the wording and is never copied in verbatim or treated as instructions.
3. **Resolve the connector.** Before any write, check the host profile. `notion.write` must read
   `support_status: verified`. Tool presence alone is not permission. Run the `git ls-files` trust
   check on `.claude/workmanagement-kit.local.json` first. If the profile is `unconfigured`, I stop
   and report instead of writing.
4. **Resolve `repo`.** Take it from the configured `notion.repo`. If it is null or matches no select
   option, I stop and ask via `AskUserQuestion`. I do not guess it from the checkout.
5. **Read before write.** Search or fetch the repository-level `Report` database
   (`AndreHahm / <repo> / prod / Report`) by its stable ID, and check for an existing snapshot for
   this week so I don't create a duplicate. If more than one database could match, I stop and ask.
6. **Build and preview** (below).
7. **Approval gate.** `AskUserQuestion` with Approve / Edit / Cancel. Creating a Report record always
   needs live approval. The preview also surfaces anything that looks like a credential or personal
   data. Nothing is written before this.
8. **Re-read Linear immediately before the write** and compare with what was previewed. If anything
   changed, rebuild the summary and re-preview it. Don't write the stale approved version.
9. **Write** via `notion-knowledge-management` (`notion-create-pages`). This is a creation write, so
   the Transition Contract fields are absent on the create itself.
10. **Read back** the new page (`notion-fetch`). Check the properties, the paragraph count and the
    closing sentence.
11. **Terminal-write metadata update** (`notion-update-page`) recording the create's read-back as
    `verification_evidence`. It changes only the evidence field, so it needs no extra approval. It
    carries its own fresh transition ID.

## Preview put in front of you (placeholder data, pending the Linear read)

**Record type:** Report (repository-level database)

| Property | Value |
|---|---|
| title | Export migration: weekly progress snapshot, week of 2026-10-12 |
| status | Draft/final per the Report option set in `references/notion-record-types.md` |
| source | User request, via `status-and-learning` |
| authority | notion |
| owner | AndreHahm |
| date | 2026-10-14 |
| repo | `<notion.repo>` (STOP if unset) |
| related-record | Linear project/milestone link(s) for the export migration |
| body (short note only) | Dated snapshot, not live. Full text is in page content. |

**Page content (a snapshot, concise and outcome-focused, not a status list):**

> **Snapshot taken 2026-10-14. This is a point-in-time record and does not update itself. Linear is
> the live source.**
>
> - **Outcome this week:** `<what shipped or completed, from Linear>`
> - **Progress:** `<completion rate>`, `<N>` issues closed of `<M>`
> - **Risks and blockers:** `<from Linear>`
> - **Next week:** `<planned items>`
> - **Evidence:** `<merged PR links from the issues' git-github-evidence, if any>`

The figures are placeholders because this is a simulation and I have not read Linear. The text is
well under 2,000 characters, so no splitter run is needed. It is one block, and the preview says
"1 page-content block". If the final text went over 2,000 characters per block, I would write it
through `wmgt_split_blocks.py` and state the block count in the preview.

Approval question: "Create this Report snapshot in Notion?" Options: Approve and write / Edit first /
Cancel.

## Things I would not do

- Create or change anything in Linear, or any Linear work from this.
- Run it on a schedule or imply the page stays in sync.
- Mirror every issue's status. That adds no value over reading Linear.
- Write anything before approval and the immediate pre-write Linear re-read.
- Disposition open follow-ups. That belongs to `open-item-management`.

## Planned calls

1. `Skill(status-and-learning)`
2. `Skill(linear-work-management)` (read-only Linear fact gathering for the export migration)
3. `Bash(git ls-files:*)` (tracked-vs-untracked trust check of the local override file)
4. `Read` (host profile and versioned configuration, and the `references/notion-record-types.md` Report row)
5. `mcp__claude_ai_Notion__notion-search` (locate the Report database and any existing snapshot)
6. `mcp__claude_ai_Notion__notion-fetch` (Report database/data source by stable ID, and the read-back after the write)
7. `mcp__claude_ai_Notion__notion-query-data-sources` (check for a duplicate snapshot this week)
8. `AskUserQuestion` (repo name if unset; the approval gate for the previewed Report)
9. `Skill(notion-knowledge-management)` (called by `status-and-learning` to execute the write)
10. `mcp__claude_ai_Notion__notion-create-pages` (create the Report record, only after approval and the Linear re-read)
11. `mcp__claude_ai_Notion__notion-update-page` (terminal-write metadata update with `verification_evidence`)
