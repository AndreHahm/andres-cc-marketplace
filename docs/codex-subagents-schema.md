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
- `sandbox_mode`
- `mcp_servers`
- `skills.config`

**There is no `tools` field in this schema.** Precedence when a value could come from more than one
place: explicit spawn values → the agent's own TOML file → `[agents]` config defaults → parent
session values.

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

## Common mistakes (per the source doc)

1. Omitting a required field (`name`, `description`, `developer_instructions`).
2. Assuming a spawned agent inherits reasoning effort when only `model` is set.
3. Not setting `sandbox_mode` for a read-only exploration agent.
4. Building an overly broad agent instead of a narrow, opinionated one.
