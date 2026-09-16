# Context Audit — Detailed Procedures

## Static Inventory Procedure

> **Automation:** `scripts/audit-context.sh` automates Steps 1-5 below. Use `--json` for structured output. The manual steps remain here as reference.

### Step 1: Discover Skills

```
Glob: ~/.claude/skills/*/SKILL.md
Glob: {project-root}/.claude/skills/*/SKILL.md   (if the project has its own)
```

Either scope alone is enough to run this procedure — a machine with only project-local skills (no
`~/.claude/skills/` at all) is a normal, supported setup, not an error.

For each skill directory found (user-scope and project-scope):
- Read `SKILL.md` — record byte size and word count
- Glob `references/*.md` — record count and total size (these are on-demand)
- Glob `rules/*.md` — record count and total size (a `rules/` directory *bundled inside a skill* is a
  skill resource, on-demand like `references/` — it only loads when that skill itself triggers, not
  every conversation)

### Step 2: Measure CLAUDE.md Files

Read these files if they exist:
- `~/.claude/CLAUDE.md` (global — not `~/CLAUDE.md`, a common mistake)
- `{project-root}/CLAUDE.md` (project-level)
- `{project-root}/.claude/CLAUDE.md` (alternate project-level location)

Record byte size and word count for each.

### Step 3: Discover Project Rules

```
Glob: {project-root}/.claude/rules/**/*.md   (recursive -- subdirectories like rules/frontend/ count too)
```

These are the project's real always-on rule surface — unlike a skill-bundled `rules/` directory
(Step 1), every file here loads into every session regardless of which skill, if any, is active.
Record byte size and word count for each.

### Step 4: Count Plugins and MCP Servers

Read `~/.claude/settings.json` and extract:
- `enabledPlugins` object — count entries whose value is `true` (an entry with value `false` is
  installed but disabled, and does not contribute to context)
- For each enabled plugin, estimate its tool-description overhead from its actual tool count (not a
  flat per-plugin estimate) — see `scripts/audit-context.sh`'s own `tool_est` table for known values
- `mcpServers` object — count keys

Then, for each enabled plugin, also check whether it bundles its own MCP servers — a plugin-root
`.mcp.json` or an inline `mcpServers` field in its own `plugin.json` (both auto-start when the plugin
is enabled and never appear in `~/.claude/settings.json`'s own `mcpServers` object). Count those keys
too, added to the `mcpServers` total above. For each MCP server (settings-configured or
plugin-bundled), note if it has custom tool descriptions.

### Step 5: Build Inventory Table

Sort all entries by size descending. Format:

```
| Source | Size | Words | Loads | Flag |
|--------|------|-------|-------|------|
| skills/tailwind/SKILL.md | 2.1KB | 620 | on-trigger | LARGE |
| CLAUDE.md (global) | 3.4KB | 890 | always-on | LARGE |
| project-rules/no-secrets.md | 450B | 95 | always-on | RULES |
| ... | ... | ... | ... | ... |
```

Flag column values:
- `LARGE` — SKILL.md > 500 words or CLAUDE.md > 2KB
- `RULES` — any `.claude/rules/*.md` file (the project's own always-on surface, Step 3 — not a
  skill-bundled `rules/` directory from Step 1, which is on-demand)
- `MCP` — 5+ MCP servers configured
- `HEAVY` — plugin with 10+ estimated tools
- `-` — within acceptable range

Compute totals:
- **Always-on context**: sum of all `.claude/rules/*.md` files + CLAUDE.md files + plugin/MCP overhead
  estimate (200 words per MCP server, tool-count-based per enabled plugin — see Step 4)
- **On-trigger context**: average SKILL.md size across all skills

Auto-memory files, scoped to the **current project only**
(`~/.claude/projects/<this-project>/memory/*.md`, where `<this-project>` encodes the absolute project
path per Claude Code's own convention — every `.`, `:`, `/`, `\` replaced with `-`), are listed in
this same inventory for their footprint (size/word count) only — never another project's memory,
which would otherwise inflate this session's always-on total with content that isn't actually loaded
here. This procedure does not assess memory content health (staleness, broken links, orphans, missing
frontmatter). For that, run `session-kit`'s `session-memory-audit` (if installed).

## Scoring Rubric

### Skills Health (30 points)

| Condition | Points |
|-----------|--------|
| All SKILL.md files < 500 words | +10 |
| No (or very few) `.claude/rules/*.md` files (minimal always-on surface, Step 3) | +10 |
| References used for detailed content | +5 |
| No overlapping skill triggers | +5 |

Deductions:
- Each SKILL.md > 500 words: -3
- Each `.claude/rules/*.md` file: -5
- Each skill > 300 words without references: -3
- Each overlapping skill trigger: -1

### CLAUDE.md Health (25 points)

| Condition | Points |
|-----------|--------|
| Global CLAUDE.md < 2KB | +10 |
| Project-specific CLAUDE.md exists and is focused | +5 |
| No duplication between global and project | +5 |
| Clear, actionable instructions (not vague) | +5 |

Deductions:
- Global CLAUDE.md > 4KB: -10
- Duplicated content across CLAUDE.md files: -5

### Plugin/MCP Health (25 points)

| Condition | Points |
|-----------|--------|
| < 5 MCP servers | +10 |
| < 10 external plugins | +5 |
| All MCP servers actively used in session | +5 |
| No redundant tool providers | +5 |

Deductions:
- Each MCP server beyond 5: -3
- Each external plugin beyond 10: -2

### Session Efficiency (20 points)

Sourced entirely from `/context` output the user shares (see SKILL.md mode 2) — this skill never parses
session JSONL itself. If no `/context` output is shared, score this component at 10/20 (neutral).

| Condition | Points |
|-----------|--------|
| Reported usage < 50% of max | +10 |
| Tool-results share of the breakdown < 40% | +5 |
| No single category (system prompt / conversation / tool results) unexpectedly dominating (> 70%) | +5 |

Deductions:
- Reported usage > 80% of max: -10
- Tool-results share > 60% of the breakdown: -5

For a full per-turn token/model/tool-usage/frustration-signal breakdown of the session (growth rate,
spikes, cache hit rate), use `session-kit`'s `session-stats` instead (if installed) — that data source
is out of scope for this rubric.

### Letter Grades

| Score | Grade |
|-------|-------|
| 90-100 | A |
| 80-89 | B+ |
| 70-79 | B |
| 60-69 | C+ |
| 50-59 | C |
| 40-49 | D |
| 0-39 | F |

## Recommendation Rules

Generate recommendations based on findings. Priority order:

1. **A `.claude/rules/*.md` file is unusually large** → "Trim `{file}` — every word in it loads into every session regardless of what's being worked on"
2. **SKILL.md > 500 words** → "Extract detailed procedures from `{skill}/SKILL.md` into `references/` — keeps trigger cost low"
3. **CLAUDE.md > 4KB** → "Split global CLAUDE.md — move project-specific instructions to per-project files"
4. **5+ MCP servers** → "Review MCP server list — each adds tool descriptions to every conversation. Disable unused servers."
5. **/context usage > 80%** → "Context usage is high — consider /compact, or session-kit's session-handoff if installed"
6. **Overlapping skill triggers** → "Skills `{a}` and `{b}` may both trigger on similar inputs — consolidate or differentiate triggers"
7. **No references/ used** → "Skills with large SKILL.md files should use references/ for detailed content that's only read when needed"
8. **High external plugin count (15+)** → "Each plugin adds tool descriptions to context. Disable plugins you rarely use."

Format each recommendation with:
- What was found (evidence)
- What to do (action)
- Expected impact (words/tokens saved estimate)
