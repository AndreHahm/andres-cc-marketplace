# Config File Schema

Full annotated format for `.claude/rules-merge.local.md` (or `~/.claude/rules-merge.local.md`).

```yaml
---
# Source projects (each must have rules-extract output)
projects:
  - ~/projects/frontend-app
  - ~/projects/backend-api

output_dir: .claude/rules/          # default
rules_dir: .claude/rules/           # per-project; corresponds to rules-extract's output_dir
promote_threshold: 0.5              # majority needed to promote a .local.md pattern (e.g. 2/3, 3/4)
language: en                        # report language, default
---
```
