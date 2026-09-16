---
name: context-audit
description: >-
  Audit context window composition and identify optimization targets. Use when performance feels
  sluggish, context warnings appear, after installing new skills, or for periodic context health checks.
allowed-tools: Read, Bash(${CLAUDE_SKILL_DIR}/scripts/audit-context.sh:*)
---

# Context Audit

Analyzes what's consuming your context window's always-on and on-trigger footprint, and recommends
optimizations. Two audit modes can run independently or together.

## When NOT to Use

- A token-usage/cost/model/tool-error/frustration-signal breakdown for one session — use `session-kit`'s
  `session-stats` instead (if installed). This skill scores the *static footprint* of skills, CLAUDE.md,
  plugins, and MCP servers; it does not parse session JSONL for per-turn token analysis.
- A memory-health check (staleness, broken links, orphans, missing frontmatter, duplicates) — use
  `session-kit`'s `session-memory-audit` instead (if installed). This skill's Static Inventory lists
  auto-memory files only for their size/word-count footprint, not their content health.

## Quick Start

- `/context-audit` or "audit my context" — runs the static inventory + scoring
- "static audit" or "context inventory" — file inventory only
- "context score" — scoring and recommendations only

## Audit Modes

### 1. Static Inventory

Run `scripts/audit-context.sh` to automate the static inventory. Supports `--json` for structured output, `--flagged` for problems only, `--top N` for largest items.

The script scans all context-contributing sources:
- Skills, both user-scope (`~/.claude/skills/`) and project-scope (`{project-root}/.claude/skills/`) —
  either scope alone is enough to run; SKILL.md, references/, and a skill-bundled rules/ (a skill
  resource, on-demand like references/, not the project's always-on surface below)
- `.claude/rules/*.md` — the project's real always-on rule surface, loaded every session regardless of
  which skill is active, discovered recursively (subdirectories like `rules/frontend/` are included)
- `~/.claude/CLAUDE.md` (the real global path) and project CLAUDE.md files (project root + subdirectories)
- Auto-memory files scoped to the current project only (`~/.claude/projects/<this-project>/memory/*.md`)
  — footprint (size/word count) only; for content health (staleness, broken links, orphans), run
  `session-kit`'s `session-memory-audit` instead
- Plugins with per-plugin tool count estimates
- MCP servers — both user-configured (`~/.claude/settings.json`) and plugin-bundled (a plugin's own
  `.mcp.json` or inline `plugin.json` `mcpServers` field)

**Thresholds:** Flag SKILL.md > 500 words, any `.claude/rules/*.md` file, CLAUDE.md > 2KB, 5+ MCP servers, plugins with 10+ tools.

### 2. Live Context Window (`/context`)

After running the static inventory, tell the user about the built-in `/context` command:
- It shows real-time token usage: current tokens, max capacity, and percentage used
- It breaks down what's in the context window right now (system prompt, conversation, tool results)
- Recommend the user run `/context` themselves for live token data — it complements the static inventory
- If the user shares `/context` output, incorporate it into the scoring (Session Efficiency component) —
  this is the only source the Session Efficiency score draws from; this skill never parses session JSONL
  itself. For a full token/model/tool-usage/frustration-signal breakdown of a session, use `session-kit`'s
  `session-stats` instead.

### 3. Recommendations & Scoring

Generate actionable recommendations and a letter grade (A-F, 0-100).

**Scoring weights:**
| Component | Weight |
|-----------|--------|
| Skills health | 30% |
| CLAUDE.md health | 25% |
| Plugin/MCP health | 25% |
| Session efficiency | 20% |

## Output Format

Produce a single report with sections:
1. Static Inventory table (from `audit-context.sh` script output)
2. `/context` note — remind the user to run `/context` for live token breakdown, and to incorporate it into the score if shared
3. Top Recommendations
4. Score

Read `references/audit-procedures.md` for detailed procedures, scoring rubric, and recommendation rules.

## Related Skills

- `session-kit`'s `session-stats` (if installed) — session token/model/tool-usage/frustration analysis, out of scope here.
- `session-kit`'s `session-memory-audit` (if installed) — memory content health, out of scope here.
- `context-window-analyze` — a narrower, live-window-only check; use it for the current window's health in the moment, this skill for the broader skills/CLAUDE.md/plugin/MCP footprint.

## Testing & Validation

No `evals/context-audit/evals.json` — this skill's variable part is `scripts/audit-context.sh` (deterministic, no model-judgment branching to eval); it was smoke-tested directly against real repo data (`--top`, `--flagged`, `--json`, `--help`, and the `--top 08`/missing-value edge cases) rather than via a `skill-tester` blind comparison. The scoring/recommendation logic in `references/audit-procedures.md` is guidance the model applies directly, not a separate code path to eval.

**Verify this skill activates on:**
- "audit my context"
- "static audit" / "context inventory"
- "context score"
- After installing new skills, or for a periodic context health check

**Verify it does NOT activate on:**
- "how much did this session use" / "what tool errors happened" (session usage stats, not static footprint) → `session-kit`'s `session-stats`
- "clean up stale memories" (memory content health, not footprint) → `session-kit`'s `session-memory-audit`
- "check the live context window right now" with no interest in the broader skills/CLAUDE.md/plugin footprint → `context-window-analyze`

**Quality gates:**
- [ ] `scripts/audit-context.sh` never claims a `--session`/JSONL mode — that capability was deliberately dropped in favor of deferring to `session-kit`'s `session-stats`
- [ ] Session Efficiency scoring is only ever sourced from user-shared `/context` output, never from self-parsed session JSONL
- [ ] `--top` accepts a leading-zero value (e.g. `08`) as decimal, not octal, and never aborts on a missing value
- [ ] `scripts/audit-context.sh` is tracked executable (`100755`) — this skill's own `allowed-tools` grant only permits invoking it directly, not via a `bash ...` wrapper
- [ ] The static inventory scans project-scope skills (`{project-root}/.claude/skills/`) as well as user-scope, and never presents a skill-bundled `rules/` directory as the project's always-on surface — only `.claude/rules/*.md` earns the `RULES` flag
- [ ] The jq-free settings fallback never reports a plugin count that silently includes disabled `enabledPlugins` entries — when `jq` is unavailable, plugin analysis is reported as unavailable rather than a confidently-wrong number
- [ ] The script never exits 1 when only one of user-scope or project-scope skills exists — the early guard requires at least one, never unconditionally requires `~/.claude/skills/`
- [ ] Global CLAUDE.md is read from `~/.claude/CLAUDE.md`, never the wrong `~/CLAUDE.md` path
- [ ] Auto-memory files are scoped to the current project's own `~/.claude/projects/<encoded-cwd>/memory/` directory, never every project under `~/.claude/projects/*/memory/`
- [ ] `.claude/rules/*.md` discovery is recursive — a rule in a subdirectory (e.g. `rules/frontend/`) is never silently dropped
- [ ] MCP server counting includes both `~/.claude/settings.json`'s own `mcpServers` and each enabled plugin's bundled `.mcp.json`/inline `plugin.json` `mcpServers` — never settings.json alone
