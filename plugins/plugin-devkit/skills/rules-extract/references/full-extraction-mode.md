# Full Extraction Mode

Steps executed when `/rules-extract` is invoked with no arguments.

## Contents

- Step 1: Load Settings
- Step 2: Detect Project Type
- Step 3: Collect Sample Files
- Step 4: Analyze by Category
- Step 5: Analyze Documentation and Existing Rules
- Step 6: Generate Output
- Step 6.5: Security Self-Check
- Step 7: Report Summary

## Step 1: Load Settings

Search for `rules-extract.local.md`:

1. **Project-level**: `.claude/rules-extract.local.md`
2. **User-level**: `~/.claude/rules-extract.local.md`

**Priority:**
- If both exist, use project-level only
- If only one exists, use that file
- If neither exists, use default settings

**Extract settings** (`target_dirs`, `exclude_dirs`, `exclude_patterns`, `output_dir`, `examples_output_dir`, `staging_output_dir`, `language`, `split_output`, `resolve_references`, `compaction_threshold`) from the config file. See Configuration section in the main SKILL.md for defaults.

**`language` resolution:** skill config → Claude Code settings (`~/.claude/settings.json` `language` field) → default `en`

## Step 2: Detect Project Type

Detect project language and framework:

**1. Detect languages** by config files (`package.json`, `tsconfig.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile`, `pom.xml`, etc.) and file extensions (`.ts`/`.tsx`, `.py`, `.go`, `.rb`, etc.)

**2. Detect frameworks** by their config files (e.g., `next.config.*`, `playwright.config.*`) and dependencies in package manifests.

**3. Detect architectural layers** (for layered frameworks):
If a framework has distinct layers with separate directories (e.g., Rails: `app/models/`, `app/controllers/`; Django: `models.py`, `views.py`), detect them for layer-specific rule files. Only split when corresponding directories actually exist.

**4. Detect integration libraries** (for layered frameworks):
Read `references/integration-criteria.md` for detection rules and classification criteria.

**Output:** List of detected languages, frameworks, architectural layers, and integration libraries

## Step 3: Collect Sample Files

Collect target files for analysis:

1. **Get git-tracked files** using `git ls-files` (respects `.gitignore`). If not a git repo, fall back to Glob with manual exclusions from settings.
2. Filter by `target_dirs`, `exclude_dirs`, `exclude_patterns`, and detected language extensions
3. Sample 10-15 files per category, distributed across directories for representative coverage. Large projects (100+): prioritize directory diversity. Small projects (<10): analyze all files.

## Step 4: Analyze by Category

Using the pre-loaded `extraction-criteria.md`, the core question for every pattern is: **"Would Claude produce something different without knowing this?"** — extract only what fills the gap between Claude's general knowledge and this project's actual conventions.

For each detected language, framework, and **integration library**:

1. Use Grep/Read to collect relevant code patterns

1.5. **Separate integration-specific patterns** (for layered frameworks with integrations):
   See `references/integration-criteria.md` "Pattern routing" section.

2. **Classify each pattern** (see `references/extraction-criteria.md`):
   - **General style choice** (uses only language built-ins) → Abstract principle + hints
   - **Project-defined symbol** (types, functions, hooks defined in project) → Include concrete example

3. **For general style patterns:**
   - Group related patterns (e.g., "prefer const", "avoid mutations", "use spread" → Immutability)
   - Formulate as principle with parenthetical implementation hints (2-4 keywords)

4. **For project-specific patterns:**
   - Extract only the **minimal signature** (type definition, function signature, or API combination)
   - Format as one line: `signature` - brief context (2-5 words)
   - Avoid multi-line code blocks to minimize context overhead

5. Apply AI judgment to determine which patterns meet the extraction criteria (see `references/extraction-criteria.md`)

Determine appropriate detection methods based on language and project structure.

## Step 5: Analyze Documentation and Existing Rules

Also analyze non-code documentation:

- README.md
- CONTRIBUTING.md
- PR templates
- Existing CLAUDE.md

Extract explicit coding rules and guidelines from these documents.

**Deduplication check:** Read any files under `.claude/rules/` to build a set of already-documented rules. Rules extracted in Step 4 that overlap with these existing rules should be skipped to avoid duplication. Note: CLAUDE.md is NOT a deduplication source — rules should exist in `.claude/rules/` even if also mentioned in CLAUDE.md, because rule files are portable across projects via rules-merge. This check applies to all modes (Full Extraction, Update, Conversation, PR Review).

## Step 6: Generate Output

Apply the pre-loaded `security.md` patterns before generating output to ensure sensitive information is not included.

1. Check if `output_dir` exists
   - If exists: Error "Output directory already exists. Use `--restructure` to reorganize, `--update` to add new patterns, or delete the directory manually to start fresh."
   - If not exists: Create `output_dir`. Also create `examples_output_dir` if it differs from `output_dir` and does not exist yet (when both resolve to the same path the single directory created above is reused).

2. Generate rule files per category. Rule files (`<name>.md` and `<name>.local.md`) are written under `output_dir`; `<name>.examples.md` files are written under `examples_output_dir` (default: `.claude/rules-extras` — outside Claude Code's `.claude/rules/**` auto-load scope, so examples do not consume context on session start).

   - `languages/<lang>.md` for language-specific rules (under `output_dir`)
   - `frameworks/<framework>.md` for framework-specific rules (under `output_dir`)
   - `project.md` for project-specific rules (under `output_dir`)
   - **Layered frameworks**: `<framework>.md` (cross-layer) + `<framework>-<layer>.md` per detected layer with scoped `paths:`
   - **Integration libraries**: See `references/integration-criteria.md` "Output structure" section.

   **By default** (`split_output: true`): Generate 3 files per category (except project which gets 2):
   - `<output_dir>/<name>.md` — `## Principles` only (portable), with `paths:` frontmatter
   - `<output_dir>/<name>.local.md` — `## Project-specific patterns` only (local), with the **same `paths:` frontmatter** as its `<name>.md` counterpart (`paths:` is retained as a human-facing category-scope hint; loader-side semantics is not empirically verified, and auto-load is determined by directory placement only)
   - `<examples_output_dir>/<name>.examples.md` — Examples for both. Whether the file is auto-loaded depends on `examples_output_dir`'s placement relative to `.claude/rules/**`: with the default `.claude/rules-extras` it is outside auto-load scope; with `examples_output_dir` set to `output_dir` (or any path under it) it is auto-loaded
   - Layer-specific and regular files each define their own `paths:` independently (applies to both `.md` and `.local.md`). Cross-layer files (`<framework>.md` / `<framework>.local.md`) use no `paths:` or broad scope as they apply across all layers.
   - Skip generating a file if it would be empty. Skipped files are omitted from the Step 7 report.

   **When `split_output: false`**: Generate single hybrid file per category under `output_dir`, and the matching `<name>.examples.md` under `examples_output_dir`.

**Rule file format:** See `references/output-structure.md` § Rule File Format for the hybrid example and format guidelines.

**Format guidelines:**

For **Principles** section:
- Each principle: `Principle name (hint1, hint2, hint3)`
- Principle name: noun phrase naming the philosophy (e.g., "Immutability" not "Use const")
- Hints: 2-4 keywords per principle, describing implementation techniques observed in the project
- Only for general style choices (language built-ins)

For **Project-specific patterns** section:
- **One line per pattern**: `` `signature` `` - brief context
- Use inline code for signatures, not code blocks
- Keep context to 2-5 words
- Only include the minimal signature: type name, function signature with return type, or API combination
- Example of minimal: `useAuth() → { user, login, logout }` (not full implementation)

**For `.examples.md` files:** Follow the pre-loaded `examples-format.md` for file structure, Good/Bad contrast guidelines, and the reference section format. Each rule file with a corresponding `.examples.md` must end with a `## Examples` reference section (see the reference for format). `###` titles must match the corresponding rule name exactly — do not translate or rephrase.

**paths patterns by category:**
- TypeScript: `**/*.ts`, `**/*.tsx`
- Python: `**/*.py`
- React: `**/*.tsx`, `**/*.jsx`
- Integration libraries: scope `paths:` to layers where the integration is used
  (e.g., Inertia in controllers: `app/controllers/**`)
- (project.md: no paths frontmatter = applies to all files)

## Step 6.5: Security Self-Check

After generating all rule files, verify no sensitive information was included:

1. Grep generated/updated files for patterns that may indicate secrets:
   - Long hex strings: `[0-9a-fA-F]{20,}`
   - Base64-like strings: `[A-Za-z0-9+/=]{40,}`
   - Keyword-adjacent literals: `(key|token|secret|password|credential)\s*[:=]\s*["'][^"']+`
   - Internal URLs: `(internal|staging|localhost:[0-9]+)`
2. If found, redact with placeholders (e.g., `API_KEY_REDACTED`) and warn the user

**Note:** This check applies to all modes that generate or update rule files (Full Extraction, Update, Restructure, Conversation Extraction). Also check `.examples.md` files — they contain actual code from the codebase and may include sensitive information.

## Step 7: Report Summary

Display analysis summary. Per the pre-loaded `report-templates.md` § Full Extraction Mode for format.
