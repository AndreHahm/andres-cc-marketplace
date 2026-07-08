# Apply Rules Report — Sample Format

```
# Apply Rules Report

## Source
- https://github.com/org/repo/tree/main/.claude/rules (15 rule files)

## Target Project Detection
- Languages: ruby
- Frameworks: rails, rails-controllers, rails-models, rails-views
- Integrations: rails-devise, rails-pundit

## Applied Rules
| File | Action | Principles |
|------|--------|------------|
| languages/ruby.md | Merged | +3 added, 7 kept |
| frameworks/rails.md | Created | 13 |
| frameworks/rails-controllers.md | Created | 5 |
| integrations/rails-devise.md | Merged | +1 added |

## Promoted Pattern Cleanup
- languages/ruby.local.md: removed 1 pattern (now in Principles)
- frameworks/rails.local.md: no duplicates found

## Preserved
- languages/ruby.local.md (2 remaining patterns)
- frameworks/rails.local.md (3 patterns, untouched)

## User-approved Integrations
- integrations/rails-pundit (not detected, approved by user)

## Skipped (not relevant to project)
- languages/typescript.md
- frameworks/react.md
- frameworks/nextjs.md
- integrations/rails-stripe.md

## Structure Cleanup
- frameworks/old-custom.md → rules migrated to frameworks/rails.md → deleted

## Conflicts (resolved by user)
- languages/ruby.md: "Immutability" → user chose: Keep both
```
