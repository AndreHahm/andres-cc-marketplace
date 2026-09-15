# Context Audit — Detailed Procedures

## Static Inventory Procedure

> **Automation:** `scripts/audit-context.sh` automates Steps 1-4 below. Use `--json` for structured output. The manual steps remain here as reference.

### Step 1: Discover Skills

```
Glob: ~/.claude/skills/*/SKILL.md
```

For each skill directory found:
- Read `SKILL.md` — record byte size and word count
- Glob `rules/*.md` — record count and total size (these are always-on)
- Glob `references/*.md` — record count and total size (these are on-demand)

### Step 2: Measure CLAUDE.md Files

Read these files if they exist:
- `~/CLAUDE.md` (global)
- `{project-root}/CLAUDE.md` (project-level)
- `{project-root}/.claude/CLAUDE.md` (alternate location)

Record byte size and word count for each.

### Step 3: Count Plugins and MCP Servers

Read `~/.claude/settings.json` and extract:
- `plugins` array — count entries
- `mcpServers` object — count keys
- For each MCP server, note if it has custom tool descriptions

### Step 4: Build Inventory Table

Sort all entries by size descending. Format:

```
| Source | Size | Words | Loads | Flag |
|--------|------|-------|-------|------|
| skills/tailwind/SKILL.md | 2.1KB | 620 | on-trigger | LARGE |
| CLAUDE.md (global) | 3.4KB | 890 | always-on | LARGE |
| skills/research/rules/defaults.md | 450B | 95 | always-on | RULES |
| ... | ... | ... | ... | ... |
```

Flag column values:
- `LARGE` — SKILL.md > 500 words or CLAUDE.md > 2KB
- `RULES` — any file in a rules/ directory (always loaded)
- `MCP` — 5+ MCP servers configured
- `HEAVY` — plugin with 10+ estimated tools
- `-` — within acceptable range

Compute totals:
- **Always-on context**: sum of all rules/ files + CLAUDE.md files + plugin/MCP overhead estimate (200 words per MCP server, 50 words per plugin for tool descriptions)
- **On-trigger context**: average SKILL.md size across all skills

Auto-memory files (`~/.claude/projects/*/memory/*.md`) are listed in this same inventory for their
footprint (size/word count) only — this procedure does not assess their content health (staleness,
broken links, orphans, missing frontmatter). For that, run `session-kit`'s `session-memory-audit`
(if installed).

## Scoring Rubric

### Skills Health (30 points)

| Condition | Points |
|-----------|--------|
| All SKILL.md files < 500 rows | +10 |
| No rules/ directories (nothing always-on) | +10 |
| References used for detailed content | +5 |
| No overlapping skill triggers | +5 |

Deductions:
- Each SKILL.md > 500 rows: -3
- Each rules/ directory: -5
- Each skill > 300 rows without references: -3
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

1. **rules/ directories exist** → "Move `{skill}/rules/{file}` content into SKILL.md — rules/ files load every conversation regardless of skill use"
2. **SKILL.md > 500 rows** → "Extract detailed procedures from `{skill}/SKILL.md` into `references/` — keeps trigger cost low"
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
