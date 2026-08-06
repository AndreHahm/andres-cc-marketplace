# Apply Rules Report — Sample Format

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — the complete, authoritative sample report format; trimming risks documenting an incomplete format.

```
# Apply Rules Report

## Source
- https://github.com/org/repo/tree/main/.claude/rules (15 rule files)

## Target Project Detection
- Languages: ruby · Frameworks: rails, rails-controllers · Integrations: rails-devise, rails-pundit

## Applied Rules
| File | Action | Principles |
|------|--------|------------|
| languages/ruby.md | Merged | +3 added, 7 kept |
| frameworks/rails.md | Created | 13 |
| integrations/rails-devise.md | Merged | +1 added |

## Promoted Pattern Cleanup / Preserved
- languages/ruby.local.md: removed 1 pattern (now in Principles); 2 remaining patterns kept

## User-approved Integrations
- integrations/rails-pundit (not detected, approved by user)

## Skipped (not relevant to project)
- languages/typescript.md, frameworks/react.md, integrations/rails-stripe.md

## Structure Cleanup
- frameworks/old-custom.md → rules migrated to frameworks/rails.md → deleted

## Conflicts (resolved by user)
- languages/ruby.md: "Immutability" → user chose: Keep both
```
