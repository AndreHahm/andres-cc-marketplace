# Codex Subagents Schema

Reference for the TOML schema Codex's custom-subagent configuration supports, and how this repo
generates it.

Source: <https://learn.chatgpt.com/docs/agent-configuration/subagents?surface=app>

## File location

Custom agents live as TOML files in `~/.codex/agents/` (personal) or `.codex/agents/`
(project-scoped — what this repo uses).

## Schema

Required fields:

- `name`
- `description`
- `developer_instructions`

Optional fields (inherited from `config.toml`'s `[agents]` section unless overridden per file):

- `model` / `model_reasoning_effort`
- `sandbox_mode` — accepted, but has no effect in a custom agent file (see below)
- `mcp_servers`
- `skills.config`

**There is no `tools` field in this schema.** Precedence when a value could come from more than one
place: explicit spawn values → the agent's own TOML file → `[agents]` config defaults → parent
session values. Sandbox and approval settings are the exception: a subagent always inherits them from
the parent turn (see "No sandbox in the exports" below).

## How this repo generates it

`.codex/agents/*.toml` is a **generated export**, not hand-authored — see
[`.claude/marketplace-sync.json`](../.claude/marketplace-sync.json)'s `codex_exports.agents` for the
registered list, and [`scripts/marketplace_ci/conversion.py`](../scripts/marketplace_ci/conversion.py)'s
`convert_agent()` for the actual Claude-agent-Markdown → Codex-TOML conversion. **Never hand-edit a
file under `.codex/agents/` directly** — edit the canonical `.claude/agents/<name>.md` source instead
and run `uv run python -m scripts.marketplace_ci convert-codex-exports` (or let `commit`'s own
targeted-repair step do it automatically when the source is staged — see `plugins/git-kit/skills/commit/SKILL.md`).

`convert_agent()` deliberately drops the Claude-side `tools:` frontmatter field rather than carrying
it into the TOML, since Codex's schema has no equivalent field. Earlier it copied `tools` through
verbatim as `tools = [...]`, which is invalid Codex-side and silently broke every agent that declared
`tools:` in its Claude frontmatter — fixed 2026-09-02.

### No sandbox in the exports (issue #700)

Per Codex's subagent docs (quoted below), a subagent always inherits the parent turn's sandbox and
approval settings, so `sandbox_mode` in a custom agent file is ignored. `convert_agent()` therefore emits no `sandbox_mode`. Instead it prepends
a generated note to every export's `developer_instructions`: the agent's stated tool and edit
restrictions are instructions, not limits Codex enforces, and a real read-only boundary comes only from
running the parent session read-only. The repo's `.codex/config.toml` sets the parent to
`workspace-write`.

Source: the [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) doc (read
2026-11-11): "Subagents inherit the parent turn's current sandbox and approval settings, including
changes made with `/permissions` or `--yolo`. A custom agent file can't replace those settings." It
also names `sandbox_mode` among the session settings that "don't override the parent configuration
when placed in a custom agent file."

Live check on Linux, `codex-cli` 0.166.0 (2026-11-12), with the subagents' own session logs read, not
just the parent's summary:

- Parent `workspace-write`, agent file `sandbox_mode = "read-only"`: the subagent's sandbox was
  `workspace-write` and its probe write succeeded.
- Parent `read-only`, agent file `sandbox_mode = "workspace-write"`: the subagent's sandbox was
  `read-only` and its probe write failed ("Read-only file system").

In both runs the parent itself ran no command.

The same two runs on Windows 11, `codex-cli` 0.162.1 (2026-11-13), gave the same result: the subagent
ran with `workspace-write` and wrote under a `workspace-write` parent, and ran with `read-only` and was
denied the write ("Access to the path ... is denied") under a `read-only` parent (issue #700). Two
Windows-specific conditions applied:

- Both runs used `windows.sandbox = "unelevated"`. With the `elevated` backend, the subagent's command
  never started ("helper_unknown_error: setup refresh had errors"). That is a setup failure, not a
  sandbox verdict.
- Codex loads a project's `.codex/agents` only when the project is trusted. In an untrusted project the
  parent's `spawn_agent` has no `agent_type` parameter, so it cannot select a custom agent. A
  `workspace-write` `codex exec` run marked its project trusted in `~/.codex/config.toml` by itself.

`features.shell_tool = false` was considered as a substitute and rejected. A live test on `codex-cli`
0.166.0 (2026-11-12) gave an agent with that key only the `collaboration.*` tools. Codex has no separate
file-read tool, since reading and searching go through its shell, so such a reviewer cannot read the
files it reviews. A control agent without the key had `functions.exec` and ran commands normally.

## Common mistakes (per the source doc)

1. Omitting a required field (`name`, `description`, `developer_instructions`).
2. Assuming a spawned agent inherits reasoning effort when only `model` is set.
3. (This repo's correction, not the source doc's wording.) Relying on a custom agent file's
   `sandbox_mode` to keep it read-only: it cannot override the parent's sandbox, so run the parent
   session read-only instead (see "No sandbox in the exports" above).
4. Building an overly broad agent instead of a narrow, opinionated one.
