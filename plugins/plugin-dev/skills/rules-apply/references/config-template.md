# Config File Template

Full annotated format for `.claude/rules-apply.local.md` (or `~/.claude/rules-apply.local.md`).

```yaml
---
# Rules directory (GitHub URL or local path)
# GitHub: https://github.com/org/repo/tree/main/.claude/rules
# Local: ~/org-rules/.claude/rules
source: https://github.com/org/repo/tree/main/.claude/rules

# Alternative: specify GitHub source components separately
# (useful when branch name contains "/" or for tags/SHAs)
# source_repo: org/repo
# source_ref: feature/rules-v2
# source_path: .claude/rules

# Output directory in target project (default: .claude/rules/)
output_dir: .claude/rules/

# Auto-detect which rules to apply (default: true)
# When false, applies ALL rules from source
auto_detect: true

# Explicitly include rules even if not auto-detected
include: []
# Example: [languages/typescript, integrations/rails-inertia]

# Explicitly exclude rules even if auto-detected
exclude: []
# Example: [frameworks/rails-views]

# Report language (default: en)
language: en
---
```
