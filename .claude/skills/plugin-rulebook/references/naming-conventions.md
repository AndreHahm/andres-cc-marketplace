# Naming Conventions

All component identifiers in a plugin must use **lowercase kebab-case**. This applies to the `name` field in frontmatter, directory names, and reference file names.

**Pattern:** `^[a-z][a-z0-9-]+[a-z0-9]$`
**Length:** 3–64 characters (configurable in `settings.json → naming.max_length`)
**Forbidden words in `name`:** `anthropic`, `claude`

## Component-Type Conventions

| Component | Convention | Examples |
|---|---|---|
| Skill | Noun or gerund phrase describing capability | `skill-development`, `plugin-rulebook`, `rules-extract` |
| Agent | Role-based noun phrase | `skill-reviewer`, `plugin-validator`, `agent-creator` |
| Command | Verb-first action phrase | `create-plugin`, `review-rules`, `extract-rules` |
| Hook | Event + optional scope | (no user-visible name; identified by file path) |
| Rule | Behavior description | `no-hardcoded-secrets`, `require-kebab-case` |
| Reference file | Topic noun phrase | `naming-conventions`, `allowed-tools`, `movement-pattern` |
| Directory | Same as component name | `skills/skill-development/`, `agents/skill-reviewer/` |

## Reference File Naming (R10)

Reference files live in `references/` and use a topic-first naming scheme.

**Primary (English):** `references/<topic>.md`
**Language variant:** `references/<topic>.<lang-code>.md`

### Topic Naming Rules

- Lowercase, hyphen-separated: `validation-checklist.md`, `allowed-tools.md`
- Max 40 characters for the topic portion (before any lang-code suffix)
- No abbreviations unless universally recognized: `api`, `mcp`, `ui`, `ux`, `url`
- Must be specific — name what the file contains, not who uses it

### Forbidden Generic Names

These names are not allowed because they provide no information about content:

| Forbidden | Why | Use Instead |
|---|---|---|
| `reference.md` | Redundant — all files in `references/` are references | `validation-checklist.md` |
| `guide.md` | No scope | `refinement-workflow.md` |
| `config.md` | No scope | `hook-configuration.md` |
| `docs.md` | No scope | `api-reference.md` |
| `info.md` | Meaningless | `plugin-manifest.md` |
| `readme.md` | Human docs, not AI instructions | N/A — remove entirely |
| `index.md` | Use table of contents in SKILL.md | N/A |

### Good vs Bad Examples

| Bad | Good | Why |
|---|---|---|
| `ref.md` | `80-percent-rule.md` | Specific topic |
| `guide.md` | `refinement-workflow.md` | Describes the workflow |
| `stuff.md` | `movement-pattern.md` | Names the pattern |
| `docs.md` | `validation-checklist.md` | Names the artifact |
| `tips.md` | `common-scenarios.md` | Describes the content |

## Skill Naming Advice

- Prefer **noun or gerund phrases** that describe the skill's domain: `skill-development`, `hook-development`
- Avoid suffixes like `-helper`, `-util`, `-tool` — name the domain, not the role
- For paired skills, use consistent prefixes: `rules-extract` / `rules-merge` / `rules-apply`

## Agent Naming Advice

- Use **role nouns**: `skill-reviewer` (not `review-skill`), `plugin-validator` (not `validate-plugin`)
- Append `-reviewer`, `-creator`, `-validator`, `-checker` to describe the agent's function
- Keep names short enough to be readable as a Skill/Task invocation target

## Command Naming Advice

- Start with a **verb**: `create-`, `review-`, `apply-`, `extract-`, `merge-`
- Commands are user-facing — names appear as `/create-plugin`, `/review-rules`
- Verb should match the primary action, not the component type

## Open Item: Plugin Suffix/Prefix Taxonomy

This file has no row for plugin-level naming. This marketplace's own hyphen-placement convention (`<domain>-kit`/`<domain>-devkit`, exactly one hyphen before the suffix) is documented in this repo's `CLAUDE.md`, not here — it's repo-specific, not a portable plugin-rulebook default.

**Not yet decided, and not implemented as a rule:** which suffix (`-kit` vs. `-devkit`) or prefix applies to which kind of plugin, and what the full list of allowed suffixes/prefixes even is. A rule can't check against a list that doesn't exist yet. Once that list is defined, the natural implementation mirrors R23's whitelist pattern: a portable rule that checks a plugin name's suffix/prefix against an allowed list, with the actual list itself living in a repo-specific override file (like `{REPO_ROOT}/.claude/plugin-rulebook.config.json` already does for R23) rather than hardcoded into the portable rulebook.

## R33 — Component-File Prefix (Not the Same "Prefix" as the Open Item Above)

**This is a different concept from the Open Item above, despite sharing the word "prefix."** The Open
Item above is about a plugin's own *name* — whether `git-kit` should be suffixed `-kit` vs. `-devkit`.
R33 is about *file naming inside an already-named plugin* — once a plugin is named `git-kit`, must its
own `scripts/check-pr-title.py` be renamed `scripts/git-check-pr-title.py`. The two are independently
decided, unrelated in scope, and this section exists specifically to prevent conflating them.

R33 requires every file recursively under a registered plugin's root-level `scripts/`, `references/`,
`assets/`, `hooks/` (including nested `hooks/scripts/`), and `commands/` directories to be named
`<prefix>-<rest>`, where `<prefix>` is that plugin's own curated, permanent, marketplace-wide-unique
value registered in `marketplace-inventory.json` (pattern `^[a-z]{3,4}$`, no separator — the hyphen is
prepended when used as a filename prefix). Inert for any plugin with no `prefix` registered yet. See
`${CLAUDE_SKILL_DIR}/references/component-file-prefix.md` for the full scope, exclusions, and the
`antigravity-kit`-only temporary `bin`/`docs` exception, and `SKILL.md`'s R33 entry for the rule's
severity and gating summary.
