---
name: migrate-to-antigravity
description: >-
  Move an existing Claude Code setup onto the Antigravity CLI (agy) — user skills, CLAUDE.md,
  auto-memory, MCP servers, installed plugins, permissions and trusted workspaces. Use when the
  user says "migrate to Antigravity", "move my Claude Code config to agy", "bring my
  skills/memory/MCP over", "set up agy like my Claude Code", "agy plugin import claude found
  nothing", or asks what can and cannot be carried across. Also use to explain the two config
  layouts, or to reverse a migration. Not for ongoing, per-task delegation of work to
  Antigravity/Gemini once set up — see the sibling `antigravity` skill for that.
allowed-tools: Bash(agy-migrate:*), Read
---

# Migrating Claude Code → Antigravity CLI

## Quick Start

1. Run `agy-migrate` with no flags for a dry-run report.
2. Read the report, including the permissions-widening warning.
3. Run `agy-migrate --apply` (backs up `~/.gemini/config` first).
4. Review `~/.gemini/.agy-migrate/proposed-permissions.json` and only merge it with
   `--apply-permissions` if you accept the widened grants.
5. `agy-migrate --uninstall --apply` reverses everything if needed.

## When to Use

- A one-time move of skills/memory/MCP/permissions from Claude Code onto agy.
- Explaining the two products' config layouts, or reversing a prior migration.

## When NOT to Use

- **Ongoing, per-task delegation of work to Antigravity/Gemini** once migration is
  done (or without ever needing it) — use the sibling `antigravity` skill instead;
  this skill is a one-time config move, not a recurring delegation workflow.

Run `agy-migrate` (dry-run) → read the report → `agy-migrate --apply`.
`agy-migrate --uninstall --apply` reverses everything.

The tool treats the Claude Code config dir as **read-only**. The single exception is
an `AGENTS.md` symlink placed beside an existing `CLAUDE.md`, and only under
`--include-repos`.

---

## Where the two products keep things

**Claude Code** — `~/.claude/` plus `~/.claude.json`, relocatable together via
`CLAUDE_CONFIG_DIR`. Two things surprise people: there is usually no
`~/.claude/CLAUDE.md`, and **auto-memory is per project**, under
`~/.claude/projects/<encoded-cwd>/memory/`. The encoding maps `/`, `_` and `.` all to
`-`, so it can only be matched forward (re-encode a known path), never decoded.

**Claude Desktop / Cowork is a separate universe.** It has its own
`~/Library/Application Support/Claude/claude_desktop_config.json` (MCP) and
`Claude Extensions/` (`.mcpb`), and its Cowork skills are server-synced into
`local-agent-mode-sessions/skills-plugin/`, so no local original exists to migrate.
Only `claude_desktop_config.json`'s `mcpServers` is portable, and the tool picks it up.
The bundled `claude-code/<version>/claude.app` inside the desktop app is the ordinary
CLI and does read `~/.claude`.

**Antigravity** — rooted at `~/.gemini/`, not `~/.antigravity`:

| Path | Shared by |
| --- | --- |
| `~/.gemini/config/` — `mcp_config.json`, `skills/`, `plugins/`, `skills.json`, `projects/` | CLI **and** both desktop apps |
| `~/.gemini/antigravity-cli/settings.json` | `agy` only |
| `~/.gemini/{antigravity-cli,antigravity,antigravity-ide}/` — conversations, brain, knowledge | each surface separately |

So customization is shared across surfaces; session state is not.

---

## What moves, and how

| Asset | Mechanism | Notes |
| --- | --- | --- |
| User skills | **live** — `skills.json` entry pointing at `~/.claude/skills` | no copy; edits show up on both sides |
| Installed plugins | native `agy plugin import claude`, run in a staging HOME | output is then repaired (below) |
| `CLAUDE.md` | symlink `AGENTS.md` → `CLAUDE.md` | `--include-repos`; both are plain Markdown |
| Auto-memory | **generated** rules | global → a plugin's `rules/`; per-repo → `<repo>/.agents/rules/` |
| MCP servers | merged + translated into `mcp_config.json` | `url`/`httpUrl` → `serverUrl`, `type` dropped, `env` copied verbatim (see below) |
| Trusted projects | `trustedWorkspaces` | the one clean settings mapping |
| Permissions | **proposal only** by default | see the warning below |

### Cannot move

Session transcripts. Claude Code writes plain JSONL; Antigravity writes one SQLite
database per conversation whose payloads are opaque protobuf blobs
(`steps.metadata`, `gen_metadata.data`, …). There is no supported writer.
Also unmovable: `tasks/`, `plans/`, `file-history/`, `jobs/`, and Claude Code's own
auth credentials (different auth systems entirely — never copy these).

**Exception, and it matters:** an MCP server's own `env` block (API keys, tokens —
whatever that server's own config carries) **is** copied verbatim into the new
`mcp_config.json`, because the server needs it to keep working under Antigravity.
This applies to the user-level `~/.gemini/config/mcp_config.json` and to every
per-plugin `~/.gemini/config/plugins/<name>/mcp_config.json` the plugin importer
repairs. `agy-migrate` locks every one of these files down (`chmod 0600`) so none
is left world-readable, but the secret itself now lives in a second (or third,
fourth…) file — review each `mcp_config.json` after a migration the same way
you'd review any file that holds credentials.

---

## Four behaviours that will bite you

These are measured against agy 1.1.12, and none of them are documented.

1. **A rule without `trigger: always_on` is silently ignored.** No error, no warning.
   Only bare `AGENTS.md` / `GEMINI.md` are always-on without frontmatter. Migrated
   memory is therefore *rewritten with* frontmatter, never stripped of it.
2. **Workspace `.agents/` only loads when the session is bound to an agy project —
   and registering one is not enough for headless runs.** `agy -p` always uses the id
   in `antigravity-cli/cache/default_project_id.txt` (`default-cli-project` out of the
   box) regardless of cwd. The tool registers each repo and **prints the id**; run
   `agy --project <id>` there, or pick the project in the TUI. Global
   `~/.gemini/config/` loads regardless, which is why global memory goes to a plugin.
3. **`~/` is not expanded in the global `skills.json`.** Entry paths must be absolute.
4. **Rules and workflows are capped at 12,000 characters per file.** Oversized memory
   is split into `-1.md`, `-2.md` parts on paragraph boundaries.

## What the native importer gets wrong

`agy plugin import claude` exists and handles skills, agents, commands, hooks and MCP —
but:

- It only scans `~/.claude/plugins/<name>/` **one level deep**, which no Claude Code
  2.x install matches (plugins live under `plugins/cache/<marketplace>/<plugin>/<version>/`),
  so on a real machine it prints `No claude extensions found.` and exits 0.
  It also does not follow symlinks, so the staging HOME must contain real copies.
- It **destroys remote MCP servers**: `{"type":"http","url":…}` becomes
  `{"command":"","args":null}` — the URL is dropped and no `serverUrl` is written.
- It **copies hooks verbatim**. Antigravity's `hooks.json` is a map of *named* hooks
  (`{"my-hook": {"PreToolUse": [...]}}`), its matchers are step-type names
  (`run_command`, not `Bash`), and it fires only `PreToolUse`, `PostToolUse`,
  `PreInvocation`, `PostInvocation`, `Stop` — `SessionStart`, `SessionEnd`,
  `PreCompact`, `Notification` and `SubagentStop` have no equivalent. `${CLAUDE_PLUGIN_ROOT}` is
  never set, so hook commands referencing it break.

`agy-migrate` runs the importer anyway (so the output tracks Google's format), then
repairs all three and drops the leftovers it copies.

## Permissions widen the grant — always review

Claude's `permissions.allow` stores whole command **lines**, quoted prompts included,
not command prefixes. They cannot map 1:1 onto agy's `command()`, which matches on a
prefix. The tool keeps the executable plus one plain sub-word (`Bash(git diff:*)` →
`command(git diff)`), absorbs redundant prefixes, and drops entries whose executable
position holds a variable or shell metacharacter.

That is strictly a widening. So the result is written to
`~/.gemini/.agy-migrate/proposed-permissions.json` for review, and merged into
`settings.json` only with `--apply-permissions`.

Also not migrated, by design: `model` (no Gemini equivalent for a Claude model id),
`effortLevel` (agy's `--effort` is a per-session flag, `low|medium|high` only), and
`env` (Anthropic/Vertex routing that means nothing to agy).

---

## Flags

| Flag | Effect |
| --- | --- |
| *(none)* | dry-run report |
| `--apply` | perform it; backs up `~/.gemini/config` first |
| `--only` / `--skip` | `plugins,skills,claudemd,memory,mcp,settings` |
| `--include-repos` | write into git repos (`AGENTS.md`, `.agents/rules/`) |
| `--include-orphan-memory` | fold memory whose source directory no longer exists into global rules |
| `--apply-permissions` | actually write the translated allow-list |
| `--no-register-projects` | skip agy project registration (workspace rules then stay inert) |
| `--roots` | scope for `CLAUDE.md` and MCP discovery (default: the project paths recorded in `~/.claude.json`, or `~` if there are none). The desktop app's `claude_desktop_config.json` is global and always included. |
| `--json` | machine-readable plan |
| `--uninstall` | remove what was generated |

Re-running is safe: generated files carry a marker comment, and a file whose marker
you deleted is treated as yours and left alone.

## Reference Guide

| Resource | Read when |
|---|---|
| `docs/MIGRATION.md` | The full layout reference, the compatibility matrix, and how each behavior above was measured — this skill covers the workflow, that doc covers the detail |

## Testing & Validation

**Last dated run record:** 2026-09-16, `evals/migrate-to-antigravity/` — 2/2 evals, 7/7 assertions passed (Quick Workflow).

**Verify this skill activates on:**
- "migrate to Antigravity" / "move my Claude Code config to agy"
- "bring my skills/memory/MCP over"
- "agy plugin import claude found nothing"

**Verify it does NOT activate on:**
- "delegate this task to antigravity/gemini" → `antigravity` skill instead
- a question about ongoing cost/routing discipline, not a one-time config move

**Quality gates:**
- [ ] Always runs the dry-run report before suggesting `--apply`
- [ ] Never applies permissions without `--apply-permissions` explicitly requested
- [ ] States plainly what cannot move (session transcripts, tasks/plans/file-history/jobs, credentials)

