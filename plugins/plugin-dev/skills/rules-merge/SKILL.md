---
name: rules-merge
description: >-
  Merges rules-extract output from multiple projects into a unified portable
  rule set. Promotes .local.md patterns shared across a threshold of projects
  to Principles format. Use when consolidating org-wide rules after running
  rules-extract on 2+ repositories, merging coding standards across projects,
  or promoting shared patterns to portable Principles.
allowed-tools: Read Glob Grep Write Bash(ls:*) Bash(mkdir:*) Bash(wc:*)
---

# Merge Rules

Merges `.claude/rules/` from multiple projects into a unified portable rule set (.md + .examples.md). Promotes `.local.md` patterns that appear across a threshold of projects by converting them to Principles format. Merges `.examples.md` files alongside rule files.

## Quick Start

1. **Run `rules-extract`** on each source project first (2+ required)
2. **Create config** — `.claude/rules-merge.local.md` with at minimum a `projects:` list (see `references/config-schema.md`)
3. **Dry run** — `/rules-merge --dry-run` to preview merges and promotions before writing
4. **Merge** — `/rules-merge` to write output to `output_dir`
5. **Review report** — check Merge Results, Promoted to Principles, and Below Threshold sections

```text
/rules-merge                    # Merge using config file
/rules-merge --config <path>    # Merge using specified config file
/rules-merge --dry-run          # Show what would be merged without writing
```

## When to Use

- Consolidating coding standards across 2+ repositories into one portable rule set
- After running `rules-extract` on multiple projects and wanting to promote shared patterns
- Producing org-wide `.claude/rules/` output for use with `rules-apply`
- Merging rule updates from new projects into an existing org rule set

## When NOT to Use

- Single-project rule extraction → use `rules-extract` instead
- Applying merged org rules to a project → use `rules-apply` instead
- Editing merged rules manually → edit the output file directly
- First-time rule extraction → run `rules-extract` per project first

## Configuration

Config file search order:
1. `--config <path>` argument
2. `.claude/rules-merge.local.md` (project-level)
3. `~/.claude/rules-merge.local.md` (user-level)

**File format:** YAML frontmatter only (no markdown body), same convention as `rules-extract.local.md`.

**Key fields:** `projects` (required, 2+ paths), `output_dir` (default: `.claude/rules/`), `rules_dir` (default: `.claude/rules/`), `promote_threshold` (default: `0.5`), `language` (default: `en`)

See `references/config-schema.md` for the full annotated config template.

## Processing Flow

### Step 1: Load Configuration

1. Search for config file (see search order above)
   - If not found: Error "No config file found. Create `.claude/rules-merge.local.md` or specify with `--config`."
2. Parse YAML frontmatter, apply defaults for omitted fields
   - **`language` resolution order:** Skill config → Claude Code settings (`~/.claude/settings.json` → `language` field) → default `en`
3. Validate:
   - `projects` must have at least 2 entries
   - Each project path must exist and contain `rules_dir`
   - Error with clear message if validation fails

### Step 2: Collect Rule Files

For each project:

1. Find all `.md`, `.local.md`, and `.examples.md` files under `{path}/{rules_dir}/` (recursive)
2. Categorize:
   - `languages/*.md` → portable principles (always merge). **If the file also contains `## Project-specific patterns`** (hybrid format from `split_output: false`), treat patterns as promotion candidates (same as `.local.md`)
   - `frameworks/*.md` → same as above
   - `integrations/*.md` → same as above
   - `languages/*.local.md` → promotion candidate
   - `frameworks/*.local.md` → promotion candidate
   - `integrations/*.local.md` → promotion candidate
   - `languages/*.examples.md` → example file (merge with rules)
   - `frameworks/*.examples.md` → example file (merge with rules)
   - `integrations/*.examples.md` → example file (merge with rules)
   - `project.md` → skip (inherently project-specific)
   - `project.examples.md` → skip (inherently project-specific)
3. Parse each file: extract YAML frontmatter (`paths:`) and body sections (`## Principles`, `## Project-specific patterns`, `## Principles Examples`, `## Project-specific Examples`)

### Step 3: Normalize Similar File Names

Before merging, group files that refer to the same concept but have different names. This applies to `.md`, `.local.md`, and `.examples.md` files — a `.md` and its corresponding `.local.md` and `.examples.md` share the same normalization.

1. Detect similar file names within the same directory (e.g., `rails-controller.md` vs `rails-controllers.md`)
   - Singular/plural variants (e.g., `controller` / `controllers`)
   - Minor naming differences for the same concept (use AI judgment based on file content and `paths:` frontmatter overlap)
2. For each group, select a canonical name:
   - Prefer the name used by the majority of projects
   - If tied, prefer the name matching rules-extract's layered framework convention (e.g., `<framework>-<layer>`)
3. Treat grouped files as the same file for subsequent merge steps
4. Report normalized groups in the summary (e.g., "`rails-controller.md` + `rails-controllers.md` → `rails-controllers.md`")

### Step 4: Merge Portable Rules (.md)

**Design note:** Once a pattern is promoted to a Principle (via Step 5), it becomes a permanent org-level rule. To demote or remove a promoted Principle, manually edit the org rules output.

For each unique (normalized) file name across projects:

1. Collect all versions from projects that have this file (including normalized variants)
2. Merge `## Principles` sections:
   - Deduplicate by principle name (text before parenthetical hints)
   - Union hints from all projects for the same principle
   - If same principle name but clearly different meaning → keep both, flag in report (see Conflict Handling)
   - Preserve unique principles from any project
3. Merge `paths:` frontmatter: union of all path patterns, deduplicate
4. If file exists in only 1 project, include as-is

### Steps 5 + 5.5: Promote Patterns and Merge Examples

Scan `.local.md` files (and hybrid `.md` files) for patterns appearing in enough projects to meet `promote_threshold`. Promoted patterns are converted from signature format to Principles format and appended to the corresponding `.md` output. `.examples.md` files are merged in parallel, with examples for promoted patterns moved to `## Principles Examples`.

See `references/promotion-algorithm.md` for the full algorithm: semantic equivalence rules, threshold calculation, deduplication logic, and examples file merging.

### Step 6: Write Output

1. Check output directory:
   - If `--dry-run`: skip writing, show planned file list with contents summary, then go to Step 7
   - If exists and has files: warn, then use `AskUserQuestion` — question: "Output directory already has files. Overwrite?", options: "Overwrite" / "Cancel" — before overwriting
   - If not exists: create with `mkdir -p`
2. Write merged files preserving directory structure:
   - `languages/<lang>.md` / `languages/<lang>.examples.md`
   - `frameworks/<framework>.md` / `frameworks/<framework>.examples.md`
   - `integrations/<framework>-<integration>.md` / `integrations/<framework>-<integration>.examples.md`
   - Only `.md` and `.examples.md` files (no `.local.md` in output)

See `references/output-formats.md` for the output file format.

### Step 7: Report Summary

Display report using the project's directory name (last path component) as label. Report headers are always in English.

See `references/report-format.md` for an annotated report example.

## Conflict Handling

- **Same principle, different hints**: Union all hints, deduplicate
- **Same principle name, different meaning**: Keep both, flag in report for human review
- **Same category, different paths**: Union all path patterns
- **Contradicting principles**: Keep both, report as conflict for human review

## Testing & Validation

After running rules-merge:

1. **Dry run first** — run with `--dry-run` to verify file list and promotion counts before writing
2. **Promoted count** — verify promoted pattern count matches expectations for patterns exceeding the threshold
3. **No `.local.md` in output** — confirm the output directory contains only `.md` and `.examples.md` files
4. **Examples pointers** — every `.md` with a sibling `.examples.md` must end with `## Examples`
5. **Conflict review** — review any flagged conflicts in the report before committing output

**Quality gates:**
- [ ] Report shows expected sources and file counts
- [ ] Promoted patterns are correct (run on known test data first if unsure)
- [ ] No unexpected conflicts
- [ ] Output directory contains no `.local.md` files
- [ ] Dry run matches live run file list

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/config-schema.md` | Full annotated config file format |
| `references/promotion-algorithm.md` | Steps 5 and 5.5 — promotion algorithm and examples merging detail |
| `references/output-formats.md` | Output file format (.md and .examples.md structures) |
| `references/report-format.md` | Annotated sample report showing all output sections |
