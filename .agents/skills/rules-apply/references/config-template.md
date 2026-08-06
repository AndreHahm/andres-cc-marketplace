# Config File Template

Full annotated format for `.claude/rules-apply.local.md` (or `~/.claude/rules-apply.local.md`).

```yaml
---
# Rules directory: GitHub URL or local path
source: https://github.com/org/repo/tree/main/.claude/rules

# Output directory in target project (default: .claude/rules/)
output_dir: .claude/rules/

# Auto-detect which rules to apply (default: true; false = apply ALL from source)
auto_detect: true

# Explicitly include/exclude rules regardless of auto-detection
include: []   # e.g. [languages/typescript, integrations/rails-inertia]
exclude: []   # e.g. [frameworks/rails-views]

# Report language (default: en)
language: en
---
```

**Alternative source form:** for a branch name containing `/`, or to pin a tag/SHA, specify GitHub source components separately instead of a single `source` URL: `source_repo: org/repo`, `source_ref: feature/rules-v2`, `source_path: .claude/rules`.
