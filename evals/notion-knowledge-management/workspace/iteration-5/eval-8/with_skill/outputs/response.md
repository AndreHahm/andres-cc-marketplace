# Capture Idea: add a --dry-run flag to the bulk exporter (simulation)

No Notion or Linear tool was called. This describes the calls I would make.

## Skill routing
The request is "capture this as an idea in Notion", so it belongs to `notion-knowledge-management`.
It is not `status-and-learning` (no outcome to summarize) and not `linear-work-management` or
`idea-to-implementation` (no Linear work is requested). I will not create any Linear issue.

## Planned steps

1. **Resolve the connector (no approval needed).**
   - Read `host-profile.json`. It ships with `notion.read` and `notion.write` as `unconfigured`.
   - Run the trust check on `.claude/workmanagement-kit.local.json`:
     `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`.
     Only exit 1 (confirmed untracked) lets me honor its overrides. A tracked or unverifiable result
     falls back to `unconfigured`, and I stop.
   - Proceed only if `notion.read` and `notion.write` read `verified`. Having the Notion tool
     available does not count as permission. For this simulation I assume both are verified.
2. **Check `repo`.** `notion.repo` = `andres-cc-marketplace`, and the Idea database's `repo` select has
   that option. This passes. If it were unset or matched no option, I would stop and report. I take
   the value from configuration, never from the idea's content.
3. **Load the property table** (`references/notion-record-types.md`, Idea).
   Required beyond the shared set: `title`, `area`, `body`.
4. **Resolve the target by stable ID.** The Idea database is repository-level, at
   `AndreHahm / andres-cc-marketplace / <env> / Idea`. I take its ID from
   `versioned_configuration.notion.databases`, never from the title. If more than one candidate
   matched, I would stop and hand the choice to you.
5. **Build the record and preview it** (below). Check each text property is at most 2,000 characters.
   The body is short, so no page-content splitting is needed and `wmgt_split_blocks.py` is not used.
6. **Get live approval via `AskUserQuestion`.** Creating an Idea always needs approval. The question
   would be "Create this Idea in Notion?" with options Create / Edit first / Cancel. The preview
   contains no credentials, tokens or third-party personal data, and that is stated in the prompt.
7. **Write** (only after approval): `mcp__claude_ai_Notion__notion-create-pages`:
   ```
   parent: { data_source_id: <Idea database data source ID from configuration> }
   pages: [{ properties: {
     "title":   "Add a --dry-run flag to the bulk exporter",
     "area":    "<confirmed area, see open question>",
     "body":    "<body text from preview>",
     "source":  "user request (direct)",
     "authority": "notion",
     "owner":   "<owner, see open question>",
     "date":    "2026-10-13",
     "status":  "<initial status option, e.g. new>",
     "repo":    "andres-cc-marketplace"
   } }]
   ```
   Per the creation-write exception, this create carries no `transition-id` fields. The new page's ID
   does not exist yet, and the create itself carries none of the Transition Contract's fields.
8. **Read back** with `notion-fetch` on the returned page ID. Confirm title, area, body, `repo` and
   status were stored as written. The read-back is the create's `verification_evidence`. I never
   assume success because the call returned without error. On a timeout or unknown result I read
   current state before any retry and never repeat the write blindly.
9. **Next write.** None is planned. The Idea's `linear-link` stays empty. It is filled only if you
   later promote the idea through `idea-to-implementation`. Because no further write is planned,
   the terminal-write exception applies. I would then do one metadata-only write recording the
   create's `verification_evidence`, plus this write's own `transition_id`, `affected_record` and
   `source_plugin: "workmanagement-kit"`. It changes only the evidence fields, so it needs no new approval.
10. Report the page URL/ID and state that no Linear work was created.

## Preview shown for approval

| Field | Value |
|---|---|
| Record type | Idea (database: AndreHahm / andres-cc-marketplace / <env> / Idea) |
| title | Add a --dry-run flag to the bulk exporter |
| area | exporter / tooling (proposed, please confirm) |
| body | Add a `--dry-run` flag to the bulk exporter so a run reports what it would export without writing anything. Lets users check scope and counts before a real bulk export. |
| repo | andres-cc-marketplace (from `notion.repo`; matches an existing option) |
| source | user request |
| authority | notion |
| owner | <current user, confirm> |
| date | 2026-10-13 |
| status | initial status for new Ideas (per database's options) |
| related-record | none |
| linear-link | none (not set at capture) |

Length check: every text property is well under 2,000 characters. No credential or personal data
detected. No Linear action is included.

## Open questions before the write
- `area` is required and you did not give one. I proposed "exporter / tooling", which you must
  confirm. I would not guess it silently.
- `owner` is required and I would confirm it with you.
- The first approval prompt carries these confirmations together with the Create / Edit / Cancel choice.
