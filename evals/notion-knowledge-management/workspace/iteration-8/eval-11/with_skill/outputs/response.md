# Log the quarterly export-performance write-up as a Report

I read the skill and its two references. This is a Report, which the skill owns. It is not a progress snapshot, so it does not go to `status-and-learning`. Nothing has been written; this is the plan and preview.

## Pre-checks
1. Host profile and override trust. I would read `host-profile.json` and `.claude/workmanagement-kit.local.json`. First I would run `git ls-files` on the override file to confirm it is untracked. I would proceed only if `notion.write` reads `support_status: verified`. If it still reads `unconfigured`, I stop and report.
2. `repo`. `notion.repo` is "andres-cc-marketplace", so that is the `repo` value. I would confirm it matches an option in the Report database's `repo` select. If it matches none, I stop and report.
3. Target. Report lives in the repository-level database `AndreHahm / andres-cc-marketplace / <env> / Report`. I would resolve it by stable ID from the versioned configuration, not by title. If the ID is missing, I run the Bootstrap flow instead.

## Long-text handling
The write-up is about 7,000 characters, and a text property is capped at 2,000. The `body` property therefore holds only a short note. The full text goes into page content as blocks, split by the splitter. This is the rule the skill gives for this case.

- I generated about 7,029 characters of placeholder prose and wrote it to `<session scratchpad>/wmgt-body-20261014T120000Z.md`. That is a generated name, outside the repo root.
- I ran `wmgt_split_blocks.py split "<session scratchpad>/wmgt-body-20261014T120000Z.md" --start 0`. The result: `ok`, `total: 4`, `has_more: false`. The block lengths are 1638, 1663, 1728 and 1994, all within 2,000 UTF-16 units. That is one page of results, so no `--start` continuation is needed.
- The text has no tables or code fences. A cut between blocks 2 and 3 or inside a paragraph will read back as a paragraph break.

## Preview for approval
Record type: Report, in the Report database for repo andres-cc-marketplace.

| Property | Value |
|---|---|
| title | Quarterly export-performance write-up |
| summary | Executive summary of the quarter's export volume, regional results, product mix, logistics, currency, customer concentration, risks and outlook (placeholder text) |
| body | "Full write-up is in the page content (4 blocks, about 7,000 characters)." Well under 2,000 characters |
| open-items | none |
| repo | andres-cc-marketplace |
| source | user request |
| authority | notion |
| owner / date | the requesting user / 2026-10-14 |
| status | per the shared property default |
| transition-id | absent on this create write (creation-write exception) |

Page content: 4 blocks, each at most 2,000 characters, joined by blank lines in the first create call. Block 1 opens "Overview. Export performance this quarte..." and block 4 closes with "...End of the quarterly write-up."

Sensitive-content scan: I found no credentials, tokens or personal data in the text. It is placeholder prose. Real content would be scanned again at this step.

## Approval gate
Creating a Report needs live approval, with no exception for archival records. I would call `AskUserQuestion` with "Create this Report?" and options "Create it" and "Cancel". Nothing is written until the user picks "Create it".

## Write and read-back, after approval
1. Create the page in the Report database with the properties above and all 4 blocks as page content. All 4 fit in one call, so no append is needed. If an append were needed and failed, I would report the page ID and the last block written and resume from the next block. I would never re-create the page.
2. Read the page back. For each of the 4 blocks, check that its opening words and closing words appear in order. Check that the last paragraph ends with the source's closing sentence. Do not compare block or paragraph counts.
3. Record this write's transition per the Transition Contract. There is no `verification_evidence` yet for a create write.
4. I would not touch Linear.

## Planned calls
- Skill: Read of SKILL.md and its two references (done)
- Bash: `python wmgt_split_blocks.py split` (run) and `git ls-files` for the override trust check
- Write: the body file in the session scratchpad
- Read: `host-profile.json`, `versioned-configuration.json` and `.claude/workmanagement-kit.local.json`
- AskUserQuestion: the approval gate
- mcp__claude_ai_Notion__notion-fetch: resolve the Report database and its `repo` select options by stable ID, then read back the created page
- mcp__claude_ai_Notion__notion-create-pages: create the Report with the 4 blocks as content
