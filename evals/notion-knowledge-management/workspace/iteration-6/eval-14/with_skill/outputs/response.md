# Capture Idea: "Rework the export pipeline" (simulation, nothing written)

I followed `notion-knowledge-management`. This is an Idea capture, so it is in scope and needs the live approval gate. Linear is not touched.

## Pre-flight checks

1. **Host profile.** `host-profile.json` ships every operation as `support_status: "unconfigured"`. I would read `.claude/workmanagement-kit.local.json`, but only after the tracked-vs-untracked trust check (`git ls-files` on that file). `notion.write` must read `verified` before any write. If it still reads `unconfigured`, I stop and report that instead of writing.
2. **`repo`.** You gave `notion.repo = "andres-cc-marketplace"`. The Idea database's `repo` select has that option, so it matches. If it did not, I would stop rather than write.
3. **Record type.** Idea. Required properties are `title`, `area`, `body`, plus the shared set (`source`, `authority`, `owner`, `date`, `repo`, `status`, `related-record`). `transition-id` is absent on the create write, per the creation-write exception.
4. **Body length.** The write-up is 2,819 characters (UTF-16 units, as the splitter counts), over the 2,000 limit for a text property. The skill forbids both writing it into a property and truncating it. So the full text goes into **page content** as blocks, and the `body` property holds only a short note.
5. **`area` is required, and you did not give one.** I will not guess it. It is asked at the approval step below.

## Splitter run (done in the session scratchpad)

- I wrote the placeholder prose to `<session scratchpad>/wmgt-body-20261014T120000Z.md`. It is six paragraphs of plain prose with no tables or code fences.
- I ran `wmgt_split_blocks.py split "<session scratchpad>/wmgt-body-20261014T120000Z.md" --start 0`.
- Result: `ok: true`, `max_units: 2000`, `total: 2`. Block 1 is 1,567 units (paragraphs 1-4) and block 2 is 1,250 units (paragraphs 5-6). Both splits fell on blank lines, so no paragraph was cut.

## Preview for approval

| Field | Value |
|---|---|
| Record type | Idea |
| Database | Idea database, repository-level scope (`AndreHahm / andres-cc-marketplace / <env> / Idea`) |
| `title` | Rework the export pipeline |
| `area` | ASK (required, not supplied) |
| `repo` | andres-cc-marketplace (from `notion.repo`; matches an existing option) |
| `body` property | Short note only: "Design write-up for reworking the export pipeline (schemas at stage boundaries, idempotent stages, run ledger). Full text in page content." |
| `source` | User request |
| `authority` | notion |
| `owner` / `date` | Current user / 2026-10-14 |
| `status` | Initial status value for an Idea (from the database schema) |
| `transition-id` | Absent (create write) |
| Page content | **2 blocks** (1,567 + 1,250 units): the full 2,819-character write-up, joined by blank lines |

**Notes for you:**
- The two blocks split on paragraph boundaries. A cut inside a paragraph would read as a paragraph break after reassembly, but none occurs here.
- The text has no tables or code fences, so the splitter cannot land inside one.
- I scanned the text for credentials, tokens and third-party personal data and found none. It is generic placeholder prose.
- Nothing is created in Linear. Promoting this Idea is `idea-to-implementation`'s separate, approval-gated job.

First paragraph of the content, for review: "The current export pipeline grew organically from a single nightly script into a chain of loosely coupled jobs, and it now shows its age. ..." The full text is in the scratchpad file.

## Approval gate (AskUserQuestion, before any write)

1. **Question: "Which `area` for this Idea?"** Options are the 2-4 most plausible values (for example "Data pipeline", "Infrastructure", "Tooling"), plus the automatic Other.
2. **Question: "Create this Idea as previewed (title, repo, 2 page-content blocks)?"** Options: "Create as previewed", "Change something", "Cancel". The two questions are asked one at a time, in sequence, not batched.

Approval is unconditional. Nothing is written without it.

## Write and read-back (after approval)

1. `notion-fetch` on the Idea database (by stable ID from the versioned configuration) to confirm the schema, the `repo` option and the `area` options.
2. `notion-create-pages` with the properties above. Page content is block 1 (paragraphs 1-4).
3. `notion-update-page` with `insert_content` appending block 2 at the end. If this append fails, I report the page ID and the last block written, re-read the page, and resume from the next block. I never re-create the page.
4. **Read-back:** `notion-fetch` the new page. A block count cannot be observed, since the read-back returns one Markdown line per paragraph. So I check that the page has six paragraphs, equal to the source, and that the last one ends with the source's closing sentence ("...where the time and the failures actually are."). I also check that `repo`, `area` and `title` were stored as written.
5. Record this write's transition per the Transition Contract. The create-write exception applies, so its `verification_evidence` lands on the next write to this record, or via the terminal-write metadata write, which needs no further approval.

## Planned calls

- Skill: `notion-knowledge-management` (this skill)
- Read (`SKILL.md`, `references/notion-record-types.md`, `references/long-text-blocks.md`, `host-profile.json`)
- Bash(`git ls-files`), for the local-override trust check
- Write (the session-scratchpad body file `wmgt-body-<timestamp>.md`)
- Bash(`wmgt_split_blocks.py`), to split the body file (done in this simulation)
- AskUserQuestion (twice, sequentially: the `area` choice, then the approval to create)
- mcp__claude_ai_Notion__notion-fetch (the Idea database schema; later the read-back)
- mcp__claude_ai_Notion__notion-create-pages (the Idea page with block 1)
- mcp__claude_ai_Notion__notion-update-page (`insert_content` to append block 2)
- mcp__claude_ai_Notion__notion-fetch (the read-back, listed again as a separate call)

No Linear tools. None of the Notion calls were actually made in this simulation.
