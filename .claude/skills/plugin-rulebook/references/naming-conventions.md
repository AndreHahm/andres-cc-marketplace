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
