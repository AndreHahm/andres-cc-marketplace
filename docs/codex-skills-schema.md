# Codex Skills Schema

Reference for the Agent Skills base specification and Codex's own support for it.

Sources: <https://agentskills.io/specification>, <https://learn.chatgpt.com/docs/build-skills>

## Base spec (agentskills.io) — shared by Claude Code, Codex, and other agent platforms

A skill is a directory containing `SKILL.md` plus optional `scripts/`, `references/`, `assets/`.

`SKILL.md` frontmatter:

| Field | Required | Constraints |
|---|---|---|
| `name` | Yes | ≤64 chars, lowercase alphanumeric + hyphens, no leading/trailing/double hyphen, must match the parent directory name |
| `description` | Yes | ≤1024 chars, non-empty |
| `license` | No | License name or reference to a bundled license file |
| `compatibility` | No | ≤500 chars — environment requirements (product, packages, network access) |
| `metadata` | No | Arbitrary string→string map for platform-specific extras |
| `allowed-tools` | No | Space-separated string of pre-approved tools. **Experimental — the spec itself says support varies by agent implementation.** |

Progressive disclosure is the spec's own loading model: `name`+`description` (~100 tokens) load for
every skill at startup; the full `SKILL.md` body loads only once a skill activates; files under
`scripts/`/`references/`/`assets/` load only as needed. Validate with the reference `skills-ref` tool.

## Codex's own support

Per the official Codex doc, **Codex's `SKILL.md` frontmatter support is only `name` and
`description`** — the two fields the base spec requires. Everything after the frontmatter is read as
imperative instructions for Codex to execute.

### Optional `agents/openai.yaml`

A skill directory may additionally carry `agents/openai.yaml`, read only by the ChatGPT desktop app
(not Codex CLI) to control presentation and invocation policy:

```yaml
interface:
  display_name: "User-facing name"
  short_description: "User-facing description"
  icon_small: "./assets/small-logo.svg"
  icon_large: "./assets/large-logo.png"
  brand_color: "#3B82F6"
  default_prompt: "Optional surrounding prompt"

policy:
  allow_implicit_invocation: true/false   # default true; false prevents automatic selection

dependencies:
  tools:
    - type: "mcp"
      value: "serverName"
      description: "Purpose"
```

### What Codex does **not** support

Per the official doc, Codex does not support: tool restrictions limiting which tools a skill may
access (so `allowed-tools` has no enforced effect on Codex, consistent with the base spec's own
"experimental, varies by implementation" caveat), model pinning to a specific version, hook
mechanisms for automation, or merging two skills that share the same `name` (both load separately
rather than being deduplicated).

### Skill discovery

Codex scans, in priority order: `REPO` (`.agents/skills` relative to cwd, then
`$REPO_ROOT/.agents/skills`), `USER` (`$HOME/.agents/skills`), `ADMIN` (`/etc/codex/skills`), and
`SYSTEM` (bundled, e.g. `skill-creator`). Symlinks are followed; changes are picked up automatically
(a restart may be needed). This confirms `.agents/skills/` — the directory this repo's own
`codex_exports.skills` convention already targets — is the correct project-scoped location.

## Claude Code's extensions beyond the base spec

Surveyed live across this repo's own `.claude/skills/*/SKILL.md` files, the frontmatter fields
actually in use are: `name`, `description`, `allowed-tools`, `argument-hint`,
`disable-model-invocation`, `hooks`, `model`. Of these, only `name`/`description` (and, experimentally,
`allowed-tools`) are part of the base spec — `argument-hint`, `disable-model-invocation`, `hooks`, and
`model` are Claude Code-only extensions with no defined meaning in the base spec or in Codex's
documented frontmatter support.

Neither source doc states what Codex does when it encounters an unrecognized frontmatter field —
that behavior is undocumented, not verified here. What *is* confirmed is narrower: Codex's own doc
lists exactly which two fields it reads (`name`, `description`) and separately lists tool
restrictions/hooks/model-pinning as unsupported capabilities — not what happens to the raw YAML keys
themselves.

## Tool availability differs, independent of the schema

A `SKILL.md` body written for Claude Code can reference Claude-specific tools by name (e.g.
`AskUserQuestion`, `Skill(...)` invocations) that have no Codex CLI equivalent — this is a runtime
capability gap, not a frontmatter/schema one, and the base spec's format doesn't address it at all.
See [`skill-conversion-from-claude-to-codex.md`](skill-conversion-from-claude-to-codex.md) for how
this repo's actual skill content is affected.

## Where this applies in this repo

See [`skill-conversion-from-claude-to-codex.md`](skill-conversion-from-claude-to-codex.md) for how
this repo's own `.claude/skills/` → `.agents/skills/` conversion pipeline currently handles (and
doesn't handle) the gaps above. Related: [`codex-subagents-schema.md`](codex-subagents-schema.md) covers
the separate `.codex/agents/*.toml` custom-subagent schema, and
[`codex-review-configuration.md`](codex-review-configuration.md) covers the `AGENTS.md` review-rule
convention — three distinct Codex integration points in this repo, each with its own schema and its
own export mechanism.
