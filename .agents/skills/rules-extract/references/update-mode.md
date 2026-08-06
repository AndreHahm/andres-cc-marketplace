# Update Mode — Complete Procedure

Steps executed when `/rules-extract --update` is invoked. Re-scans the codebase and adds new patterns while preserving existing rules.

## Contents

- Step U1: Load Settings and Check Prerequisites
- Step U2: Re-scan Codebase
- Step U3: Staleness Check
- Step U4: Compare and Merge
- Step U5: Append New Rules
- Step U5.5: Security Self-Check
- Step U6: Report Changes

## Step U1: Load Settings and Check Prerequisites

1. Load settings from `rules-extract.local.md` (same as Step 1 in `references/full-extraction-mode.md`)

2. Check if output directory exists (default: `.claude/rules/`)
   - If not exists: Error "Run /rules-extract first to initialize rule files."
   - If `split_output: true` and hybrid files exist (`.md` files containing both `## Principles` and `## Project-specific patterns`): warn that hybrid files were found — recommend running `--restructure` to migrate to split format
   - If `split_output: false` and `.local.md` files exist: warn that orphaned `.local.md` files were found — recommend deleting orphaned files manually or running `--restructure`

3. Load existing rule files to understand current rules (load `<output_dir>/<name>.md`, `<output_dir>/<name>.local.md`, and `<examples_output_dir>/<name>.examples.md` when split). When `examples_output_dir` does not yet exist (e.g. legacy projects where examples were co-located under `output_dir`), fall back to loading `<output_dir>/<name>.examples.md` so existing examples are not invisible to the merge step; `--restructure` can subsequently migrate them to `examples_output_dir`. Additionally load `<staging_output_dir>/project.staging.local.md` if present — this file is required for the Step U4 staging-match branch. Skip silently if the staging file does not yet exist (no incremental run has populated it yet).

## Step U2: Re-scan Codebase

Execute Steps 2–5 from `references/full-extraction-mode.md` (Detect project type, Collect sample files, Analyze by category using pre-loaded `extraction-criteria.md`, Analyze documentation).

## Step U3: Staleness Check

Before adding new rules, check existing project-specific patterns for staleness:

1. Collect patterns from `## Project-specific patterns` sections:
   - When `split_output: true`: from `.local.md` files
   - When `split_output: false`: from `## Project-specific patterns` sections in `.md` files
2. For each pattern that has an inline code signature (`` `symbol` ``), verify the symbol still exists in the codebase using Grep
   - Skip patterns without searchable symbols (e.g., principles, anti-patterns like "No default exports")
   - For combination patterns (e.g., `` `pathFor() + url()` ``), check each symbol individually
3. Patterns whose symbols can no longer be found → Flag as potentially stale in the Step U6 report
4. Do NOT auto-delete stale rules — only report them for user review

This prevents rule files from growing indefinitely as the codebase evolves.

## Step U4: Compare and Merge

For each extracted principle/pattern:

1. **Check if already exists**: Compare with existing rules (check both shared and local files if `split_output: true`). Evaluate the branches below in order, first match wins (same evaluate-in-order discipline as `references/conversation-mode.md` § Step C5's "Check for duplicates and route per category" step):
   - Exact match → Skip
   - Similar but different → Keep both (let user review)
   - **Cross-format duplicate check**: A project-specific pattern may have been promoted to a Principle by rules-merge. Check if the pattern's description semantically matches an existing principle name in the corresponding `.md` file (use AI judgment: case-insensitive, synonyms). For example, `` `useAuth() → { user, login, logout }` - auth hook interface `` is a duplicate of `Auth hook interface (useAuth)` in `## Principles`. Skip patterns that already exist as Principles.
   - **Staging match (project-level patterns only)**: if the pattern matches an entry in `<staging_output_dir>/project.staging.local.md` per the staging-match criterion (see `references/conversation-mode.md` § Step C5's "staging-match criterion" paragraph), schedule a **promote** — append to `<output_dir>/project.md` (the single hybrid file for project-level patterns) in Step U5, then delete the matched entry from staging in Step U5 (move-atomicity: canonical-first, staging-delete-second). Update Mode does not write new staging entries; un-matched project-level patterns land directly in canonical.
   - New → Add

2. **Preserve manual edits**: Do not modify existing rules

## Step U5: Append New Rules

1. **New category detected** (e.g., new framework/language): Create new rule files following Step 6 format in `references/full-extraction-mode.md`. Report as "New" in Step U6.
2. Append new principles to `## Principles` section
3. Append new project-specific patterns to `## Project-specific patterns` section
4. **When `split_output: true`**: Principles go to `<output_dir>/<name>.md`, patterns go to `<output_dir>/<name>.local.md`. Create missing files with proper frontmatter.
5. For `<output_dir>/project.md`: always append to the single file
6. Maintain file structure and formatting
7. **Update `.examples.md`**: Resolve the target path via `examples_output_dir` (`<examples_output_dir>/<name>.examples.md`). Create the file (and any missing parent directories under `examples_output_dir`) when absent. Follow the pre-loaded `examples-format.md` common generation procedure to add examples for each new rule. Per `references/conversation-mode.md` § Step C5's **"Update `.examples.md`"** step ("examples-on-canonical-only"), both direct canonical appends and promotes from staging count as canonical writes and trigger examples; Update Mode has no staging-only path, so every new rule in this step gets an `.examples.md` entry.
8. **Promote staging matches** (project-level patterns flagged in Step U4 as staging matches): append each to `<output_dir>/project.md` (the single hybrid file for project-level patterns, per item 5) and, after verifying the canonical write, `Edit` `<staging_output_dir>/project.staging.local.md` to remove the corresponding bullet. If the staging-delete `Edit` fails because the bullet is no longer uniquely matchable, leave the duplicate — the next session's canonical-match skip resolves it. Update Mode does not write new staging entries.

## Step U5.5: Security Self-Check

Using the pre-loaded `security.md` patterns, run the security self-check on new/updated files, **including the staging file** if any staging-delete edits landed in Step U5 (the staging file was rewritten by the staging-delete `Edit`).

## Step U6: Report Changes

Report what was added per file. Also report any stale rules found in Step U3. Include `canonical_skip_count` and `promoted_count` (Update Mode never increments `staged_count` because it does not write new staging entries). Per the pre-loaded `report-templates.md` § Update Mode for format.
