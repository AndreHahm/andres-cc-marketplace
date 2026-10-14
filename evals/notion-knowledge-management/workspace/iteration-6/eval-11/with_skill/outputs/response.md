# Log the quarterly export-performance write-up as a Notion Report (simulation)

Nothing has been written. No Notion or Linear tool was called.

## Checks before building the record

- **Skill routing.** This is a direct request to log a Report, so it belongs to `notion-knowledge-management`. It is not an Outcome/Learning summary, so `status-and-learning` is not involved. Linear is never touched.
- **Connector scope.** The shipped `host-profile.json` has `notion.read` and `notion.write` at `support_status: "unconfigured"`. In a real run I would first check `.claude/workmanagement-kit.local.json`. If the file is git-tracked I would ignore it. I would only proceed if both operations read `verified`. For this simulation I assume they do, and I say so here.
- **`repo`.** `notion.repo` is "andres-cc-marketplace". I would confirm it matches an existing option in the Report database's `repo` select. If it matched none, I would stop and report instead of writing.
- **Where Reports live.** A Report is a repository-level type. The target is the database `AndreHahm / andres-cc-marketplace / prod / Report` on the page `AndreHahm / andres-cc-marketplace / prod`. I would resolve it by the stable ID stored in the versioned configuration, not by title.
- **Long text.** Notion text properties and blocks are held to 2,000 characters. The write-up is longer, so it cannot go in `body`. `body` keeps a short note, and the full text goes into page content as blocks of at most 2,000 characters, split by `wmgt_split_blocks.py`.

## Splitter run (real, on a scratchpad file)

I generated placeholder prose with 8 paragraphs and wrote it to `<session scratchpad>/wmgt-body-20261014T120000Z.md`. It is 6,445 characters, a little under the "about 7,000" you asked for, and the splitter behaves the same at either length.

```
python ${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_split_blocks.py split "<session scratchpad>/wmgt-body-20261014T120000Z.md" --start 0
-> ok, max_units 2000, total 4 blocks, returned 4 (lengths 1600, 1602, 1604, 1633)
```

All 4 blocks are under 2,000 characters, and `total` is 4, so one page of blocks is enough. No `--start` paging is needed, because the splitter returns ten blocks per page.

## Preview for approval

**Database:** `AndreHahm / andres-cc-marketplace / prod / Report`

| Property | Value |
|---|---|
| title | Q3 Export Performance Review |
| summary | Quarterly write-up of export performance across regional demand, freight, currency, customs, pricing, customer concentration, supplier lead times and outlook (placeholder prose). |
| body | "Full write-up is in the page content below (4 blocks, about 6,450 characters)." This is under 2,000 characters. |
| open-items | none |
| source | user request |
| related-record | none |
| authority | notion |
| transition-id | absent on the create write (creation-write exception) |
| owner | AndreHahm |
| date | 2026-10-14 |
| repo | andres-cc-marketplace (from `notion.repo`) |
| status | the shared status default, which I would confirm against the schema |

**Page content:** the 4 blocks, joined by blank lines. Block 1 opens "Regional demand. During the quarter, export performance...". Block 4 ends "This concludes the write-up."

Notes on the page content:
- Each block holds whole paragraphs, so no paragraph is cut. If a cut did land inside a paragraph, it would read as a paragraph break after reassembly.
- The text has no tables or code fences, so there is no risk of a split landing inside one.
- I scanned the text for credentials, tokens and third-party personal data and found none.

**Approval gate.** I would ask via `AskUserQuestion`: "Create this Report in `AndreHahm / andres-cc-marketplace / prod / Report` with 4 page-content blocks?" The options would be Create, Edit first and Cancel. Creating a Report always needs this approval.

## Plan after approval (not executed)

1. Create the page with `notion-create-pages` in the Report database. It sets the properties above, and the page content is blocks 1 to 4 joined by blank lines.
2. Read the page back with `notion-fetch`.
   - The read-back is Markdown with one line per paragraph, so a block count cannot be observed.
   - I would check that the paragraph count is 8, matching the source, and that the last paragraph ends with "This concludes the write-up."
   - I would also check the properties, especially `repo` and the length of `body`.
3. If the page creation succeeds but an append fails, I would report the page ID and the last block written, re-read the page, and resume from the next block. I would never re-create the page. Here the 4 blocks fit in one create call, so no append is expected.
4. Record the transition per the plugin's transition contract. This was the create write, so `verification_evidence` lands on the next write to this record.
5. Do not create Linear work from this Report.

## Planned calls

- `Read` (done): SKILL.md, `references/long-text-blocks.md`, `references/notion-record-types.md`, `host-profile.json`
- `Bash` (done): `wmgt_split_blocks.py split` on the scratchpad file
- `Bash(git ls-files)`: trust check on `.claude/workmanagement-kit.local.json` before honoring it
- `mcp__claude_ai_Notion__notion-fetch`: resolve the Report database by stable ID, check the `repo` options, and read back the created page
- `AskUserQuestion`: approval gate before the write
- `mcp__claude_ai_Notion__notion-create-pages`: create the Report page with properties and the 4 page-content blocks (only after approval)
