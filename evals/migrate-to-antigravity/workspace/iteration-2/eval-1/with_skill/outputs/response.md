Here's where to start — this is a one-time config move, handled by the `agy-migrate` tool.

## Steps

1. **Dry-run first.** Run `agy-migrate` with no flags. This produces a report of what it would do without changing anything.
2. **Read the report carefully**, especially the permissions-widening warning (see below — it matters).
3. **Apply the migration.** Run `agy-migrate --apply`. This performs the move and automatically backs up `~/.gemini/config` first, so you have a rollback point.
4. **Review the permissions proposal.** Check `~/.gemini/.agy-migrate/proposed-permissions.json`. Only run `agy-migrate --apply-permissions` if you're comfortable with the widened grants it lists.
5. **If you ever want to undo it**, `agy-migrate --uninstall --apply` reverses the whole migration.

## What actually moves

| Asset | How it moves | Notes |
|---|---|---|
| User skills | **Live**, not copied — `skills.json` gets an entry pointing at `~/.claude/skills` | Edits to a skill show up on both sides since it's the same directory |
| CLAUDE.md / auto-memory | Migrated | |
| MCP servers | Merged and translated into `mcp_config.json` | `url`/`httpUrl` → `serverUrl`, `type` is dropped, `env` is copied as-is |
| Installed plugins | Migrated | |
| Permissions | **Proposed only**, not applied automatically | See the widening warning below |
| Trusted workspaces | Migrated | |

## What can't move

- **Session transcripts.** Claude Code stores these as plain JSONL; Antigravity uses one SQLite database per conversation with opaque protobuf payloads. There's no writer that can translate between the two, so past conversations stay behind.
- **`tasks/`, `plans/`, `file-history/`, `jobs/`** — none of these have an equivalent path in Antigravity's layout.
- **Auth credentials.** Claude Code's and Antigravity's auth systems are entirely different — these are never copied, by design, not just as a current limitation.

## The permissions warning — read this before applying

Claude Code's `permissions.allow` stores whole command **lines**. Antigravity's `command()` matching works on a **prefix** instead. That difference is strictly a widening of what gets allowed — a line like `git commit -m "foo"` in Claude's allow-list becomes something that matches any command starting the same way in agy's model.

Because of that, the migration never auto-merges your permissions into agy's live `settings.json`. It writes the translated result to `~/.gemini/.agy-migrate/proposed-permissions.json` for you to review, and only merges it in if you explicitly run `agy-migrate --apply-permissions`. Don't skip reading that file — it's the one part of the migration that can silently make things more permissive than you intended.

## Bottom line

Run `agy-migrate` (no flags) now to see the dry-run report, read it end to end, then decide on `--apply` and separately on `--apply-permissions` once you've reviewed the proposed grants.
