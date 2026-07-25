# Output File Formats

## Merged Rule File (.md)

```markdown
---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---
# TypeScript Rules

## Principles

- Immutability (spread, map/filter/reduce, const)
- Type safety (strict mode, explicit annotations, no any)
- Auth hook interface (useAuth)

## Examples
When in doubt: ./typescript.examples.md
```

The `## Examples` reference is only appended when a corresponding `.examples.md` was generated. Output `.md` files contain only `## Principles` — promoted patterns are converted and included there.

## Examples File (.examples.md)

Structure: `# <Category> Rules - Examples` as the file title, then `## Principles Examples` containing `### <Principle name>` subsections each with **Good:** and **Bad:** fenced code blocks.

Rules:
- `###` titles must match the corresponding rule name in the merged `.md` exactly — do not rephrase
- No `paths:` frontmatter (prevents auto-loading)
- Omit the file entirely if no examples exist for any merged rule
