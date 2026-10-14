# Record a Decision: move transition history export to a background job

## Result: I am stopping before any write

This is a Decision record, so it needs the required `repo` property. The skill sets `repo` only from the resolved `notion.repo` value. It never takes it from the record's content, your message, or the checkout. `notion.repo` is null, so there is no valid `repo` option to write. The skill says to stop and report in this case, not to write the record without `repo` or guess a value.

Nothing is written to Notion or Linear. Nothing is created or changed in Linear either, because this skill never touches Linear.

## What I need from you

The skill's Bootstrap rules say the repo name must be asked of the user, not inferred from the checkout. I would ask via `AskUserQuestion`:

- Question: "`notion.repo` is not set. Which repository name should this Decision (and later records) be filed under?"
- Options: the repository name you give me, or "Stop for now".
- The answer is recorded through the local override, `.claude/workmanagement-kit.local.json`. Before honoring that file I would run the tracked-vs-untracked trust check (`git ls-files`). A tracked copy falls back to the shipped `unconfigured` defaults.
- I would also confirm the host profile's `support_status` for `notion.write` is `verified`. The shipped default is `unconfigured`, and tool presence alone is not permission.
- I would confirm the `repo` select option exists on the Decision database. If it is missing, adding it is a schema change that goes in a Bootstrap plan for your approval.

## Preview of the record, for review only (no approval needed to preview)

The Decision belongs in the repository-level `decision` database, titled `AndreHahm / <repo> / <env> / Decision`. The `<repo>` segment is unresolved until you answer.

| Property | Value |
|---|---|
| title | Move transition history export to a background job |
| decision-state | proposed (you said "record a decision"; accept it later as a separate approved step) |
| context | Draft: the transition history export currently runs in the request path. Please supply the actual reason, for example latency or timeouts. I won't invent it. |
| alternatives | Draft: keep it synchronous (status quo). Please add any others you weighed. |
| consequences | Draft: the export becomes asynchronous. Please confirm the expected effects, for example delivery delay or a completion notification. |
| source | user request |
| related-record | none |
| authority | notion |
| transition-id | absent (creation-write exception) |
| owner | you |
| date | 2026-10-14 |
| repo | **unresolved: blocked (`notion.repo` is null)** |
| status | not tracked on Decisions (`decision-state` is the sole state) |

Each text value is well under 2,000 characters, so the splitter is not needed. No credentials or personal data appear in the content.

## Once you give a repo name

1. Resolve the connector and host profile, and run the trust check on the local override.
2. Read the decision database to confirm it exists and the `repo` option matches.
3. Show the final preview, with the context, alternatives and consequences you confirm.
4. Ask via `AskUserQuestion` for explicit approval. Creating a Decision is unconditionally approval-gated, even though it starts as `proposed`.
5. Create the page, then read it back to verify. Record the transition per the Transition Contract.

Accepting the Decision later is a separate approved step.

## Planned calls

- `Read`: host profile, versioned configuration and local override (plugin-root files)
- `Bash` (`git ls-files` trust check on `.claude/workmanagement-kit.local.json`)
- `AskUserQuestion`: ask for the repository name to set `notion.repo`
- After the answer and an `AskUserQuestion` approval of the final preview:
  - `mcp__claude_ai_Notion__notion-fetch` or `mcp__claude_ai_Notion__notion-search`: read the Decision database and `repo` options
  - `mcp__claude_ai_Notion__notion-create-pages`: create the Decision (not called now, blocked)
  - `mcp__claude_ai_Notion__notion-fetch`: read-back after the write (not called now)
- No Linear tools.
