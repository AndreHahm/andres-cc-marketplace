# Capture an Idea in Notion: add `--dry-run` to the bulk exporter (simulation)

This is a simulation. I made no Notion or Linear calls. Below are the steps the skill requires and the preview I would put in front of you.

## 1. Classification

- This is a Notion Idea capture, so `notion-knowledge-management` applies. It is not a Linear action and not an Outcome/Learning, so `status-and-learning` and `linear-work-management` do not apply.
- It is small and clear, so I would not offer classification help from `work-intake-classifier`.
- It is an Idea only. I would not create any Linear work. Promotion to Linear is `idea-to-implementation`'s job, with its own approval.

## 2. Resolve the connector (before any read or write)

1. Run `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"` and branch on the outcome. Untracked (exit 1) means the override may be honored. Tracked or unverifiable means I fall back to the shipped `unconfigured` defaults and stop, with no write.
2. Read the host profile (`host-profile.json`) and the merged override. Confirm `notion.read` and `notion.write` both show `support_status: "verified"` with a non-null `verified_at`. Having the Notion tools in the session is not proof of permission.
3. Read `notion.repo` and `notion.databases.<env>.idea`. You told me `notion.repo` is `"andres-cc-marketplace"`. The Idea database is repository-level (`AndreHahm / andres-cc-marketplace / <env> / Idea`) and is found by its stored ID, not by title.
4. Confirm the `repo` option exists. You said it does. In the live run I would still check it in the `notion-fetch` read below rather than rely on that statement alone. If `notion.repo` were null, or the option were missing, I would stop and report without writing.

## 3. Reads (no approval needed)

- `notion-fetch` on the Idea database by its stored ID. This confirms the schema (`title`, `area`, `body`, `repo` select options, `status`) and that the `andres-cc-marketplace` option exists.
- `notion-search` and/or `notion-query-data-sources` for an existing Idea about "dry-run" or "bulk exporter". If one exists, I would show it and ask whether to capture a new Idea or reuse it. I would not guess.

## 4. Record built per the Idea property table

| Property | Value |
|---|---|
| `title` | Add `--dry-run` flag to the bulk exporter |
| `area` (required) | `tooling / exporter` (inferred, see open question below) |
| `body` (required) | "Add a `--dry-run` flag to the bulk exporter so a run can show what would be exported without writing or sending anything." (about 140 characters, well under the 2,000 limit) |
| `repo` (required select) | `andres-cc-marketplace` (from `notion.repo`, not from your message) |
| `status` | Initial status per the database's default option (read from the schema; I will not invent one) |
| `source` | Direct user request in this session (`workmanagement-kit`) |
| `authority` | `notion` |
| `owner` | You (resolved from the Notion user list or the override) |
| `date` | 2026-10-14 |
| `related-record` | none |
| `linear-link` | empty. This is populated only after `idea-to-implementation` promotes the Idea. |
| `transition-id` | absent on this create write, per the creation-write exception |

Length and safety checks:
- Every text property is under 2,000 characters, so the splitter `wmgt_split_blocks.py` is not needed. I would put no page-content body in, and no blocks.
- I found no credentials, tokens, or third-party personal data in the content, so no extra acknowledgment is needed.

## 5. Approval gate (required, no exception for a low-risk record)

I would show the table above and ask via `AskUserQuestion`:

> Create this Idea in the andres-cc-marketplace Idea database?
> - **Create it** — write the record exactly as previewed.
> - **Edit first** — change the title, area, or body before writing.
> - **Cancel** — write nothing.

Open question, asked in the same step or just before: the `area` value is my inference, because you didn't give one and the property is required. I would offer `tooling / exporter`, plus the 2 or 3 existing `area` values read from the database, with "Other" as the free-text fallback. If you chose "Edit first", I would re-preview and ask again.

## 6. Write and read-back (only after approval)

1. `notion-create-pages` with the parent set to the Idea database ID and the properties above.
2. Read the new page back with `notion-fetch` to confirm what was actually stored. That covers `title`, `area`, `body`, and that `repo` equals `andres-cc-marketplace`. The connector returning without error does not count as confirmation.
3. That read-back is the create's `verification_evidence`. It gets attached to the record's next write, per the next-write convention. The create write carried no transition fields.
4. If nothing more will be written to this record, I would do one metadata-only `notion-update-page` to record the evidence. It needs no new approval, since it changes only the evidence field. Only this step touches the record after creation.
5. If the create timed out or returned an unknown result, I would read current state first and never blindly retry.
6. Final report: the page link and ID, the read-back result, and a note that no Linear work was created (use `idea-to-implementation` if you want to promote it).

## Planned calls

Not called, because this is a simulation. In the live run, in order:

1. `Bash` (`git ls-files` trust check on `.claude/workmanagement-kit.local.json`)
2. `Read` (host profile, versioned configuration, local override)
3. `mcp__claude_ai_Notion__notion-fetch` (Idea database schema, `repo` options)
4. `mcp__claude_ai_Notion__notion-search` (existing similar Idea)
5. `mcp__claude_ai_Notion__notion-query-data-sources` (duplicate check, if search is inconclusive)
6. `AskUserQuestion` (area choice, then the create approval)
7. `mcp__claude_ai_Notion__notion-create-pages` (only after approval)
8. `mcp__claude_ai_Notion__notion-fetch` (read-back of the new page)
9. `mcp__claude_ai_Notion__notion-update-page` (optional terminal metadata write for `verification_evidence`)

No Linear tool and no `wmgt_split_blocks.py` call would be made.
