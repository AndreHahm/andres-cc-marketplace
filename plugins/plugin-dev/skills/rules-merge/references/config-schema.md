# Config File Schema

Full annotated format for `.claude/rules-merge.local.md` (or `~/.claude/rules-merge.local.md`).

```yaml
---
# Source projects (each must have rules-extract output)
projects:
  - ~/projects/frontend-app
  - ~/projects/backend-api
  - ~/projects/shared-lib

# Output directory (default: .claude/rules/)
output_dir: .claude/rules/

# Rules directory within each project (default: .claude/rules/)
# Corresponds to rules-extract's output_dir setting
rules_dir: .claude/rules/

# Threshold for promoting .local.md patterns (default: 0.5 = majority)
# Examples: 3 projects → 2/3 needed, 4 projects → 3/4, 5 projects → 3/5
promote_threshold: 0.5

# Report language (default: en)
language: en
---
```
