---
name: rules-apply
description: >-
  Apply organization-wide rules (from rules-merge output) to the current project.
  Use when syncing portable Principles from a shared rules repository, merging org
  rules into project rules, cleaning up promoted patterns from .local.md files,
  fixing non-conforming rule files, or propagating rules-merge output to a project.
  Detects tech stack, merges Principles, removes duplicate patterns, and ensures
  rules-extract/rules-merge convention conformance.
allowed-tools: Read Glob Grep Write Bash(gh:*) Bash(mktemp:*) Bash(rm -rf */rules-apply-*) Bash(rm .Codex/rules/**/*.local.md)
---

# Apply Rules

Applies organization-wide rules (produced by rules-merge) to the current project. Detects the project's tech stack, selects relevant rules, merges them with existing rules-extract output, cleans up promoted patterns from `.local.md` files, and ensures the final structure conforms to the rules-extract/rules-merge convention.

## Quick Start

1. **Set up source** — pass a GitHub URL/local path as argument, or create `.Codex/rules-apply.local.md` with a `source:` field
2. **Run** — `/rules-apply <source>` or `/rules-apply` (uses config file); add `--dry-run` to preview first
3. **Confirm tech stack** — review detected languages/frameworks; add `include:` overrides if anything is missing
4. **Approve integrations** — respond to any prompts for undetected integration rules (all / none / by number)
5. **Resolve conflicts** — for Principles that differ between org and project: adopt org / keep project / keep both
6. **Confirm structure cleanup** — approve migration plan for any non-conforming files
7. **Check report** — verify Applied Rules, Promoted Pattern Cleanup, and Skipped sections

## When to Use

- Syncing portable Principles from a shared rules repository into the current project
- After `rules-merge` produces updated org rules that need propagating downstream
- Cleaning up `.local.md` patterns that have been promoted to org-level Principles
- Fixing non-conforming rule files to match the rules-extract/rules-merge convention
- Updating project rules when org conventions change

## When NOT to Use

- Creating new rules from scratch → use `rule-development` instead
- Extracting project patterns into portable rules → use `rules-extract` instead
- Merging rules across multiple projects into one org set → use `rules-merge` instead
- Reviewing compliance of existing rules against a diff → use `rules-review` instead

## Usage

```text
/rules-apply <source>                  # Apply from GitHub URL or local path
/rules-apply                           # Apply using config file
/rules-apply --config <path>           # Apply using specified config file
/rules-apply --dry-run                 # Show what would change without writing
/rules-apply --dry-run <source>        # Dry run with specified source
```

`<source>` points directly to the rules directory (rules-merge or rules-extract output):
- GitHub: `https://github.com/org/repo/tree/main/.Codex/rules`
- Local: `~/org-rules/.Codex/rules`

## Configuration

Config file search order:
1. `--config <path>` argument
2. `.Codex/rules-apply.local.md` (project-level)
3. `~/.Codex/rules-apply.local.md` (user-level)

**File format:** YAML frontmatter only (no markdown body), same convention as `rules-extract.local.md` and `rules-merge.local.md`.

**Key fields:** `source` (required), `output_dir` (default: `.Codex/rules/`), `auto_detect` (default: `true`), `include`/`exclude` (arrays), `language` (default: `en`)

See `references/config-template.md` for the full annotated config file.

CLI argument `<source>` overrides the config's `source` field.

## Processing Flow

### Step 1: Load Configuration

1. If CLI `<source>` argument provided, use it (overrides config `source`)
2. Search for config file (see search order above)
3. Parse YAML frontmatter, apply defaults for omitted fields
   - **`language` resolution order:** Skill config → Codex settings (`~/.Codex/settings.json` → `language` field) → default `en`
4. Validate:
   - `source` must be specified (via CLI argument or config file)
   - If neither: Error "No source specified. Provide a GitHub URL or local path as argument, or create `.Codex/rules-apply.local.md` with a `source:` field."

### Step 2: Fetch Source Rules

**If source is a local path:**

1. Expand `~` and resolve to absolute path
2. Verify directory exists and contains rule files (`.md`)
3. Read directly from this location

**If source is a GitHub URL:**

Parse URL to extract owner, repo, branch, and path:
- `https://github.com/{owner}/{repo}/tree/{branch}/{path}`
- Example: `https://github.com/org/repo/tree/main/.Codex/rules`
  → owner: `org`, repo: `repo`, branch: `main`, path: `.Codex/rules`

**Note on ambiguous refs:** Branch names may contain `/` (e.g., `feature/rules-v2`), and refs can also be tags or SHAs. Simple URL splitting cannot reliably separate ref from path. To handle this robustly:
- Try resolving ref candidates from longest prefix first using `gh api repos/{owner}/{repo}/git/ref/{candidate}`
- Alternatively, the user can specify components separately in the config:
  ```yaml
  source_repo: org/repo
  source_ref: feature/rules-v2
  source_path: .Codex/rules
  ```
  When these fields are present, they take precedence over URL parsing.
- For the common case (branch = `main` or `master`), simple URL parsing works.

Fetch using `gh api`:

1. Verify authentication: `gh auth status`
2. Create temp directory: `mktemp -d -t rules-apply-XXXXXX`. Record the exact path `mktemp` returns — Step 8's cleanup deletes only this literal path, never a re-derived or pattern-matched one.
3. List top-level directory contents:
   ```
   gh api repos/{owner}/{repo}/contents/{path}?ref={branch}
   ```
   For each entry with `type: "dir"`, recursively fetch subdirectory contents:
   ```
   gh api repos/{owner}/{repo}/contents/{path}/{subdir}?ref={branch}
   ```
   This dynamically discovers all categories (not limited to `languages/`, `frameworks/`, `integrations/`).
4. For each `.md` file found, fetch content and decode:
   ```
   gh api repos/{owner}/{repo}/contents/{file_path}?ref={branch} --jq '.content | @base64d'
   ```
   Save to tmpdir preserving directory structure
5. Temp dir is cleaned up in Step 8

**Inventory source files:**
- Glob for `**/*.md` and `**/*.examples.md` under the source rules directory
- Skip `project.md` and `project.examples.md` (inherently project-specific)
- Skip `.local.md` files (rules-merge output should not contain these, but handle gracefully)
- Parse each file: extract YAML frontmatter (`paths:`) and body sections

### Step 3: Detect Target Project Tech Stack

Analyze the current working directory to determine which source rules are relevant. Detection is best-effort, based on dependency files (e.g., `Gemfile`, `package.json`) and project directory structure (e.g., `app/controllers/`).

Read `references/detection-heuristics.md` for the full detection table mapping indicators to rule files. If the source contains rule files not covered in the table, use AI judgment to match them against the project's dependencies and file structure.

**Apply overrides:**
- Add `include:` entries to the detected set
- Remove `exclude:` entries from the detected set
- If `auto_detect: false`: start with ALL source rules, then apply `exclude` only

### Step 4: Filter and Propose

**If `auto_detect: false`:** Apply ALL source rules (minus `exclude` entries). Skip the proposal step entirely — no integration proposals or skipped rules. Proceed directly to Step 5.

**If `auto_detect: true` (default):**

1. **Auto-matched rules**: Rules that match detected tech stack → apply automatically
2. **Integration proposals**: For integrations NOT detected in the project but related to a detected framework (e.g., source has `integrations/rails-pundit` but project doesn't use `pundit`), use `AskUserQuestion` to present them as a single list:

   > The following integration rules are available in the source but were not detected in your project. Which would you like to apply?
   > 1. `integrations/rails-pundit` — Authorization library Pundit rules
   > 2. `integrations/rails-good-job` — Job queue GoodJob rules
   >
   > Options: all / none / specify by number (e.g. "1" or "1,2")

   Apply only those the user approves.

3. **Skipped rules**: Rules for tech not detected and not in related frameworks → skip, list in report

### Step 5: Inventory Existing Target Rules

1. Check if `{output_dir}/` exists in the target project
2. If exists, read all files: `.md`, `.local.md`, `.examples.md`
3. Parse frontmatter and body sections for each
4. Categorize files the same way as source files
5. **Detect hybrid format**: If any target `.md` file contains `## Project-specific patterns` (hybrid format from rules-extract `split_output: false`), note this. The merge step will convert hybrid to split format because the split format (separate `.md` and `.local.md`) is the standard expected by both rules-extract and rules-merge, and mixing formats causes confusion when rules flow back through the pipeline. Note: source files from rules-merge should not contain `## Project-specific patterns` (promoted patterns are converted to Principles format)

### Step 5.5: Normalize File Names

Before merging, align target file names with source (canonical) names. This prevents duplicate files for the same concept (e.g., `rails-controller.md` vs `rails-controllers.md`).

1. Compare target file names against source file names within the same category
2. Detect naming variants: singular/plural (`controller`/`controllers`), minor differences for the same concept
3. If renames are detected, use `AskUserQuestion` to confirm:
   > The following target files will be renamed to match source (canonical) names:
   > 1. `frameworks/rails-controller.md` → `frameworks/rails-controllers.md`
   >
   > Options: all / none / specify by number
4. Apply approved renames and report in the summary

### Step 6: Merge Rules

For each filtered source rule file, determine the merge action:

**6a. Merge `.md` files (Principles):**

**Case: No existing `.md`**
1. Copy source `.md` as-is (source from rules-merge contains only `## Principles`)

**Case: Existing `.md` exists**
1. **`paths:` frontmatter**: Union of all path patterns, deduplicate
2. **Hybrid → split conversion**: If existing `.md` contains `## Project-specific patterns` (hybrid format):
   - Extract that section and move to `.local.md` (create if not exists, append if exists)
   - Remove the section from `.md`, keeping only `## Principles`
3. **`## Principles`**:
   - Match principles by name (text before parenthetical hints)
   - Source principle not in target → Add
   - Target principle not in source → Keep (project may have added its own)
   - Same principle, same meaning but different hints → Union hints from both
   - Same principle name but different content → Collect all conflicts, then use `AskUserQuestion` to present them together:
     > The following principles differ between org rules and project rules:
     >
     > **1. Immutability** (in `languages/ruby.md`)
     > - Org: `Immutability (spread, map/filter/reduce, const)`
     > - Project: `Immutability (freeze, deep clone, readonly)`
     >
     > **2. Error handling** (in `frameworks/rails.md`)
     > - Org: `Error handling (rescue, custom exceptions)`
     > - Project: `Error handling (rescue, retry, circuit breaker)`
     >
     > For each, choose: (a) Adopt org rule / (b) Keep project rule / (c) Keep both
     > Example: "1a, 2c" or "all a"

**6b. Clean up promoted patterns from `.local.md` files:**

`.local.md` files contain project-specific patterns discovered by rules-extract. When org rules promote a pattern to a Principle, the original pattern in `.local.md` becomes redundant. rules-apply cleans up these duplicates while preserving genuinely project-specific patterns.

- rules-apply does not write new patterns to `.local.md`
- **Cross-format duplicate removal**: After merging Principles in Step 6a, scan target `.local.md` for patterns whose description matches a Principle name now present in the corresponding `.md` (e.g., `` `useAuth() → { user, login, logout }` - auth hook interface `` is a duplicate of `Auth hook interface (useAuth)` in `## Principles`). Use AI judgment for semantic equivalence (case-insensitive, synonyms)
- Remove matched patterns from `.local.md`
- If `.local.md` becomes empty after removal, use `AskUserQuestion` to confirm before deleting the file — present the full list of `.local.md` files this run would delete as a single list for confirmation, same pattern as Step 7's non-conforming-file migration: "The following `.local.md` files are now empty after duplicate cleanup. Delete them?" — options "Delete all" / "Keep all (leave as empty files)" / "specify by number". Never delete silently, even though the removed patterns were confirmed duplicates — the file itself is a real, separately-named artifact a user may still reference elsewhere.
- Preserve all patterns that do not match any Principle (genuinely project-specific)
- **Sync `paths:` frontmatter**: for any `.local.md` that still exists after cleanup, ensure its `paths:` frontmatter matches the sibling `.md`'s `paths:` (union and deduplicate with any existing entries on `.local.md`). This keeps project-specific patterns auto-loading under the same scope as the portable Principles. Older `.local.md` files generated before rules-extract propagated `paths:` to `.local.md` may be unscoped; this step retrofits the scope without requiring a full rules-extract re-run

**6c. Merge `.examples.md` files:**

**Case: No existing `.examples.md`**
- Copy source `.examples.md` as-is (source from rules-merge contains only `## Principles Examples`)

**Case: Existing `.examples.md` exists**
1. **`## Principles Examples`**: Add examples from source for principles not already covered in target
2. **`## Project-specific Examples`** (target only): Remove examples whose `###` title corresponds to patterns removed from `.local.md` in Step 6b. Preserve all other existing entries

**6d. Ensure `## Examples` reference:**
- Every `.md` and `.local.md` that still exists and has a corresponding `.examples.md` must end with:
  ```markdown
  ## Examples
  When in doubt: ./<name>.examples.md
  ```
- If a `.local.md` was deleted in Step 6b (became empty), no reference is needed

### Step 7: Structure Conformance Check + Auto-cleanup

Scan `output_dir` for files that don't conform to rules-extract/rules-merge convention:

**Valid patterns:**
- `{category}/{name}.md`
- `{category}/{name}.local.md`
- `{category}/{name}.examples.md`
- `project.md`
- `project.examples.md`

**Valid categories:** `languages/`, `frameworks/`, `integrations/`

**Non-conforming file handling:**
1. Read the non-conforming file and analyze its content
2. Determine the appropriate conforming file(s) to migrate rules into (based on category, content, and `paths:` hints)
3. Use `AskUserQuestion` to present the migration plan as a single list for confirmation:
   > The following non-conforming files were detected. Migrate their rules to conforming files and delete them?
   > 1. `frameworks/old-custom-rules.md` → migrate to `frameworks/rails.md`
   > 2. `ruby-rules.md` → migrate to `languages/ruby.md`
   > 3. `project.rules.md` → migrate to `project.md` (**project file — confirm individually**)
   >
   > Options: all / none / specify by number (e.g. "1,2")
   >
   > Note: `project.*` files are excluded from "all". Specify them individually by number.
4. User approval → merge rules into conforming file(s) and delete non-conforming files
5. Report all migrations and deletions

### Step 8: Cleanup

If source was a GitHub URL, remove the temp directory: `rm -rf <tmpdir>`, where `<tmpdir>` is the exact literal path `mktemp` returned in Step 2 — never a re-derived, globbed, or reconstructed path. The `allowed-tools` scope (`Bash(rm -rf */rules-apply-*)`) is a coarse pattern match, not a path-boundary guarantee, since it matches the `rules-apply-` prefix as text regardless of which directory it appears under — the actual safety boundary is this step using only the recorded Step 2 path, not the permission string alone.

### Step 9: Report Summary

Display report. Report headers are always in English, content in the configured `language`.

See `references/report-format.md` for an annotated report example.

## Conflict Handling

Summary of user-confirmation points and automatic actions:

| Situation | Action |
|-----------|--------|
| Principle in source, not in target | Auto-add |
| Principle in target, not in source | Auto-keep |
| Same principle, different hints | Auto-union hints |
| Same principle name, different content | **AskUserQuestion**: collect all conflicts, present together (adopt org / keep project / keep both) |
| Non-conforming file detected | **AskUserQuestion**: present migration plan as single list for confirmation |
| `project.*` non-conforming file | Excluded from "all" — must be specified individually by number |
| Target file name differs from source canonical name | **AskUserQuestion**: confirm renames (all / none / specify) |
| Undetected integration rule (related framework) | **AskUserQuestion**: present as single list for approval (all / none / specify) |
| `.local.md` pattern matching a Principle | Auto-remove from `.local.md` (cross-format duplicate cleanup) |
| `.local.md` pattern not matching any Principle | Preserved |
| `## Project-specific Examples` for removed pattern | Auto-remove |
| `## Project-specific Examples` for remaining pattern | Preserved |

---

## Testing & Validation

After running rules-apply:

1. **Applied rules** — each rule file in the report appears at the correct path in `output_dir`
2. **Promoted cleanup** — patterns removed from `.local.md` match Principles now in the corresponding `.md`
3. **Examples reference** — every `.md`/`.local.md` with a sibling `.examples.md` ends with `## Examples`
4. **No orphaned `.local.md`** — `.local.md` files that became empty were deleted
5. **Dry run first** — run with `--dry-run` on unfamiliar sources to preview changes before writing

**Quality gates:**
- [ ] Report shows no unexpected skips (verify `auto_detect` and `include`/`exclude` config)
- [ ] Conflict resolutions recorded in report
- [ ] Structure cleanup applied: no non-conforming files remain in `output_dir`
- [ ] `paths:` frontmatter on `.local.md` matches sibling `.md` after sync
- [ ] Temp directory cleaned up (no leftover dirs from GitHub fetch)

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/detection-heuristics.md` | Tech stack detection table — maps dependency files and project structure to rule files |
| `references/config-template.md` | Full annotated config file format for `rules-apply.local.md` |
| `references/report-format.md` | Annotated sample report showing all output sections |