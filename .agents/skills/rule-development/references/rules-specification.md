# Claude Code Official Rules Documentation

Official Claude Code documentation for `.claude/rules/` directory usage.

## Setup

Place markdown files in your project's `.claude/rules/` directory. Each file should cover one topic, with a descriptive filename like `testing.md` or `api-design.md`. All `.md` files are discovered recursively, so you can organize rules into subdirectories like `frontend/` or `backend/`:

```text
your-project/
├── .claude/
│   ├── CLAUDE.md           # Main project instructions
│   └── rules/
│       ├── code-style.md   # Code style guidelines
│       ├── testing.md      # Testing conventions
│       └── security.md     # Security requirements
```

Rules without `paths` frontmatter are loaded at launch with the same priority as `.claude/CLAUDE.md`.

## Path-Specific Rules

Rules can be scoped to specific files using YAML frontmatter with the `paths` field. These conditional rules only apply when Claude is working with files matching the specified patterns.

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API Development Rules

- All API endpoints must include input validation
- Use the standard error response format
- Include OpenAPI documentation comments
```

Rules without a `paths` field are loaded unconditionally and apply to all files. Rules with a `paths` field load when Claude works with matching files — they trigger when Claude reads a matching file, not on every tool use.

Use glob patterns in the `paths` field to match files by extension, directory, or any combination:

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | All TypeScript files in any directory |
| `src/**/*` | All files under `src/` directory |
| `*.md` | Markdown files in the project root |
| `src/components/*.tsx` | React components in a specific directory |

Prefer the narrowest pattern that covers the intended files. Overly broad patterns match nearly
every file and defeat the purpose of scoping — they add context on every read instead of only when
relevant:

| Pattern | Assessment |
|---------|-----------|
| `src/api/**/*.ts` | Acceptable — scoped to a specific directory and file type |
| `**/*.test.ts` | Acceptable — scoped by file type and naming convention |
| `**/*` | Overly broad — matches everything; no scoping benefit |
| `*` | Overly broad — matches only the project root, rarely intentional |

If a broad pattern is genuinely required, state the justification in the rule's description.

You can specify multiple patterns and use brace expansion:

```markdown
---
paths:
  - "src/**/*.{ts,tsx}"
  - "lib/**/*.ts"
  - "tests/**/*.test.ts"
---
```

## Frontmatter Fields

`paths` is the only frontmatter field with official platform-recognized meaning — it controls
conditional loading as described above. Fields such as `title` and `impact` are internal
plugin-devkit conventions for organizing and prioritizing rules; the platform does not require or
interpret them.

## Rule Content Requirements

Rule bodies must use imperative language — `MUST`, `NEVER` — not passive voice, "try to," or
"consider." Hedged phrasing weakens enforcement and gives the agent room to rationalize
non-compliance.

Rule files must not contain procedural content: numbered steps, multi-step workflows, or
multi-step code blocks. Procedures belong in skills, not rules.

## Rules vs. Skills

A rule states *what* must or must not happen. A skill teaches *how* to perform multi-step work.
Keep this boundary strict: if guidance needs sequential steps to execute, it belongs in a skill,
not a rule.

## Shared Rules via Symlinks

The `.claude/rules/` directory supports symlinks, so you can maintain a shared set of rules and link them into multiple projects. Symlinks are resolved and loaded normally, and circular symlinks are detected and handled gracefully.

```bash
ln -s ~/shared-claude-rules .claude/rules/shared
ln -s ~/company-standards/security.md .claude/rules/security.md
```

## User-Level Rules

Personal rules in `~/.claude/rules/` apply to every project on your machine:

```text
~/.claude/rules/
├── preferences.md    # Your personal coding preferences
└── workflows.md      # Your preferred workflows
```

User-level rules are loaded before project rules, giving project rules higher priority.
