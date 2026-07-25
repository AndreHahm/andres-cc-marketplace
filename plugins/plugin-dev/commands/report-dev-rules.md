---
description: >-
  Generate a plugin, component, or marketplace rules report
argument-hint: --level <marketplace|plugin|component> --name <name> [--output-dir <dir>]
allowed-tools: Read Write Glob Bash(mkdir:*)
---

Generate or update a rules report from the arguments below, following the Report Format defined in Step 6 below.

> **Invocation:** Run as `/report-dev-rules --level ...` in the Claude Code prompt. This command cannot be invoked via `Skill()` — it must be triggered as a slash command or followed manually.

> **Pipeline:** This is step 1 of 4 in the dev-rules pipeline: `/report-dev-rules` (this command) → `/verify-dev-rules` (check the report against official docs, find gaps) → `/plan-dev-rules` (turn verified gaps into a file-by-file implementation plan) → `/implement-dev-rules` (apply the plan, then check for stale duplicate copies of any changed value). Each step reads the previous step's output.

**Arguments:** $ARGUMENTS

---

## Step 1: Parse Arguments

Extract from the argument string:

| Argument | Required | Default | Valid Values |
|---|---|---|---|
| `--level` | Yes | — | `marketplace`, `plugin`, `component` |
| `--name` | Yes | — | Any identifier |
| `--output-dir` | No | `.claude/output/rules` | Any writable path |

If `--level` or `--name` is missing, stop and print:
```
Usage: /report-dev-rules --level <marketplace|plugin|component> --name <name> [--output-dir <dir>]

  --level     marketplace  Parent report + one report per plugin
              plugin       Single report for the named plugin
              component    Single report for the named component

  --name      Marketplace name, plugin name, or component name

  --output-dir  Output directory (default: .claude/output/rules)
```

---

## Step 2: Discover Sources

**Discover all plugins** by globbing `**/.claude-plugin/plugin.json` from the current working directory. For each result, record the plugin `name` field and its root directory (parent of `.claude-plugin/`).

**Discover the marketplace** by reading `.claude-plugin/marketplace.json` if it exists at the project root.

**Resolve the target:**

- `level=marketplace` → find the marketplace manifest; list all plugins from its `plugins` array; match each to the plugin map by `name` or `source` path.
- `level=plugin` → match `--name` against plugin map entries (by `name` field in plugin.json, then by directory name). If no match, print "Plugin '{name}' not found. Discovered plugins: {list}." and stop.
- `level=component` → search every discovered plugin root for a component named `--name`:
  - Skill: `skills/{name}/SKILL.md`
  - Agent: `agents/{name}.md`
  - Command: `commands/{name}.md`
  - Hook: `hooks/hooks.json` (if `--name` is "hooks" or the hook file name)
  - Rule: `.claude/rules/{name}.md` or `.claude/rules/**/{name}.md`
  - **Also check project-scope and user-scope locations that aren't inside any discovered plugin:** `{CWD}/.claude/skills/{name}/`, `{CWD}/.claude/agents/{name}.md`, `~/.claude/skills/{name}/`, `~/.claude/agents/{name}.md`. A component of the same name can exist both inside a plugin and at project/user scope simultaneously — these are separate, independently-maintained copies that silently shadow one another depending on which one Claude Code resolves at runtime. If any such shadow copy exists, always report it, even when the plugin-scoped copy is the primary target.
  - If multiple matches exist across plugins, or a plugin match has a project/user-scope shadow, include all in the report with their owning plugin (or "project scope" / "user scope") noted.

**Discover CLAUDE.md files** — collect all relevant CLAUDE.md files for the target, walking from specific to general:

| Scope label | Path | Include when |
|---|---|---|
| `component` | `{component-dir}/CLAUDE.md` | `level=component` and file exists |
| `plugin` | `{plugin-root}/CLAUDE.md` | `level=plugin` or `level=component` and file exists |
| `project` | `{CWD}/CLAUDE.md` | Always (all levels) |
| `global` | `~/.claude/CLAUDE.md` (expand `~`) | Always (all levels) |

If a CLAUDE.md does not exist at a given scope, skip it silently.

---

## Step 3: Pre-flight Confirmation

Before reading any source files or writing any output, print a dry-run summary, then use `AskUserQuestion` to confirm:

```
Pre-flight: /report-dev-rules --level {level} --name {name}

Sources to read:
  {list each discovered source file or directory, one per line}

Output to write:
  {list each planned output file path, one per line}
```

`AskUserQuestion` — question: "Proceed with this report?", options: "Proceed" / "Cancel". On "Cancel" (or any answer other than an affirmative), print "Cancelled." and stop — do not read any further files or write any output.

---

## Step 4: Read Sources

For each target, read in this order — later sources add detail, earlier sources are more reliable:

**1. Existing rules reports** (read first to preserve prior analysis and update in place):
- `{output-dir}/{name}-rules.md` or `{output-dir}/{name}-marketplace-rules.md` if already present

**2. Automated enforcement** (what the plugin validates automatically):
- `hooks/hooks.json` — which events and file types trigger validation
- `hooks/validators/*.py` / any `validate_*.py` — allowed fields, valid enum values, structural checks
- Any validation scripts at `skills/*/scripts/validate_*.py` or `*.sh` — these encode enum values (e.g. valid `color`, `model`, `permissionMode` values) as executable `case`/`if` logic; read the actual conditional branches, don't assume a script matches its own sibling documentation
- Any `assets/settings.json` or similar structured config file — treat these as the fastest-changing, most authoritative source for enum lists and numeric thresholds; when a rule has both a structured config entry and a prose description elsewhere, the config value wins if they disagree

**3. Component source files** (ground truth for each component type):
- All `skills/*/SKILL.md` files — naming conventions, description format, line limits, frontmatter rules
- All `agents/*.md` files — required frontmatter fields, valid enum values, structural constraints
- All `commands/*.md` files — allowed frontmatter fields, argument-hint rules, tool-scoping conventions
- `hooks/hooks.json` + hook scripts — structural requirements, exit code contract, location rules
- `.claude/rules/*.md` (and subdirectories) — frontmatter restrictions, content rules, line budget
- `skills/plugin-rulebook/` or `.claude/skills/plugin-rulebook/` (if present) — canonical rule list. If **both** exist, treat this as a reportable conflict on its own (see Step 5) rather than silently picking one. Also read `upstream-sources-registry`'s `assets/sources.json` for the current list of tracked official sources, their classification, and last-verified state — this supersedes `plugin-rulebook`'s former "Tracked Upstream Sources" table, which existed for the same purpose before this registry consolidated it.

**4. Plugin manifest** (plugin-level constraints):
- `.claude-plugin/plugin.json` — manifest schema and required fields
- `.claude-plugin/marketplace.json` — marketplace schema, source path requirements

**5. CLAUDE.md files** (behavioral and cross-cutting rules in loading order — most specific last, so later files narrow or override earlier ones):
- `~/.claude/CLAUDE.md` — global behavioral rules applying to all projects
- `{CWD}/CLAUDE.md` — project-level rules overriding global
- `{plugin-root}/CLAUDE.md` — plugin-local rules (if present)
- `{component-dir}/CLAUDE.md` — component-local rules (if present, `level=component` only)

Extract every distinct rule, guideline, constraint, or behavioral instruction. Note any rule that has an associated hook or automated enforcement mechanism.

---

## Step 5: Extract and Classify Rules

From all sources read, extract every constraint, requirement, or limitation. Assign each:

| Field | Values |
|---|---|
| **Severity** | `REQUIRED`, `BEST PRACTICE`, `LIMITATION`, `TIERED`, `BEHAVIORAL` |
| **Source** | File path or system name (e.g., `hooks/validators/constants.py`, `skill-reviewer agent`) |
| **Detail** | Full constraint description including valid values, thresholds, or examples |

Use `BEHAVIORAL` for rules extracted from CLAUDE.md files — these are behavioral guidelines for the AI rather than structural or syntactic constraints.

Group rules by component type: Skill, Agent, Command, Hook, Rule, Plugin Manifest, enforcement-layer, and CLAUDE.md rules.

For `level=marketplace`, additionally extract **marketplace-level rules** — constraints that apply to `marketplace.json` and inter-plugin distribution — separate from per-plugin rules.

**Cross-file consistency check (always run, at every level):** The same rule is frequently documented in more than one source file — a SKILL.md's own frontmatter reference table, a `references/*.md` schema doc, a validation checklist, a prompt/example template, and a validator script can all separately state the same enum (e.g. valid `color`, `model`, `permissionMode`, hook `type` values) or the same numeric threshold (e.g. a line-count limit). These copies are edited independently and drift apart silently — a fix applied to one copy does not propagate to the others. For every rule that appears in 2+ sources:
- Compare the stated values/thresholds across all occurrences, including inside code examples, checklists, and executable validator logic — not just the primary schema reference.
- If they match, extract once and list every source file in the **Source** field.
- If they differ, do not silently prefer one — emit a `CONFLICT` entry noting each differing value and its exact source file, so it lands in the Conflict and Gap Summary / Internal Consistency Check section (see Step 6). A validator script accepting or rejecting a value that a sibling doc no longer agrees with counts as a conflict, not just prose-vs-prose disagreement.

---

## Step 6: Write Report

**Output file paths:**

| Level | Output file(s) |
|---|---|
| `component` | `{output-dir}/{name}-rules.md` |
| `plugin` | `{output-dir}/{name}-rules.md` |
| `marketplace` | `{output-dir}/{name}-marketplace-rules.md` (parent) + `{output-dir}/{plugin-name}-rules.md` per plugin |

Create the output directory if it does not exist: `mkdir -p {output-dir}`.

**Always fully regenerate all sections from current sources.** If the output file already exists, read it first to recover the intro description (the one-sentence summary below the title) and any manually-added annotations or custom notes within sections — then discard all section content and rewrite the report from scratch. Do not carry forward stale section content from a previous run.

---

### Report Format

Every report follows this structure:

```markdown
# {Name} Rules Reference

{One-sentence description: what plugin/component/marketplace this covers and what the report is for.}

**Sources used:**
- `{source path or system}` — {what it contributes}

**Generated:** {YYYY-MM-DD} | **Level:** {level} | **Plugin version:** {version if known}

---

## {Section — see below}
```

**Standard table format for all rule sections:**

```markdown
| Rule | Severity | Source | Detail |
|---|---|---|---|
| Brief rule statement | REQUIRED | source-file | Full constraint with valid values or thresholds |
```

For the enforcement-layer section (if the plugin has automated validation), add a column for what triggers it:

```markdown
| File Pattern | Validator | What Is Checked |
|---|---|---|
```

For the CLAUDE.md rules section, use this table format — include a **Scope** column to distinguish which file the rule comes from, and an **Enforcement** column to note whether a hook or other mechanism backs the rule:

```markdown
| Rule | Scope | Source File | Enforcement | Detail |
|---|---|---|---|---|
| Brief rule statement | global/project/plugin/component | ~/.claude/CLAUDE.md | hook name / manual / none | Full rule or guideline text |
```

For the Internal Consistency Check / Conflict and Gap Summary sections (component and plugin levels), use this table format for CONFLICT entries from the Step 5 cross-file check:

```markdown
| Rule | Source A | Value in A | Source B | Value in B |
|---|---|---|---|---|
| What the rule is about (e.g. "valid `color` values") | SKILL.md:100 | `blue, cyan, ..., red` | scripts/validate-agent.sh:131 | `red, blue, ..., cyan` |
```

Add one row per pair of disagreeing sources (more than two sources may need more than one row). Shadow copies discovered in Step 2 (a component or plugin duplicated outside its expected scope) go in the same section as a plain note, not a table row, since there's no single "rule" to compare — just the fact that two independently-maintained copies exist.

---

### Sections by Level

**Section normalization rule:** When extracting rules from source files (SKILL.md, agent/command files, hook validators, etc.), distribute each rule into the appropriate section defined below — never copy section headings from source files verbatim. Rules that don't match any defined section go into the closest matching section; if no match exists, add an `## Additional Rules` section after Plugin Manifest Rules and before CLAUDE.md Rules.

**`level=component` — one report:**
```
# {name} Component Rules Reference
## {Component Type} Rules
(single table for the matched component type)
## CLAUDE.md Rules
(table with Scope + Source File + Enforcement columns)
## Internal Consistency Check   (only if 2+ source files were read for this component)
(CONFLICT entries from the Step 5 cross-file check: same rule/enum/threshold, differing values,
each occurrence's source file listed — e.g. a SKILL.md quick-reference table stating one set of
valid values while a references/*.md schema doc or validator script states another. Also list any
project/user-scope shadow copy of this component discovered in Step 2. Omit this section entirely
if only one source file existed to check.)
```

**`level=plugin` — one report:**
```
# {name} Rules Reference
## Enforcement Layer          (only if automated validation exists)
## Skill Rules
## Agent Rules
## Command Rules
## Hook Rules
## Rule (.claude/rules/) Rules
## Plugin Manifest Rules
## CLAUDE.md Rules            (global, project, and plugin-root CLAUDE.md files)
## Conflict and Gap Summary   (CONFLICT entries from the Step 5 cross-file check, plus any
                               project/user-scope shadow copies of this plugin's components
                               discovered in Step 2)
```

**`level=marketplace` — parent report + one plugin report per plugin:**

Parent (`{name}-marketplace-rules.md`):
```
# {name} Marketplace Rules Reference
## Marketplace Manifest Rules
(rules from marketplace.json schema: owner format, plugins array, source paths)

## CLAUDE.md Rules
(global and project-level CLAUDE.md rules only; plugin-level CLAUDE.md rules appear in each plugin's report)

## Plugin Inventory
| Plugin | Version | Source Path | Report |
|---|---|---|---|
| plugin-name | 1.0.0 | ./plugins/plugin-name | [plugin-name-rules.md](plugin-name-rules.md) |

## Cross-Plugin Conflicts and Gaps
| # | Topic | {Plugin A} Rule | {Plugin B} Rule | Classification |
|---|---|---|---|---|
(compare rules across plugins: CONFLICT = directly contradictory, DIFFERENCE = different but compatible, GAP = one plugin has a rule the other lacks)
```

Each plugin report (`{plugin-name}-rules.md`): same format as `level=plugin`.

---

**Section verification:** After writing all files, verify that each report's `##` headings match the Sections by Level spec above exactly — correct headings, correct order, no extra headings. If any mismatch is found, rewrite the affected sections before proceeding to Step 7.

---

## Step 7: Confirm Output

After writing all files, print:

```
Rules report written:
  {file path 1}
  {file path 2}    (marketplace level only, one per plugin)

Sources read: {n} files
Rules extracted: {n} total ({n} required, {n} best practice, {n} limitations)

Next: /verify-dev-rules --report {file path 1}
```
