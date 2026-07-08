# Formatting Rules

Formatting rules that apply to all plugin component files (SKILL.md, agent files, command files, reference files).

## Contents

- [R7 — No Emoji in Structural Elements](#r7--no-emoji-in-structural-elements)
- [R8 — Multiline Description Syntax](#r8--multiline-description-syntax)
- [R11 — Max Heading Depth (optional, default off)](#r11--max-heading-depth-optional-default-off)
- [R12 — Code Block Language Specifiers (optional, default off)](#r12--code-block-language-specifiers-optional-default-off)
- [R16 — Progressive Disclosure Order (optional, default off)](#r16--progressive-disclosure-order-optional-default-off)
- [R17 — No Bare URLs (SUGGESTED, default on)](#r17--no-bare-urls-suggested-default-on)
- [General Formatting Conventions](#general-formatting-conventions)

---

## R7 — No Emoji in Structural Elements

Emoji must not appear in section headings, frontmatter fields, or procedural step labels.

**Forbidden locations:**
- Section headings: `## 🚀 Quick Start` ❌
- Frontmatter fields: `name: my-skill ✨` ❌
- Numbered step labels: `1. ✅ Locate the skill` ❌
- Bullet point labels used as procedural steps: `- ✅ Step 1: ...` ❌

**Permitted locations:**
- Sample output that the skill produces for users
- Illustrative examples (e.g., showing what a UI looks like)
- Status indicators inside code blocks

**Rationale:** Structural emoji create visual noise, break plain-text processing, and may not render consistently across all Claude surfaces.

## R8 — Multiline Description Syntax

Descriptions over 80 characters must use `>-` YAML block scalar syntax.

```yaml
# Correct — multiline >- syntax
description: >-
  Defines and enforces plugin-level rules governing all components. Use when
  creating, validating, or refining any plugin component.

# Wrong — quoted single line
description: "Defines and enforces plugin-level rules governing all components across the plugin."

# Wrong — unquoted single line (works but visually breaks on long text)
description: Defines and enforces plugin-level rules governing all components in a Claude Code plugin.
```

**Why `>-` specifically:** The `-` strips the trailing newline, producing a clean single-string value. `>` (without `-`) appends a newline, which is usually unwanted in description fields.

## R11 — Max Heading Depth (optional, default off)

When enabled, headings must not exceed depth 3 (`###`).

```markdown
## Section      ✅ depth 2
### Sub-section  ✅ depth 3
#### Sub-sub     ❌ depth 4 — restructure or extract to reference file
```

**When to restructure:** Content needing depth 4+ is usually a candidate for extraction to a dedicated reference file where it can have its own heading hierarchy starting at `##`.

## R12 — Code Block Language Specifiers (optional, default off)

When enabled, all fenced code blocks must declare a language.

```markdown
```yaml        ✅ language declared
```json        ✅ language declared
```bash        ✅ language declared
```markdown    ✅ language declared
```            ❌ no language — add one
```

**Common language identifiers:** `yaml`, `json`, `bash`, `python`, `javascript`, `typescript`, `markdown`, `text`

## R16 — Progressive Disclosure Order (optional, default off)

When enabled, `Quick Start` must appear before detailed workflow or reference sections.

**Required order:**
1. `## Quick Start` (or equivalent first-action section)
2. `## When to Use`
3. `## When NOT to Use`
4. Core workflow sections
5. Advanced / reference sections

**Violation:** A 200-line workflow section appears before `## Quick Start`.

## R17 — No Bare URLs (SUGGESTED, default on)

When enabled, all hyperlinks must use named reference syntax.

```markdown
Named reference (correct):
See the [Claude Code documentation](https://docs.anthropic.com) for details.

Bare URL (wrong):
See https://docs.anthropic.com for details.
```

**Exception:** URLs inside code blocks or as placeholder values in examples are allowed.

## General Formatting Conventions

These apply regardless of settings:

### Lists

Use `-` for unordered lists (not `*` or `+`):
```markdown
- Item one
- Item two
```

### Tables

Always include a separator row and align columns consistently:
```markdown
| Column A | Column B |
|---|---|
| Value 1  | Value 2  |
```

### Code examples

Place code examples before prose explanations (code-first principle). One concrete example beats three paragraphs of description.

### Heading hierarchy

Start body sections at `##` (never `#` — that is reserved for the document title). Use `###` for subsections within a section.
