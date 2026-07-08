# Output Structure Reference

## Contents

- Configuration YAML
- Configuration Details
- Default Output (`split_output: true`)
- Hybrid Output (`split_output: false`)
- Integration Libraries Example (split mode)
- Rule File Format

## Configuration YAML

Full YAML example with all settings and their defaults:

```yaml
---
target_dirs:
  - .
exclude_dirs:
  - .git
  - .claude
exclude_patterns:
  - "*.generated.ts"
output_dir: .claude/rules
examples_output_dir: .claude/rules-extras
staging_output_dir: .claude/rules-staging
language: ja
split_output: true
resolve_references: true
compaction_threshold: 40000
min_cluster_size: 3
---
```

## Configuration Details

**`staging_output_dir`**: Project-level patterns observed for the first time are written to `staging_output_dir` (staged candidates). A second observation in a later incremental run (`--from-conversation`, `--from-pr`, or `--update`) promotes the entry to canonical (`<output_dir>/project.md`) and removes it from staging. Language / framework / integration patterns bypass staging entirely and land directly in their respective files. Defaults to `.claude/rules-staging` — outside `.claude/rules/**` auto-load scope so staged candidates don't consume context. Set to `output_dir` to opt staging into auto-load.

**`compaction_threshold`**: Files with a char count above this value are compacted in `--compact` mode. The default `40000` matches Claude Code's per-file warning threshold (40k chars) — firing the gate at the warning matches the user's visible signal that the file needs attention. To opt out of compaction entirely, set to a very large number (e.g. `99999999`). To use a preventive trigger before the warning fires (e.g. 80% buffer), set `compaction_threshold: 32000`.

**`min_cluster_size`**: Consolidation detection in `--compact` mode emits `consolidation_proposals` only when a related-bullet cluster meets this minimum count (`≥ min_cluster_size`). To disable consolidation while keeping compaction, set to a very large number (e.g. `99999999`) — the same opt-out sentinel convention as `compaction_threshold`.

## Default Output (`split_output: true`)

```text
.claude/rules/                     # output_dir (inside auto-load scope)
├── languages/
│   ├── typescript.md              # Principles only (portable)
│   └── typescript.local.md        # Project-specific patterns only
├── frameworks/
│   ├── react.md                   # Principles only (portable)
│   └── react.local.md             # Project-specific patterns only
└── project.md                     # Always single file (no split)

.claude/rules-extras/              # examples_output_dir (outside auto-load scope)
├── languages/
│   └── typescript.examples.md     # Examples for both
├── frameworks/
│   └── react.examples.md          # Examples for both
└── project.examples.md            # Examples

.claude/rules-staging/             # staging_output_dir (outside auto-load scope)
└── project.staging.local.md       # 1st-observation candidates (incremental modes only)
```

Staging holds project-level 1-shot pattern candidates written by a single `--from-conversation` / `--from-pr` invocation; the next incremental run promotes a re-observed candidate to canonical and removes it from staging.

Principles (portable across projects) and Project-specific patterns (local) are separated by default, enabling organizational rule sharing and AI-driven merge across projects.

## Hybrid Output (`split_output: false`)

```text
.claude/rules/                     # output_dir (inside auto-load scope)
├── languages/
│   └── typescript.md              # Principles + Project-specific patterns
├── frameworks/
│   └── react.md                   # Principles + Project-specific patterns
└── project.md                     # Domain, architecture, conventions

.claude/rules-extras/              # examples_output_dir (outside auto-load scope)
├── languages/
│   └── typescript.examples.md     # Examples
├── frameworks/
│   └── react.examples.md          # Examples
└── project.examples.md            # Examples

.claude/rules-staging/             # staging_output_dir (outside auto-load scope)
└── project.staging.local.md       # 1st-observation candidates (incremental modes only)
```

## Integration Libraries Example (split mode)

Example output when integration libraries (Inertia, Pundit, Devise, Turbo, etc.) are detected alongside a layered framework. Each category also gets a `.examples.md` under `examples_output_dir`.

```text
.claude/rules/                     # output_dir
├── languages/
│   └── ruby.md / ruby.local.md
├── frameworks/
│   ├── rails.md / rails.local.md
│   ├── rails-controllers.md / .local.md
│   └── rails-models.md / .local.md
├── integrations/
│   ├── rails-inertia.md / .local.md
│   └── rails-pundit.md / .local.md
└── project.md

.claude/rules-extras/              # examples_output_dir
├── languages/
│   └── ruby.examples.md
├── frameworks/
│   ├── rails.examples.md
│   ├── rails-controllers.examples.md
│   └── rails-models.examples.md
├── integrations/
│   ├── rails-inertia.examples.md
│   └── rails-pundit.examples.md
└── project.examples.md
```

## Rule File Format

Hybrid rule file example (in split mode: only `## Principles` goes in `.md`, only `## Project-specific patterns` goes in `.local.md`):

```markdown
---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---
# TypeScript Rules

## Principles

- FP only (no classes, pure functions, composition over inheritance)
- Strict null handling (no non-null assertions, explicit narrowing required)
- Barrel exports required (re-export from index.ts per directory)

## Project-specific patterns

- `RefOrNull<T extends { id: string }> = T | { id: null }` - nullable relationships
- `pathFor(page) + url()` - Page Object navigation pair
- `useAuthClient()` returns `{ user, login, logout }` - auth hook interface

## Examples

When in doubt: ../../rules-extras/languages/typescript.examples.md
```

Path assumes defaults: `output_dir: .claude/rules`, `examples_output_dir: .claude/rules-extras`. See `references/examples-format.md` § Reference Section in Rule Files for relative-path computation under non-default settings.
