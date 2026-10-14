# Capture Idea: "Rework the export pipeline" (simulation, nothing written)

## What I did first

1. Read `notion-knowledge-management/SKILL.md`, `references/notion-record-types.md` and `references/long-text-blocks.md` (worktree copies only).
2. Classified the request: a new **Idea** record. The skill owns it (not `linear-work-management`, not `status-and-learning`), and it never touches Linear.
3. Connector and scope check: the shipped `host-profile.json` has `notion.read` and `notion.write` at `support_status: "unconfigured"`. I am assuming that your local override (`.claude/workmanagement-kit.local.json`) marks them `verified`. I would first run `git ls-files` on that override as the tracked-vs-untracked trust check, and I would stop if the file were tracked or the status were not `verified`. Nothing in this simulation tests that.
4. `repo` comes from `notion.repo` = "andres-cc-marketplace". You say the Idea database's `repo` select has that option. I would confirm that on the read before the write. If `notion.repo` were unset or matched no option, I would stop and report.

## Length check (the 2,000-character limit)

The body is 2,545 characters (UTF-16 units), which is over the 2,000 limit for a text property.
So I would **not** put it in the `body` property, and I would not truncate it. The skill's rule is:
the property holds only a short note, and the full text goes into the page content as blocks of at
most 2,000 characters.

I wrote the body to `<session scratchpad>/wmgt-body-20261014T120000Z.md` (a generated name, not built from
the content) and ran:

`python ${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_split_blocks.py split "<session scratchpad>/wmgt-body-20261014T120000Z.md" --start 0`

Result: `ok: true`, `total: 2`, `has_more: false`, so no further paging is needed.
- Block 1 runs from "The current export pipeline grew organically..." to "...without touching the others."
- Block 2 runs from "Observability is the fourth area..." to "...before cutting over."

The splitter cut on a blank line, so no cut falls inside a paragraph.

## Preview for approval (not yet written)

| Field | Value |
|---|---|
| Record type | Idea |
| Database | repository-level `AndreHahm / andres-cc-marketplace / <env> / Idea`, by stable ID from `versioned-configuration.json`; I would not pick it by name |
| `title` | Rework the export pipeline |
| `area` (required) | **Not supplied.** Proposed: "Data pipeline". Please confirm or change it. |
| `body` (property) | Short note: "Proposes reworking the nightly export into incremental, resumable extract, transform and publish stages. Full write-up is in the page content." (under 2,000 characters) |
| Page content | The full design write-up, as **2 blocks** of at most 2,000 characters, joined by blank lines |
| `repo` | andres-cc-marketplace |
| `status` | Initial status per the record-type defaults |
| `source` | User request |
| `authority` | notion |
| `owner` / `date` | You / 2026-10-14 |
| `related-record`, `linear-link`, `transition-id` | Empty. `transition-id` is absent on the create write itself (the creation-write exception). |

Page-content preview (first 2 lines of each block, the full text is in the scratchpad file):
- Block 1: "The current export pipeline grew organically around a single nightly job... This write-up proposes reworking the pipeline into incremental, resumable stages..." Then it covers the three-stage split, idempotent batches, and per-tenant scheduling.
- Block 2: "Observability is the fourth area... There are open questions..." Then it covers the staging-area and rollout questions.

Notes for the approval:
- The 2 blocks come from a cut at a paragraph boundary, so there is no mid-paragraph cut.
- The text has no markdown table or code fence, so the splitter cannot cut inside one.
- Sensitive-content scan of the captured text: no credentials, tokens or third-party personal data found.
- The write-up is placeholder prose that I generated for this simulation. A real run would use your text.

## Approval gate

I would ask with `AskUserQuestion` (creating any Idea always needs live approval): "Create this Idea record with a 2-block page body?"
Options: "Create as previewed", "Change the area first", "Cancel". I would not write anything before the answer.

## Calls after approval

1. `notion-fetch` on the Idea database (stable ID). It reads the schema and confirms the `repo` select has "andres-cc-marketplace" and that `area` and `body` are valid. This is a read and needs no approval.
2. `notion-create-pages` under the Idea database. It sets the properties above and puts block 1 as the page content.
3. `notion-update-page` with `insert_content` appends block 2 at the end of the page. If the append fails midway, I would report the page ID and the last block written, re-read the page, and resume from the next block. I would never re-create the page.
4. Read-back with `notion-fetch` on the new page. Confirm the properties (title, area, repo, short body note). Confirm each block's opening and closing words appear in order, and that the last paragraph ends with "...before cutting over." I would not compare block or paragraph counts, because the read-back has no block structure.
5. Record this write's transition per `FOUNDATION_CONTRACTS.md` (a creation write, so no prior `transition-id`). Its `verification_evidence` lands on the next write to this record, or via the terminal-write metadata write if none is planned. That metadata write needs no extra approval.

No Linear call is made. Promoting this Idea to Linear would be `idea-to-implementation`'s job, with its own approval.

## Planned calls

- `AskUserQuestion`
- `Bash` (`git ls-files` trust check on the local override file)
- `Bash` (`python ${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_split_blocks.py split <session scratchpad>/wmgt-body-20261014T120000Z.md --start 0`, already run once in this simulation)
- `Write` (the body file in `<session scratchpad>/`)
- `mcp__claude_ai_Notion__notion-fetch`
- `mcp__claude_ai_Notion__notion-create-pages`
- `mcp__claude_ai_Notion__notion-update-page`
