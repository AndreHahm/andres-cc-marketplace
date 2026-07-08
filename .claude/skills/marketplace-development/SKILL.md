---
name: marketplace-development
description: >-
  Converts a Claude Code skills repository (skills/ directories with SKILL.md files,
  no individual plugin.json per skill) into an official plugin marketplace —
  generates spec-conforming .claude-plugin/marketplace.json, validates with
  `claude plugin validate`, tests real installation, and PRs the upstream repo,
  encoding hard-won schema/version/description anti-patterns. Use when the user
  mentions marketplace.json, one-click install, auto-update, plugin distribution
  for a skills collection, or wants a skills repo installable via `claude plugin install`.
  For plugins that already have plugin.json, plugin-development handles marketplace publishing.
allowed-tools: Read Write Glob Bash(bash:*) Bash(jq:*) Bash(python3:*) Bash(find:*) Bash(claude:*) Bash(git:*)
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/skills/marketplace-development/hooks/post_edit_validate.sh"
          timeout: 30
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/skills/marketplace-development/hooks/post_edit_sync_check.sh"
          timeout: 10
---

# marketplace-development

Convert a Claude Code skills repository into an official plugin marketplace so users
can install skills via `claude plugin marketplace add` and get auto-updates.

**Input**: a repo with `skills/` directories containing SKILL.md files.
**Output**: `.claude-plugin/marketplace.json` + validated + installation-tested + PR-ready.

## Quick Start

1. **Check existing marketplace** — run `bash scripts/check_marketplace.sh`; if `RESULT: PASSED`, jump to Phase 4 (PR) or stop
2. **New marketplace** — Phases 1 → 2 → 3 → 4 in order
3. **Adding skills to existing marketplace** — see "Maintaining an existing marketplace" below → Phase 3 → Phase 4
4. **Debugging `claude plugin validate` failures** — see `references/debugging-guide.md` for session history mining
5. **Schema field reference** — `references/marketplace-schema.md`; for `source`/`skills` path pitfalls — `references/cache-and-source-patterns.md`

## When to Use

- Creating `.claude-plugin/marketplace.json` for a skills repository
- Adding new skills to an existing marketplace catalog
- Bumping plugin versions after SKILL.md content changes
- Debugging `claude plugin validate` or install failures
- Preparing a PR for a skills repo to support `claude plugin install` distribution

## When NOT to Use

- For plugins with an existing `plugin.json` — use `plugin-development` instead
- For local-only skills not intended for distribution

---

## Phase 0: Evidence Intake

Before editing an **existing** marketplace, collect evidence first — read
`references/debugging-guide.md` for session history mining patterns and
evidence-backed rule extraction. For new marketplaces, skip to Phase 1.

---

## Phase 1: Analyze the Target Repo

### Step 1: Discover all skills

```bash
# Find every SKILL.md
find <repo-path>/skills -name "SKILL.md" -type f 2>/dev/null
```

For each skill, extract from SKILL.md frontmatter:
- `name` — the skill identifier
- `description` — the ORIGINAL text, do NOT rewrite or translate

### Step 2: Read the repo metadata

- `VERSION` file (if exists) — this becomes `metadata.version`
- `README.md` — understand the project, author info, categories
- `LICENSE` — note the license type
- Git remotes — identify upstream vs fork (`git remote -v`)

### Step 3: Determine categories

Group skills by function. Categories are freeform strings. Good patterns:
- `business-diagnostics`, `content-creation`, `thinking-tools`, `utilities`
- `developer-tools`, `productivity`, `documentation`, `security`

Ask the user to confirm categories if grouping is ambiguous.

### Step 4: Choose plugin boundaries

Claude Code has three separate levels:

```text
marketplace -> plugin -> skill
```

- Marketplace name is used for install identity: `plugin@marketplace`.
- Plugin name is the slash namespace: `/plugin-name:skill-name`.
- Skill name comes from `SKILL.md` frontmatter when the skill path points to a
  directory containing `SKILL.md` directly.

Choose each plugin boundary by installation/update/cache intent:

- **Single-skill plugin**: use when the skill should install, update, and roll back
  independently with a narrow cache.
- **Suite plugin**: use when related skills should share one namespace and one
  install command, for example `/acme-docs:mermaid-tools`.

For detailed source/cache patterns and pitfalls, read
`references/cache-and-source-patterns.md` before changing `source` or `skills`.

---

## Phase 2: Create marketplace.json

### The official schema (memorize this)

Read `references/marketplace-schema.md` for the complete field reference.
Key rules that are NOT obvious from the docs:

1. **`$schema` field is REJECTED** by `claude plugin validate`. Do not include it.
2. **`metadata` only has 3 valid fields**: `description`, `version`, `pluginRoot`. Nothing else.
   `metadata.homepage` does NOT exist — the validator accepts it silently but it's not in the spec.
3. **`metadata.version`** is the marketplace catalog version, NOT individual plugin versions.
   It should match the repo's VERSION file (e.g., `"2.3.0"`).
4. **Plugin entry `version`** is independent. For first-time marketplace registration, use `"1.0.0"`.
5. **`strict: false`** is required when there's no `plugin.json` in the repo.
   With `strict: false`, the marketplace entry IS the entire plugin definition.
   Having BOTH `strict: false` AND a `plugin.json` with components causes a load failure.
6. **`source` defines the installed plugin root**. For single-skill plugins, point
   `source` directly at the skill directory (e.g., `"./tunnel-doctor"`) and omit
   `skills` entirely — this is the official pattern used by 167/168 plugins in
   `anthropics/claude-plugins-official`. For suite plugins, use
   `source: "./<suite>"` with explicit `skills` array listing subdirectories.
   Avoid `source: "./"` (installs full repo as cache) and `skills: ["./"]`
   (rejected by Claude Code 2.1.x path-escape validator).
7. **Reserved marketplace names** that CANNOT be used: `claude-code-marketplace`,
   `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`,
   `anthropic-plugins`, `agent-skills`, `knowledge-work-plugins`, `life-sciences`.
8. **`tags` vs `keywords`**: Both are optional. In the current Claude Code source,
   `keywords` is defined but never consumed in search. `tags` only has a UI effect
   for the value `"community-managed"` (shows a label). Neither affects discovery.
   The Discover tab searches only `name` + `description` + `marketplaceName`.
   Include `keywords` for future-proofing but don't over-invest.

### Generate the marketplace.json

Use the template in `references/marketplace-schema.md` (see "marketplace.json Template" section).
Key shape: root fields `name / owner / metadata / plugins[]`; each plugin entry requires `name / source / strict / version`.

### Naming the marketplace

The `name` field is what users type after `@` in install commands:
`claude plugin install dbs@<marketplace-name>`

Choose a name that is:
- Short and memorable
- kebab-case (lowercase, hyphens only)
- Related to the project identity, not generic

### Description rules

- **Use the ORIGINAL description from each SKILL.md frontmatter**
- Do NOT translate, embellish, or "improve" descriptions
- If the repo's audience is Chinese, keep descriptions in Chinese
- If bilingual, use the first language in the SKILL.md description field
- The `metadata.description` at marketplace level can be a new summary

---

## Maintaining an existing marketplace

When adding a new plugin to an existing marketplace.json:

1. **Bump `metadata.version`** — this is the marketplace catalog version.
   Follow semver: new plugin = minor bump, breaking change = major bump.
2. **Update `metadata.description`** — append the new skill's summary.
3. **Set new plugin `version` to `"1.0.0"`** — it's new to the marketplace.
4. **Bump existing plugin `version`** when its SKILL.md content changes.
   Claude Code uses version to detect updates — same version = skip update.
5. **Bump existing plugin `version`** when its `source` or `skills` changes.
   The installed cache path and component resolution changed even if SKILL.md did not.
6. **Audit `metadata` for invalid fields** — `metadata.homepage` is a common
   mistake (not in spec, silently ignored). Remove if found.
7. **Sync human-facing doc lists** — run `python3 scripts/check_doc_skill_lists.py` after
   adding or removing skills. It verifies that CLAUDE.md, README.md, and README.zh-CN.md
   skill lists match `marketplace.json` and flags any drift.

---

## Phase 3: Validate

### Step 1: One-shot pre-flight check

Run the bundled validator. It runs four checks in sequence and exits non-zero on
any required failure:

```bash
bash scripts/check_marketplace.sh          # validates current repo
bash scripts/check_marketplace.sh /path    # validates a target repo
```

What it checks:

| # | Check | Failure means |
|---|-------|---------------|
| 1 | JSON syntax of `.claude-plugin/marketplace.json` | file is not parseable JSON |
| 2 | `claude plugin validate .` (skipped if `claude` CLI missing) | schema-level rejection (e.g. `Unrecognized key: "$schema"`, duplicate names) |
| 3 | `source` + `skills` resolution for every plugin entry | a plugin entry points to a SKILL.md that does not exist on disk |
| 4 | Reverse sync (disk → manifest) | WARN-only: a SKILL.md on disk is not registered in any plugin entry |

Common schema failures and fixes:
- `Unrecognized key: "$schema"` → remove the `$schema` field
- `Duplicate plugin name` → ensure all names are unique
- `Path contains ".."` → use `./` relative paths only
- `No manifest found in directory` when validating an installed cache path → validate
  the marketplace manifest or plugin source, not a `strict: false` cache directory.

### Step 2: Installation test

```bash
# Add as local marketplace
claude plugin marketplace add .

# Install a plugin
claude plugin install <plugin-name>@<marketplace-name>

# Verify it appears
claude plugin list | grep <plugin-name>

# Check for updates (should say "already at latest")
claude plugin update <plugin-name>@<marketplace-name>

# Clean up
claude plugin uninstall <plugin-name>@<marketplace-name>
claude plugin marketplace remove <marketplace-name>
```

### Step 3: Cache footprint test

After installation or update, inspect the actual cache. This is the only way to
confirm `source` produced the intended snapshot:

```bash
PLUGIN=<plugin-name>
MARKET=<marketplace-name>
CACHE=$(jq -r --arg id "$PLUGIN@$MARKET" '.plugins[$id][0].installPath' ~/.claude/plugins/installed_plugins.json)
find "$CACHE" -maxdepth 1 -mindepth 1 -exec basename {} \; | sort
```

Expected results:

- Single-skill plugin cache: `SKILL.md` plus its own `scripts/`, `references/`,
  `assets/` as applicable.
- Suite plugin cache: only the suite member skill directories and suite-scoped
  resources.
- If unrelated skill directories appear, `source` is too broad.
- If cache entries are symlinks, the plugin is not self-contained; use canonical
  source directories instead of symlink farms.

### Step 4: GitHub installation test (if pushed)

```bash
# Test from GitHub (requires the branch to be pushed)
claude plugin marketplace add <github-user>/<repo>
claude plugin install <plugin-name>@<marketplace-name>

# Verify
claude plugin list | grep <plugin-name>

# Clean up
claude plugin uninstall <plugin-name>@<marketplace-name>
claude plugin marketplace remove <marketplace-name>
```

---

## Pre-flight Checklist (MUST pass before proceeding to PR)

Run this checklist after every marketplace.json change. Do not skip items.

### Automated checks

```bash
bash scripts/check_marketplace.sh
```

All four checks must pass. Treat the reverse-sync WARN as a real signal: an
unregistered `SKILL.md` on disk is almost always either an accidentally-dropped
skill you forgot to register, or dead code that should be removed.

### Metadata check

Verify these by reading marketplace.json:

- [ ] `metadata.version` bumped from previous version
- [ ] `metadata.description` mentions all skill categories
- [ ] No `metadata.homepage` (not in spec, silently ignored)
- [ ] No `$schema` field (rejected by validator)

### Per-plugin check

For each plugin entry:

- [ ] `description` matches SKILL.md frontmatter EXACTLY (not rewritten)
- [ ] `version` is `"1.0.0"` for new plugins, bumped for changed plugins
- [ ] `source` points directly at the skill directory (e.g., `"./skill-name"`)
- [ ] Single-skill plugins omit the `skills` field (auto-discovery from `source`)
- [ ] Suite plugins list `skills` paths relative to `source`
- [ ] `strict` is `false` (no plugin.json in repo)
- [ ] `name` is kebab-case, unique across all entries

### Final validation

```bash
bash scripts/check_marketplace.sh
```

Must print `RESULT: PASSED` before creating a PR. A `WARN [4/4]` is acceptable
only when you have consciously decided to leave a SKILL.md unregistered.

---

## Phase 4: Create PR

### Principles
- **Pure incremental**: do NOT modify any existing files (skills, README, etc.)
- **Squash commits**: avoid binary bloat in git history from iterative changes
- Only add: `.claude-plugin/marketplace.json`, optionally `scripts/`, optionally update README

### README update (if appropriate)
Add the marketplace install method above existing install instructions:

```markdown
## Install

<!-- Add a demo screenshot or gif here if one exists in the repo -->

**Claude Code plugin marketplace (one-click install, auto-update):**

\`\`\`bash
claude plugin marketplace add <owner>/<repo>
claude plugin install <skill>@<marketplace-name>
\`\`\`
```

### PR description template
Include:
- What was added (marketplace.json with N skills, M categories)
- Install commands users will use after merge
- Design decisions (pure incremental, original descriptions, etc.)
- Validation evidence (`claude plugin validate .` passed)
- Test plan (install commands to verify)

---

## Testing & Validation

After creating or modifying marketplace.json:

1. **JSON syntax** — `jq empty .claude-plugin/marketplace.json && echo "Valid"` before anything else
2. **Schema validation** — `bash scripts/check_marketplace.sh` — must print `RESULT: PASSED`
3. **Installation test** — `claude plugin marketplace add . && claude plugin install <name>@<market>` — verify via `claude plugin list`
4. **Cache footprint** — inspect installed cache to confirm `source` produced the right snapshot (see Phase 3, Step 3)
5. **Version bump** — if editing an existing plugin, confirm its `version` was incremented

**Quality gates:**
- [ ] `scripts/check_marketplace.sh` prints `RESULT: PASSED`
- [ ] All plugin `description` fields match SKILL.md frontmatter exactly
- [ ] No `$schema` field, no `metadata.homepage` field
- [ ] New plugins use `version: "1.0.0"`, changed plugins have version bumped
- [ ] `strict: false` on every plugin entry (no plugin.json in repo)

---

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/marketplace-schema.md` | Complete field reference for marketplace.json |
| `references/cache-and-source-patterns.md` | `source`/`skills` path patterns, pitfalls, cache behavior |
| `references/anti-patterns.md` | Real failures encountered and fixes (NOT theoretical) |
| `references/debugging-guide.md` | Session history mining for debugging existing marketplace failures |
| `scripts/check_marketplace.sh` | Automated pre-flight validator (4 checks, prints RESULT: PASSED) |
| `scripts/check_doc_skill_lists.py` | Verify skill lists match documentation |
| `hooks/post_edit_validate.sh` | Auto-runs `claude plugin validate` on marketplace.json writes (auto-activated) |
| `hooks/post_edit_sync_check.sh` | Warns when SKILL.md edited but plugin version not bumped (auto-activated) |
