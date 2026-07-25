# Language Rules

Language rules apply to all content in plugin component files: SKILL.md, agent files, command files, hook configurations, rule files, and all files in `references/`.

## Contents

- [R1 — English Only (Primary Language)](#r1--english-only-primary-language)
- [R2 — English Primary File Required](#r2--english-primary-file-required)
- [R3 — Optional Multilingual Variants](#r3--optional-multilingual-variants)
- [Checking Language Compliance](#checking-language-compliance)

---

## R1 — English Only (Primary Language)

All frontmatter and body content must be in English.

### What "English only" covers

| Content | Rule |
|---|---|
| Frontmatter `name` field | English (kebab-case identifier) |
| Frontmatter `description` field | English prose |
| Frontmatter `allowed-tools` | English tool names (always) |
| Section headings | English |
| Procedural instructions | English |
| Code comments | English (see exception below) |
| Reference file content | English (for primary `.md` files) |

### Exception: User-facing output strings

Code comments or string literals that represent output shown to end users may use the target locale language when that is explicitly the point of the example. The surrounding instructions and documentation must remain in English.

```bash
# English comment — allowed ✅
echo "Verarbeitungsfortschritt: $percent%" # German output string — allowed in examples ✅
```

### Common violations to fix

- Non-English section headings: `## Schnellstart` → `## Quick Start`
- Non-English descriptions in frontmatter
- Non-English procedural steps or instructions in SKILL.md body
- Reference files written entirely in a non-English language without an English primary

## R2 — English Primary File Required

Every topic in `references/` must have an English file as the primary version.

**Rule:** `references/<topic>.md` must exist before `references/<topic>.<lang>.md` is added.

```
references/
  patterns.md          ✅ English primary — required
  patterns.de.md       ✅ German variant — allowed (R3)
  patterns.zh.md       ✅ Chinese variant — allowed (R3)

references/
  patterns.de.md       ❌ No English primary — R2 violation
```

## R3 — Optional Multilingual Variants

Reference files may be translated into additional languages. Language variants are optional and supplementary.

### Supported Language Codes

Configured in `settings.json → languages.additional`. Defaults:

| Code | Language |
|---|---|
| `de` | German |
| `zh` | Chinese (Simplified) |
| `fr` | French |
| `es` | Spanish |
| `ja` | Japanese |
| `pt` | Portuguese |

To add a language: append its BCP-47 code to `settings.json → languages.additional`.

### Naming Pattern

```
references/<topic>.<lang-code>.md
```

Examples:
- `references/naming-conventions.de.md` — German version of naming-conventions
- `references/formatting-rules.zh.md` — Chinese version of formatting-rules
- `references/language-rules.fr.md` — French version of language-rules

### Content Parity Requirement

Language variants must cover the same topics as the English primary. They may omit English-specific examples (e.g., English-language anti-pattern names) but must not introduce new rules or contradict the English version.

**English is authoritative.** When a variant conflicts with the English primary, the English version wins.

### When to Add Variants

Add a language variant when:
- The plugin is used by teams who work primarily in that language
- The `languages.additional` list in `settings.json` includes that language code
- An English primary already exists for the topic (R2 must be satisfied first)

Do not add variants for:
- Config files (`settings.json`, `plugin.json`) — always English
- SKILL.md body — always English (R1)
- Agent and command files — always English (R1)
- Scripts and code — always English (R1)

## Checking Language Compliance

When running an R1 check:
1. Read all frontmatter fields — flag any non-English content
2. Read all section headings — flag non-English headings
3. Read procedural steps — flag non-English instructions
4. Spot-check body prose — flag non-English paragraphs

When running an R2 check:
1. List all files matching `references/*.*.md` (variant pattern)
2. For each variant `references/<topic>.<lang>.md`, verify `references/<topic>.md` exists
3. Report any missing English primaries as REQUIRED violations
